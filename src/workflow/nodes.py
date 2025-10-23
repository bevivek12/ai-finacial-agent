"""
LangGraph node implementations for the financial agent workflow.

Each node function:
1. Receives the current state
2. Performs its specific processing task
3. Updates and returns the modified state
4. Logs execution details
5. Handles errors gracefully
"""

import time
from datetime import datetime
from typing import Any, Dict

from ..models.state import AgentState
from ..utils.logger import get_logger

logger = get_logger({"module": "workflow_nodes"})


def ingest_pdf_node(state: AgentState) -> AgentState:
    """
    Node: PDF Ingestion
    
    Validates PDF, extracts metadata, and classifies document type.
    
    TODO: Implement using src/services/ingestion.py when created
    """
    start_time = time.time()
    logger.info("node_started", node="ingest_pdf")
    
    try:
        pdf_path = state["raw_pdf_path"]
        
        # TODO: Implement actual ingestion logic
        # from ..services.ingestion import PDFIngestionService
        # ingestion_service = PDFIngestionService()
        # metadata = ingestion_service.ingest(pdf_path)
        
        # Placeholder implementation
        from ..models.schemas import DocumentMetadata, ReportType
        from datetime import date
        
        metadata = DocumentMetadata(
            document_id=f"doc_{int(time.time())}",
            company_name="Example Company",
            report_type=ReportType.ANNUAL,
            fiscal_period_end=date(2023, 12, 31),
            source_path=pdf_path
        )
        
        state["document_metadata"] = metadata
        
        execution_time = time.time() - start_time
        state.setdefault("node_execution_times", {})["ingest_pdf"] = execution_time
        
        logger.info("node_completed", node="ingest_pdf", execution_time=execution_time)
        
    except Exception as e:
        logger.error("node_failed", node="ingest_pdf", error=str(e))
        state.setdefault("errors", []).append({
            "node": "ingest_pdf",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return state


def parse_blockify_node(state: AgentState) -> AgentState:
    """
    Node: Parse and Blockify
    
    Extracts text and table blocks from PDF using multi-parser strategy.
    
    TODO: Implement using src/services/blockification.py when created
    """
    start_time = time.time()
    logger.info("node_started", node="parse_blockify")
    
    try:
        pdf_path = state["raw_pdf_path"]
        
        # TODO: Implement actual parsing logic
        # from ..services.blockification import BlockificationService
        # blockify_service = BlockificationService()
        # text_blocks, table_blocks = blockify_service.parse(pdf_path)
        
        # Placeholder implementation
        state["text_blocks"] = []
        state["table_blocks"] = []
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["parse_blockify"] = execution_time
        
        logger.info("node_completed", node="parse_blockify", execution_time=execution_time)
        
    except Exception as e:
        logger.error("node_failed", node="parse_blockify", error=str(e))
        state.setdefault("errors", []).append({
            "node": "parse_blockify",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return state


def locate_sections_node(state: AgentState) -> AgentState:
    """
    Node: Locate Sections
    
    Identifies financial statement sections using hybrid regex + embedding approach.
    
    TODO: Implement using src/services/section_locator.py when created
    """
    start_time = time.time()
    logger.info("node_started", node="locate_sections")
    
    try:
        # TODO: Implement section location logic
        state["sections"] = []
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["locate_sections"] = execution_time
        
        logger.info("node_completed", node="locate_sections", execution_time=execution_time)
        
    except Exception as e:
        logger.error("node_failed", node="locate_sections", error=str(e))
        state.setdefault("errors", []).append({
            "node": "locate_sections",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return state


def extract_tables_node(state: AgentState) -> AgentState:
    """Node: Extract Tables - TODO: Implement"""
    start_time = time.time()
    logger.info("node_started", node="extract_tables")
    
    try:
        state["extracted_tables"] = []
        execution_time = time.time() - start_time
        state["node_execution_times"]["extract_tables"] = execution_time
        logger.info("node_completed", node="extract_tables", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="extract_tables", error=str(e))
        state.setdefault("errors", []).append({"node": "extract_tables", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
    
    return state


def normalize_metrics_node(state: AgentState) -> AgentState:
    """Node: Normalize Metrics - Normalize currency, scale, labels, and periods"""
    start_time = time.time()
    logger.info("node_started", node="normalize_metrics")
    
    try:
        from ..services.metric_normalizer import MetricNormalizerService
        
        # Get candidates from state
        candidates = state.get("candidates", [])
        
        if candidates:
            # Initialize normalizer
            normalizer = MetricNormalizerService(
                base_currency="GBP",
                base_scale="millions"
            )
            
            # Convert candidates to metrics for normalization
            from ..models.schemas import FinancialMetric
            temp_metrics = [
                FinancialMetric(
                    metric_id=c.candidate_id,
                    metric_name=c.metric_name,
                    value=c.value,
                    currency=c.currency,
                    scale=c.scale,
                    period_end_date=c.period_end_date
                )
                for c in candidates
            ]
            
            # Normalize metrics
            normalized = normalizer.normalize_metrics(temp_metrics)
            state["normalized_metrics"] = normalized
            
            logger.info("metrics_normalized", count=len(normalized))
        else:
            state["normalized_metrics"] = []
            logger.warning("no_candidates_to_normalize")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["normalize_metrics"] = execution_time
        logger.info("node_completed", node="normalize_metrics", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="normalize_metrics", error=str(e))
        state.setdefault("errors", []).append({"node": "normalize_metrics", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["normalized_metrics"] = []
    
    return state


def generate_candidates_node(state: AgentState) -> AgentState:
    """Node: Generate Candidates - Extract candidate values from tables and text"""
    start_time = time.time()
    logger.info("node_started", node="generate_candidates")
    
    try:
        from ..services.candidate_generator import CandidateGenerator
        
        sections = state.get("sections", [])
        table_blocks = state.get("table_blocks", [])
        text_blocks = state.get("text_blocks", [])
        
        if sections and (table_blocks or text_blocks):
            # Initialize candidate generator
            generator = CandidateGenerator()
            
            # Generate candidates
            candidates = generator.generate_candidates(
                sections=sections,
                table_blocks=table_blocks,
                text_blocks=text_blocks
            )
            
            state["candidates"] = candidates
            logger.info("candidates_generated", count=len(candidates))
        else:
            state["candidates"] = []
            logger.warning("insufficient_data_for_candidate_generation")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["generate_candidates"] = execution_time
        logger.info("node_completed", node="generate_candidates", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="generate_candidates", error=str(e))
        state.setdefault("errors", []).append({"node": "generate_candidates", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["candidates"] = []
    
    return state


def validate_deterministic_node(state: AgentState) -> AgentState:
    """Node: Deterministic Validation - Apply rule-based validation"""
    start_time = time.time()
    logger.info("node_started", node="validate_deterministic")
    
    try:
        from ..services.validators import DeterministicValidator, ValidationAggregator
        from ..models.schemas import ValidationStatus
        
        candidates = state.get("candidates", [])
        
        if candidates:
            # Initialize validator
            validator = DeterministicValidator()
            aggregator = ValidationAggregator()
            
            # Validate candidates
            validation_results = validator.validate_candidates(candidates)
            state["validation_results"] = validation_results
            
            # Aggregate results
            summary = aggregator.aggregate_results(validation_results)
            
            # Determine if adjudication needed
            needs_adjudication = aggregator.get_candidates_needing_adjudication(validation_results)
            state["has_conflicts"] = len(needs_adjudication) > 0
            
            logger.info(
                "validation_completed",
                total=summary["total_validated"],
                valid=summary["status_counts"]["valid"],
                needs_adjudication=len(needs_adjudication)
            )
        else:
            state["validation_results"] = []
            state["has_conflicts"] = False
            logger.warning("no_candidates_to_validate")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["validate_deterministic"] = execution_time
        logger.info("node_completed", node="validate_deterministic", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="validate_deterministic", error=str(e))
        state.setdefault("errors", []).append({"node": "validate_deterministic", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
    
    return state


def adjudicate_llm_node(state: AgentState) -> AgentState:
    """Node: LLM Adjudication - Resolve conflicts using LLM"""
    start_time = time.time()
    logger.info("node_started", node="adjudicate_llm")
    
    try:
        from ..services.llm_adjudicator import LLMAdjudicator
        import os
        
        candidates = state.get("candidates", [])
        validation_results = state.get("validation_results", [])
        
        if candidates and validation_results:
            # Initialize LLM adjudicator
            llm_client = None
            
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from openai import OpenAI
                    llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                except ImportError:
                    logger.warning("openai_not_installed_using_fallback")
            
            adjudicator = LLMAdjudicator(llm_client=llm_client)
            
            # Adjudicate candidates
            validated_metrics = adjudicator.adjudicate_candidates(
                candidates=candidates,
                validation_results=validation_results
            )
            
            state["validated_metrics"] = validated_metrics
            logger.info("adjudication_completed", metrics_count=len(validated_metrics))
        else:
            state["validated_metrics"] = []
            logger.warning("no_data_for_adjudication")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["adjudicate_llm"] = execution_time
        logger.info("node_completed", node="adjudicate_llm", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="adjudicate_llm", error=str(e))
        state.setdefault("errors", []).append({"node": "adjudicate_llm", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["validated_metrics"] = []
    
    return state


def compute_derived_node(state: AgentState) -> AgentState:
    """Node: Compute Derived Metrics - Calculate ratios and growth rates"""
    start_time = time.time()
    logger.info("node_started", node="compute_derived")
    
    try:
        from ..analysis.derived_metrics import DerivedMetricsComputer
        
        validated_metrics = state.get("validated_metrics", [])
        
        if validated_metrics:
            # Initialize derived metrics computer
            computer = DerivedMetricsComputer()
            
            # Compute all derived metrics
            derived_metrics = computer.compute_all_metrics(validated_metrics)
            
            state["derived_metrics"] = derived_metrics
            logger.info("derived_metrics_computed", count=len(derived_metrics))
        else:
            state["derived_metrics"] = []
            logger.warning("no_validated_metrics_for_derivation")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["compute_derived"] = execution_time
        logger.info("node_completed", node="compute_derived", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="compute_derived", error=str(e))
        state.setdefault("errors", []).append({"node": "compute_derived", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["derived_metrics"] = []
    
    return state


def generate_commentary_node(state: AgentState) -> AgentState:
    """Node: Generate Commentary - Create financial narrative commentary"""
    start_time = time.time()
    logger.info("node_started", node="generate_commentary")
    
    try:
        from ..services.commentary_generator import FinancialCommentaryGenerator
        import os
        
        validated_metrics = state.get("validated_metrics", [])
        derived_metrics = state.get("derived_metrics", [])
        
        if validated_metrics:
            # Initialize commentary generator
            llm_client = None
            
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from openai import OpenAI
                    llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                except ImportError:
                    logger.warning("openai_not_installed_using_fallback_commentary")
            
            generator = FinancialCommentaryGenerator(llm_client=llm_client)
            
            # Generate full commentary
            commentary = generator.generate_full_commentary(
                metrics=validated_metrics,
                derived_metrics=derived_metrics
            )
            
            state["commentary"] = commentary
            logger.info("commentary_generated", sections=len(commentary))
        else:
            state["commentary"] = {}
            logger.warning("no_metrics_for_commentary")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["generate_commentary"] = execution_time
        logger.info("node_completed", node="generate_commentary", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="generate_commentary", error=str(e))
        state.setdefault("errors", []).append({"node": "generate_commentary", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["commentary"] = {}
    
    return state


def summarize_news_node(state: AgentState) -> AgentState:
    """Node: Summarize News - TODO: Implement"""
    start_time = time.time()
    logger.info("node_started", node="summarize_news")
    
    try:
        state["recent_developments"] = ""
        execution_time = time.time() - start_time
        state["node_execution_times"]["summarize_news"] = execution_time
        logger.info("node_completed", node="summarize_news", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="summarize_news", error=str(e))
        state.setdefault("errors", []).append({"node": "summarize_news", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
    
    return state


def export_results_node(state: AgentState) -> AgentState:
    """Node: Export Results - Generate Word, Excel, and JSON reports"""
    start_time = time.time()
    logger.info("node_started", node="export_results")
    
    try:
        from ..export.export_service import ExportService
        
        metadata = state.get("document_metadata")
        validated_metrics = state.get("validated_metrics", [])
        derived_metrics = state.get("derived_metrics", [])
        commentary = state.get("commentary", {})
        
        if metadata and validated_metrics:
            # Initialize export service
            output_dir = state.get("output_dir", "./output")
            export_service = ExportService(output_dir=output_dir)
            
            # Export to all formats
            output_paths = export_service.export_all(
                company_name=metadata.company_name,
                report_period=metadata.fiscal_period_end,
                metrics=validated_metrics,
                derived_metrics=derived_metrics,
                commentary=commentary,
                formats=["word", "excel", "json"]
            )
            
            state["export_paths"] = output_paths
            logger.info("exports_created", formats=list(output_paths.keys()))
        else:
            state["export_paths"] = {}
            logger.warning("insufficient_data_for_export")
        
        execution_time = time.time() - start_time
        state["node_execution_times"]["export_results"] = execution_time
        logger.info("node_completed", node="export_results", execution_time=execution_time)
    except Exception as e:
        logger.error("node_failed", node="export_results", error=str(e))
        state.setdefault("errors", []).append({"node": "export_results", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
        state["export_paths"] = {}
    
    return state


def error_handler_node(state: AgentState) -> AgentState:
    """Node: Error Handler - TODO: Implement"""
    logger.error("error_handler_invoked", errors=state.get("errors", []))
    return state
