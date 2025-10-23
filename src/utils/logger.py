"""Logging infrastructure with structured logging support."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from loguru import logger as loguru_logger


class StructuredLogger:
    """Structured logger wrapper combining loguru and structlog."""
    
    def __init__(
        self,
        name: str = "financial_agent",
        level: str = "INFO",
        log_format: str = "json",
        output_paths: Optional[list] = None,
        log_file_path: Optional[str] = None,
        max_file_size_mb: int = 50,
        backup_count: int = 5
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Format type (json, text)
            output_paths: List of output destinations (console, file)
            log_file_path: Path to log file
            max_file_size_mb: Maximum log file size in MB
            backup_count: Number of backup log files to keep
        """
        self.name = name
        self.level = level.upper()
        self.log_format = log_format
        self.output_paths = output_paths or ["console"]
        self.log_file_path = log_file_path
        self.max_file_size_mb = max_file_size_mb
        self.backup_count = backup_count
        
        # Configure loguru
        self._configure_loguru()
        
        # Configure structlog
        self._configure_structlog()
    
    def _configure_loguru(self):
        """Configure loguru logger."""
        # Remove default handler
        loguru_logger.remove()
        
        # Add console handler
        if "console" in self.output_paths:
            if self.log_format == "json":
                loguru_logger.add(
                    sys.stderr,
                    format="{message}",
                    level=self.level,
                    serialize=True
                )
            else:
                loguru_logger.add(
                    sys.stderr,
                    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                    level=self.level,
                    colorize=True
                )
        
        # Add file handler
        if "file" in self.output_paths and self.log_file_path:
            log_path = Path(self.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            loguru_logger.add(
                self.log_file_path,
                rotation=f"{self.max_file_size_mb} MB",
                retention=self.backup_count,
                level=self.level,
                format="{message}" if self.log_format == "json" else None,
                serialize=self.log_format == "json"
            )
    
    def _configure_structlog(self):
        """Configure structlog processors."""
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
        ]
        
        if self.log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(self.level)),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def get_logger(self, context: Optional[Dict[str, Any]] = None) -> structlog.BoundLogger:
        """
        Get a structured logger instance.
        
        Args:
            context: Additional context to bind to logger
            
        Returns:
            Bound structlog logger
        """
        logger = structlog.get_logger(self.name)
        
        if context:
            logger = logger.bind(**context)
        
        return logger


# Global logger instance
_logger_instance: Optional[StructuredLogger] = None


def setup_logger(
    level: str = "INFO",
    log_format: str = "json",
    output_paths: Optional[list] = None,
    log_file_path: Optional[str] = None,
    max_file_size_mb: int = 50,
    backup_count: int = 5
) -> StructuredLogger:
    """
    Setup the global logger instance.
    
    Args:
        level: Logging level
        log_format: Format type (json, text)
        output_paths: List of output destinations
        log_file_path: Path to log file
        max_file_size_mb: Maximum log file size
        backup_count: Number of backup files
        
    Returns:
        Configured StructuredLogger instance
    """
    global _logger_instance
    
    _logger_instance = StructuredLogger(
        level=level,
        log_format=log_format,
        output_paths=output_paths,
        log_file_path=log_file_path,
        max_file_size_mb=max_file_size_mb,
        backup_count=backup_count
    )
    
    return _logger_instance


def get_logger(context: Optional[Dict[str, Any]] = None) -> structlog.BoundLogger:
    """
    Get the global logger instance.
    
    Args:
        context: Additional context to bind
        
    Returns:
        Bound logger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        # Initialize with default settings
        _logger_instance = StructuredLogger()
    
    return _logger_instance.get_logger(context)
