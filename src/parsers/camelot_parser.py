"""Camelot parser wrapper for advanced financial table extraction."""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import camelot
except ImportError:
    camelot = None

from ..models.schemas import TextBlock, TableBlock
from ..utils.logger import get_logger

logger = get_logger({"module": "camelot_parser"})


class CamelotParser:
    """Wrapper for Camelot library for high-accuracy financial table extraction."""
    
    def __init__(self, timeout: int = 300, flavor: str = "lattice"):
        """
        Initialize Camelot parser.
        
        Args:
            timeout: Parsing timeout in seconds
            flavor: Parsing mode - 'lattice' for bordered tables, 'stream' for borderless
        """
        if camelot is None:
            raise ImportError(
                "Camelot is not installed. Install with: pip install camelot-py[cv]"
            )
        
        self.timeout = timeout
        self.flavor = flavor
        self.logger = logger
    
    def parse_pdf(self, pdf_path: str, pages: str = "all") -> Tuple[List[TextBlock], List[TableBlock]]:
        """
        Parse PDF and extract tables using Camelot.
        
        Note: Camelot is primarily for table extraction, not text.
        
        Args:
            pdf_path: Path to PDF file
            pages: Pages to process (e.g., "1,2,3" or "1-5" or "all")
            
        Returns:
            Tuple of (text_blocks, table_blocks)
        """
        self.logger.info("parsing_pdf", pdf_path=pdf_path, parser="camelot", flavor=self.flavor)
        
        try:
            # Camelot doesn't extract text, only tables
            text_blocks = []
            table_blocks = []
            
            # Extract tables
            table_blocks = self._extract_tables(pdf_path, pages)
            
            self.logger.info(
                "pdf_parsed_successfully",
                table_blocks_count=len(table_blocks),
                flavor=self.flavor
            )
            
            return text_blocks, table_blocks
            
        except Exception as e:
            self.logger.error("pdf_parsing_failed", error=str(e), pdf_path=pdf_path)
            raise
    
    def _extract_tables(self, pdf_path: str, pages: str = "all") -> List[TableBlock]:
        """
        Extract tables from PDF using Camelot.
        
        Args:
            pdf_path: Path to PDF file
            pages: Pages to process
            
        Returns:
            List of TableBlock objects
        """
        table_blocks = []
        
        try:
            # Try lattice flavor first (for bordered tables)
            tables = camelot.read_pdf(
                pdf_path,
                pages=pages,
                flavor=self.flavor,
                suppress_stdout=True
            )
            
            self.logger.info(
                "tables_extracted",
                count=len(tables),
                flavor=self.flavor
            )
            
            for table_idx, table in enumerate(tables):
                table_block = self._process_camelot_table(table, table_idx)
                if table_block:
                    table_blocks.append(table_block)
            
        except Exception as e:
            self.logger.warning(
                "camelot_extraction_failed",
                error=str(e),
                flavor=self.flavor
            )
            
            # If lattice fails, try stream flavor
            if self.flavor == "lattice":
                self.logger.info("trying_stream_flavor")
                try:
                    tables = camelot.read_pdf(
                        pdf_path,
                        pages=pages,
                        flavor="stream",
                        suppress_stdout=True
                    )
                    
                    for table_idx, table in enumerate(tables):
                        table_block = self._process_camelot_table(table, table_idx)
                        if table_block:
                            table_blocks.append(table_block)
                except Exception as e2:
                    self.logger.error("stream_flavor_also_failed", error=str(e2))
        
        return table_blocks
    
    def _process_camelot_table(self, table, table_idx: int) -> Optional[TableBlock]:
        """
        Process a Camelot table object into a TableBlock.
        
        Args:
            table: Camelot table object
            table_idx: Table index
            
        Returns:
            TableBlock object or None
        """
        try:
            # Get table data as list of lists
            data = table.df.values.tolist()
            
            if not data or len(data) < 2:
                return None
            
            # Get page number
            page_number = table.page
            
            # Separate headers and data
            # Assume first row is header
            headers = [data[0]]
            table_data = data[1:]
            
            # Clean the data
            cleaned_data = []
            for row in table_data:
                cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                cleaned_data.append(cleaned_row)
            
            # Extract metadata from table
            metadata = self._extract_table_metadata(table, headers, cleaned_data)
            
            # Get bounding box
            bbox = None
            if hasattr(table, '_bbox'):
                bbox = list(table._bbox)
            
            table_block = TableBlock(
                table_id=f"camelot_table_{page_number}_{table_idx}",
                page_number=page_number,
                headers=headers,
                data=cleaned_data,
                metadata=metadata,
                bbox=bbox
            )
            
            return table_block
            
        except Exception as e:
            self.logger.warning("table_processing_failed", error=str(e), table_idx=table_idx)
            return None
    
    def _extract_table_metadata(self, table, headers: List[List[str]], data: List[List[str]]) -> Dict:
        """
        Extract metadata from Camelot table.
        
        Args:
            table: Camelot table object
            headers: Table headers
            data: Table data
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'accuracy': table.accuracy if hasattr(table, 'accuracy') else None,
            'whitespace': table.whitespace if hasattr(table, 'whitespace') else None,
            'order': table.order if hasattr(table, 'order') else None,
            'page': table.page if hasattr(table, 'page') else None
        }
        
        # Concatenate all text for analysis
        all_text = ' '.join([' '.join(row) for row in headers + data])
        
        # Detect currency
        if '£' in all_text or 'GBP' in all_text:
            metadata['currency'] = 'GBP'
        elif '$' in all_text or 'USD' in all_text:
            metadata['currency'] = 'USD'
        elif '€' in all_text or 'EUR' in all_text:
            metadata['currency'] = 'EUR'
        
        # Detect scale
        text_lower = all_text.lower()
        if 'million' in text_lower or '£m' in all_text or '$m' in all_text or '(m)' in text_lower:
            metadata['scale'] = 'millions'
        elif 'thousand' in text_lower or '£k' in all_text or '$k' in all_text or '(k)' in text_lower:
            metadata['scale'] = 'thousands'
        elif 'billion' in text_lower or '£b' in all_text or '$b' in all_text or '(b)' in text_lower:
            metadata['scale'] = 'billions'
        
        # Detect years in headers
        import re
        years = []
        for header_row in headers:
            for cell in header_row:
                if cell:
                    year_matches = re.findall(r'\b(20\d{2})\b', str(cell))
                    years.extend(year_matches)
        
        if years:
            metadata['years'] = list(set(years))
        
        return metadata
    
    def extract_tables_with_quality(
        self,
        pdf_path: str,
        pages: str = "all",
        min_accuracy: float = 50.0
    ) -> List[TableBlock]:
        """
        Extract tables filtered by quality threshold.
        
        Args:
            pdf_path: Path to PDF file
            pages: Pages to process
            min_accuracy: Minimum accuracy threshold (0-100)
            
        Returns:
            List of high-quality TableBlock objects
        """
        _, all_tables = self.parse_pdf(pdf_path, pages)
        
        # Filter by accuracy
        quality_tables = []
        for table in all_tables:
            accuracy = table.metadata.get('accuracy')
            if accuracy is not None and accuracy >= min_accuracy:
                quality_tables.append(table)
                self.logger.debug(
                    "high_quality_table",
                    table_id=table.table_id,
                    accuracy=accuracy
                )
            else:
                self.logger.debug(
                    "low_quality_table_filtered",
                    table_id=table.table_id,
                    accuracy=accuracy
                )
        
        self.logger.info(
            "quality_filtering_complete",
            total_tables=len(all_tables),
            quality_tables=len(quality_tables),
            min_accuracy=min_accuracy
        )
        
        return quality_tables
