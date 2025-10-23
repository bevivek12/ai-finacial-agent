"""
Unit tests for metric normalization and validation components.

Tests cover:
- Period parser
- Label standardizer
- Metric normalizer
- Currency/scale conversion
- Deterministic validator
"""

import pytest
from decimal import Decimal
from datetime import date

from src.utils.periods import PeriodParser, LabelStandardizer
from src.utils.currency import CurrencyConverter, ScaleConverter, MetricNormalizer
from src.services.metric_normalizer import MetricNormalizerService, MetricFilter
from src.services.validators import DeterministicValidator, ValidationAggregator
from src.models.schemas import FinancialMetric, CandidateValue, EntityType, EvidenceSource


class TestPeriodParser:
    """Test period parsing functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create period parser."""
        return PeriodParser()
    
    def test_fiscal_year_simple_format(self, parser):
        """Test parsing simple FY format."""
        result = parser.parse_period_label("FY2023")
        
        assert result is not None
        assert result["period_type"] == "fiscal_year"
        assert result["fiscal_year"] == 2023
    
    def test_fiscal_year_long_format(self, parser):
        """Test parsing long format."""
        result = parser.parse_period_label("Year ended 31 December 2023")
        
        assert result is not None
        assert result["period_type"] == "fiscal_year"
        assert result["fiscal_year"] == 2023
        assert result["end_date"] == date(2023, 12, 31)
    
    def test_quarter_format(self, parser):
        """Test parsing quarter format."""
        result = parser.parse_period_label("Q1 2023")
        
        assert result is not None
        assert result["period_type"] == "quarter"
        assert result["quarter"] == 1
        assert result["fiscal_year"] == 2023
    
    def test_normalize_period_label(self, parser):
        """Test period label normalization."""
        normalized = parser.normalize_period_label("Year ended 31 Dec 2023")
        assert normalized == "FY2023"
    
    def test_invalid_period_label(self, parser):
        """Test handling of invalid period label."""
        result = parser.parse_period_label("Invalid Period")
        assert result is None


class TestLabelStandardizer:
    """Test label standardization functionality."""
    
    @pytest.fixture
    def standardizer(self):
        """Create label standardizer."""
        return LabelStandardizer()
    
    def test_revenue_standardization(self, standardizer):
        """Test revenue label standardization."""
        assert standardizer.standardize_label("Total Revenue") == "revenue"
        assert standardizer.standardize_label("Net Sales") == "revenue"
        assert standardizer.standardize_label("Turnover") == "revenue"
    
    def test_profit_standardization(self, standardizer):
        """Test profit label standardization."""
        assert standardizer.standardize_label("Net Profit") == "net_income"
        assert standardizer.standardize_label("Profit for the year") == "net_income"
    
    def test_custom_mapping(self, standardizer):
        """Test adding custom label mapping."""
        standardizer.add_custom_mapping("custom_metric", ["My Custom Label"])
        assert standardizer.standardize_label("My Custom Label") == "custom_metric"


class TestCurrencyConverter:
    """Test currency conversion functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create currency converter."""
        return CurrencyConverter()
    
    def test_same_currency_conversion(self, converter):
        """Test conversion when currencies are the same."""
        result = converter.convert(Decimal("100"), "GBP", "GBP")
        assert result == Decimal("100")
    
    def test_gbp_to_usd_conversion(self, converter):
        """Test GBP to USD conversion."""
        result = converter.convert(Decimal("100"), "GBP", "USD")
        assert result > Decimal("100")  # GBP > USD typically
    
    def test_custom_exchange_rate(self):
        """Test custom exchange rate."""
        custom_rates = {"EUR": Decimal("1.15")}
        converter = CurrencyConverter(exchange_rates=custom_rates)
        
        result = converter.convert(Decimal("100"), "EUR", "GBP")
        assert result == Decimal("115.00")


class TestScaleConverter:
    """Test scale conversion functionality."""
    
    @pytest.fixture
    def converter(self):
        """Create scale converter."""
        return ScaleConverter()
    
    def test_millions_to_billions(self, converter):
        """Test conversion from millions to billions."""
        result = converter.convert_to_scale(Decimal("1000"), "millions", "billions")
        assert result == Decimal("1")
    
    def test_thousands_to_millions(self, converter):
        """Test conversion from thousands to millions."""
        result = converter.convert_to_scale(Decimal("1000"), "thousands", "millions")
        assert result == Decimal("1")
    
    def test_same_scale_conversion(self, converter):
        """Test conversion when scales are the same."""
        result = converter.convert_to_scale(Decimal("100"), "millions", "millions")
        assert result == Decimal("100")


class TestMetricNormalizerService:
    """Test metric normalizer service."""
    
    @pytest.fixture
    def normalizer(self):
        """Create metric normalizer service."""
        return MetricNormalizerService(base_currency="GBP", base_scale="millions")
    
    def test_normalize_metric(self, normalizer):
        """Test single metric normalization."""
        metric = FinancialMetric(
            metric_id="m1",
            metric_name="Total Revenue",
            value=Decimal("1000"),
            currency="USD",
            scale="thousands",
            period_end_date=date(2023, 12, 31)
        )
        
        normalized = normalizer.normalize_metric(metric)
        
        assert normalized.currency == "GBP"
        assert normalized.scale == "millions"
        assert normalized.metric_name == "revenue"
    
    def test_group_metrics_by_period(self, normalizer):
        """Test grouping metrics by period."""
        metrics = [
            FinancialMetric(
                metric_id="m1",
                metric_name="revenue",
                value=Decimal("100"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2023, 12, 31)
            ),
            FinancialMetric(
                metric_id="m2",
                metric_name="revenue",
                value=Decimal("90"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2022, 12, 31)
            ),
        ]
        
        grouped = normalizer.group_metrics_by_period(metrics)
        
        assert len(grouped) == 2
        assert "FY2023" in grouped
        assert "FY2022" in grouped


class TestDeterministicValidator:
    """Test deterministic validation."""
    
    @pytest.fixture
    def validator(self):
        """Create deterministic validator."""
        return DeterministicValidator()
    
    def test_unit_consistency_check(self, validator):
        """Test unit consistency validation."""
        candidate = CandidateValue(
            candidate_id="c1",
            metric_name="revenue",
            value=Decimal("100"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31),
            section_type="income_statement",
            source=EvidenceSource.TABLE_CELL,
            confidence_score=0.9,
            evidence={}
        )
        
        result = validator._check_unit_consistency(candidate)
        assert result["valid"] is True
    
    def test_invalid_currency(self, validator):
        """Test invalid currency detection."""
        candidate = CandidateValue(
            candidate_id="c1",
            metric_name="revenue",
            value=Decimal("100"),
            currency="INVALID",
            scale="millions",
            period_end_date=date(2023, 12, 31),
            section_type="income_statement",
            source=EvidenceSource.TABLE_CELL,
            confidence_score=0.9,
            evidence={}
        )
        
        result = validator._check_unit_consistency(candidate)
        assert result["valid"] is False
    
    def test_yoy_delta_calculation(self, validator):
        """Test year-over-year delta validation."""
        current = CandidateValue(
            candidate_id="c1",
            metric_name="revenue",
            value=Decimal("110"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023, 12, 31),
            section_type="income_statement",
            source=EvidenceSource.TABLE_CELL,
            confidence_score=0.9,
            evidence={}
        )
        
        prior = CandidateValue(
            candidate_id="c2",
            metric_name="revenue",
            value=Decimal("100"),
            currency="GBP",
            scale="millions",
            period_end_date=date(2022, 12, 31),
            section_type="income_statement",
            source=EvidenceSource.TABLE_CELL,
            confidence_score=0.9,
            evidence={}
        )
        
        all_candidates = [current, prior]
        result = validator._check_yoy_delta(current, all_candidates)
        
        assert result is not None
        assert result["valid"] is True
        assert "yoy_change" in result


class TestMetricFilter:
    """Test metric filtering utilities."""
    
    def test_filter_by_period(self):
        """Test filtering metrics by period."""
        metrics = [
            FinancialMetric(
                metric_id="m1",
                metric_name="revenue",
                value=Decimal("100"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2023, 12, 31)
            ),
            FinancialMetric(
                metric_id="m2",
                metric_name="revenue",
                value=Decimal("90"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2022, 12, 31)
            ),
        ]
        
        filtered = MetricFilter.filter_by_period(
            metrics,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
        
        assert len(filtered) == 1
        assert filtered[0].metric_id == "m1"
    
    def test_filter_by_label(self):
        """Test filtering metrics by label."""
        metrics = [
            FinancialMetric(
                metric_id="m1",
                metric_name="revenue",
                value=Decimal("100"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2023, 12, 31)
            ),
            FinancialMetric(
                metric_id="m2",
                metric_name="net_income",
                value=Decimal("10"),
                currency="GBP",
                scale="millions",
                period_end_date=date(2023, 12, 31)
            ),
        ]
        
        filtered = MetricFilter.filter_by_label(metrics, ["revenue"])
        
        assert len(filtered) == 1
        assert filtered[0].metric_name == "revenue"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
