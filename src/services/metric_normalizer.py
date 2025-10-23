"""
Metric Normalizer Service.

This service orchestrates the complete normalization pipeline for financial metrics:
1. Currency conversion to base currency
2. Scale adjustment to base scale
3. Period label standardization
4. Metric label standardization
5. Entity type normalization
"""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import date
from loguru import logger

from src.models.schemas import FinancialMetric, EntityType
from src.utils.currency import CurrencyConverter, ScaleConverter, MetricNormalizer as CurrencyScaleNormalizer
from src.utils.periods import PeriodParser, LabelStandardizer


class MetricNormalizerService:
    """
    Complete metric normalization service.
    
    Normalizes financial metrics across multiple dimensions:
    - Currency (convert to base currency)
    - Scale (convert to base scale: millions)
    - Period labels (standardize format)
    - Metric labels (standardize naming)
    - Entity types (consolidate variants)
    """
    
    def __init__(
        self,
        base_currency: str = "GBP",
        base_scale: str = "millions",
        exchange_rates: Optional[Dict[str, Decimal]] = None
    ):
        """
        Initialize metric normalizer.
        
        Args:
            base_currency: Base currency for normalization (default: GBP)
            base_scale: Base scale for normalization (default: millions)
            exchange_rates: Custom exchange rates (optional)
        """
        self.base_currency = base_currency
        self.base_scale = base_scale
        
        # Initialize sub-components
        self.currency_scale_normalizer = CurrencyScaleNormalizer(
            base_currency=base_currency,
            base_scale=base_scale,
            exchange_rates=exchange_rates
        )
        self.period_parser = PeriodParser()
        self.label_standardizer = LabelStandardizer()
        
        self.logger = logger.bind(component="metric_normalizer_service")
    
    def normalize_metric(
        self,
        metric: FinancialMetric,
        preserve_original: bool = True
    ) -> FinancialMetric:
        """
        Normalize a single financial metric.
        
        Args:
            metric: Input metric to normalize
            preserve_original: Whether to preserve original values in metadata
        
        Returns:
            Normalized metric with standardized values
        """
        self.logger.debug(
            "normalizing_metric",
            metric_id=metric.metric_id,
            original_value=float(metric.value),
            original_currency=metric.currency,
            original_scale=metric.scale
        )
        
        # Store original values if requested
        original_data = {}
        if preserve_original:
            original_data = {
                "original_value": float(metric.value),
                "original_currency": metric.currency,
                "original_scale": metric.scale,
                "original_metric_name": metric.metric_name
            }
        
        # 1. Normalize currency and scale
        normalized_currency_scale = self.currency_scale_normalizer.normalize_value(
            amount=metric.value,
            currency=metric.currency,
            scale=metric.scale
        )
        
        normalized_value = normalized_currency_scale["normalized_value"]
        normalized_currency = normalized_currency_scale["normalized_currency"]
        normalized_scale = normalized_currency_scale["normalized_scale"]
        
        # 2. Standardize metric label
        standardized_label = self.label_standardizer.standardize_label(metric.metric_name)
        
        # 3. Create normalized metric
        normalized_metric = FinancialMetric(
            metric_id=metric.metric_id,
            metric_name=standardized_label,
            value=normalized_value,
            currency=normalized_currency,
            scale=normalized_scale,
            period_end_date=metric.period_end_date,
            entity_type=metric.entity_type,
            **original_data
        )
        
        self.logger.info(
            "metric_normalized",
            metric_id=metric.metric_id,
            normalized_value=float(normalized_value),
            normalized_currency=normalized_currency,
            normalized_scale=normalized_scale,
            standardized_label=standardized_label
        )
        
        return normalized_metric
    
    def normalize_metrics(
        self,
        metrics: List[FinancialMetric],
        preserve_original: bool = True
    ) -> List[FinancialMetric]:
        """
        Normalize a batch of financial metrics.
        
        Args:
            metrics: List of metrics to normalize
            preserve_original: Whether to preserve original values
        
        Returns:
            List of normalized metrics
        """
        self.logger.info("normalizing_metrics_batch", count=len(metrics))
        
        normalized_metrics = []
        for metric in metrics:
            try:
                normalized = self.normalize_metric(metric, preserve_original)
                normalized_metrics.append(normalized)
            except Exception as e:
                self.logger.error(
                    "metric_normalization_failed",
                    metric_id=metric.metric_id,
                    error=str(e)
                )
                # Optionally include failed metrics as-is
                normalized_metrics.append(metric)
        
        self.logger.info(
            "metrics_batch_normalized",
            total=len(metrics),
            successful=len(normalized_metrics)
        )
        
        return normalized_metrics
    
    def parse_and_normalize_period(self, period_label: str) -> Optional[Dict[str, any]]:
        """
        Parse and normalize a period label.
        
        Args:
            period_label: Period label string
        
        Returns:
            Dictionary with parsed and normalized period information
        """
        parsed = self.period_parser.parse_period_label(period_label)
        
        if not parsed:
            return None
        
        normalized_label = self.period_parser.normalize_period_label(period_label)
        
        return {
            **parsed,
            "normalized_label": normalized_label
        }
    
    def detect_fiscal_year_end(self, metrics: List[FinancialMetric]) -> Optional[Dict[str, int]]:
        """
        Detect fiscal year end from a list of metrics.
        
        Args:
            metrics: List of financial metrics
        
        Returns:
            Dictionary with fiscal year end information (month, day)
        """
        # Extract unique period end dates
        end_dates = list(set([m.period_end_date for m in metrics]))
        
        # Find most common month/day combination
        from collections import Counter
        date_tuples = [(d.month, d.day) for d in end_dates]
        most_common = Counter(date_tuples).most_common(1)
        
        if most_common:
            month, day = most_common[0][0]
            return {"month": month, "day": day}
        
        return None
    
    def group_metrics_by_period(
        self,
        metrics: List[FinancialMetric]
    ) -> Dict[str, List[FinancialMetric]]:
        """
        Group metrics by their fiscal periods.
        
        Args:
            metrics: List of financial metrics
        
        Returns:
            Dictionary mapping period labels to metrics
        """
        grouped = {}
        
        for metric in metrics:
            # Create period key from end date
            period_key = f"FY{metric.period_end_date.year}"
            
            if period_key not in grouped:
                grouped[period_key] = []
            
            grouped[period_key].append(metric)
        
        self.logger.info(
            "metrics_grouped_by_period",
            total_metrics=len(metrics),
            periods=len(grouped)
        )
        
        return grouped
    
    def group_metrics_by_label(
        self,
        metrics: List[FinancialMetric]
    ) -> Dict[str, List[FinancialMetric]]:
        """
        Group metrics by their standardized labels.
        
        Args:
            metrics: List of financial metrics
        
        Returns:
            Dictionary mapping metric labels to metrics
        """
        grouped = {}
        
        for metric in metrics:
            label = metric.metric_name
            
            if label not in grouped:
                grouped[label] = []
            
            grouped[label].append(metric)
        
        self.logger.info(
            "metrics_grouped_by_label",
            total_metrics=len(metrics),
            unique_labels=len(grouped)
        )
        
        return grouped
    
    def create_time_series(
        self,
        metrics: List[FinancialMetric],
        metric_name: str
    ) -> List[Dict[str, any]]:
        """
        Create a time series for a specific metric across periods.
        
        Args:
            metrics: List of financial metrics
            metric_name: Name of the metric to track
        
        Returns:
            List of dictionaries with period and value information
        """
        # Filter metrics by name
        filtered = [m for m in metrics if m.metric_name == metric_name]
        
        # Sort by period end date
        sorted_metrics = sorted(filtered, key=lambda m: m.period_end_date)
        
        # Create time series
        time_series = []
        for metric in sorted_metrics:
            time_series.append({
                "period_end_date": metric.period_end_date,
                "value": metric.value,
                "currency": metric.currency,
                "scale": metric.scale,
                "entity_type": metric.entity_type
            })
        
        self.logger.info(
            "time_series_created",
            metric_name=metric_name,
            periods=len(time_series)
        )
        
        return time_series
    
    def validate_normalization_consistency(
        self,
        metrics: List[FinancialMetric]
    ) -> Dict[str, any]:
        """
        Validate that all metrics are consistently normalized.
        
        Args:
            metrics: List of metrics to validate
        
        Returns:
            Validation report with consistency checks
        """
        currencies = set([m.currency for m in metrics])
        scales = set([m.scale for m in metrics])
        
        is_consistent = (
            len(currencies) == 1 and 
            list(currencies)[0] == self.base_currency and
            len(scales) == 1 and 
            list(scales)[0] == self.base_scale
        )
        
        report = {
            "is_consistent": is_consistent,
            "total_metrics": len(metrics),
            "currencies": list(currencies),
            "scales": list(scales),
            "expected_currency": self.base_currency,
            "expected_scale": self.base_scale
        }
        
        if not is_consistent:
            self.logger.warning("normalization_inconsistency_detected", report=report)
        else:
            self.logger.info("normalization_validated", total=len(metrics))
        
        return report
    
    def add_custom_label_mapping(self, standard_label: str, variations: List[str]):
        """
        Add custom metric label mapping.
        
        Args:
            standard_label: Standard label name
            variations: List of label variations
        """
        self.label_standardizer.add_custom_mapping(standard_label, variations)
        self.logger.info(
            "custom_label_mapping_added",
            standard=standard_label,
            variations=len(variations)
        )
    
    def update_exchange_rate(self, currency: str, rate: Decimal):
        """
        Update exchange rate for a currency.
        
        Args:
            currency: Currency code
            rate: Exchange rate to base currency
        """
        self.currency_scale_normalizer.currency_converter.exchange_rates[currency] = rate
        self.logger.info("exchange_rate_updated", currency=currency, rate=float(rate))


class MetricFilter:
    """Utility for filtering normalized metrics."""
    
    @staticmethod
    def filter_by_period(
        metrics: List[FinancialMetric],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[FinancialMetric]:
        """
        Filter metrics by period date range.
        
        Args:
            metrics: List of metrics to filter
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            Filtered list of metrics
        """
        filtered = metrics
        
        if start_date:
            filtered = [m for m in filtered if m.period_end_date >= start_date]
        
        if end_date:
            filtered = [m for m in filtered if m.period_end_date <= end_date]
        
        return filtered
    
    @staticmethod
    def filter_by_label(
        metrics: List[FinancialMetric],
        labels: List[str]
    ) -> List[FinancialMetric]:
        """
        Filter metrics by label names.
        
        Args:
            metrics: List of metrics to filter
            labels: List of label names to include
        
        Returns:
            Filtered list of metrics
        """
        return [m for m in metrics if m.metric_name in labels]
    
    @staticmethod
    def filter_by_entity_type(
        metrics: List[FinancialMetric],
        entity_type: EntityType
    ) -> List[FinancialMetric]:
        """
        Filter metrics by entity type.
        
        Args:
            metrics: List of metrics to filter
            entity_type: Entity type to filter by
        
        Returns:
            Filtered list of metrics
        """
        return [m for m in metrics if m.entity_type == entity_type]
    
    @staticmethod
    def get_latest_period(metrics: List[FinancialMetric]) -> List[FinancialMetric]:
        """
        Get metrics from the latest period.
        
        Args:
            metrics: List of metrics
        
        Returns:
            Metrics from the latest period
        """
        if not metrics:
            return []
        
        latest_date = max(m.period_end_date for m in metrics)
        return [m for m in metrics if m.period_end_date == latest_date]
    
    @staticmethod
    def get_fiscal_year(
        metrics: List[FinancialMetric],
        fiscal_year: int
    ) -> List[FinancialMetric]:
        """
        Get metrics for a specific fiscal year.
        
        Args:
            metrics: List of metrics
            fiscal_year: Fiscal year to filter by
        
        Returns:
            Metrics for the specified fiscal year
        """
        return [m for m in metrics if m.period_end_date.year == fiscal_year]
