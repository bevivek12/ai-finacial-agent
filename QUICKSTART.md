# Quick Start Guide - AI Financial Agent

## Installation (5 minutes)

### Step 1: Create Virtual Environment

```bash
# Navigate to project directory
cd "c:\Users\vivek\Desktop\ai finacial agent"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/macOS:
# source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**Note**: This will install 50+ packages including:
- LangGraph, LangChain
- PyMuPDF, pdfplumber, Camelot
- pandas, numpy
- sentence-transformers, faiss
- And more...

Installation may take 5-10 minutes.

### Step 3: Setup Environment

```bash
# Run setup script
python setup.py
```

This will:
- Create necessary directories (logs/, output/, etc.)
- Create .env file from template
- Verify Python version

### Step 4: Configure API Keys

Edit the `.env` file and add your OpenAI API key:

```bash
# Open .env file
# Windows: notepad .env
# Unix/macOS: nano .env

# Add your API key:
OPENAI_API_KEY=sk-your-key-here
```

## Verify Installation

### Test 1: Import Core Modules

```bash
python -c "from src.models.schemas import DocumentMetadata; print('✓ Models work')"
python -c "from src.utils.config import get_config; print('✓ Config works')"
python -c "from src.utils.logger import get_logger; print('✓ Logger works')"
```

### Test 2: Run Unit Tests

```bash
# Run model tests
pytest tests/unit/test_models.py -v

# Expected output: All tests should PASS
```

### Test 3: Load Configuration

```python
# test_config.py
from src.utils.config import get_config

config = get_config()
print(f"App Name: {config.app.name}")
print(f"Environment: {config.app.environment}")
print(f"LLM Model: {config.llm.model}")
print("✓ Configuration loaded successfully!")
```

Run it:
```bash
python test_config.py
```

## What's Working

After installation, you can use:

### 1. Data Models

```python
from src.models.schemas import DocumentMetadata, FinancialMetric, ReportType
from datetime import date
from decimal import Decimal

# Create document metadata
metadata = DocumentMetadata(
    document_id="test_001",
    company_name="Example plc",
    report_type=ReportType.ANNUAL,
    fiscal_period_end=date(2023, 12, 31),
    source_path="/path/to/report.pdf"
)

# Create financial metric
metric = FinancialMetric(
    metric_id="revenue_2023",
    metric_name="Revenue",
    value=Decimal("1250.5"),
    currency="GBP",
    scale="millions",
    period_end_date=date(2023, 12, 31),
    extraction_method="table"
)

print(f"Metric value in base units: {metric.to_base_units()}")
```

### 2. Structured Logging

```python
from src.utils.logger import setup_logger, get_logger

# Setup logger (do this once)
setup_logger(level="INFO", log_format="text")

# Get logger with context
logger = get_logger({"module": "my_app", "user": "test"})

# Log messages
logger.info("application_started", version="0.1.0")
logger.warning("low_confidence", confidence=0.65)
logger.error("processing_failed", error="File not found")
```

### 3. Configuration Management

```python
from src.utils.config import get_config

config = get_config()

# Access configuration sections
print(config.pdf.parser_priority)  # ['pymupdf', 'pdfplumber', 'camelot']
print(config.llm.model)            # 'gpt-4o-mini'
print(config.validation.yoy_growth_max)  # 5.0
```

### 4. PDF Parsing (Basic)

```python
from src.parsers.pymupdf_parser import PyMuPDFParser

parser = PyMuPDFParser()

# Parse a PDF (when you have one)
# text_blocks, table_blocks = parser.parse_pdf("path/to/report.pdf")

# Get page count
# page_count = parser.get_page_count("path/to/report.pdf")
```

### 5. Workflow Graph (Structure Only)

```python
from src.workflow.graph import create_financial_agent_graph

# Create the workflow graph
graph = create_financial_agent_graph()

# Note: The graph structure is ready, but nodes need implementation
# to actually process documents
```

## What Needs Implementation

See `IMPLEMENTATION_ROADMAP.md` for detailed plan. Key items:

1. **Complete PDF parsers** (pdfplumber, Camelot)
2. **Implement service layer** (ingestion, section location, table extraction)
3. **Build validation** (deterministic validator, LLM adjudicator)
4. **Add analysis** (derived metrics, commentary, RAG)
5. **Create export** (Word/Excel templates and exporters)
6. **Fill in node implementations** (all 12 workflow nodes)

## Development Workflow

### When Adding New Components:

1. **Create the file** in appropriate directory
2. **Import utilities**:
   ```python
   from ..utils.logger import get_logger
   from ..utils.config import get_config
   
   logger = get_logger({"module": "your_module"})
   config = get_config()
   ```

3. **Write the implementation**
4. **Create tests** in `tests/unit/`
5. **Run tests**:
   ```bash
   pytest tests/unit/test_your_module.py -v
   ```

6. **Check code quality**:
   ```bash
   black src/your_module.py
   flake8 src/your_module.py
   ```

## Common Commands

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# View coverage report
# Open htmlcov/index.html in browser
```

## Troubleshooting

### Import Errors

Make sure virtual environment is activated:
```bash
# Windows
venv\Scripts\activate
# Unix/macOS
source venv/bin/activate
```

### Configuration Not Found

Ensure you're running from project root:
```bash
cd "c:\Users\vivek\Desktop\ai finacial agent"
```

### API Key Issues

Check `.env` file exists and has correct format:
```
OPENAI_API_KEY=sk-...
```

## Next Steps

1. **Read**: `README.md` for project overview
2. **Plan**: `IMPLEMENTATION_ROADMAP.md` for what to build
3. **Build**: Start with Phase 2 (PDF Processing)
4. **Test**: Write tests as you go
5. **Document**: Update docs when adding features

## Getting Help

- **Architecture**: See design document
- **Implementation**: See `IMPLEMENTATION_ROADMAP.md`
- **Examples**: Check `tests/` directory
- **Config Options**: See `config/config.yaml`

---

**Ready to Start?**

```bash
# Activate environment
venv\Scripts\activate

# Verify installation
python -c "from src.models.schemas import DocumentMetadata; print('Ready!')"

# Start building!
```
