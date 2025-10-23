# AI Financial Agent

An intelligent financial document processing agent powered by LangGraph that extracts, validates, normalizes, and analyzes financial metrics from company reports (Annual Reports, Half-Year Reports, RNS files).

## Overview

This system combines deterministic parsing, machine learning-based extraction, and LLM-powered validation to transform unstructured PDF financial reports into structured, validated, and analyzed financial data.

### Key Features

- **Multi-Parser PDF Processing**: PyMuPDF, pdfplumber, and Camelot for robust PDF parsing
- **Hybrid Section Detection**: Regex + embedding-based semantic search for financial statement sections
- **Multi-Candidate Validation**: Generate multiple candidate values per metric with evidence-based justification
- **LLM Adjudication**: Intelligent conflict resolution using language models
- **Automated Financial Analysis**: Derived metrics computation and commentary generation
- **RAG-Powered Summarization**: Recent developments from news/RNS using retrieval-augmented generation
- **Template-Based Export**: Word and Excel output with audit trails

## Project Structure

```
ai finacial agent/
├── src/
│   ├── models/          # Data models and schemas
│   │   ├── schemas.py   # Pydantic models (DocumentMetadata, FinancialMetric, etc.)
│   │   └── state.py     # LangGraph state schema
│   ├── parsers/         # PDF parsing modules
│   │   ├── pymupdf_parser.py
│   │   ├── pdfplumber_parser.py (to implement)
│   │   └── camelot_parser.py (to implement)
│   ├── services/        # Core services
│   │   ├── ingestion.py (to implement)
│   │   ├── blockification.py (to implement)
│   │   ├── section_locator.py (to implement)
│   │   ├── table_extractor.py (to implement)
│   │   ├── metric_normalizer.py (to implement)
│   │   └── candidate_generator.py (to implement)
│   ├── validation/      # Validation components
│   │   ├── deterministic_validator.py (to implement)
│   │   └── llm_adjudicator.py (to implement)
│   ├── analysis/        # Analysis components
│   │   ├── derived_metrics.py (to implement)
│   │   ├── commentary_generator.py (to implement)
│   │   └── rag_summarizer.py (to implement)
│   ├── export/          # Output generation
│   │   ├── word_exporter.py (to implement)
│   │   └── excel_exporter.py (to implement)
│   ├── workflow/        # LangGraph workflow
│   │   ├── nodes.py (to implement)
│   │   ├── graph.py (to implement)
│   │   └── conditions.py (to implement)
│   └── utils/           # Utilities
│       ├── config.py    # Configuration management
│       └── logger.py    # Structured logging
├── config/
│   ├── config.yaml      # Main configuration
│   ├── config.dev.yaml  # Development overrides
│   └── config.prod.yaml # Production overrides
├── templates/
│   ├── word/            # Word document templates
│   └── excel/           # Excel workbook templates
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── data/
│   └── sample_pdfs/     # Sample PDF files for testing
├── logs/                # Log files
├── output/              # Generated outputs
├── requirements.txt     # Python dependencies
├── .env.template        # Environment variable template
└── README.md           # This file
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

1. **Clone or create the project directory:**

```bash
cd "c:\Users\vivek\Desktop\ai finacial agent"
```

2. **Create a virtual environment (recommended):**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/macOS
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**

Copy `.env.template` to `.env` and fill in your API keys:

```bash
cp .env.template .env
```

Edit `.env`:
```
OPENAI_API_KEY=your-openai-api-key-here
```

5. **Verify installation:**

```bash
python -c "import src; print('Installation successful!')"
```

## Configuration

Configuration is managed through YAML files in the `config/` directory:

- `config.yaml`: Base configuration
- `config.dev.yaml`: Development overrides
- `config.prod.yaml`: Production overrides

Set the environment:
```bash
# Windows
set ENVIRONMENT=development
# Unix/macOS
export ENVIRONMENT=development
```

### Key Configuration Sections

- **PDF Processing**: Parser priorities, timeouts, file size limits
- **Section Detection**: Regex patterns, embedding models, similarity thresholds
- **LLM**: Provider, model, temperature, token limits
- **Validation**: Growth rate thresholds, margin limits
- **RAG**: Chunk sizes, retrieval parameters
- **Export**: Output directories, template paths

## Implementation Status

### ✅ Completed Components

1. **Project Setup**
   - Directory structure created
   - Dependencies defined in `requirements.txt`
   - Configuration system with YAML support
   - Structured logging infrastructure

2. **Data Models**
   - `DocumentMetadata`: Document classification and metadata
   - `FinancialMetric`: Financial data with provenance
   - `CandidateValue`: Multi-candidate values with evidence
   - `ValidationResult`: Validation outcomes
   - `AgentState`: LangGraph state schema
   - Supporting models: `TextBlock`, `TableBlock`, `Section`

3. **PDF Parsers**
   - PyMuPDF parser wrapper with text and table extraction

### 🚧 To Be Implemented

The following components are defined in the architecture but need implementation:

#### PDF Processing
- pdfplumber parser wrapper
- Camelot parser wrapper
- PDF Ingestion Service
- Parsing & Blockification Service

#### Section Location and Table Extraction
- Regex pattern library for financial sections
- Embedding-based semantic search
- Section Locator (hybrid approach)
- Table Extractor with metadata enrichment

#### Metric Processing
- Currency conversion and scale adjustment
- Period mapping and label standardization
- Metric Normalizer service
- Candidate Generator

#### Validation
- Deterministic Validator (unit checks, arithmetic, YoY delta)
- LLM Adjudicator with prompt engineering

#### Analysis
- Derived Metrics Computer
- Financial Commentary Generator
- RAG-based Recent Developments Summarizer

#### Export
- Word document template and exporter
- Excel workbook template and exporter

#### LangGraph Workflow
- Node definitions for all processing stages
- Conditional routing logic
- Complete workflow graph
- Error handling mechanisms

#### Testing
- Unit tests for all components
- Integration tests for end-to-end pipeline
- Sample test data with ground truth

#### CLI and Documentation
- Command-line interface
- API documentation
- Usage examples

## Usage (Planned)

Once implementation is complete, the system will be used as follows:

### Command Line

```bash
# Process a single financial report
python -m src.cli process --pdf "path/to/annual_report.pdf" --output "./output"

# Batch processing
python -m src.cli batch --input-dir "./data/sample_pdfs" --output-dir "./output"

# With custom configuration
python -m src.cli process --pdf "report.pdf" --config "./config/custom.yaml"
```

### Python API

```python
from src.workflow.graph import create_financial_agent_graph
from src.models.state import AgentState

# Create workflow graph
graph = create_financial_agent_graph()

# Process document
initial_state = {
    "raw_pdf_path": "path/to/annual_report.pdf"
}

result = graph.invoke(initial_state)

# Access results
validated_metrics = result["validated_metrics"]
commentary = result["commentary"]
export_paths = result["export_paths"]
```

## Architecture Highlights

### LangGraph Workflow

The system operates as a state machine with the following key nodes:

1. **ingest_pdf**: Validate and classify document
2. **parse_blockify**: Extract text and table blocks
3. **locate_sections**: Find financial statement sections
4. **extract_tables**: Extract structured tables
5. **normalize_metrics**: Standardize metric values
6. **generate_candidates**: Create multi-candidate values
7. **validate_deterministic**: Apply rule-based validation
8. **adjudicate_llm**: Resolve conflicts (conditional)
9. **compute_derived**: Calculate ratios and changes
10. **generate_commentary**: Produce AI analysis
11. **summarize_news**: RAG-based summarization
12. **export_results**: Generate Word/Excel outputs

### Multi-Parser Strategy

| Parser | Strengths | Use Case |
|--------|-----------|----------|
| PyMuPDF | Fast text extraction | Primary text parsing |
| pdfplumber | Simple tables | Table detection |
| Camelot | Complex tables | Financial statement tables |

### Validation Pipeline

1. **Candidate Generation**: Extract 2-5 candidate values per metric
2. **Deterministic Validation**: Unit consistency, arithmetic, range checks
3. **LLM Adjudication**: Resolve conflicts using reasoning
4. **Final Selection**: Choose validated value with highest confidence

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_parsers.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## Dependencies

### Core
- **langgraph**: Workflow orchestration
- **langchain**: LLM integration
- **pydantic**: Data validation

### PDF Processing
- **PyMuPDF**: PDF parsing
- **pdfplumber**: Table extraction
- **camelot-py**: Advanced table extraction

### ML/AI
- **sentence-transformers**: Embeddings
- **faiss-cpu**: Vector search
- **chromadb**: Vector store

### Data Processing
- **pandas**: Data manipulation
- **numpy**: Numerical operations

### Output
- **python-docx**: Word generation
- **openpyxl**: Excel manipulation

## Logging

The system uses structured logging with both console and file output:

```python
from src.utils.logger import get_logger

logger = get_logger({"module": "my_module"})
logger.info("processing_started", document_id="doc_123")
```

Logs are written to `./logs/financial_agent.log` with automatic rotation.

## License

[To be determined]

## Contributing

[To be determined]

## Contact

[To be determined]

## Acknowledgments

This project implements the architecture specified in the "AI Financial Agent - LangGraph Architecture Design" document.
