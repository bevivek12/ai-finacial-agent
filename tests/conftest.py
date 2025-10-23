"""
Pytest configuration and shared fixtures.
"""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date


@pytest.fixture
def sample_financial_metric():
    """Create a sample financial metric for testing."""
    from src.models.schemas import FinancialMetric
    
    return FinancialMetric(
        metric_id="test_metric_1",
        metric_name="revenue",
        value=Decimal("1000.50"),
        currency="GBP",
        scale="millions",
        period_end_date=date(2023, 12, 31)
    )


@pytest.fixture
def sample_candidate():
    """Create a sample candidate value for testing."""
    from src.models.schemas import CandidateValue, EvidenceSource
    
    return CandidateValue(
        candidate_id="test_candidate_1",
        metric_name="revenue",
        value=Decimal("1000.50"),
        currency="GBP",
        scale="millions",
        period_end_date=date(2023, 12, 31),
        section_type="income_statement",
        source=EvidenceSource.TABLE_CELL,
        confidence_score=0.95,
        evidence={
            "table_id": "t1",
            "row_index": 1,
            "column_index": 2
        }
    )


@pytest.fixture
def sample_metrics_list():
    """Create a list of sample metrics for testing."""
    from src.models.schemas import FinancialMetric
    
    return [
        FinancialMetric(
            metric_id=f"m{i}",
            metric_name="revenue",
            value=Decimal(str(1000 + i * 100)),
            currency="GBP",
            scale="millions",
            period_end_date=date(2023 - i, 12, 31)
        )
        for i in range(3)
    ]


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)
