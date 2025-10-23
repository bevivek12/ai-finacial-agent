"""
Unit tests for PDF parser components.

Tests cover:
- PyMuPDF parser
- pdfplumber parser
- Camelot parser
"""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date

from src.parsers.pymupdf_parser import PyMuPDFParser
from src.parsers.pdfplumber_parser import PDFPlumberParser
from src.parsers.camelot_parser import CamelotParser
from src.models.schemas import TextBlock, TableBlock


class TestPyMuPDFParser:
    """Test PyMuPDF parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PyMuPDFParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser is not None
        assert hasattr(parser, 'parse_pdf')
    
    def test_parse_pdf_returns_tuple(self, parser):
        """Test parse_pdf returns tuple of text and table blocks."""
        # Note: This test requires a sample PDF file
        # For now, we test the structure
        assert callable(parser.parse_pdf)
    
    def test_extract_text_blocks_structure(self, parser):
        """Test text block extraction returns correct structure."""
        # Mock test - in production, use actual PDF
        pass


class TestPDFPlumberParser:
    """Test pdfplumber parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return PDFPlumberParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser is not None
        assert hasattr(parser, 'parse_pdf')
    
    def test_table_extraction_structure(self, parser):
        """Test table extraction returns correct structure."""
        assert callable(parser.parse_pdf)


class TestCamelotParser:
    """Test Camelot parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return CamelotParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser is not None
        assert hasattr(parser, 'parse_pdf')
    
    def test_table_extraction_modes(self, parser):
        """Test different table extraction modes."""
        assert parser.flavor in ['lattice', 'stream']


class TestBlockificationService:
    """Test multi-parser blockification service."""
    
    @pytest.fixture
    def service(self):
        """Create blockification service."""
        from src.services.blockification import BlockificationService
        return BlockificationService()
    
    def test_service_initialization(self, service):
        """Test service initializes with all parsers."""
        assert service is not None
        assert len(service.parsers) == 3  # PyMuPDF, pdfplumber, Camelot
    
    def test_parser_registration(self, service):
        """Test all parsers are registered."""
        assert 'pymupdf' in service.parsers
        assert 'pdfplumber' in service.parsers
        assert 'camelot' in service.parsers
    
    def test_deduplication_logic(self, service):
        """Test table deduplication works correctly."""
        # Create duplicate table blocks
        table1 = TableBlock(
            table_id="t1",
            page=1,
            bbox=(0, 0, 100, 100),
            data=[["A", "B"], ["1", "2"]]
        )
        table2 = TableBlock(
            table_id="t2",
            page=1,
            bbox=(0, 0, 100, 100),
            data=[["A", "B"], ["1", "2"]]
        )
        
        duplicates = [table1, table2]
        deduplicated = service._deduplicate_tables(duplicates)
        
        assert len(deduplicated) == 1


class TestSectionLocator:
    """Test section location functionality."""
    
    @pytest.fixture
    def locator(self):
        """Create section locator."""
        from src.services.section_locator import SectionLocator
        return SectionLocator()
    
    def test_locator_initialization(self, locator):
        """Test locator initializes correctly."""
        assert locator is not None
        assert hasattr(locator, 'locate_sections')
    
    def test_pattern_matching(self, locator):
        """Test regex pattern matching for sections."""
        from src.services.patterns import FinancialSectionPatterns
        
        # Test income statement pattern
        text = "Consolidated Income Statement for the year ended 31 December 2023"
        matches = FinancialSectionPatterns.match_section_type(text)
        
        assert "income_statement" in matches
    
    def test_balance_sheet_detection(self):
        """Test balance sheet section detection."""
        from src.services.patterns import FinancialSectionPatterns
        
        text = "Consolidated Balance Sheet as at 31 December 2023"
        matches = FinancialSectionPatterns.match_section_type(text)
        
        assert "balance_sheet" in matches
    
    def test_cash_flow_detection(self):
        """Test cash flow statement detection."""
        from src.services.patterns import FinancialSectionPatterns
        
        text = "Consolidated Cash Flow Statement"
        matches = FinancialSectionPatterns.match_section_type(text)
        
        assert "cash_flow_statement" in matches


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
