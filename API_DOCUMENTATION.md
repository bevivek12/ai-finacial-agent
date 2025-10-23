# API Documentation

## AI Financial Agent - API Reference

This document provides comprehensive API documentation for all major components of the AI Financial Agent.

---

## Table of Contents

1. [Core Services](#core-services)
2. [PDF Parsers](#pdf-parsers)
3. [Data Models](#data-models)
4. [Utilities](#utilities)
5. [Workflow Nodes](#workflow-nodes)
6. [Export Services](#export-services)

---

## Core Services

### PDFIngestionService

**Module**: `src.services.ingestion`

Validates and extracts metadata from PDF documents.

#### Methods

##### `ingest(pdf_path: str) -> DocumentMetadata`

Ingests a PDF file and extracts metadata.

**Parameters:**
- `pdf_path` (str): Path to the PDF file

**Returns:**
- `DocumentMetadata`: Extracted document metadata

**Raises:**
- `FileNotFoundError`: If PDF file doesn't exist
- `ValueError`: If PDF is invalid or corrupted

**Example:**
```python
from src.services.ingestion import PDFIngestionService

service = PDFIngestionService()
metadata = service.ingest("annual_report.pdf")
print(f"Company: {metadata.company_name}")
```

---

### CandidateGenerator

**Module**: `src.services.candidate_generator`

Generates candidate metric values from PDF content.

#### Methods

##### `generate_candidates(sections: List[Section], table_blocks: List[TableBlock], text_blocks: List[TextBlock], target_metrics: Optional[List[str]] = None) -> List[CandidateValue]`

Extract candidate values from tables and text.

**Parameters:**
- `sections`: List of detected financial sections
- `table_blocks`: List of extracted table blocks
- `text_blocks`: List of extracted text blocks
- `target_metrics`: Optional list of specific metrics to extract

**Returns:**
- `List[CandidateValue]`: List of candidate values with evidence

**Example:**
```python
from src.services.candidate_generator import CandidateGenerator

generator = CandidateGenerator()
candidates = generator.generate_candidates(
    sections=sections,
    table_blocks=tables,
    text_blocks=text
)
```

---

### MetricNormalizerService

**Module**: `src.services.metric_normalizer`

Normalizes financial metrics across multiple dimensions.

#### Constructor

##### `__init__(base_currency: str = "GBP", base_scale: str = "millions", exchange_rates: Optional[Dict[str, Decimal]] = None)`

**Parameters:**
- `base_currency`: Target currency for normalization (default: "GBP")
- `base_scale`: Target scale for normalization (default: "millions")
- `exchange_rates`: Custom exchange rates dictionary

#### Methods

##### `normalize_metric(metric: FinancialMetric, preserve_original: bool = True) -> FinancialMetric`

Normalize a single financial metric.

**Parameters:**
- `metric`: Metric to normalize
- `preserve_original`: Whether to preserve original values in metadata

**Returns:**
- `FinancialMetric`: Normalized metric

**Example:**
```python
from src.services.metric_normalizer import MetricNormalizerService

normalizer = MetricNormalizerService(base_currency="GBP")
normalized = normalizer.normalize_metric(metric)
```

##### `normalize_metrics(metrics: List[FinancialMetric]) -> List[FinancialMetric]`

Normalize a batch of metrics.

---

### DeterministicValidator

**Module**: `src.services.validators`

Performs rule-based validation on financial metrics.

#### Constructor

##### `__init__(tolerance: Decimal = Decimal("0.05"))`

**Parameters:**
- `tolerance`: Tolerance for arithmetic checks (default: 5%)

#### Methods

##### `validate_candidates(candidates: List[CandidateValue]) -> List[ValidationResult]`

Validate a list of candidate values.

**Parameters:**
- `candidates`: List of candidates to validate

**Returns:**
- `List[ValidationResult]`: Validation results for each candidate

**Validation Rules:**
1. **Unit Consistency**: Validates currency and scale
2. **Range Bounds**: Checks realistic value ranges
3. **YoY Delta**: Validates year-over-year changes
4. **Arithmetic**: Checks subtotal/total consistency

**Example:**
```python
from src.services.validators import DeterministicValidator

validator = DeterministicValidator(tolerance=Decimal("0.05"))
results = validator.validate_candidates(candidates)

for result in results:
    print(f"{result.candidate_id}: {result.status}")
```

---

### LLMAdjudicator

**Module**: `src.services.llm_adjudicator`

Uses LLM to adjudicate conflicting metric candidates.

#### Constructor

##### `__init__(llm_client=None, model: str = "gpt-4")`

**Parameters:**
- `llm_client`: LLM client instance (OpenAI, etc.)
- `model`: Model name to use

#### Methods

##### `adjudicate_candidates(candidates: List[CandidateValue], validation_results: List[ValidationResult]) -> List[FinancialMetric]`

Adjudicate candidates using LLM.

**Parameters:**
- `candidates`: List of candidates
- `validation_results`: Corresponding validation results

**Returns:**
- `List[FinancialMetric]`: Final validated metrics

**Example:**
```python
from src.services.llm_adjudicator import LLMAdjudicator
from openai import OpenAI

llm_client = OpenAI(api_key="your-key")
adjudicator = LLMAdjudicator(llm_client=llm_client)

metrics = adjudicator.adjudicate_candidates(
    candidates=candidates,
    validation_results=results
)
```

---

### DerivedMetricsComputer

**Module**: `src.analysis.derived_metrics`

Computes derived financial metrics and ratios.

#### Methods

##### `compute_all_metrics(validated_metrics: List[FinancialMetric]) -> List[FinancialMetric]`

Compute all possible derived metrics.

**Parameters:**
- `validated_metrics`: List of validated base metrics

**Returns:**
- `List[FinancialMetric]`: List of derived metrics

**Computed Metrics:**
- Growth rates (YoY)
- Profitability ratios (margins, ROE, ROA)
- Leverage ratios (debt-to-equity, etc.)
- Liquidity ratios (current, quick)

**Example:**
```python
from src.analysis.derived_metrics import DerivedMetricsComputer

computer = DerivedMetricsComputer()
derived = computer.compute_all_metrics(validated_metrics)
```

---

### ExportService

**Module**: `src.export.export_service`

Exports financial data to multiple formats.

#### Constructor

##### `__init__(output_dir: str = "./output")`

**Parameters:**
- `output_dir`: Base output directory for exports

#### Methods

##### `export_all(company_name: str, report_period: date, metrics: List[FinancialMetric], derived_metrics: Optional[List[FinancialMetric]] = None, commentary: Optional[Dict[str, str]] = None, formats: List[str] = ["word", "excel", "json"]) -> Dict[str, str]`

Export to all requested formats.

**Parameters:**
- `company_name`: Company name
- `report_period`: Reporting period end date
- `metrics`: Financial metrics
- `derived_metrics`: Derived metrics (optional)
- `commentary`: Commentary sections (optional)
- `formats`: List of export formats

**Returns:**
- `Dict[str, str]`: Mapping of format to output file path

**Example:**
```python
from src.export.export_service import ExportService

export_service = ExportService(output_dir="./reports")
paths = export_service.export_all(
    company_name="Test Company",
    report_period=date(2023, 12, 31),
    metrics=metrics,
    formats=["word", "excel"]
)

print(f"Word: {paths['word']}")
print(f"Excel: {paths['excel']}")
```

---

## PDF Parsers

### PyMuPDFParser

**Module**: `src.parsers.pymupdf_parser`

Extracts text blocks using PyMuPDF.

#### Methods

##### `parse_pdf(pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]`

Parse PDF and extract text blocks.

**Returns:**
- Tuple of (text_blocks, table_blocks)

---

### PDFPlumberParser

**Module**: `src.parsers.pdfplumber_parser`

Extracts tables using pdfplumber.

#### Methods

##### `parse_pdf(pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]`

Parse PDF and extract table blocks.

---

### CamelotParser

**Module**: `src.parsers.camelot_parser`

Extracts complex tables using Camelot.

#### Methods

##### `parse_pdf(pdf_path: str) -> Tuple[List[TextBlock], List[TableBlock]]`

Parse PDF and extract complex tables.

---

## Data Models

### FinancialMetric

**Module**: `src.models.schemas`

Represents a validated financial metric.

#### Fields

- `metric_id` (str): Unique identifier
- `metric_name` (str): Metric name
- `value` (Decimal): Metric value
- `currency` (str): Currency code
- `scale` (str): Scale (millions, billions, etc.)
- `period_end_date` (date): Period end date
- `entity_type` (EntityType): Entity type

#### Methods

##### `to_base_units() -> Decimal`

Convert value to base units (actual amount).

**Example:**
```python
from src.models.schemas import FinancialMetric
from decimal import Decimal
from datetime import date

metric = FinancialMetric(
    metric_id="m1",
    metric_name="revenue",
    value=Decimal("1000"),
    currency="GBP",
    scale="millions",
    period_end_date=date(2023, 12, 31)
)

base_value = metric.to_base_units()  # 1,000,000,000
```

---

### CandidateValue

**Module**: `src.models.schemas`

Represents a candidate metric value with evidence.

#### Fields

- `candidate_id` (str): Unique identifier
- `metric_name` (str): Metric name
- `value` (Decimal): Candidate value
- `currency` (str): Currency
- `scale` (str): Scale
- `period_end_date` (Optional[date]): Period end date
- `section_type` (str): Section where found
- `source` (EvidenceSource): Source type
- `confidence_score` (float): Confidence score (0-1)
- `evidence` (Dict): Evidence dictionary

---

## Utilities

### PeriodParser

**Module**: `src.utils.periods`

Parses financial period labels.

#### Methods

##### `parse_period_label(label: str) -> Optional[Dict[str, any]]`

Parse period label into structured format.

**Supported Formats:**
- FY2023
- Year ended 31 December 2023
- Q1 2023
- H1 2023
- 2023-24

**Example:**
```python
from src.utils.periods import PeriodParser

parser = PeriodParser()
result = parser.parse_period_label("FY2023")
# {'period_type': 'fiscal_year', 'fiscal_year': 2023, ...}
```

---

### CurrencyConverter

**Module**: `src.utils.currency`

Converts between currencies.

#### Methods

##### `convert(amount: Decimal, from_currency: str, to_currency: str) -> Decimal`

Convert amount between currencies.

**Example:**
```python
from src.utils.currency import CurrencyConverter
from decimal import Decimal

converter = CurrencyConverter()
usd_amount = converter.convert(Decimal("100"), "GBP", "USD")
```

---

## Workflow Integration

### Running the Complete Workflow

```python
from src.workflow.runner import run_financial_agent

result = run_financial_agent(
    pdf_path="annual_report.pdf",
    output_dir="./output",
    config_path="config/config.yaml"
)

# Access results
print(f"Extracted {len(result['validated_metrics'])} metrics")
print(f"Generated {len(result['derived_metrics'])} derived metrics")
print(f"Exports: {result['export_paths']}")
```

---

## Error Handling

All services implement comprehensive error handling:

```python
try:
    result = service.process(data)
except FileNotFoundError:
    # Handle missing file
    pass
except ValueError:
    # Handle invalid data
    pass
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

---

## Configuration

### Loading Configuration

```python
from src.utils.config import load_config

# Load default config
config = load_config()

# Load environment-specific config
config = load_config(env="production")
```

### Configuration Schema

```yaml
pdf:
  max_file_size_mb: 50
  allowed_extensions: [".pdf"]

parsing:
  parsers:
    - pymupdf
    - pdfplumber
    - camelot
  
llm:
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 1000

export:
  formats: ["word", "excel", "json"]
  output_dir: "./output"
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_normalizers.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

---

For more examples and detailed usage, see the [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).
