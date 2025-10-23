"""Unit tests for data models."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.models.schemas import (
    DocumentMetadata,
    FinancialMetric,
    CandidateValue,
    ValidationResult,
    ReportType,
    EntityType,
    ExtractionMethod,
    ValidationStatus,
    ValidationSeverity,
)


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""
    
    def test_create_valid_metadata(self):
        """Test creating valid document metadata."""
        metadata = DocumentMetadata(
            document_id="test_001",
            company_name="Test Company",
            report_type=ReportType.ANNUAL,
            fiscal_period_end=date(2023, 12, 31),
            source_path="/path/to/report.pdf"
        )
        
        assert metadata.document_id == "test_001"
        assert metadata.company_name == "Test Company"
        assert metadata.report_type == ReportType.ANNUAL
        assert metadata.currency == "GBP"  # default value
    
    def test_metadata_with_all_fields(self):
        """Test metadata with all optional fields."""
        metadata = DocumentMetadata(
            document_id="test_002",
            company_name="Example plc",
            company_identifier="EXM.L",
            report_type=ReportType.HALF_YEAR,
            fiscal_period_end=date(2024, 6, 30),
            currency="USD",
            filing_date=date(2024, 8, 15),
            source_path="/reports/example_h1_2024.pdf",
            page_count=150,
            file_size_bytes=5242880
        )
        
        assert metadata.company_identifier == "EXM.L"
        assert metadata.currency == "USD"
        assert metadata.page_count == 150


class TestFinancialMetric:
    """Tests for FinancialMetric model."""
    
    def test_create_valid_metric(self):
        """Test creating valid financial metric."""
        metric = FinancialMetric(
            metric_id="revenue_2023",
            metric_name="Revenue",
            value=Decimal("1250.5"),
            currency="GBP",
            period_end_date=date(2023, 12, 31),
            extraction_method=ExtractionMethod.TABLE
        )
        
        assert metric.metric_id == "revenue_2023"
        assert metric.value == Decimal("1250.5")
        assert metric.scale == "millions"  # default
    
    def test_value_conversion_from_float(self):
        """Test automatic conversion of float to Decimal."""
        metric = FinancialMetric(
            metric_id="test",
            metric_name="Test Metric",
            value=1250.5,  # float input
            currency="GBP",
            period_end_date=date(2023, 12, 31),
            extraction_method=ExtractionMethod.TABLE
        )
        
        assert isinstance(metric.value, Decimal)
        assert metric.value == Decimal("1250.5")
    
    def test_to_base_units_millions(self):
        """Test conversion to base units from millions."""
        metric = FinancialMetric(
            metric_id="test",
            metric_name="Test",
            value=Decimal("100"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31),
            extraction_method=ExtractionMethod.TABLE
        )
        
        base_value = metric.to_base_units()
        assert base_value == Decimal("100000000")
    
    def test_to_base_units_thousands(self):
        """Test conversion to base units from thousands."""
        metric = FinancialMetric(
            metric_id="test",
            metric_name="Test",
            value=Decimal("100"),
            currency="GBP",
            scale="thousands",
            period_end_date=date(2023, 12, 31),
            extraction_method=ExtractionMethod.TABLE
        )
        
        base_value = metric.to_base_units()
        assert base_value == Decimal("100000")


class TestCandidateValue:
    """Tests for CandidateValue model."""
    
    def test_create_candidate(self):
        """Test creating candidate value."""
        candidate = CandidateValue(
            candidate_id="cand_001",
            metric_id="revenue_2023",
            value=Decimal("1250.5"),
            currency="GBP",
            confidence_score=0.95,
            source_reference="Income Statement, Page 15",
            justification="Primary revenue line",
            supporting_evidence="Revenue for year: £1,250.5m"
        )
        
        assert candidate.candidate_id == "cand_001"
        assert candidate.confidence_score == 0.95
        assert candidate.scale == "millions"  # default
    
    def test_candidate_with_metadata(self):
        """Test candidate with additional metadata."""
        candidate = CandidateValue(
            candidate_id="cand_002",
            metric_id="ebitda_2023",
            value=Decimal("300.2"),
            currency="GBP",
            confidence_score=0.88,
            source_reference="Page 16",
            justification="Calculated from operating profit",
            supporting_evidence="EBITDA: £300.2m",
            metadata={"parser": "pymupdf", "table_id": "table_003"}
        )
        
        assert candidate.metadata["parser"] == "pymupdf"
        assert "table_id" in candidate.metadata


class TestValidationResult:
    """Tests for ValidationResult model."""
    
    def test_create_validation_result(self):
        """Test creating validation result."""
        result = ValidationResult(
            candidate_id="cand_001",
            rule_name="unit_consistency",
            result=ValidationStatus.PASS,
            message="Units are consistent",
            severity=ValidationSeverity.MINOR
        )
        
        assert result.result == ValidationStatus.PASS
        assert result.severity == ValidationSeverity.MINOR
    
    def test_validation_with_details(self):
        """Test validation result with additional details."""
        result = ValidationResult(
            candidate_id="cand_002",
            rule_name="yoy_delta_check",
            result=ValidationStatus.WARNING,
            message="Growth rate exceeds threshold",
            severity=ValidationSeverity.MAJOR,
            details={"growth_rate": 2.5, "threshold": 2.0}
        )
        
        assert result.result == ValidationStatus.WARNING
        assert result.details["growth_rate"] == 2.5
