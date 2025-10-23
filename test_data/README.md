# Test Data Documentation

This directory contains sample financial PDFs and ground truth data for testing the AI Financial Agent.

## Test Data Structure

```
test_data/
├── sample_pdfs/
│   ├── annual_report_simple.pdf          # Simple annual report
│   ├── annual_report_complex.pdf         # Complex multi-section report
│   ├── quarterly_report.pdf              # Quarterly financial report
│   └── interim_report.pdf                # Interim/half-year report
├── ground_truth/
│   ├── annual_report_simple.json         # Expected extraction results
│   ├── annual_report_complex.json
│   ├── quarterly_report.json
│   └── interim_report.json
└── README.md                              # This file
```

## Sample Data Files

### 1. annual_report_simple.pdf
**Description**: Basic annual report with standard financial statements
**Contains**:
- Income Statement (2 years of data)
- Balance Sheet (2 years of data)
- Cash Flow Statement (2 years of data)
- Simple table structures

**Ground Truth Metrics**:
```json
{
  "company_name": "Test Company Ltd",
  "fiscal_year_end": "2023-12-31",
  "metrics": [
    {
      "metric_name": "revenue",
      "value": 1000.5,
      "currency": "GBP",
      "scale": "millions",
      "period": "FY2023"
    },
    {
      "metric_name": "net_income",
      "value": 100.2,
      "currency": "GBP",
      "scale": "millions",
      "period": "FY2023"
    }
  ]
}
```

### 2. annual_report_complex.pdf
**Description**: Complex annual report with multiple entities and segments
**Contains**:
- Consolidated and standalone statements
- Segment reporting
- Multi-currency data
- Complex table structures
- Notes to accounts

### 3. quarterly_report.pdf
**Description**: Quarterly (Q1) financial report
**Contains**:
- Income Statement (Q1 2023 vs Q1 2022)
- Balance Sheet (as at 31 Mar 2023)
- Condensed Cash Flow Statement

### 4. interim_report.pdf
**Description**: Half-year (H1) interim report
**Contains**:
- Income Statement (H1 2023 vs H1 2022)
- Balance Sheet (as at 30 Jun 2023)
- Condensed Cash Flow Statement

## Ground Truth Format

Each ground truth JSON file follows this schema:

```json
{
  "document_metadata": {
    "company_name": "string",
    "report_type": "ANNUAL | QUARTERLY | INTERIM",
    "fiscal_period_end": "YYYY-MM-DD",
    "currency": "GBP | USD | EUR",
    "scale": "millions | billions"
  },
  "expected_sections": [
    {
      "section_type": "income_statement",
      "start_page": 1,
      "end_page": 2,
      "title": "Consolidated Income Statement"
    }
  ],
  "expected_metrics": [
    {
      "metric_name": "revenue",
      "value": 1000.5,
      "currency": "GBP",
      "scale": "millions",
      "period_end_date": "2023-12-31",
      "section_type": "income_statement",
      "evidence": {
        "page": 1,
        "table_row": 1,
        "table_col": 2
      }
    }
  ],
  "expected_derived_metrics": [
    {
      "metric_name": "revenue_growth_yoy",
      "value": 10.5,
      "unit": "percent"
    }
  ]
}
```

## Using Test Data

### In Unit Tests
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_pdf_path():
    return Path(__file__).parent / "test_data" / "sample_pdfs" / "annual_report_simple.pdf"

def test_pdf_processing(sample_pdf_path):
    from src.workflow.runner import run_financial_agent
    
    result = run_financial_agent(str(sample_pdf_path))
    assert result is not None
```

### For Validation
```python
import json
from pathlib import Path

def load_ground_truth(test_name):
    """Load ground truth data for a test."""
    truth_path = Path(__file__).parent / "test_data" / "ground_truth" / f"{test_name}.json"
    with open(truth_path) as f:
        return json.load(f)

def validate_extraction(result, ground_truth):
    """Validate extracted metrics against ground truth."""
    gt_metrics = {m["metric_name"]: m for m in ground_truth["expected_metrics"]}
    
    for metric in result["validated_metrics"]:
        if metric.metric_name in gt_metrics:
            expected = gt_metrics[metric.metric_name]
            assert abs(float(metric.value) - expected["value"]) < 0.01
```

## Creating Your Own Test Data

1. **Prepare PDF**: Create or obtain a financial PDF
2. **Manual Extraction**: Manually extract expected metrics
3. **Create Ground Truth**: Document in JSON format
4. **Add to Test Suite**: Create test case using the data

## Test Data Guidelines

- **Representativeness**: Include various report types and complexities
- **Coverage**: Cover all major financial sections
- **Edge Cases**: Include challenging scenarios (multi-currency, complex tables)
- **Realism**: Use realistic financial data patterns
- **Documentation**: Always document the expected results

## Generating Synthetic Test PDFs

For initial testing, you can generate synthetic financial PDFs:

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_simple_financial_pdf(output_path):
    """Generate a simple test financial PDF."""
    c = canvas.Canvas(output_path, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Test Company Ltd")
    c.drawString(100, 730, "Consolidated Income Statement")
    c.drawString(100, 710, "For the year ended 31 December 2023")
    
    # Table headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(100, 680, "Metric")
    c.drawString(300, 680, "2023")
    c.drawString(400, 680, "2022")
    
    # Data rows
    c.setFont("Helvetica", 10)
    rows = [
        ("Revenue", "1,000.5", "900.2"),
        ("Cost of Sales", "(600.3)", "(540.1)"),
        ("Gross Profit", "400.2", "360.1"),
        ("Operating Expenses", "(200.1)", "(180.0)"),
        ("Operating Profit", "200.1", "180.1"),
        ("Finance Costs", "(10.5)", "(9.2)"),
        ("Profit Before Tax", "189.6", "170.9"),
        ("Tax", "(89.4)", "(80.7)"),
        ("Net Income", "100.2", "90.2"),
    ]
    
    y = 660
    for row in rows:
        c.drawString(100, y, row[0])
        c.drawString(300, y, row[1])
        c.drawString(400, y, row[2])
        y -= 20
    
    c.save()

# Usage
generate_simple_financial_pdf("test_data/sample_pdfs/generated_simple.pdf")
```

## Validation Metrics

When testing, measure:
- **Extraction Accuracy**: % of metrics correctly extracted
- **Value Accuracy**: Absolute error in extracted values
- **Section Detection**: % of sections correctly identified
- **Processing Time**: Time to process each document
- **Error Rate**: % of documents that fail processing

## Notes

- Test PDFs should be added to `.gitignore` if they contain real financial data
- Ground truth files should be version controlled
- Update test data when adding new features
- Regularly validate test data accuracy

---

For questions or to contribute test data, see the main project documentation.
