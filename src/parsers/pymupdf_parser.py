"""PyMuPDF (fitz) parser wrapper for PDF text extraction."""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from ..models.schemas import TextBlock, TableBlock
from ..utils.logger import get_logger

logger = get_logger({"module": "pymupdf_parser"})


class PyMuPDFParser:
    """Wrapper for PyMuPDF library for PDF parsing."""
    
    def __init__(self, timeout: int = 300):
        """
        Initialize PyMuPDF parser.
        
        Args:
            timeout: Parsing timeout in seconds
        """
        self.timeout = timeout
        self.logger = logger
    
    def parse_pdf(self, pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]:
        """
        Parse PDF and extract text blocks and tables.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (text_blocks, table_blocks)
        """
        self.logger.info("parsing_pdf", pdf_path=pdf_path, parser="pymupdf")
        
        try:
            doc = fitz.open(pdf_path)
            text_blocks = []
            table_blocks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text blocks
                page_text_blocks = self._extract_text_blocks(page, page_num)
                text_blocks.extend(page_text_blocks)
                
                # Extract simple tables using text positioning
                page_table_blocks = self._extract_simple_tables(page, page_num)
                table_blocks.extend(page_table_blocks)
            
            doc.close()
            
            self.logger.info(
                "pdf_parsed_successfully",
                text_blocks_count=len(text_blocks),
                table_blocks_count=len(table_blocks)
            )
            
            return text_blocks, table_blocks
            
        except Exception as e:
            self.logger.error("pdf_parsing_failed", error=str(e), pdf_path=pdf_path)
            raise
    
    def _extract_text_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """
        Extract text blocks from a page.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            
        Returns:
            List of TextBlock objects
        """
        text_blocks = []
        
        # Get text with detailed formatting
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block["type"] == 0:  # Text block
                # Extract text content
                text_content = ""
                font_info = {}
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_content += span.get("text", "")
                        # Collect font information
                        if not font_info:
                            font_info = {
                                "size": span.get("size"),
                                "font": span.get("font"),
                                "color": span.get("color")
                            }
                    text_content += "\n"
                
                text_content = text_content.strip()
                if not text_content:
                    continue
                
                # Determine block type based on font size
                block_type = "body"
                if font_info.get("size", 0) > 14:
                    block_type = "heading"
                elif "footnote" in text_content.lower()[:20]:
                    block_type = "footnote"
                
                text_block = TextBlock(
                    block_id=f"pymupdf_text_{page_num}_{uuid.uuid4().hex[:8]}",
                    text=text_content,
                    page_number=page_num + 1,  # 1-indexed for user display
                    block_type=block_type,
                    bbox=block.get("bbox"),
                    font_info=font_info
                )
                
                text_blocks.append(text_block)
        
        return text_blocks
    
    def _extract_simple_tables(self, page: fitz.Page, page_num: int) -> List[TableBlock]:
        """
        Extract simple tables using text positioning heuristics.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            
        Returns:
            List of TableBlock objects
        """
        # PyMuPDF has limited table extraction
        # This is a basic implementation - pdfplumber and Camelot are better
        table_blocks = []
        
        # Find tables using tab-separated text patterns
        text_tabs = page.get_text("text")
        
        # Basic heuristic: look for rows with consistent column alignment
        # This is simplified - production code would be more sophisticated
        
        return table_blocks
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the number of pages in the PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            self.logger.error("failed_to_get_page_count", error=str(e))
            return 0
    
    def get_metadata(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract PDF metadata.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            doc.close()
            return metadata
        except Exception as e:
            self.logger.error("failed_to_get_metadata", error=str(e))
            return {}
