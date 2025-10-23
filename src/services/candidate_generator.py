"""
Candidate Generator Service.

This service implements the multi-source candidate generation strategy:
1. Extract candidates from table cells (primary source)
2. Extract candidates from text blocks (secondary source)  
3. Collect evidence and context for each candidate
4. Score and rank candidates based on evidence quality
5. Generate structured candidate objects with provenance
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal, InvalidOperation
from datetime import date
import re
from loguru import logger

from src.models.schemas import (
    CandidateValue, FinancialMetric, TableBlock, TextBlock, 
    Section, EntityType, EvidenceSource
)
from src.utils.periods import PeriodParser, LabelStandardizer
from src.utils.currency import ScaleConverter


class CandidateGenerator:
    """
    Generate candidate values for financial metrics from multiple sources.
    
    Strategy:
    - Table cells: Primary source (structured data)
    - Text blocks: Secondary source (narrative mentions)
    - Evidence collection: Context, formatting, neighboring cells
    - Scoring: Based on evidence quality, source reliability, formatting
    """
    
    # Numeric value patterns
    VALUE_PATTERNS = [
        r'(?:£|GBP|USD|\$|€|EUR)\s*([\d,]+(?:\.\d+)?)',  # With currency symbol
        r'([\d,]+(?:\.\d+)?)\s*(?:million|mn|m|billion|bn|b|thousand|k)',  # With scale
        r'\(\s*([\d,]+(?:\.\d+)?)\s*\)',  # Parentheses (negative)
        r'([\d,]+(?:\.\d+)?)',  # Plain number
    ]
    
    # Currency detection patterns
    CURRENCY_PATTERNS = {
        'GBP': r'(?:£|GBP|pounds?)',
        'USD': r'(?:\$|USD|dollars?)',
        'EUR': r'(?:€|EUR|euros?)',
    }
    
    # Scale detection patterns
    SCALE_PATTERNS = {
        'millions': r'(?:million|mn|m\b)',
        'billions': r'(?:billion|bn|b\b)',
        'thousands': r'(?:thousand|k\b)',
    }
    
    def __init__(self):
        self.logger = logger.bind(component="candidate_generator")
        self.period_parser = PeriodParser()
        self.label_standardizer = LabelStandardizer()
        self.scale_converter = ScaleConverter()
    
    def generate_candidates(
        self,
        sections: List[Section],
        table_blocks: List[TableBlock],
        text_blocks: List[TextBlock],
        target_metrics: Optional[List[str]] = None
    ) -> List[CandidateValue]:
        """
        Generate all candidate values from available sources.
        
        Args:
            sections: Detected financial sections
            table_blocks: Extracted table blocks
            text_blocks: Extracted text blocks
            target_metrics: Optional list of specific metrics to extract
        
        Returns:
            List of candidate values with evidence
        """
        self.logger.info(
            "generating_candidates",
            sections=len(sections),
            tables=len(table_blocks),
            text_blocks=len(text_blocks)
        )
        
        all_candidates = []
        
        # Generate candidates from tables (primary source)
        table_candidates = self._generate_from_tables(sections, table_blocks, target_metrics)
        all_candidates.extend(table_candidates)
        
        # Generate candidates from text (secondary source)
        text_candidates = self._generate_from_text(sections, text_blocks, target_metrics)
        all_candidates.extend(text_candidates)
        
        # Score and rank candidates
        scored_candidates = self._score_candidates(all_candidates)
        
        self.logger.info(
            "candidates_generated",
            total=len(scored_candidates),
            from_tables=len(table_candidates),
            from_text=len(text_candidates)
        )
        
        return scored_candidates
    
    def _generate_from_tables(
        self,
        sections: List[Section],
        table_blocks: List[TableBlock],
        target_metrics: Optional[List[str]] = None
    ) -> List[CandidateValue]:
        """Generate candidates from table cells."""
        candidates = []
        
        for section in sections:
            # Find tables in this section
            section_tables = self._get_tables_in_section(section, table_blocks)
            
            for table in section_tables:
                table_candidates = self._extract_from_table(table, section, target_metrics)
                candidates.extend(table_candidates)
        
        return candidates
    
    def _extract_from_table(
        self,
        table: TableBlock,
        section: Section,
        target_metrics: Optional[List[str]] = None
    ) -> List[CandidateValue]:
        """Extract candidate values from a single table."""
        candidates = []
        
        if not table.data or len(table.data) == 0:
            return candidates
        
        # Detect header row and period columns
        header_row_idx = 0  # Assume first row is header
        header_row = table.data[header_row_idx] if len(table.data) > 0 else []
        
        # Parse period columns
        period_columns = self._detect_period_columns(header_row)
        
        # Detect metric label column (usually first column)
        label_column_idx = 0
        
        # Extract candidates from each data row
        for row_idx in range(header_row_idx + 1, len(table.data)):
            row = table.data[row_idx]
            
            if not row or len(row) <= label_column_idx:
                continue
            
            # Get metric label from first column
            raw_label = str(row[label_column_idx]).strip()
            
            if not raw_label or raw_label == "":
                continue
            
            # Standardize label
            standard_label = self.label_standardizer.standardize_label(raw_label)
            
            # Skip if not in target metrics
            if target_metrics and standard_label not in target_metrics:
                continue
            
            # Extract values for each period column
            for col_idx, period_info in period_columns.items():
                if col_idx >= len(row):
                    continue
                
                cell_value = row[col_idx]
                
                # Parse numeric value
                parsed_value = self._parse_numeric_value(cell_value)
                
                if parsed_value is None:
                    continue
                
                # Create candidate
                candidate = self._create_candidate(
                    metric_name=standard_label,
                    value=parsed_value["value"],
                    currency=parsed_value.get("currency", "GBP"),
                    scale=parsed_value.get("scale", "millions"),
                    period_end_date=period_info.get("end_date"),
                    section_type=section.section_type,
                    source=EvidenceSource.TABLE_CELL,
                    evidence={
                        "table_id": table.table_id,
                        "row_index": row_idx,
                        "column_index": col_idx,
                        "raw_label": raw_label,
                        "raw_value": str(cell_value),
                        "period_label": period_info.get("label", ""),
                        "section_id": section.section_id
                    }
                )
                
                candidates.append(candidate)
        
        return candidates
    
    def _generate_from_text(
        self,
        sections: List[Section],
        text_blocks: List[TextBlock],
        target_metrics: Optional[List[str]] = None
    ) -> List[CandidateValue]:
        """Generate candidates from text blocks."""
        candidates = []
        
        for section in sections:
            # Find text blocks in this section
            section_text_blocks = self._get_text_blocks_in_section(section, text_blocks)
            
            for text_block in section_text_blocks:
                text_candidates = self._extract_from_text_block(
                    text_block, section, target_metrics
                )
                candidates.extend(text_candidates)
        
        return candidates
    
    def _extract_from_text_block(
        self,
        text_block: TextBlock,
        section: Section,
        target_metrics: Optional[List[str]] = None
    ) -> List[CandidateValue]:
        """Extract candidate values from a single text block."""
        candidates = []
        text = text_block.text
        
        # Look for metric mentions with values
        # Pattern: "Revenue was £X million" or "Net profit: $X.X billion"
        metric_value_patterns = [
            r'([\w\s]+)\s+(?:was|is|of|:)\s+([£$€]?[\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?',
            r'([£$€]?[\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?\s+([\w\s]+)',
        ]
        
        for pattern in metric_value_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                # Extract components
                groups = match.groups()
                
                # Try to identify metric name and value
                metric_name = None
                value_str = None
                scale = "millions"
                
                for group in groups:
                    if group:
                        # Check if it's a number
                        if re.search(r'[\d,]+(?:\.\d+)?', group):
                            value_str = group
                        # Check if it's a scale
                        elif group.lower() in ['million', 'billion', 'thousand']:
                            scale = group.lower() + 's'
                        # Otherwise, assume it's a metric name
                        else:
                            metric_name = group.strip()
                
                if not metric_name or not value_str:
                    continue
                
                # Standardize label
                standard_label = self.label_standardizer.standardize_label(metric_name)
                
                # Skip if not in target metrics
                if target_metrics and standard_label not in target_metrics:
                    continue
                
                # Parse value
                parsed_value = self._parse_numeric_value(value_str)
                
                if parsed_value is None:
                    continue
                
                # Create candidate
                candidate = self._create_candidate(
                    metric_name=standard_label,
                    value=parsed_value["value"],
                    currency=parsed_value.get("currency", "GBP"),
                    scale=scale,
                    period_end_date=None,  # Would need to infer from context
                    section_type=section.section_type,
                    source=EvidenceSource.TEXT_BLOCK,
                    evidence={
                        "text_block_id": text_block.block_id,
                        "page": text_block.page,
                        "raw_text": match.group(0),
                        "raw_metric_name": metric_name,
                        "section_id": section.section_id
                    }
                )
                
                candidates.append(candidate)
        
        return candidates
    
    def _detect_period_columns(self, header_row: List[str]) -> Dict[int, Dict[str, any]]:
        """
        Detect which columns contain period labels and parse them.
        
        Args:
            header_row: Header row from table
        
        Returns:
            Dictionary mapping column index to period information
        """
        period_columns = {}
        
        for col_idx, cell_value in enumerate(header_row):
            if not cell_value:
                continue
            
            cell_str = str(cell_value).strip()
            
            # Try to parse as period label
            parsed = self.period_parser.parse_period_label(cell_str)
            
            if parsed:
                period_columns[col_idx] = {
                    "label": cell_str,
                    "end_date": parsed.get("end_date"),
                    "fiscal_year": parsed.get("fiscal_year"),
                    "period_type": parsed.get("period_type")
                }
        
        return period_columns
    
    def _parse_numeric_value(self, value: any) -> Optional[Dict[str, any]]:
        """
        Parse a numeric value from various formats.
        
        Args:
            value: Value to parse (string, number, etc.)
        
        Returns:
            Dictionary with parsed value, currency, and scale
        """
        if value is None:
            return None
        
        value_str = str(value).strip()
        
        if not value_str or value_str == "":
            return None
        
        # Detect currency
        currency = "GBP"  # Default
        for curr, pattern in self.CURRENCY_PATTERNS.items():
            if re.search(pattern, value_str, re.IGNORECASE):
                currency = curr
                break
        
        # Detect scale
        scale = "millions"  # Default
        for sc, pattern in self.SCALE_PATTERNS.items():
            if re.search(pattern, value_str, re.IGNORECASE):
                scale = sc
                break
        
        # Extract numeric value
        is_negative = '(' in value_str and ')' in value_str
        
        # Try each pattern
        for pattern in self.VALUE_PATTERNS:
            match = re.search(pattern, value_str)
            if match:
                num_str = match.group(1)
                # Remove commas
                num_str = num_str.replace(',', '')
                
                try:
                    numeric_value = Decimal(num_str)
                    if is_negative:
                        numeric_value = -numeric_value
                    
                    return {
                        "value": numeric_value,
                        "currency": currency,
                        "scale": scale
                    }
                except (InvalidOperation, ValueError):
                    continue
        
        return None
    
    def _create_candidate(
        self,
        metric_name: str,
        value: Decimal,
        currency: str,
        scale: str,
        period_end_date: Optional[date],
        section_type: str,
        source: EvidenceSource,
        evidence: Dict[str, any]
    ) -> CandidateValue:
        """Create a candidate value object."""
        import uuid
        
        candidate = CandidateValue(
            candidate_id=str(uuid.uuid4()),
            metric_name=metric_name,
            value=value,
            currency=currency,
            scale=scale,
            period_end_date=period_end_date,
            section_type=section_type,
            source=source,
            confidence_score=0.0,  # Will be calculated in scoring
            evidence=evidence
        )
        
        return candidate
    
    def _score_candidates(self, candidates: List[CandidateValue]) -> List[CandidateValue]:
        """
        Score candidates based on evidence quality.
        
        Scoring factors:
        - Source reliability (table > text)
        - Section type relevance
        - Formatting quality
        - Evidence completeness
        """
        for candidate in candidates:
            score = 0.0
            
            # Source score (0-40 points)
            if candidate.source == EvidenceSource.TABLE_CELL:
                score += 40
            elif candidate.source == EvidenceSource.TEXT_BLOCK:
                score += 20
            
            # Section type score (0-20 points)
            if candidate.section_type in [
                "income_statement", "balance_sheet", "cash_flow_statement"
            ]:
                score += 20
            elif candidate.section_type in ["notes", "commentary"]:
                score += 10
            
            # Period detection score (0-20 points)
            if candidate.period_end_date is not None:
                score += 20
            
            # Evidence completeness score (0-20 points)
            evidence = candidate.evidence or {}
            evidence_fields = len([k for k, v in evidence.items() if v is not None])
            score += min(20, evidence_fields * 3)
            
            # Normalize to 0-1 range
            candidate.confidence_score = score / 100.0
        
        # Sort by confidence score (descending)
        candidates.sort(key=lambda c: c.confidence_score, reverse=True)
        
        return candidates
    
    def _get_tables_in_section(
        self,
        section: Section,
        table_blocks: List[TableBlock]
    ) -> List[TableBlock]:
        """Get all tables within a section's boundaries."""
        section_tables = []
        
        for table in table_blocks:
            # Check if table page is within section range
            if section.start_page <= table.page <= section.end_page:
                section_tables.append(table)
        
        return section_tables
    
    def _get_text_blocks_in_section(
        self,
        section: Section,
        text_blocks: List[TextBlock]
    ) -> List[TextBlock]:
        """Get all text blocks within a section's boundaries."""
        section_blocks = []
        
        for block in text_blocks:
            # Check if block page is within section range
            if section.start_page <= block.page <= section.end_page:
                section_blocks.append(block)
        
        return section_blocks
