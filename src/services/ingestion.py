"""PDF Ingestion Service for validating and classifying financial documents."""

import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF for basic PDF operations

from ..models.schemas import DocumentMetadata, ReportType
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger({"module": "pdf_ingestion"})


class PDFIngestionService:
    """Service for ingesting and validating PDF financial documents."""
    
    def __init__(self):
        """Initialize the PDF ingestion service."""
        self.config = get_config()
        self.logger = logger
        self.max_file_size_bytes = self.config.pdf.max_file_size_mb * 1024 * 1024
    
    def ingest(self, pdf_path: str) -> DocumentMetadata:
        """
        Ingest a PDF document and extract metadata.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentMetadata object
            
        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PDF is invalid or too large
        """
        self.logger.info("ingesting_pdf", pdf_path=pdf_path)
        
        # Validate PDF file
        self._validate_pdf(pdf_path)
        
        # Extract basic metadata from PDF
        pdf_metadata = self._extract_pdf_metadata(pdf_path)
        
        # Extract business metadata (company name, dates, etc.)
        business_metadata = self._extract_business_metadata(pdf_path, pdf_metadata)
        
        # Classify report type
        report_type = self._classify_report_type(pdf_path, business_metadata)
        
        # Create DocumentMetadata object
        metadata = DocumentMetadata(
            document_id=self._generate_document_id(pdf_path),
            company_name=business_metadata.get('company_name', 'Unknown Company'),
            company_identifier=business_metadata.get('company_identifier'),
            report_type=report_type,
            fiscal_period_end=business_metadata.get('fiscal_period_end', date.today()),
            currency=business_metadata.get('currency', self.config.normalization.default_currency),
            filing_date=business_metadata.get('filing_date'),
            source_path=str(Path(pdf_path).resolve()),
            page_count=pdf_metadata.get('page_count'),
            file_size_bytes=pdf_metadata.get('file_size_bytes')
        )
        
        self.logger.info(
            "pdf_ingested_successfully",
            document_id=metadata.document_id,
            company_name=metadata.company_name,
            report_type=metadata.report_type.value
        )
        
        return metadata
    
    def _validate_pdf(self, pdf_path: str) -> None:
        """
        Validate that the PDF file exists and is readable.
        
        Args:
            pdf_path: Path to PDF file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid
        """
        # Check if file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > self.max_file_size_bytes:
            raise ValueError(
                f"PDF file too large: {file_size / (1024*1024):.2f} MB "
                f"(max: {self.config.pdf.max_file_size_mb} MB)"
            )
        
        # Check if it's a valid PDF
        try:
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                raise ValueError("PDF has no pages")
            doc.close()
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PDF: {str(e)}")
        
        self.logger.debug("pdf_validation_passed", pdf_path=pdf_path, file_size_mb=file_size/(1024*1024))
    
    def _extract_pdf_metadata(self, pdf_path: str) -> dict:
        """
        Extract basic metadata from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of PDF metadata
        """
        metadata = {}
        
        try:
            doc = fitz.open(pdf_path)
            
            # Get page count
            metadata['page_count'] = len(doc)
            
            # Get file size
            metadata['file_size_bytes'] = os.path.getsize(pdf_path)
            
            # Get PDF metadata
            pdf_info = doc.metadata
            metadata['title'] = pdf_info.get('title', '')
            metadata['author'] = pdf_info.get('author', '')
            metadata['subject'] = pdf_info.get('subject', '')
            metadata['creator'] = pdf_info.get('creator', '')
            metadata['producer'] = pdf_info.get('producer', '')
            
            # Parse creation/modification dates
            if pdf_info.get('creationDate'):
                metadata['creation_date'] = self._parse_pdf_date(pdf_info['creationDate'])
            if pdf_info.get('modDate'):
                metadata['modification_date'] = self._parse_pdf_date(pdf_info['modDate'])
            
            doc.close()
            
        except Exception as e:
            self.logger.warning("pdf_metadata_extraction_failed", error=str(e))
        
        return metadata
    
    def _extract_business_metadata(self, pdf_path: str, pdf_metadata: dict) -> dict:
        """
        Extract business-specific metadata (company name, dates, etc.).
        
        Args:
            pdf_path: Path to PDF file
            pdf_metadata: Basic PDF metadata
            
        Returns:
            Dictionary of business metadata
        """
        business_metadata = {}
        
        try:
            doc = fitz.open(pdf_path)
            
            # Extract text from first few pages for analysis
            first_pages_text = ""
            for page_num in range(min(3, len(doc))):
                first_pages_text += doc[page_num].get_text()
            
            doc.close()
            
            # Extract company name
            company_name = self._extract_company_name(first_pages_text, pdf_metadata)
            if company_name:
                business_metadata['company_name'] = company_name
            
            # Extract company identifier (ticker, etc.)
            company_id = self._extract_company_identifier(first_pages_text)
            if company_id:
                business_metadata['company_identifier'] = company_id
            
            # Extract fiscal period
            fiscal_period = self._extract_fiscal_period(first_pages_text)
            if fiscal_period:
                business_metadata['fiscal_period_end'] = fiscal_period
            
            # Extract currency
            currency = self._extract_currency(first_pages_text)
            if currency:
                business_metadata['currency'] = currency
            
        except Exception as e:
            self.logger.warning("business_metadata_extraction_failed", error=str(e))
        
        return business_metadata
    
    def _classify_report_type(self, pdf_path: str, business_metadata: dict) -> ReportType:
        """
        Classify the type of financial report.
        
        Args:
            pdf_path: Path to PDF file
            business_metadata: Business metadata dictionary
            
        Returns:
            ReportType enum value
        """
        # Check filename first
        filename_lower = Path(pdf_path).name.lower()
        
        if 'annual' in filename_lower or 'annual report' in filename_lower:
            return ReportType.ANNUAL
        elif 'half' in filename_lower or 'h1' in filename_lower or 'h2' in filename_lower:
            return ReportType.HALF_YEAR
        elif 'quarter' in filename_lower or 'q1' in filename_lower or 'q2' in filename_lower:
            return ReportType.QUARTERLY
        elif 'rns' in filename_lower:
            return ReportType.RNS
        
        # Check document content
        try:
            doc = fitz.open(pdf_path)
            first_page_text = doc[0].get_text().lower()
            doc.close()
            
            if 'annual report' in first_page_text:
                return ReportType.ANNUAL
            elif 'half year' in first_page_text or 'interim report' in first_page_text:
                return ReportType.HALF_YEAR
            elif 'quarterly' in first_page_text or 'quarter' in first_page_text:
                return ReportType.QUARTERLY
            elif 'regulatory news' in first_page_text or 'rns' in first_page_text:
                return ReportType.RNS
        except Exception as e:
            self.logger.warning("report_type_classification_failed", error=str(e))
        
        # Default to annual
        self.logger.warning("defaulting_to_annual_report_type", pdf_path=pdf_path)
        return ReportType.ANNUAL
    
    def _extract_company_name(self, text: str, pdf_metadata: dict) -> Optional[str]:
        """Extract company name from document text."""
        # Try PDF metadata first
        if pdf_metadata.get('author'):
            return pdf_metadata['author']
        
        # Look for common patterns
        patterns = [
            r'([\w\s]+)\s+(plc|PLC|Ltd|Limited|Inc|Corp|Corporation)',
            r'([\w\s]+)\s+Annual Report',
            r'([\w\s]+)\s+Financial Statements'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:1000])
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_company_identifier(self, text: str) -> Optional[str]:
        """Extract company identifier/ticker from text."""
        # Look for common ticker patterns
        ticker_patterns = [
            r'\b([A-Z]{2,4}\.L)\b',  # LSE format (e.g., TSCO.L)
            r'\b([A-Z]{2,4})\b:\s*[A-Z]{2,4}',  # NYSE/NASDAQ format
        ]
        
        for pattern in ticker_patterns:
            match = re.search(pattern, text[:500])
            if match:
                return match.group(1)
        
        return None
    
    def _extract_fiscal_period(self, text: str) -> Optional[date]:
        """Extract fiscal period end date from text."""
        # Look for date patterns
        date_patterns = [
            r'year ended?\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
            r'period ended?\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
            r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})'
        ]
        
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, text[:1000], re.IGNORECASE)
            if match:
                try:
                    day = int(match.group(1))
                    month_name = match.group(2).lower()
                    year = int(match.group(3))
                    
                    month = months.get(month_name)
                    if month:
                        return date(year, month, day)
                except Exception:
                    continue
        
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract primary currency from text."""
        # Check for currency mentions in first page
        if '£' in text or 'GBP' in text or 'sterling' in text.lower():
            return 'GBP'
        elif '$' in text or 'USD' in text:
            return 'USD'
        elif '€' in text or 'EUR' in text or 'euro' in text.lower():
            return 'EUR'
        
        return None
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date string to datetime."""
        try:
            # PDF dates are typically in format: D:YYYYMMDDHHmmSS
            if date_str.startswith('D:'):
                date_str = date_str[2:16]  # Extract YYYYMMDDHHmmSS
                return datetime.strptime(date_str, '%Y%m%d%H%M%S')
        except Exception:
            pass
        return None
    
    def _generate_document_id(self, pdf_path: str) -> str:
        """Generate a unique document ID."""
        # Use filename + timestamp
        filename = Path(pdf_path).stem
        timestamp = int(datetime.now().timestamp())
        return f"doc_{filename}_{timestamp}"
