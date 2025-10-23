"""LangGraph workflow graph construction for the financial agent."""

from langgraph.graph import END, StateGraph

from ..models.state import AgentState
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger({"module": "workflow_graph"})


def create_financial_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph workflow for financial document processing.
    
    Returns:
        Configured StateGraph ready for execution
    """
    config = get_config()
    logger.info("creating_financial_agent_graph")
    
    # Initialize the state graph
    workflow = StateGraph(AgentState)
    
    # Import node functions (to be implemented)
    from .nodes import (
        ingest_pdf_node,
        parse_blockify_node,
        locate_sections_node,
        extract_tables_node,
        normalize_metrics_node,
        generate_candidates_node,
        validate_deterministic_node,
        adjudicate_llm_node,
        compute_derived_node,
        generate_commentary_node,
        summarize_news_node,
        export_results_node,
        error_handler_node,
    )
    
    from .conditions import should_adjudicate
    
    # Add all nodes to the graph
    workflow.add_node("ingest_pdf", ingest_pdf_node)
    workflow.add_node("parse_blockify", parse_blockify_node)
    workflow.add_node("locate_sections", locate_sections_node)
    workflow.add_node("extract_tables", extract_tables_node)
    workflow.add_node("normalize_metrics", normalize_metrics_node)
    workflow.add_node("generate_candidates", generate_candidates_node)
    workflow.add_node("validate_deterministic", validate_deterministic_node)
    workflow.add_node("adjudicate_llm", adjudicate_llm_node)
    workflow.add_node("compute_derived", compute_derived_node)
    workflow.add_node("generate_commentary", generate_commentary_node)
    workflow.add_node("summarize_news", summarize_news_node)
    workflow.add_node("export_results", export_results_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # Set entry point
    workflow.set_entry_point("ingest_pdf")
    
    # Add edges for the main processing flow
    workflow.add_edge("ingest_pdf", "parse_blockify")
    workflow.add_edge("parse_blockify", "locate_sections")
    workflow.add_edge("locate_sections", "extract_tables")
    workflow.add_edge("extract_tables", "normalize_metrics")
    workflow.add_edge("normalize_metrics", "generate_candidates")
    workflow.add_edge("generate_candidates", "validate_deterministic")
    
    # Conditional edge for adjudication
    workflow.add_conditional_edges(
        "validate_deterministic",
        should_adjudicate,
        {
            "adjudicate": "adjudicate_llm",
            "skip": "compute_derived"
        }
    )
    
    # Continue after adjudication
    workflow.add_edge("adjudicate_llm", "compute_derived")
    workflow.add_edge("compute_derived", "generate_commentary")
    workflow.add_edge("generate_commentary", "summarize_news")
    workflow.add_edge("summarize_news", "export_results")
    
    # Set finish point
    workflow.add_edge("export_results", END)
    
    # Compile the graph
    app = workflow.compile()
    
    logger.info("financial_agent_graph_created")
    
    return app


def run_financial_agent(pdf_path: str, output_dir: str = "./output") -> dict:
    """
    Run the financial agent workflow on a PDF document.
    
    Args:
        pdf_path: Path to the PDF financial report
        output_dir: Directory for output files
        
    Returns:
        Final state dictionary with all results
    """
    logger.info("running_financial_agent", pdf_path=pdf_path)
    
    # Create the graph
    app = create_financial_agent_graph()
    
    # Initialize state
    initial_state = {
        "raw_pdf_path": pdf_path,
        "errors": [],
        "warnings": [],
        "provenance": [],
        "node_execution_times": {},
    }
    
    try:
        # Run the workflow
        final_state = app.invoke(initial_state)
        
        logger.info(
            "workflow_completed_successfully",
            pdf_path=pdf_path,
            export_paths=final_state.get("export_paths", {})
        )
        
        return final_state
        
    except Exception as e:
        logger.error("workflow_execution_failed", error=str(e), pdf_path=pdf_path)
        raise


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.workflow.graph <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = run_financial_agent(pdf_path)
    
    print("\n" + "=" * 60)
    print("Workflow Execution Complete")
    print("=" * 60)
    print(f"\nValidated Metrics: {len(result.get('validated_metrics', []))}")
    print(f"Derived Metrics: {len(result.get('derived_metrics', []))}")
    print(f"Export Paths: {result.get('export_paths', {})}")
    print(f"Errors: {len(result.get('errors', []))}")
    print(f"Warnings: {len(result.get('warnings', []))}")
