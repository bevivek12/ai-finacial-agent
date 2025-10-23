"""Regex pattern library for financial section detection."""

import re
from typing import Dict, List, Pattern


class FinancialSectionPatterns:
    """Library of regex patterns for detecting financial statement sections."""
    
    # Income Statement / P&L patterns
    INCOME_STATEMENT_PATTERNS = [
        r'(?i)consolidated\s+income\s+statement',
        r'(?i)income\s+statement',
        r'(?i)statement\s+of\s+comprehensive\s+income',
        r'(?i)statement\s+of\s+income',
        r'(?i)profit\s+and\s+loss\s+statement',
        r'(?i)profit\s+&\s+loss\s+statement',
        r'(?i)p\s*&\s*l\s+statement',
        r'(?i)statement\s+of\s+profit\s+or\s+loss',
        r'(?i)consolidated\s+statement\s+of\s+operations',
    ]
    
    # Cash Flow Statement patterns
    CASH_FLOW_PATTERNS = [
        r'(?i)consolidated\s+cash\s+flow\s+statement',
        r'(?i)cash\s+flow\s+statement',
        r'(?i)statement\s+of\s+cash\s+flows',
        r'(?i)consolidated\s+statement\s+of\s+cash\s+flows',
        r'(?i)cashflow\s+statement',
    ]
    
    # Balance Sheet patterns
    BALANCE_SHEET_PATTERNS = [
        r'(?i)consolidated\s+balance\s+sheet',
        r'(?i)balance\s+sheet',
        r'(?i)statement\s+of\s+financial\s+position',
        r'(?i)consolidated\s+statement\s+of\s+financial\s+position',
        r'(?i)statement\s+of\s+assets',
    ]
    
    # Borrowings/Debt section patterns
    BORROWINGS_PATTERNS = [
        r'(?i)borrowings',
        r'(?i)debt\s+and\s+borrowings',
        r'(?i)loans\s+and\s+borrowings',
        r'(?i)financial\s+liabilities',
        r'(?i)long[\s-]?term\s+debt',
        r'(?i)bank\s+loans',
    ]
    
    # Notes to Financial Statements
    NOTES_PATTERNS = [
        r'(?i)notes\s+to\s+the\s+financial\s+statements',
        r'(?i)notes\s+to\s+financial\s+statements',
        r'(?i)notes\s+to\s+the\s+accounts',
        r'(?i)notes\s+to\s+accounts',
        r'(?i)accounting\s+policies',
    ]
    
    # Revenue/Turnover section patterns
    REVENUE_PATTERNS = [
        r'(?i)revenue',
        r'(?i)turnover',
        r'(?i)sales\s+revenue',
        r'(?i)net\s+sales',
        r'(?i)total\s+revenue',
    ]
    
    # EBITDA patterns
    EBITDA_PATTERNS = [
        r'(?i)EBITDA',
        r'(?i)earnings\s+before\s+interest,?\s+tax',
        r'(?i)operating\s+profit\s+before',
        r'(?i)adjusted\s+EBITDA',
    ]
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, List[str]]:
        """
        Get all pattern categories.
        
        Returns:
            Dictionary mapping section type to list of patterns
        """
        return {
            'income_statement': cls.INCOME_STATEMENT_PATTERNS,
            'cash_flow': cls.CASH_FLOW_PATTERNS,
            'balance_sheet': cls.BALANCE_SHEET_PATTERNS,
            'borrowings': cls.BORROWINGS_PATTERNS,
            'notes': cls.NOTES_PATTERNS,
            'revenue': cls.REVENUE_PATTERNS,
            'ebitda': cls.EBITDA_PATTERNS,
        }
    
    @classmethod
    def get_compiled_patterns(cls) -> Dict[str, List[Pattern]]:
        """
        Get all patterns as compiled regex objects.
        
        Returns:
            Dictionary mapping section type to list of compiled patterns
        """
        all_patterns = cls.get_all_patterns()
        compiled = {}
        
        for section_type, patterns in all_patterns.items():
            compiled[section_type] = [re.compile(p) for p in patterns]
        
        return compiled
    
    @classmethod
    def match_section_type(cls, text: str) -> List[str]:
        """
        Match text against all patterns to determine section types.
        
        Args:
            text: Text to match
            
        Returns:
            List of matching section types
        """
        matches = []
        compiled_patterns = cls.get_compiled_patterns()
        
        for section_type, patterns in compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    matches.append(section_type)
                    break  # One match per section type is enough
        
        return matches
    
    @classmethod
    def is_section_header(cls, text: str, min_match_score: float = 0.5) -> bool:
        """
        Determine if text is likely a section header.
        
        Args:
            text: Text to check
            min_match_score: Minimum score to consider a header
            
        Returns:
            True if text appears to be a section header
        """
        # Check length - headers are typically short
        if len(text) > 200:
            return False
        
        # Check if it matches any patterns
        matches = cls.match_section_type(text)
        if matches:
            return True
        
        # Check for common header characteristics
        text_lower = text.lower().strip()
        
        # All caps or title case
        if text.isupper() or text.istitle():
            # Contains financial keywords
            keywords = [
                'statement', 'report', 'financial', 'consolidated',
                'note', 'summary', 'analysis', 'position'
            ]
            if any(keyword in text_lower for keyword in keywords):
                return True
        
        return False


class MetricPatterns:
    """Patterns for detecting specific financial metrics."""
    
    # Revenue patterns
    REVENUE_PATTERNS = [
        r'(?i)revenue\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)\s*(million|thousand|billion)?',
        r'(?i)turnover\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)\s*(million|thousand|billion)?',
        r'(?i)total\s+revenue\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)net\s+sales\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
    ]
    
    # EBITDA patterns
    EBITDA_PATTERNS = [
        r'(?i)EBITDA\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)\s*(million|thousand|billion)?',
        r'(?i)adjusted\s+EBITDA\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)operating\s+profit\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
    ]
    
    # Debt patterns
    DEBT_PATTERNS = [
        r'(?i)total\s+debt\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)\s*(million|thousand|billion)?',
        r'(?i)net\s+debt\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)borrowings\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)long[\s-]?term\s+debt\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
    ]
    
    # Cash patterns
    CASH_PATTERNS = [
        r'(?i)cash\s+and\s+cash\s+equivalents\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)cash\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)\s*(million|thousand|billion)?',
    ]
    
    # Net Income patterns
    NET_INCOME_PATTERNS = [
        r'(?i)net\s+income\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)net\s+profit\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
        r'(?i)profit\s+for\s+the\s+year\s*:?\s*(£|GBP|USD|\$|€|EUR)?\s*([\d,\.]+)',
    ]
    
    @classmethod
    def extract_metric_value(cls, text: str, metric_type: str) -> List[Dict]:
        """
        Extract metric values from text.
        
        Args:
            text: Text to search
            metric_type: Type of metric to extract
            
        Returns:
            List of dictionaries with extracted values
        """
        pattern_map = {
            'revenue': cls.REVENUE_PATTERNS,
            'ebitda': cls.EBITDA_PATTERNS,
            'debt': cls.DEBT_PATTERNS,
            'cash': cls.CASH_PATTERNS,
            'net_income': cls.NET_INCOME_PATTERNS,
        }
        
        patterns = pattern_map.get(metric_type, [])
        results = []
        
        for pattern_str in patterns:
            pattern = re.compile(pattern_str)
            matches = pattern.finditer(text)
            
            for match in matches:
                groups = match.groups()
                result = {
                    'full_match': match.group(0),
                    'currency': groups[0] if len(groups) > 0 else None,
                    'value': groups[1] if len(groups) > 1 else None,
                    'scale': groups[2] if len(groups) > 2 else None,
                    'position': match.span(),
                }
                results.append(result)
        
        return results


class DatePatterns:
    """Patterns for detecting dates in financial documents."""
    
    DATE_PATTERNS = [
        r'(?i)year\s+ended\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(?i)period\s+ended\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(?i)as\s+at\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(?i)for\s+the\s+year\s+ended\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        r'(\d{4})-(\d{2})-(\d{2})',
    ]
    
    @classmethod
    def extract_dates(cls, text: str) -> List[Dict]:
        """
        Extract dates from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of dictionaries with date information
        """
        results = []
        
        for pattern_str in cls.DATE_PATTERNS:
            pattern = re.compile(pattern_str)
            matches = pattern.finditer(text)
            
            for match in matches:
                results.append({
                    'full_match': match.group(0),
                    'groups': match.groups(),
                    'position': match.span(),
                })
        
        return results
