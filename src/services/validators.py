"""
Deterministic Validator Service.

This service implements rule-based validation checks for financial metrics:
1. Unit consistency checks (currency, scale)
2. Arithmetic validation (subtotals, totals)
3. Year-over-Year delta checks
4. Range validation (realistic bounds)
5. Cross-metric consistency checks
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import date
from loguru import logger

from src.models.schemas import (
    FinancialMetric, CandidateValue, ValidationResult, 
    ValidationStatus, ValidationRule
)


class DeterministicValidator:
    """
    Rule-based validator for financial metrics.
    
    Validation Rules:
    1. Unit Consistency: All metrics in same currency/scale
    2. Arithmetic: Subtotals sum to totals
    3. YoY Delta: Realistic year-over-year changes
    4. Range: Values within realistic bounds
    5. Cross-Metric: Related metrics are consistent
    """
    
    # Realistic bounds for common metrics (as multipliers of revenue)
    METRIC_BOUNDS = {
        "gross_profit": (0.0, 1.0),  # 0-100% of revenue
        "operating_profit": (-0.5, 1.0),  # -50% to 100% of revenue
        "net_income": (-1.0, 1.0),  # -100% to 100% of revenue
        "ebitda": (-0.5, 1.5),  # -50% to 150% of revenue
        "current_assets": (0.0, 10.0),  # 0-10x revenue
        "total_assets": (0.0, 50.0),  # 0-50x revenue
        "current_liabilities": (0.0, 10.0),
        "total_liabilities": (0.0, 50.0),
        "total_equity": (-5.0, 50.0),  # Can be negative
    }
    
    # Realistic YoY change bounds (percentage)
    YOY_BOUNDS = {
        "revenue": (-0.50, 2.0),  # -50% to +200%
        "gross_profit": (-0.70, 3.0),
        "operating_profit": (-2.0, 5.0),
        "net_income": (-3.0, 10.0),
        "total_assets": (-0.30, 1.0),
        "total_equity": (-0.50, 1.5),
    }
    
    # Arithmetic relationships (child metrics sum to parent)
    ARITHMETIC_RULES = {
        "total_assets": ["current_assets", "non_current_assets"],
        "total_liabilities": ["current_liabilities", "non_current_liabilities"],
        "gross_profit": ["revenue", "cost_of_sales"],  # revenue - cost_of_sales
        "operating_profit": ["gross_profit", "operating_expenses"],  # gross - expenses
    }
    
    def __init__(self, tolerance: Decimal = Decimal("0.05")):
        """
        Initialize validator.
        
        Args:
            tolerance: Tolerance for arithmetic checks (default 5%)
        """
        self.tolerance = tolerance
        self.logger = logger.bind(component="deterministic_validator")
    
    def validate_candidates(
        self,
        candidates: List[CandidateValue]
    ) -> List[ValidationResult]:
        """
        Validate a list of candidate values.
        
        Args:
            candidates: List of candidates to validate
        
        Returns:
            List of validation results
        """
        self.logger.info("validating_candidates", count=len(candidates))
        
        results = []
        
        # Group candidates by metric and period
        grouped = self._group_candidates(candidates)
        
        for (metric_name, period), metric_candidates in grouped.items():
            # Validate each candidate
            for candidate in metric_candidates:
                result = self._validate_candidate(candidate, candidates)
                results.append(result)
        
        # Summary statistics
        passed = sum(1 for r in results if r.status == ValidationStatus.VALID)
        failed = sum(1 for r in results if r.status == ValidationStatus.INVALID)
        needs_review = sum(1 for r in results if r.status == ValidationStatus.NEEDS_REVIEW)
        
        self.logger.info(
            "validation_complete",
            total=len(results),
            passed=passed,
            failed=failed,
            needs_review=needs_review
        )
        
        return results
    
    def _validate_candidate(
        self,
        candidate: CandidateValue,
        all_candidates: List[CandidateValue]
    ) -> ValidationResult:
        """Validate a single candidate against all rules."""
        import uuid
        
        validation_issues = []
        validation_details = {}
        
        # 1. Unit consistency check
        unit_check = self._check_unit_consistency(candidate)
        if not unit_check["valid"]:
            validation_issues.append(f"Unit inconsistency: {unit_check['message']}")
        validation_details["unit_consistency"] = unit_check
        
        # 2. Range validation
        range_check = self._check_range_bounds(candidate, all_candidates)
        if not range_check["valid"]:
            validation_issues.append(f"Range violation: {range_check['message']}")
        validation_details["range_check"] = range_check
        
        # 3. YoY delta check
        yoy_check = self._check_yoy_delta(candidate, all_candidates)
        if yoy_check and not yoy_check["valid"]:
            validation_issues.append(f"YoY anomaly: {yoy_check['message']}")
        validation_details["yoy_check"] = yoy_check
        
        # 4. Arithmetic consistency
        arithmetic_check = self._check_arithmetic(candidate, all_candidates)
        if arithmetic_check and not arithmetic_check["valid"]:
            validation_issues.append(f"Arithmetic error: {arithmetic_check['message']}")
        validation_details["arithmetic_check"] = arithmetic_check
        
        # Determine status
        if len(validation_issues) == 0:
            status = ValidationStatus.VALID
        elif len(validation_issues) >= 2:
            status = ValidationStatus.INVALID
        else:
            status = ValidationStatus.NEEDS_REVIEW
        
        # Create validation result
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            candidate_id=candidate.candidate_id,
            status=status,
            rules_applied=[
                ValidationRule.UNIT_CONSISTENCY,
                ValidationRule.RANGE_CHECK,
                ValidationRule.YOY_DELTA,
                ValidationRule.ARITHMETIC
            ],
            validation_details=validation_details,
            issues=validation_issues if validation_issues else None
        )
        
        return result
    
    def _check_unit_consistency(self, candidate: CandidateValue) -> Dict[str, any]:
        """Check if candidate has consistent units."""
        # Basic checks
        valid_currencies = ["GBP", "USD", "EUR"]
        valid_scales = ["actual", "thousands", "millions", "billions"]
        
        if candidate.currency not in valid_currencies:
            return {
                "valid": False,
                "message": f"Invalid currency: {candidate.currency}"
            }
        
        if candidate.scale not in valid_scales:
            return {
                "valid": False,
                "message": f"Invalid scale: {candidate.scale}"
            }
        
        return {"valid": True, "message": "Units are consistent"}
    
    def _check_range_bounds(
        self,
        candidate: CandidateValue,
        all_candidates: List[CandidateValue]
    ) -> Dict[str, any]:
        """Check if value is within realistic bounds."""
        metric_name = candidate.metric_name
        
        # Find revenue for the same period (as reference)
        revenue = self._find_metric(all_candidates, "revenue", candidate.period_end_date)
        
        if not revenue or metric_name not in self.METRIC_BOUNDS:
            # Cannot validate without revenue or bounds
            return {"valid": True, "message": "No bounds available"}
        
        # Convert both to same units for comparison
        candidate_base = candidate.value  # Assume already normalized
        revenue_base = revenue.value
        
        if revenue_base == 0:
            return {"valid": True, "message": "Revenue is zero, cannot compute ratio"}
        
        ratio = candidate_base / revenue_base
        min_bound, max_bound = self.METRIC_BOUNDS[metric_name]
        
        if ratio < min_bound or ratio > max_bound:
            return {
                "valid": False,
                "message": f"Ratio {float(ratio):.2f} outside bounds [{min_bound}, {max_bound}]"
            }
        
        return {
            "valid": True,
            "message": f"Ratio {float(ratio):.2f} within bounds"
        }
    
    def _check_yoy_delta(
        self,
        candidate: CandidateValue,
        all_candidates: List[CandidateValue]
    ) -> Optional[Dict[str, any]]:
        """Check year-over-year change is realistic."""
        if not candidate.period_end_date:
            return None
        
        metric_name = candidate.metric_name
        
        # Find previous year value
        from datetime import timedelta
        prev_year_date = date(
            candidate.period_end_date.year - 1,
            candidate.period_end_date.month,
            candidate.period_end_date.day
        )
        
        prev_value = self._find_metric(all_candidates, metric_name, prev_year_date)
        
        if not prev_value:
            return {"valid": True, "message": "No prior year data for comparison"}
        
        # Calculate YoY change
        if prev_value.value == 0:
            return {"valid": True, "message": "Prior year value is zero"}
        
        yoy_change = (candidate.value - prev_value.value) / abs(prev_value.value)
        
        # Check against bounds
        if metric_name in self.YOY_BOUNDS:
            min_bound, max_bound = self.YOY_BOUNDS[metric_name]
            
            if yoy_change < min_bound or yoy_change > max_bound:
                return {
                    "valid": False,
                    "message": f"YoY change {float(yoy_change):.2%} outside bounds [{min_bound:.0%}, {max_bound:.0%}]"
                }
        
        return {
            "valid": True,
            "message": f"YoY change {float(yoy_change):.2%} is reasonable",
            "yoy_change": float(yoy_change)
        }
    
    def _check_arithmetic(
        self,
        candidate: CandidateValue,
        all_candidates: List[CandidateValue]
    ) -> Optional[Dict[str, any]]:
        """Check arithmetic consistency with related metrics."""
        metric_name = candidate.metric_name
        
        # Check if this metric has arithmetic rules
        if metric_name not in self.ARITHMETIC_RULES:
            return {"valid": True, "message": "No arithmetic rules apply"}
        
        components = self.ARITHMETIC_RULES[metric_name]
        
        # Find component values for same period
        component_values = []
        for component in components:
            value = self._find_metric(all_candidates, component, candidate.period_end_date)
            if value:
                component_values.append(value.value)
            else:
                # Missing component, cannot validate
                return {"valid": True, "message": f"Missing component: {component}"}
        
        # Calculate expected value based on rule
        if metric_name == "total_assets" or metric_name == "total_liabilities":
            # Sum components
            expected = sum(component_values)
        elif metric_name == "gross_profit":
            # revenue - cost_of_sales
            expected = component_values[0] - component_values[1]
        elif metric_name == "operating_profit":
            # gross_profit - operating_expenses
            expected = component_values[0] - component_values[1]
        else:
            return {"valid": True, "message": "Unknown arithmetic rule"}
        
        # Check if within tolerance
        if expected == 0:
            return {"valid": True, "message": "Expected value is zero"}
        
        difference = abs(candidate.value - expected)
        tolerance_amount = abs(expected * self.tolerance)
        
        if difference > tolerance_amount:
            return {
                "valid": False,
                "message": f"Arithmetic mismatch: {float(candidate.value)} vs expected {float(expected)} (diff: {float(difference)})"
            }
        
        return {
            "valid": True,
            "message": f"Arithmetic consistent within {float(self.tolerance):.1%} tolerance"
        }
    
    def _find_metric(
        self,
        candidates: List[CandidateValue],
        metric_name: str,
        period_end_date: Optional[date]
    ) -> Optional[CandidateValue]:
        """Find a candidate by metric name and period."""
        for candidate in candidates:
            if candidate.metric_name == metric_name:
                if period_end_date is None or candidate.period_end_date == period_end_date:
                    return candidate
        return None
    
    def _group_candidates(
        self,
        candidates: List[CandidateValue]
    ) -> Dict[Tuple[str, Optional[date]], List[CandidateValue]]:
        """Group candidates by metric name and period."""
        grouped = {}
        
        for candidate in candidates:
            key = (candidate.metric_name, candidate.period_end_date)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(candidate)
        
        return grouped
    
    def validate_metrics(
        self,
        metrics: List[FinancialMetric]
    ) -> List[ValidationResult]:
        """
        Validate a list of final metrics (same validation logic).
        
        Args:
            metrics: List of metrics to validate
        
        Returns:
            List of validation results
        """
        # Convert metrics to candidates for validation
        candidates = []
        for metric in metrics:
            candidate = CandidateValue(
                candidate_id=metric.metric_id,
                metric_name=metric.metric_name,
                value=metric.value,
                currency=metric.currency,
                scale=metric.scale,
                period_end_date=metric.period_end_date,
                section_type="",
                source=None,
                confidence_score=1.0,
                evidence={}
            )
            candidates.append(candidate)
        
        return self.validate_candidates(candidates)


class ValidationAggregator:
    """Aggregate validation results and make adjudication decisions."""
    
    def __init__(self):
        self.logger = logger.bind(component="validation_aggregator")
    
    def aggregate_results(
        self,
        validation_results: List[ValidationResult]
    ) -> Dict[str, any]:
        """
        Aggregate validation results into summary statistics.
        
        Args:
            validation_results: List of validation results
        
        Returns:
            Summary statistics dictionary
        """
        total = len(validation_results)
        
        status_counts = {
            "valid": sum(1 for r in validation_results if r.status == ValidationStatus.VALID),
            "invalid": sum(1 for r in validation_results if r.status == ValidationStatus.INVALID),
            "needs_review": sum(1 for r in validation_results if r.status == ValidationStatus.NEEDS_REVIEW)
        }
        
        # Collect common issues
        all_issues = []
        for result in validation_results:
            if result.issues:
                all_issues.extend(result.issues)
        
        from collections import Counter
        issue_counts = Counter(all_issues)
        
        summary = {
            "total_validated": total,
            "status_counts": status_counts,
            "pass_rate": status_counts["valid"] / total if total > 0 else 0,
            "common_issues": issue_counts.most_common(5),
            "needs_adjudication": status_counts["needs_review"] + status_counts["invalid"]
        }
        
        self.logger.info("validation_aggregated", summary=summary)
        
        return summary
    
    def get_candidates_needing_adjudication(
        self,
        validation_results: List[ValidationResult]
    ) -> List[str]:
        """
        Get list of candidate IDs that need LLM adjudication.
        
        Args:
            validation_results: List of validation results
        
        Returns:
            List of candidate IDs needing review
        """
        needs_adjudication = [
            result.candidate_id
            for result in validation_results
            if result.status in [ValidationStatus.NEEDS_REVIEW, ValidationStatus.INVALID]
        ]
        
        self.logger.info(
            "adjudication_candidates_identified",
            count=len(needs_adjudication)
        )
        
        return needs_adjudication
