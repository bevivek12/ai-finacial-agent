"""
Integration tests for end-to-end pipeline.

Tests the complete workflow from PDF ingestion to report export.
"""

import pytest
from pathlib import Path
from datetime import date
from decimal import Decimal

from src.models.schemas import DocumentMetadata, FinancialMetric, ReportType
from src.models.state import AgentState


class TestEndToEndPipeline:
    """Test complete end-to-end processing pipeline."""
    
    @pytest.fixture
    def sample_state(self):
        """Create sample agent state for testing."""
        return {
            "raw_pdf_path": "test_data/sample_report.pdf",
            "document_metadata": None,
            "text_blocks": [],
            "table_blocks": [],
            "sections": [],
            "candidates": [],
            "validated_metrics": [],
            "derived_metrics": [],
            "commentary": {},
            "export_paths": {},
            "node_execution_times": {},
            "errors": []
        }
    
    def test_pdf_ingestion_node(self, sample_state):
        """Test PDF ingestion node."""
        from src.workflow.nodes import ingest_pdf_node
        
        result_state = ingest_pdf_node(sample_state)
        
        assert "document_metadata" in result_state
        assert "node_execution_times" in result_state
        assert "ingest_pdf" in result_state["node_execution_times"]
    
    def test_parse_blockify_node(self, sample_state):
        """Test parse and blockify node."""
        from src.workflow.nodes import parse_blockify_node
        
        result_state = parse_blockify_node(sample_state)
        
        assert "text_blocks" in result_state
        assert "table_blocks" in result_state
        assert "parse_blockify" in result_state["node_execution_times"]
    
    def test_candidate_generation_flow(self):
        """Test candidate generation from sections and blocks."""
        from src.services.candidate_generator import CandidateGenerator
        from src.models.schemas import Section, TableBlock, TextBlock
        
        # Create sample data
        section = Section(
            section_id="s1",
            section_type="income_statement",
            title="Income Statement",
            start_page=1,
            end_page=2
        )
        
        table = TableBlock(
            table_id="t1",
            page=1,
            bbox=(0, 0, 100, 100),
            data=[
                ["Metric", "2023", "2022"],
                ["Revenue", "1000", "900"],
                ["Net Income", "100", "90"]
            ]
        )
        
        generator = CandidateGenerator()
        candidates = generator.generate_candidates(
            sections=[section],
            table_blocks=[table],
            text_blocks=[]
        )
        
        assert len(candidates) > 0
    
    def test_validation_flow(self):
        """Test validation of candidates."""
        from src.services.validators import DeterministicValidator
        from src.models.schemas import CandidateValue, EvidenceSource
        
        # Create sample candidate
        candidate = CandidateValue(
            candidate_id="c1",
            metric_name="revenue",
            value=Decimal("1000"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31),
            section_type="income_statement",
            source=EvidenceSource.TABLE_CELL,
            confidence_score=0.9,
            evidence={}
        )
        
        validator = DeterministicValidator()
        results = validator.validate_candidates([candidate])
        
        assert len(results) > 0
        assert results[0].candidate_id == "c1"
    
    def test_export_flow(self):
        """Test export service."""
        from src.export.export_service import ExportService
        import tempfile
        import os
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample metrics
            metrics = [
                FinancialMetric(
                    metric_id="m1",
                    metric_name="revenue",
                    value=Decimal("1000"),
                    currency="GBP",
                    scale="millions",
                    period_end_date=date(2023, 12, 31)
                )
            ]
            
            # Export
            export_service = ExportService(output_dir=tmpdir)
            paths = export_service.export_all(
                company_name="Test Company",
                report_period=date(2023, 12, 31),
                metrics=metrics,
                formats=["json"]  # Only JSON for quick test
            )
            
            assert "json" in paths
            assert os.path.exists(paths["json"])


class TestWorkflowIntegration:
    """Test LangGraph workflow integration."""
    
    def test_workflow_creation(self):
        """Test workflow graph creation."""
        from src.workflow.graph import create_financial_agent_graph
        
        graph = create_financial_agent_graph()
        
        assert graph is not None
    
    def test_conditional_routing(self):
        """Test conditional routing logic."""
        from src.workflow.graph import should_adjudicate
        
        # Test with conflicts
        state_with_conflicts = {"has_conflicts": True}
        result = should_adjudicate(state_with_conflicts)
        assert result == "adjudicate"
        
        # Test without conflicts
        state_no_conflicts = {"has_conflicts": False}
        result = should_adjudicate(state_no_conflicts)
        assert result == "skip"


class TestDataModels:
    """Test data model integrity."""
    
    def test_financial_metric_creation(self):
        """Test FinancialMetric model creation."""
        metric = FinancialMetric(
            metric_id="m1",
            metric_name="revenue",
            value=Decimal("1000"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31)
        )
        
        assert metric.metric_id == "m1"
        assert metric.metric_name == "revenue"
        assert metric.value == Decimal("1000")
    
    def test_metric_to_base_units(self):
        """Test metric conversion to base units."""
        metric = FinancialMetric(
            metric_id="m1",
            metric_name="revenue",
            value=Decimal("1000"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31)
        )
        
        base_value = metric.to_base_units()
        assert base_value == Decimal("1000000000")  # 1000 millions
    
    def test_document_metadata_validation(self):
        """Test DocumentMetadata validation."""
        metadata = DocumentMetadata(
            document_id="doc1",
            company_name="Test Company",
            report_type=ReportType.ANNUAL,
            fiscal_period_end=date(2023, 12, 31),
            source_path="test.pdf"
        )
        
        assert metadata.company_name == "Test Company"
        assert metadata.report_type == ReportType.ANNUAL


class TestConfigurationManagement:
    """Test configuration loading and management."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        from src.utils.config import load_config
        
        config = load_config()
        
        assert config is not None
        assert "pdf" in config
        assert "logging" in config
    
    def test_environment_override(self):
        """Test environment-specific overrides."""
        from src.utils.config import load_config
        
        # Load with environment
        config = load_config(env="development")
        
        assert config is not None


class TestErrorHandling:
    """Test error handling throughout the pipeline."""
    
    def test_invalid_pdf_handling(self):
        """Test handling of invalid PDF."""
        from src.services.ingestion import PDFIngestionService
        
        ingestion = PDFIngestionService()
        
        with pytest.raises(Exception):
            ingestion.ingest("nonexistent.pdf")
    
    def test_validation_error_recovery(self):
        """Test recovery from validation errors."""
        from src.services.validators import DeterministicValidator
        
        validator = DeterministicValidator()
        
        # Empty candidates should not crash
        results = validator.validate_candidates([])
        assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
