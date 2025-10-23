"""pdfplumber parser wrapper for PDF table extraction."""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

from ..models.schemas import TextBlock, TableBlock
from ..utils.logger import get_logger

logger = get_logger({"module": "pdfplumber_parser"})


class PDFPlumberParser:
    """Wrapper for pdfplumber library for enhanced table extraction."""
    
    def __init__(self, timeout: int = 300):
        """
        Initialize pdfplumber parser.
        
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
        self.logger.info("parsing_pdf", pdf_path=pdf_path, parser="pdfplumber")
        
        try:
            text_blocks = []
            table_blocks = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text blocks
                    page_text_blocks = self._extract_text_blocks(page, page_num)
                    text_blocks.extend(page_text_blocks)
                    
                    # Extract tables
                    page_table_blocks = self._extract_tables(page, page_num)
                    table_blocks.extend(page_table_blocks)
            
            self.logger.info(
                "pdf_parsed_successfully",
                text_blocks_count=len(text_blocks),
                table_blocks_count=len(table_blocks)
            )
            
            return text_blocks, table_blocks
            
        except Exception as e:
            self.logger.error("pdf_parsing_failed", error=str(e), pdf_path=pdf_path)
            raise
    
    def _extract_text_blocks(self, page: pdfplumber.page.Page, page_num: int) -> List[TextBlock]:
        """
        Extract text blocks from a page.
        
        Args:
            page: pdfplumber page object
            page_num: Page number (0-indexed)
            
        Returns:
            List of TextBlock objects
        """
        text_blocks = []
        
        # Extract text with layout preservation
        text = page.extract_text()
        
        if text and text.strip():
            # Split into paragraphs (simple approach)
            paragraphs = text.split('\n\n')
            
            for i, para in enumerate(paragraphs):
                para = para.strip()
                if not para:
                    continue
                
                # Determine block type based on text characteristics
                block_type = "body"
                if len(para) < 100 and para.isupper():
                    block_type = "heading"
                elif para.lower().startswith(('note:', 'footnote')):
                    block_type = "footnote"
                
                text_block = TextBlock(
                    block_id=f"pdfplumber_text_{page_num}_{i}_{uuid.uuid4().hex[:8]}",
                    text=para,
                    page_number=page_num + 1,  # 1-indexed
                    block_type=block_type,
                    bbox=None,  # pdfplumber doesn't easily provide bbox for paragraphs
                    font_info={}
                )
                
                text_blocks.append(text_block)
        
        return text_blocks
    
    def _extract_tables(self, page: pdfplumber.page.Page, page_num: int) -> List[TableBlock]:
        """
        Extract tables from a page.
        
        Args:
            page: pdfplumber page object
            page_num: Page number (0-indexed)
            
        Returns:
            List of TableBlock objects
        """
        table_blocks = []
        
        # Extract tables using pdfplumber's table detection
        tables = page.extract_tables()
        
        for table_idx, table_data in enumerate(tables):
            if not table_data or len(table_data) < 2:
                continue
            
            # Process table data
            processed_table = self._process_table_data(table_data)
            
            if processed_table:
                headers, data, metadata = processed_table
                
                table_block = TableBlock(
                    table_id=f"pdfplumber_table_{page_num}_{table_idx}",
                    page_number=page_num + 1,  # 1-indexed
                    headers=headers,
                    data=data,
                    metadata=metadata,
                    bbox=None
                )
                
                table_blocks.append(table_block)
        
        return table_blocks
    
    def _process_table_data(self, table_data: List[List[str]]) -> Optional[Tuple[List[List[str]], List[List[str]], Dict]]:
        """
        Process raw table data to separate headers and data.
        
        Args:
            table_data: Raw table data from pdfplumber
            
        Returns:
            Tuple of (headers, data, metadata) or None
        """
        if not table_data or len(table_data) < 2:
            return None
        
        # Clean table data (remove None values)
        cleaned_table = []
        for row in table_data:
            cleaned_row = [cell.strip() if cell else "" for cell in row]
            cleaned_table.append(cleaned_row)
        
        # Assume first row(s) are headers
        # Simple heuristic: if first row contains non-numeric values, it's a header
        headers = [cleaned_table[0]]
        data_start_idx = 1
        
        # Check if there's a second header row
        if len(cleaned_table) > 2:
            second_row = cleaned_table[1]
            # If second row is mostly non-numeric, it's also a header
            numeric_count = sum(1 for cell in second_row if cell and any(c.isdigit() for c in cell))
            if numeric_count < len(second_row) / 2:
                headers.append(second_row)
                data_start_idx = 2
        
        # Extract data rows
        data = cleaned_table[data_start_idx:]
        
        # Extract metadata from table content
        metadata = self._extract_table_metadata(headers, data)
        
        return headers, data, metadata
    
    def _extract_table_metadata(self, headers: List[List[str]], data: List[List[str]]) -> Dict:
        """
        Extract metadata from table (currency, units, etc.).
        
        Args:
            headers: Table headers
            data: Table data
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Look for currency symbols
        all_text = ' '.join([' '.join(row) for row in headers + data])
        
        if '£' in all_text or 'GBP' in all_text:
            metadata['currency'] = 'GBP'
        elif '$' in all_text or 'USD' in all_text:
            metadata['currency'] = 'USD'
        elif '€' in all_text or 'EUR' in all_text:
            metadata['currency'] = 'EUR'
        
        # Look for scale indicators
        if 'million' in all_text.lower() or '(m)' in all_text.lower():
            metadata['scale'] = 'millions'
        elif 'thousand' in all_text.lower() or '(k)' in all_text.lower():
            metadata['scale'] = 'thousands'
        elif 'billion' in all_text.lower() or '(b)' in all_text.lower():
            metadata['scale'] = 'billions'
        
        # Look for year indicators in headers
        years = []
        for header_row in headers:
            for cell in header_row:
                if cell and any(c.isdigit() for c in cell):
                    # Check for year patterns (2020, 2021, etc.)
                    import re
                    year_matches = re.findall(r'\b(20\d{2})\b', cell)
                    years.extend(year_matches)
        
        if years:
            metadata['years'] = list(set(years))
        
        return metadata
    
    def extract_tables_only(self, pdf_path: str) -> List[TableBlock]:
        """
        Extract only tables from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of TableBlock objects
        """
        _, table_blocks = self.parse_pdf(pdf_path)
        return table_blocks
