"""
LLM Adjudicator Service.

This service uses LLM to adjudicate conflicting or uncertain metric candidates:
1. Construct detailed prompts with evidence and context
2. Query LLM for decision and reasoning
3. Parse LLM response and extract final value
4. Log reasoning for audit trail
"""

from typing import List, Dict, Optional
from decimal import Decimal
from loguru import logger
import json

from src.models.schemas import (
    CandidateValue, ValidationResult, FinancialMetric, 
    ValidationStatus, EntityType
)


class LLMAdjudicator:
    """
    LLM-based adjudicator for uncertain metric candidates.
    
    Uses structured prompts to:
    - Present conflicting candidates with evidence
    - Request LLM decision with reasoning
    - Parse and validate LLM response
    - Generate final metric with provenance
    """
    
    ADJUDICATION_PROMPT_TEMPLATE = """You are a financial data extraction expert reviewing candidate values for a metric.

**Metric Name:** {metric_name}
**Period:** {period}
**Section Type:** {section_type}

**Candidates:**
{candidates_formatted}

**Validation Issues:**
{validation_issues}

**Task:**
1. Review all candidate values and their evidence
2. Determine which candidate is most likely correct
3. Provide clear reasoning for your decision
4. Consider: source reliability, evidence quality, consistency with financial logic

**Response Format (JSON):**
{{
    "selected_candidate_id": "candidate_id",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation",
    "alternative_value": null or numeric value if correction needed,
    "flags": ["any concerns or notes"]
}}

Respond only with the JSON object, no other text."""
    
    def __init__(self, llm_client=None, model: str = "gpt-4"):
        """
        Initialize LLM adjudicator.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, etc.)
            model: Model name to use
        """
        self.llm_client = llm_client
        self.model = model
        self.logger = logger.bind(component="llm_adjudicator")
    
    def adjudicate_candidates(
        self,
        candidates: List[CandidateValue],
        validation_results: List[ValidationResult]
    ) -> List[FinancialMetric]:
        """
        Adjudicate a list of candidates that need LLM review.
        
        Args:
            candidates: List of candidate values
            validation_results: Corresponding validation results
        
        Returns:
            List of adjudicated financial metrics
        """
        self.logger.info("adjudicating_candidates", count=len(candidates))
        
        # Group candidates by metric and period
        grouped = self._group_candidates(candidates)
        
        adjudicated_metrics = []
        
        for (metric_name, period), metric_candidates in grouped.items():
            # Get validation results for these candidates
            candidate_ids = [c.candidate_id for c in metric_candidates]
            relevant_validations = [
                v for v in validation_results 
                if v.candidate_id in candidate_ids
            ]
            
            # Check if adjudication is needed
            needs_adjudication = any(
                v.status in [ValidationStatus.NEEDS_REVIEW, ValidationStatus.INVALID]
                for v in relevant_validations
            )
            
            if not needs_adjudication:
                # All candidates are valid, select highest confidence
                best_candidate = max(metric_candidates, key=lambda c: c.confidence_score)
                metric = self._candidate_to_metric(best_candidate)
                adjudicated_metrics.append(metric)
                continue
            
            # Perform LLM adjudication
            try:
                adjudicated_metric = self._adjudicate_with_llm(
                    metric_candidates,
                    relevant_validations
                )
                adjudicated_metrics.append(adjudicated_metric)
            except Exception as e:
                self.logger.error(
                    "adjudication_failed",
                    metric=metric_name,
                    period=period,
                    error=str(e)
                )
                # Fallback: use highest confidence candidate
                best_candidate = max(metric_candidates, key=lambda c: c.confidence_score)
                metric = self._candidate_to_metric(best_candidate)
                adjudicated_metrics.append(metric)
        
        self.logger.info(
            "adjudication_complete",
            adjudicated=len(adjudicated_metrics)
        )
        
        return adjudicated_metrics
    
    def _adjudicate_with_llm(
        self,
        candidates: List[CandidateValue],
        validation_results: List[ValidationResult]
    ) -> FinancialMetric:
        """Adjudicate a single metric using LLM."""
        # Get metric info from first candidate
        metric_name = candidates[0].metric_name
        period = candidates[0].period_end_date
        section_type = candidates[0].section_type
        
        self.logger.info(
            "invoking_llm_adjudication",
            metric=metric_name,
            period=str(period),
            candidate_count=len(candidates)
        )
        
        # Format candidates for prompt
        candidates_formatted = self._format_candidates(candidates)
        
        # Format validation issues
        validation_issues = self._format_validation_issues(validation_results)
        
        # Construct prompt
        prompt = self.ADJUDICATION_PROMPT_TEMPLATE.format(
            metric_name=metric_name,
            period=str(period) if period else "Unknown",
            section_type=section_type,
            candidates_formatted=candidates_formatted,
            validation_issues=validation_issues
        )
        
        # Query LLM
        if self.llm_client is None:
            # Fallback if no LLM client configured
            self.logger.warning("no_llm_client_using_fallback")
            return self._fallback_adjudication(candidates)
        
        response = self._query_llm(prompt)
        
        # Parse LLM response
        adjudication = self._parse_llm_response(response)
        
        # Select candidate based on LLM decision
        selected_candidate = self._find_candidate_by_id(
            candidates,
            adjudication["selected_candidate_id"]
        )
        
        if selected_candidate is None:
            self.logger.warning("llm_selected_invalid_candidate_using_fallback")
            return self._fallback_adjudication(candidates)
        
        # Create final metric
        metric = self._candidate_to_metric(
            selected_candidate,
            llm_reasoning=adjudication["reasoning"],
            llm_confidence=adjudication["confidence"],
            alternative_value=adjudication.get("alternative_value")
        )
        
        self.logger.info(
            "llm_adjudication_complete",
            metric=metric_name,
            selected_id=selected_candidate.candidate_id,
            llm_confidence=adjudication["confidence"]
        )
        
        return metric
    
    def _format_candidates(self, candidates: List[CandidateValue]) -> str:
        """Format candidates for LLM prompt."""
        formatted = []
        
        for i, candidate in enumerate(candidates, 1):
            evidence = candidate.evidence or {}
            
            candidate_str = f"""
Candidate {i}:
- ID: {candidate.candidate_id}
- Value: {candidate.value} {candidate.currency} ({candidate.scale})
- Source: {candidate.source.value if candidate.source else 'Unknown'}
- Confidence Score: {candidate.confidence_score:.2f}
- Evidence:
  * Section: {candidate.section_type}
  * Raw Value: {evidence.get('raw_value', 'N/A')}
  * Raw Label: {evidence.get('raw_label', 'N/A')}
  * Page: {evidence.get('page', 'N/A')}
  * Additional Context: {json.dumps(evidence, default=str)}
"""
            formatted.append(candidate_str)
        
        return "\n".join(formatted)
    
    def _format_validation_issues(self, validation_results: List[ValidationResult]) -> str:
        """Format validation issues for LLM prompt."""
        if not validation_results:
            return "No validation issues detected."
        
        issues = []
        for result in validation_results:
            if result.issues:
                issues.append(f"- Candidate {result.candidate_id}:")
                for issue in result.issues:
                    issues.append(f"  * {issue}")
        
        if not issues:
            return "No validation issues detected."
        
        return "\n".join(issues)
    
    def _query_llm(self, prompt: str) -> str:
        """
        Query LLM with prompt.
        
        Args:
            prompt: Formatted prompt
        
        Returns:
            LLM response text
        """
        # This is a placeholder - actual implementation depends on LLM client
        # Example for OpenAI:
        try:
            if hasattr(self.llm_client, 'chat'):
                # OpenAI-style client
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a financial data extraction expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                return response.choices[0].message.content
            else:
                # Generic client
                return self.llm_client.generate(prompt)
        except Exception as e:
            self.logger.error("llm_query_failed", error=str(e))
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, any]:
        """Parse LLM JSON response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            response_clean = response_clean.strip()
            
            # Parse JSON
            adjudication = json.loads(response_clean)
            
            # Validate required fields
            required_fields = ["selected_candidate_id", "confidence", "reasoning"]
            for field in required_fields:
                if field not in adjudication:
                    raise ValueError(f"Missing required field: {field}")
            
            return adjudication
        except Exception as e:
            self.logger.error("llm_response_parse_failed", error=str(e), response=response)
            raise
    
    def _candidate_to_metric(
        self,
        candidate: CandidateValue,
        llm_reasoning: Optional[str] = None,
        llm_confidence: Optional[float] = None,
        alternative_value: Optional[Decimal] = None
    ) -> FinancialMetric:
        """Convert candidate to final metric."""
        # Use alternative value if provided by LLM
        final_value = alternative_value if alternative_value is not None else candidate.value
        
        metric = FinancialMetric(
            metric_id=candidate.candidate_id,
            metric_name=candidate.metric_name,
            value=final_value,
            currency=candidate.currency,
            scale=candidate.scale,
            period_end_date=candidate.period_end_date,
            entity_type=EntityType.CONSOLIDATED,  # Default
            llm_reasoning=llm_reasoning,
            llm_confidence=llm_confidence
        )
        
        return metric
    
    def _fallback_adjudication(self, candidates: List[CandidateValue]) -> FinancialMetric:
        """Fallback adjudication without LLM (use highest confidence)."""
        best_candidate = max(candidates, key=lambda c: c.confidence_score)
        return self._candidate_to_metric(best_candidate)
    
    def _find_candidate_by_id(
        self,
        candidates: List[CandidateValue],
        candidate_id: str
    ) -> Optional[CandidateValue]:
        """Find candidate by ID."""
        for candidate in candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        return None
    
    def _group_candidates(
        self,
        candidates: List[CandidateValue]
    ) -> Dict[tuple, List[CandidateValue]]:
        """Group candidates by metric name and period."""
        from datetime import date
        
        grouped = {}
        for candidate in candidates:
            key = (candidate.metric_name, candidate.period_end_date)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(candidate)
        
        return grouped


class PromptBuilder:
    """Builder for LLM adjudication prompts."""
    
    @staticmethod
    def build_adjudication_prompt(
        metric_name: str,
        candidates: List[CandidateValue],
        validation_results: List[ValidationResult],
        context: Optional[Dict[str, any]] = None
    ) -> str:
        """
        Build a detailed adjudication prompt.
        
        Args:
            metric_name: Name of the metric
            candidates: List of candidates
            validation_results: Validation results
            context: Additional context (optional)
        
        Returns:
            Formatted prompt string
        """
        sections = []
        
        # Header
        sections.append("# Financial Metric Adjudication\n")
        sections.append(f"**Metric:** {metric_name}\n")
        
        # Context
        if context:
            sections.append("## Context")
            for key, value in context.items():
                sections.append(f"- {key}: {value}")
            sections.append("")
        
        # Candidates
        sections.append("## Candidate Values\n")
        for i, candidate in enumerate(candidates, 1):
            sections.append(f"### Candidate {i}")
            sections.append(f"- Value: {candidate.value}")
            sections.append(f"- Currency: {candidate.currency}")
            sections.append(f"- Scale: {candidate.scale}")
            sections.append(f"- Source: {candidate.source}")
            sections.append(f"- Confidence: {candidate.confidence_score:.2f}")
            sections.append("")
        
        # Validation issues
        sections.append("## Validation Issues\n")
        for result in validation_results:
            if result.issues:
                sections.append(f"Candidate {result.candidate_id}:")
                for issue in result.issues:
                    sections.append(f"- {issue}")
        
        return "\n".join(sections)
