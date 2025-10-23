"""Configuration management for the AI Financial Agent."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration."""
    name: str = "AI Financial Agent"
    version: str = "0.1.0"
    environment: str = "development"


class PDFConfig(BaseSettings):
    """PDF processing configuration."""
    parser_priority: List[str] = ["pymupdf", "pdfplumber", "camelot"]
    parser_timeout: int = 300
    max_file_size_mb: int = 100


class SectionDetectionConfig(BaseSettings):
    """Section detection configuration."""
    regex_weight: float = 0.7
    embedding_weight: float = 0.3
    similarity_threshold: float = 0.75
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    patterns: Dict[str, List[str]] = Field(default_factory=dict)


class TableExtractionConfig(BaseSettings):
    """Table extraction configuration."""
    min_rows: int = 2
    min_columns: int = 2
    detect_merged_cells: bool = True
    extract_footnotes: bool = True


class NormalizationConfig(BaseSettings):
    """Metric normalization configuration."""
    default_currency: str = "GBP"
    default_scale: str = "millions"
    supported_currencies: List[str] = ["GBP", "USD", "EUR"]
    supported_scales: List[str] = ["actual", "thousands", "millions", "billions"]


class ValidationConfig(BaseSettings):
    """Validation configuration."""
    yoy_growth_max: float = 5.0
    yoy_growth_min: float = -0.9
    margin_max: float = 1.0
    margin_min: float = -1.0
    significant_change_threshold: float = 0.1


class LLMConfig(BaseSettings):
    """LLM configuration."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    max_retries: int = 3
    retry_delay: int = 2


class RAGConfig(BaseSettings):
    """RAG configuration."""
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_retrieval: int = 10
    vector_store: str = "faiss"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class ExportConfig(BaseSettings):
    """Export configuration."""
    output_directory: str = "./output"
    word_template_path: str = "./templates/word/financial_report_template.docx"
    excel_template_path: str = "./templates/excel/financial_metrics_template.xlsx"
    include_audit_trail: bool = True


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    output: List[str] = ["console", "file"]
    file_path: str = "./logs/financial_agent.log"
    max_file_size_mb: int = 50
    backup_count: int = 5


class PerformanceConfig(BaseSettings):
    """Performance configuration."""
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    parallel_processing: bool = True
    max_workers: int = 4


class Config(BaseSettings):
    """Main configuration class."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # API Keys from environment
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    exchange_rate_api_key: Optional[str] = None
    
    # Configuration sections
    app: AppConfig = Field(default_factory=AppConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)
    section_detection: SectionDetectionConfig = Field(default_factory=SectionDetectionConfig)
    table_extraction: TableExtractionConfig = Field(default_factory=TableExtractionConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config/config.yaml") -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
        
        # Load environment-specific overrides
        environment = os.getenv("ENVIRONMENT", "development")
        env_config_path = config_file.parent / f"config.{environment}.yaml"
        
        if env_config_path.exists():
            with open(env_config_path, "r") as f:
                env_config_data = yaml.safe_load(f)
                # Merge environment-specific config
                config_data = cls._merge_configs(config_data, env_config_data)
        
        return cls(**config_data)
    
    @staticmethod
    def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = Config._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    
    if _config is None:
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        _config = Config.load_from_yaml(config_path)
    
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
