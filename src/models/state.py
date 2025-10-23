"""LangGraph state schema for the financial agent workflow."""

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict

from .schemas import (
    CandidateValue,
    DocumentMetadata,
    FinancialMetric,
    Section,
    TableBlock,
    TextBlock,
    ValidationResult,
)


class AgentState(TypedDict, total=False):
    """
    State schema for the LangGraph workflow.
    
    This maintains all intermediate and final outputs throughout
    the multi-stage financial document processing pipeline.
    """
    
    # Input and Document Metadata
    document_metadata: Optional[DocumentMetadata]
    raw_pdf_path: str
    
    # Parsing Results
    text_blocks: List[TextBlock]
    table_blocks: List[TableBlock]
    
    # Section Location
    sections: List[Section]
    
    # Table Extraction
    extracted_tables: List[Dict[str, Any]]
    
    # Metric Extraction and Normalization
    raw_metrics: List[Dict[str, Any]]
    normalized_metrics: List[FinancialMetric]
    
    # Candidate Generation
    candidates: Dict[str, List[CandidateValue]]  # metric_id -> list of candidates
    
    # Validation
    validation_results: List[ValidationResult]
    has_conflicts: bool
    
    # Adjudication
    adjudication_results: Dict[str, Any]
    
    # Final Validated Metrics
    validated_metrics: List[FinancialMetric]
    
    # Derived Metrics
    derived_metrics: List[FinancialMetric]
    
    # Commentary and Analysis
    commentary: Dict[str, str]
    
    # Recent Developments Summary
    recent_developments: str
    
    # Export
    export_paths: Dict[str, str]
    
    # Error Handling
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    
    # Provenance and Audit Trail
    provenance: List[Dict[str, Any]]
    
    # Processing Metadata
    processing_start_time: Optional[str]
    processing_end_time: Optional[str]
    node_execution_times: Dict[str, float]


class WorkflowConfig(TypedDict, total=False):
    """Configuration for workflow execution."""
    
    enable_adjudication: bool
    enable_commentary: bool
    enable_rag_summary: bool
    parallel_processing: bool
    max_retries: int
    timeout_seconds: int
