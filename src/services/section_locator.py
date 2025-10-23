"""Section Locator Service using hybrid regex + embedding approach."""

from typing import List, Optional, Tuple

from ..models.schemas import Section, TextBlock
from ..services.patterns import FinancialSectionPatterns
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger({"module": "section_locator"})


class SectionLocator:
    """Service for locating financial statement sections in documents."""
    
    def __init__(self):
        """Initialize the section locator."""
        self.config = get_config()
        self.logger = logger
        self.patterns = FinancialSectionPatterns()
        
        # Weights for hybrid scoring
        self.regex_weight = self.config.section_detection.regex_weight
        self.embedding_weight = self.config.section_detection.embedding_weight
        self.similarity_threshold = self.config.section_detection.similarity_threshold
    
    def locate_sections(self, text_blocks: List[TextBlock]) -> List[Section]:
        """
        Locate financial statement sections in text blocks.
        
        Args:
            text_blocks: List of text blocks from PDF
            
        Returns:
            List of identified sections
        """
        self.logger.info("locating_sections", total_blocks=len(text_blocks))
        
        sections = []
        
        # First pass: Use regex to find section headers
        regex_sections = self._locate_sections_regex(text_blocks)
        
        self.logger.info(
            "regex_detection_complete",
            sections_found=len(regex_sections)
        )
        
        # For now, return regex results
        # TODO: Implement embedding-based search for non-standard sections
        sections = regex_sections
        
        # Merge overlapping or duplicate sections
        sections = self._merge_sections(sections)
        
        self.logger.info("section_location_complete", total_sections=len(sections))
        
        return sections
    
    def _locate_sections_regex(self, text_blocks: List[TextBlock]) -> List[Section]:
        """
        Locate sections using regex pattern matching.
        
        Args:
            text_blocks: List of text blocks
            
        Returns:
            List of sections found via regex
        """
        sections = []
        section_candidates = []
        
        # Scan through text blocks looking for section headers
        for idx, block in enumerate(text_blocks):
            # Check if this block is a section header
            if self.patterns.is_section_header(block.text):
                # Determine section type
                section_types = self.patterns.match_section_type(block.text)
                
                if section_types:
                    # Use the first matched type
                    section_type = section_types[0]
                    
                    section_candidates.append({
                        'type': section_type,
                        'name': block.text.strip(),
                        'start_page': block.page_number,
                        'start_block_idx': idx,
                        'confidence': 0.9,  # High confidence for regex matches
                    })
        
        # Determine section boundaries
        for i, candidate in enumerate(section_candidates):
            # End page is either the start of next section or last page
            if i + 1 < len(section_candidates):
                end_page = section_candidates[i + 1]['start_page'] - 1
                if end_page < candidate['start_page']:
                    end_page = candidate['start_page']
            else:
                # Last section extends to end of document
                end_page = text_blocks[-1].page_number if text_blocks else candidate['start_page']
            
            section = Section(
                section_id=f"section_{candidate['type']}_{candidate['start_page']}",
                section_type=candidate['type'],
                section_name=candidate['name'],
                start_page=candidate['start_page'],
                end_page=end_page,
                confidence_score=candidate['confidence'],
                detection_method='regex'
            )
            
            sections.append(section)
        
        return sections
    
    def _merge_sections(self, sections: List[Section]) -> List[Section]:
        """
        Merge overlapping or duplicate sections.
        
        Args:
            sections: List of sections
            
        Returns:
            Merged list of sections
        """
        if not sections:
            return []
        
        # Sort by start page
        sorted_sections = sorted(sections, key=lambda s: s.start_page)
        
        merged = []
        current = sorted_sections[0]
        
        for next_section in sorted_sections[1:]:
            # Check if sections overlap or are duplicates
            if (next_section.section_type == current.section_type and
                next_section.start_page <= current.end_page + 1):
                # Merge: extend current section
                current = Section(
                    section_id=current.section_id,
                    section_type=current.section_type,
                    section_name=current.section_name,
                    start_page=current.start_page,
                    end_page=max(current.end_page, next_section.end_page),
                    confidence_score=max(current.confidence_score, next_section.confidence_score),
                    detection_method=current.detection_method
                )
                self.logger.debug(
                    "sections_merged",
                    type=current.section_type,
                    pages=f"{current.start_page}-{current.end_page}"
                )
            else:
                # No overlap, add current and move to next
                merged.append(current)
                current = next_section
        
        # Add the last section
        merged.append(current)
        
        return merged
    
    def get_section_text(
        self,
        section: Section,
        text_blocks: List[TextBlock]
    ) -> str:
        """
        Extract all text from a section.
        
        Args:
            section: Section to extract
            text_blocks: All text blocks
            
        Returns:
            Combined text from section
        """
        section_text = []
        
        for block in text_blocks:
            if section.start_page <= block.page_number <= section.end_page:
                section_text.append(block.text)
        
        return '\n\n'.join(section_text)
    
    def find_section_by_type(
        self,
        sections: List[Section],
        section_type: str
    ) -> Optional[Section]:
        """
        Find first section of a specific type.
        
        Args:
            sections: List of sections
            section_type: Type to find
            
        Returns:
            First matching section or None
        """
        for section in sections:
            if section.section_type == section_type:
                return section
        
        return None
    
    def validate_sections(self, sections: List[Section]) -> Tuple[bool, List[str]]:
        """
        Validate that critical sections are present.
        
        Args:
            sections: List of detected sections
            
        Returns:
            Tuple of (is_valid, list of missing sections)
        """
        # Critical sections for financial reports
        critical_sections = [
            'income_statement',
            'balance_sheet',
            'cash_flow'
        ]
        
        found_types = set(s.section_type for s in sections)
        missing = [s for s in critical_sections if s not in found_types]
        
        is_valid = len(missing) == 0
        
        if not is_valid:
            self.logger.warning(
                "missing_critical_sections",
                missing=missing,
                found=list(found_types)
            )
        
        return is_valid, missing
