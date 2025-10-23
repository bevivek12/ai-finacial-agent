"""
Period mapping and label standardization utilities.

This module provides utilities for:
- Parsing period labels from financial statements
- Normalizing period formats (FY2023, Year ended 31 Dec 2023, etc.)
- Detecting fiscal year end dates
- Mapping period labels to standard date ranges
"""

import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from loguru import logger


class PeriodParser:
    """Parse and normalize financial reporting periods."""
    
    # Common fiscal year patterns
    FY_PATTERNS = [
        r'(?:FY|Fiscal\s+Year)\s*[:\-]?\s*(\d{4})',
        r'(?:Year\s+ended?|YE)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(\d{4})\s*[-/]\s*(\d{2,4})',  # 2023-24 or 2023/2024
        r'For\s+the\s+year\s+ended?\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
    ]
    
    # Quarter patterns
    QUARTER_PATTERNS = [
        r'(?:Q|Quarter)\s*(\d)\s*(?:FY)?(\d{4})',
        r'(\d)(?:st|nd|rd|th)\s+Quarter\s+(\d{4})',
        r'Three\s+months\s+ended?\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
    ]
    
    # Half-year patterns
    HALF_YEAR_PATTERNS = [
        r'(?:H|Half)\s*(\d)\s*(?:FY)?(\d{4})',
        r'Six\s+months\s+ended?\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
    ]
    
    # Month name to number mapping
    MONTH_MAP = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    def __init__(self):
        self.logger = logger.bind(component="period_parser")
    
    def parse_period_label(self, label: str) -> Optional[Dict[str, any]]:
        """
        Parse a period label into structured format.
        
        Args:
            label: Period label string (e.g., "FY2023", "Year ended 31 Dec 2023")
        
        Returns:
            Dictionary with period information:
            {
                "period_type": "fiscal_year" | "quarter" | "half_year" | "month",
                "start_date": date object,
                "end_date": date object,
                "fiscal_year": int,
                "original_label": str
            }
        """
        label_clean = label.strip()
        
        # Try fiscal year patterns
        fy_result = self._parse_fiscal_year(label_clean)
        if fy_result:
            return fy_result
        
        # Try quarter patterns
        quarter_result = self._parse_quarter(label_clean)
        if quarter_result:
            return quarter_result
        
        # Try half-year patterns
        half_year_result = self._parse_half_year(label_clean)
        if half_year_result:
            return half_year_result
        
        self.logger.warning("period_parse_failed", label=label)
        return None
    
    def _parse_fiscal_year(self, label: str) -> Optional[Dict[str, any]]:
        """Parse fiscal year labels."""
        for pattern in self.FY_PATTERNS:
            match = re.search(pattern, label, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Simple FY2023 format
                if len(groups) == 1:
                    fiscal_year = int(groups[0])
                    # Assume calendar year end (31 Dec)
                    end_date = date(fiscal_year, 12, 31)
                    start_date = date(fiscal_year - 1, 1, 1)
                
                # Year ended 31 Dec 2023 format
                elif len(groups) == 3:
                    day = int(groups[0])
                    month_str = groups[1].lower()
                    year = int(groups[2])
                    month = self.MONTH_MAP.get(month_str[:3])
                    
                    if not month:
                        continue
                    
                    end_date = date(year, month, day)
                    start_date = date(year - 1, month, day + 1 if day < 28 else 1)
                    fiscal_year = year
                
                # 2023-24 or 2023/2024 format
                elif len(groups) == 2:
                    year1 = int(groups[0])
                    year2_str = groups[1]
                    
                    # Handle short year format (23 -> 2023)
                    if len(year2_str) == 2:
                        year2 = int(str(year1)[:2] + year2_str)
                    else:
                        year2 = int(year2_str)
                    
                    end_date = date(year2, 12, 31)
                    start_date = date(year1, 1, 1)
                    fiscal_year = year2
                
                else:
                    continue
                
                return {
                    "period_type": "fiscal_year",
                    "start_date": start_date,
                    "end_date": end_date,
                    "fiscal_year": fiscal_year,
                    "original_label": label
                }
        
        return None
    
    def _parse_quarter(self, label: str) -> Optional[Dict[str, any]]:
        """Parse quarter labels."""
        for pattern in self.QUARTER_PATTERNS:
            match = re.search(pattern, label, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Q1 FY2023 format
                if len(groups) == 2 and groups[0].isdigit():
                    quarter = int(groups[0])
                    fiscal_year = int(groups[1])
                    
                    # Calculate quarter dates (assuming calendar year)
                    quarter_starts = {
                        1: (1, 1),
                        2: (4, 1),
                        3: (7, 1),
                        4: (10, 1)
                    }
                    quarter_ends = {
                        1: (3, 31),
                        2: (6, 30),
                        3: (9, 30),
                        4: (12, 31)
                    }
                    
                    start_month, start_day = quarter_starts[quarter]
                    end_month, end_day = quarter_ends[quarter]
                    
                    start_date = date(fiscal_year, start_month, start_day)
                    end_date = date(fiscal_year, end_month, end_day)
                
                # Three months ended 31 Mar 2023 format
                elif len(groups) == 3:
                    day = int(groups[0])
                    month_str = groups[1].lower()
                    year = int(groups[2])
                    month = self.MONTH_MAP.get(month_str[:3])
                    
                    if not month:
                        continue
                    
                    end_date = date(year, month, day)
                    # Approximate start date (3 months back)
                    start_month = month - 3 if month > 3 else month + 9
                    start_year = year if month > 3 else year - 1
                    start_date = date(start_year, start_month, day)
                    fiscal_year = year
                    quarter = (month - 1) // 3 + 1
                
                else:
                    continue
                
                return {
                    "period_type": "quarter",
                    "start_date": start_date,
                    "end_date": end_date,
                    "fiscal_year": fiscal_year,
                    "quarter": quarter,
                    "original_label": label
                }
        
        return None
    
    def _parse_half_year(self, label: str) -> Optional[Dict[str, any]]:
        """Parse half-year labels."""
        for pattern in self.HALF_YEAR_PATTERNS:
            match = re.search(pattern, label, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # H1 FY2023 format
                if len(groups) == 2 and groups[0].isdigit():
                    half = int(groups[0])
                    fiscal_year = int(groups[1])
                    
                    if half == 1:
                        start_date = date(fiscal_year, 1, 1)
                        end_date = date(fiscal_year, 6, 30)
                    else:  # half == 2
                        start_date = date(fiscal_year, 7, 1)
                        end_date = date(fiscal_year, 12, 31)
                
                # Six months ended 30 Jun 2023 format
                elif len(groups) == 3:
                    day = int(groups[0])
                    month_str = groups[1].lower()
                    year = int(groups[2])
                    month = self.MONTH_MAP.get(month_str[:3])
                    
                    if not month:
                        continue
                    
                    end_date = date(year, month, day)
                    # Approximate start date (6 months back)
                    start_month = month - 6 if month > 6 else month + 6
                    start_year = year if month > 6 else year - 1
                    start_date = date(start_year, start_month, day)
                    fiscal_year = year
                    half = 1 if month <= 6 else 2
                
                else:
                    continue
                
                return {
                    "period_type": "half_year",
                    "start_date": start_date,
                    "end_date": end_date,
                    "fiscal_year": fiscal_year,
                    "half": half,
                    "original_label": label
                }
        
        return None
    
    def normalize_period_label(self, label: str) -> str:
        """
        Normalize a period label to standard format.
        
        Args:
            label: Original period label
        
        Returns:
            Normalized label in format: "FY2023", "Q1-2023", "H1-2023"
        """
        parsed = self.parse_period_label(label)
        
        if not parsed:
            return label
        
        if parsed["period_type"] == "fiscal_year":
            return f"FY{parsed['fiscal_year']}"
        elif parsed["period_type"] == "quarter":
            return f"Q{parsed['quarter']}-{parsed['fiscal_year']}"
        elif parsed["period_type"] == "half_year":
            return f"H{parsed['half']}-{parsed['fiscal_year']}"
        
        return label
    
    def detect_fiscal_year_end(self, labels: List[str]) -> Optional[Tuple[int, int]]:
        """
        Detect fiscal year end month and day from a list of period labels.
        
        Args:
            labels: List of period labels
        
        Returns:
            Tuple of (month, day) or None if cannot detect
        """
        end_dates = []
        
        for label in labels:
            parsed = self.parse_period_label(label)
            if parsed and parsed["period_type"] == "fiscal_year":
                end_date = parsed["end_date"]
                end_dates.append((end_date.month, end_date.day))
        
        if not end_dates:
            return None
        
        # Find most common fiscal year end
        from collections import Counter
        most_common = Counter(end_dates).most_common(1)
        
        if most_common:
            return most_common[0][0]
        
        return None


class LabelStandardizer:
    """Standardize metric labels across different financial statements."""
    
    # Standard label mappings
    STANDARD_LABELS = {
        # Income Statement
        "revenue": ["revenue", "total revenue", "net revenue", "sales", "turnover", "net sales"],
        "gross_profit": ["gross profit", "gross margin"],
        "operating_profit": ["operating profit", "operating income", "ebit", "operating earnings"],
        "net_income": ["net income", "net profit", "profit for the year", "profit for the period", "net earnings"],
        "ebitda": ["ebitda", "adjusted ebitda"],
        
        # Balance Sheet
        "total_assets": ["total assets", "assets"],
        "current_assets": ["current assets"],
        "non_current_assets": ["non-current assets", "non current assets", "fixed assets"],
        "total_liabilities": ["total liabilities", "liabilities"],
        "current_liabilities": ["current liabilities"],
        "non_current_liabilities": ["non-current liabilities", "non current liabilities", "long-term liabilities"],
        "total_equity": ["total equity", "shareholders' equity", "stockholders' equity", "equity"],
        "retained_earnings": ["retained earnings", "accumulated profits"],
        
        # Cash Flow
        "operating_cash_flow": ["cash from operating activities", "operating cash flow", "net cash from operations"],
        "investing_cash_flow": ["cash from investing activities", "investing cash flow", "net cash used in investing"],
        "financing_cash_flow": ["cash from financing activities", "financing cash flow", "net cash from financing"],
        "free_cash_flow": ["free cash flow", "fcf"],
    }
    
    def __init__(self):
        self.logger = logger.bind(component="label_standardizer")
        self._build_reverse_mapping()
    
    def _build_reverse_mapping(self):
        """Build reverse mapping from variations to standard labels."""
        self.reverse_map = {}
        for standard_label, variations in self.STANDARD_LABELS.items():
            for variation in variations:
                self.reverse_map[variation.lower().strip()] = standard_label
    
    def standardize_label(self, label: str) -> str:
        """
        Standardize a metric label.
        
        Args:
            label: Original metric label
        
        Returns:
            Standardized label or original if no mapping found
        """
        label_clean = label.lower().strip()
        
        # Remove common prefixes/suffixes
        label_clean = re.sub(r'\s*\(.*?\)\s*', '', label_clean)  # Remove parentheses
        label_clean = re.sub(r'\s+', ' ', label_clean).strip()
        
        # Look up in reverse mapping
        standard = self.reverse_map.get(label_clean)
        
        if standard:
            self.logger.debug("label_standardized", original=label, standard=standard)
            return standard
        
        # If no exact match, try fuzzy matching
        standard = self._fuzzy_match(label_clean)
        if standard:
            return standard
        
        # Return original if no match
        return label
    
    def _fuzzy_match(self, label: str) -> Optional[str]:
        """Fuzzy match label to standard labels."""
        label_lower = label.lower()
        
        # Try substring matching
        for standard_label, variations in self.STANDARD_LABELS.items():
            for variation in variations:
                if variation in label_lower or label_lower in variation:
                    self.logger.debug("label_fuzzy_matched", original=label, standard=standard_label)
                    return standard_label
        
        return None
    
    def get_standard_labels(self, category: Optional[str] = None) -> List[str]:
        """
        Get list of all standard labels.
        
        Args:
            category: Optional category filter (not implemented)
        
        Returns:
            List of standard label names
        """
        return list(self.STANDARD_LABELS.keys())
    
    def add_custom_mapping(self, standard_label: str, variations: List[str]):
        """
        Add custom label mapping.
        
        Args:
            standard_label: Standard label name
            variations: List of label variations
        """
        if standard_label not in self.STANDARD_LABELS:
            self.STANDARD_LABELS[standard_label] = []
        
        self.STANDARD_LABELS[standard_label].extend(variations)
        
        # Update reverse mapping
        for variation in variations:
            self.reverse_map[variation.lower().strip()] = standard_label
        
        self.logger.info("custom_mapping_added", standard=standard_label, count=len(variations))
