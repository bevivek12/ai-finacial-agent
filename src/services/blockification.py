"""Blockification Service for orchestrating multi-parser PDF processing."""

from typing import Dict, List, Tuple

from ..models.schemas import TextBlock, TableBlock
from ..parsers.pymupdf_parser import PyMuPDFParser
from ..parsers.pdfplumber_parser import PDFPlumberParser
from ..parsers.camelot_parser import CamelotParser
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger({"module": "blockification"})


class BlockificationService:
    """Service for parsing PDFs using multiple parsers with fallback strategy."""
    
    def __init__(self):
        """Initialize the blockification service."""
        self.config = get_config()
        self.logger = logger
        
        # Initialize parsers based on configuration
        self.parsers = {}
        parser_priority = self.config.pdf.parser_priority
        
        for parser_name in parser_priority:
            try:
                if parser_name == "pymupdf":
                    self.parsers["pymupdf"] = PyMuPDFParser(timeout=self.config.pdf.parser_timeout)
                elif parser_name == "pdfplumber":
                    self.parsers["pdfplumber"] = PDFPlumberParser(timeout=self.config.pdf.parser_timeout)
                elif parser_name == "camelot":
                    self.parsers["camelot"] = CamelotParser(timeout=self.config.pdf.parser_timeout)
                
                self.logger.debug("parser_initialized", parser=parser_name)
            except Exception as e:
                self.logger.warning("parser_initialization_failed", parser=parser_name, error=str(e))
    
    def parse(self, pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]:
        """
        Parse PDF using multi-parser strategy.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (text_blocks, table_blocks)
        """
        self.logger.info("starting_blockification", pdf_path=pdf_path)
        
        all_text_blocks = []
        all_table_blocks = []
        parser_results = {}
        
        # Parse with all available parsers
        for parser_name, parser in self.parsers.items():
            try:
                self.logger.debug("parsing_with_parser", parser=parser_name)
                text_blocks, table_blocks = parser.parse_pdf(pdf_path)
                
                parser_results[parser_name] = {
                    "text_blocks": text_blocks,
                    "table_blocks": table_blocks,
                    "success": True
                }
                
                self.logger.info(
                    "parser_completed",
                    parser=parser_name,
                    text_blocks=len(text_blocks),
                    table_blocks=len(table_blocks)
                )
                
            except Exception as e:
                self.logger.warning(
                    "parser_failed",
                    parser=parser_name,
                    error=str(e)
                )
                parser_results[parser_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Merge results from all parsers
        all_text_blocks, all_table_blocks = self._merge_parser_results(parser_results)
        
        self.logger.info(
            "blockification_complete",
            total_text_blocks=len(all_text_blocks),
            total_table_blocks=len(all_table_blocks)
        )
        
        return all_text_blocks, all_table_blocks
    
    def _merge_parser_results(
        self,
        parser_results: Dict[str, Dict]
    ) -> Tuple[List[TextBlock], List[TableBlock]]:
        """
        Merge results from multiple parsers.
        
        Strategy:
        - For text: Use PyMuPDF as primary (most reliable for text positioning)
        - For tables: Combine Camelot (high accuracy) and pdfplumber (good coverage)
        
        Args:
            parser_results: Dictionary of parser results
            
        Returns:
            Tuple of (merged_text_blocks, merged_table_blocks)
        """
        text_blocks = []
        table_blocks = []
        
        # Text blocks: prioritize PyMuPDF, fallback to pdfplumber
        if parser_results.get("pymupdf", {}).get("success"):
            text_blocks = parser_results["pymupdf"]["text_blocks"]
            self.logger.debug("using_pymupdf_for_text", count=len(text_blocks))
        elif parser_results.get("pdfplumber", {}).get("success"):
            text_blocks = parser_results["pdfplumber"]["text_blocks"]
            self.logger.debug("using_pdfplumber_for_text", count=len(text_blocks))
        
        # Table blocks: combine Camelot and pdfplumber, deduplicate
        camelot_tables = []
        pdfplumber_tables = []
        
        if parser_results.get("camelot", {}).get("success"):
            camelot_tables = parser_results["camelot"]["table_blocks"]
            self.logger.debug("camelot_tables_extracted", count=len(camelot_tables))
        
        if parser_results.get("pdfplumber", {}).get("success"):
            pdfplumber_tables = parser_results["pdfplumber"]["table_blocks"]
            self.logger.debug("pdfplumber_tables_extracted", count=len(pdfplumber_tables))
        
        # Merge tables with deduplication
        table_blocks = self._merge_tables(camelot_tables, pdfplumber_tables)
        
        return text_blocks, table_blocks
    
    def _merge_tables(
        self,
        camelot_tables: List[TableBlock],
        pdfplumber_tables: List[TableBlock]
    ) -> List[TableBlock]:
        """
        Merge table results from different parsers with deduplication.
        
        Args:
            camelot_tables: Tables from Camelot
            pdfplumber_tables: Tables from pdfplumber
            
        Returns:
            Merged list of unique tables
        """
        # Group tables by page
        tables_by_page = {}
        
        # Add Camelot tables (higher priority)
        for table in camelot_tables:
            page = table.page_number
            if page not in tables_by_page:
                tables_by_page[page] = []
            tables_by_page[page].append(table)
        
        # Add pdfplumber tables if not duplicates
        for table in pdfplumber_tables:
            page = table.page_number
            if page not in tables_by_page:
                tables_by_page[page] = [table]
            else:
                # Check if this table is similar to any existing table on the page
                is_duplicate = False
                for existing_table in tables_by_page[page]:
                    if self._tables_similar(table, existing_table):
                        is_duplicate = True
                        self.logger.debug(
                            "duplicate_table_skipped",
                            page=page,
                            table_id=table.table_id
                        )
                        break
                
                if not is_duplicate:
                    tables_by_page[page].append(table)
        
        # Flatten and return
        merged_tables = []
        for page in sorted(tables_by_page.keys()):
            merged_tables.extend(tables_by_page[page])
        
        self.logger.info(
            "tables_merged",
            camelot_count=len(camelot_tables),
            pdfplumber_count=len(pdfplumber_tables),
            merged_count=len(merged_tables)
        )
        
        return merged_tables
    
    def _tables_similar(self, table1: TableBlock, table2: TableBlock) -> bool:
        """
        Check if two tables are similar (likely duplicates).
        
        Args:
            table1: First table
            table2: Second table
            
        Returns:
            True if tables are similar
        """
        # Must be on same page
        if table1.page_number != table2.page_number:
            return False
        
        # Compare dimensions
        rows1 = len(table1.data)
        cols1 = len(table1.data[0]) if table1.data else 0
        rows2 = len(table2.data)
        cols2 = len(table2.data[0]) if table2.data else 0
        
        # If dimensions are very different, not the same table
        if abs(rows1 - rows2) > 2 or abs(cols1 - cols2) > 1:
            return False
        
        # If dimensions are similar, check first cell content
        if table1.data and table2.data:
            if table1.data[0] and table2.data[0]:
                cell1 = str(table1.data[0][0]).strip()
                cell2 = str(table2.data[0][0]).strip()
                
                # If first cells match, likely same table
                if cell1 and cell2 and cell1 == cell2:
                    return True
        
        return False
    
    def parse_with_fallback(self, pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]:
        """
        Parse PDF with fallback strategy (try parsers in priority order).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (text_blocks, table_blocks)
        """
        self.logger.info("parsing_with_fallback", pdf_path=pdf_path)
        
        for parser_name in self.config.pdf.parser_priority:
            if parser_name not in self.parsers:
                continue
            
            try:
                parser = self.parsers[parser_name]
                self.logger.debug("trying_parser", parser=parser_name)
                
                text_blocks, table_blocks = parser.parse_pdf(pdf_path)
                
                self.logger.info(
                    "parser_succeeded",
                    parser=parser_name,
                    text_blocks=len(text_blocks),
                    table_blocks=len(table_blocks)
                )
                
                return text_blocks, table_blocks
                
            except Exception as e:
                self.logger.warning(
                    "parser_failed_trying_next",
                    parser=parser_name,
                    error=str(e)
                )
                continue
        
        # If all parsers failed
        raise RuntimeError(f"All parsers failed for PDF: {pdf_path}")
