"""Data models for the AI Financial Agent."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ReportType(str, Enum):
    """Type of financial report."""
    ANNUAL = "annual"
    HALF_YEAR = "half_year"
    QUARTERLY = "quarterly"
    RNS = "rns"


class DocumentMetadata(BaseModel):
    """Metadata for financial documents."""
    
    document_id: str = Field(..., description="Unique identifier for the document")
    company_name: str = Field(..., description="Name of the company")
    company_identifier: Optional[str] = Field(None, description="Ticker or registry number")
    report_type: ReportType = Field(..., description="Type of report")
    fiscal_period_end: date = Field(..., description="Reporting period end date")
    currency: str = Field(default="GBP", description="Primary reporting currency")
    filing_date: Optional[date] = Field(None, description="Document publication date")
    source_path: str = Field(..., description="Original file location")
    page_count: Optional[int] = Field(None, description="Number of pages in document")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Metadata creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_12345",
                "company_name": "Example plc",
                "company_identifier": "EXM.L",
                "report_type": "annual",
                "fiscal_period_end": "2023-12-31",
                "currency": "GBP",
                "filing_date": "2024-02-15",
                "source_path": "/data/sample_pdfs/example_plc_annual_2023.pdf"
            }
        }


class EntityType(str, Enum):
    """Type of financial entity."""
    CONSOLIDATED = "consolidated"
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"


class ExtractionMethod(str, Enum):
    """Method used to extract metric."""
    TABLE = "table"
    TEXT = "text"
    CALCULATED = "calculated"


class FinancialMetric(BaseModel):
    """Financial metric with complete metadata."""
    
    metric_id: str = Field(..., description="Canonical metric identifier")
    metric_name: str = Field(..., description="Display name of the metric")
    value: Decimal = Field(..., description="Numeric amount")
    currency: str = Field(..., description="Currency code (e.g., GBP, USD)")
    scale: str = Field(default="millions", description="Scale: actual, thousands, millions, billions")
    period_end_date: date = Field(..., description="Reporting period end date")
    entity_type: EntityType = Field(default=EntityType.CONSOLIDATED, description="Entity type")
    source_page: Optional[int] = Field(None, description="Page number in PDF")
    source_section: Optional[str] = Field(None, description="Section name")
    extraction_method: ExtractionMethod = Field(..., description="How the metric was extracted")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence")
    notes: Optional[str] = Field(None, description="Additional notes or context")
    
    @field_validator("value", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert value to Decimal."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    def to_base_units(self) -> Decimal:
        """Convert value to base units (actual)."""
        scale_multipliers = {
            "actual": 1,
            "thousands": 1000,
            "millions": 1000000,
            "billions": 1000000000
        }
        multiplier = scale_multipliers.get(self.scale.lower(), 1)
        return self.value * Decimal(str(multiplier))
    
    class Config:
        json_schema_extra = {
            "example": {
                "metric_id": "revenue_2023",
                "metric_name": "Revenue",
                "value": "1250.5",
                "currency": "GBP",
                "scale": "millions",
                "period_end_date": "2023-12-31",
                "entity_type": "consolidated",
                "source_page": 15,
                "source_section": "Income Statement",
                "extraction_method": "table"
            }
        }


class CandidateValue(BaseModel):
    """Candidate value for a metric with evidence."""
    
    candidate_id: str = Field(..., description="Unique candidate identifier")
    metric_id: str = Field(..., description="Associated metric identifier")
    value: Decimal = Field(..., description="Proposed value")
    currency: str = Field(..., description="Currency code")
    scale: str = Field(default="millions", description="Scale of the value")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    source_reference: str = Field(..., description="Location in document")
    justification: str = Field(..., description="Extraction reasoning")
    supporting_evidence: str = Field(..., description="Text snippet or table cell content")
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When extracted")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("value", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert value to Decimal."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "cand_rev_001",
                "metric_id": "revenue_2023",
                "value": "1250.5",
                "currency": "GBP",
                "scale": "millions",
                "confidence_score": 0.95,
                "source_reference": "Income Statement, Page 15, Row 1",
                "justification": "Primary revenue line before deductions",
                "supporting_evidence": "Revenue for year: £1,250.5m"
            }
        }


class ValidationStatus(str, Enum):
    """Status of validation."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class ValidationSeverity(str, Enum):
    """Severity of validation result."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ValidationResult(BaseModel):
    """Result of validation for a candidate."""
    
    candidate_id: str = Field(..., description="Candidate being validated")
    rule_name: str = Field(..., description="Validation rule applied")
    result: ValidationStatus = Field(..., description="Pass, fail, or warning")
    message: str = Field(..., description="Explanation of result")
    severity: ValidationSeverity = Field(..., description="Severity level")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "cand_rev_001",
                "rule_name": "unit_consistency",
                "result": "pass",
                "message": "Units are consistent across all candidates",
                "severity": "minor"
            }
        }


class TextBlock(BaseModel):
    """Parsed text block from PDF."""
    
    block_id: str = Field(..., description="Unique block identifier")
    text: str = Field(..., description="Text content")
    page_number: int = Field(..., description="Page number")
    block_type: str = Field(default="body", description="Type: heading, body, table, footnote")
    bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates [x0, y0, x1, y1]")
    font_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Font information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "block_id": "block_001",
                "text": "Income Statement for the year ended 31 December 2023",
                "page_number": 15,
                "block_type": "heading",
                "bbox": [72.0, 720.0, 540.0, 740.0]
            }
        }


class TableBlock(BaseModel):
    """Extracted table from PDF."""
    
    table_id: str = Field(..., description="Unique table identifier")
    page_number: int = Field(..., description="Page number")
    headers: List[List[str]] = Field(..., description="Table headers (can be multi-level)")
    data: List[List[Any]] = Field(..., description="Table data rows")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Table metadata")
    bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates")
    
    class Config:
        json_schema_extra = {
            "example": {
                "table_id": "table_001",
                "page_number": 15,
                "headers": [["", "2023", "2022"], ["", "£m", "£m"]],
                "data": [["Revenue", "1250.5", "1100.2"], ["Operating Profit", "320.1", "280.5"]],
                "metadata": {"currency": "GBP", "scale": "millions"}
            }
        }


class Section(BaseModel):
    """Financial statement section."""
    
    section_id: str = Field(..., description="Unique section identifier")
    section_type: str = Field(..., description="Type: income_statement, cash_flow, balance_sheet, notes")
    section_name: str = Field(..., description="Display name")
    start_page: int = Field(..., description="Starting page number")
    end_page: int = Field(..., description="Ending page number")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    detection_method: str = Field(..., description="Detection method: regex, embedding, hybrid")
    
    class Config:
        json_schema_extra = {
            "example": {
                "section_id": "sec_001",
                "section_type": "income_statement",
                "section_name": "Consolidated Income Statement",
                "start_page": 15,
                "end_page": 17,
                "confidence_score": 0.95,
                "detection_method": "regex"
            }
        }
