"""
Logging utilities for the LLM-Derived Data module.

Provides structured logging with correlation ID support for tracing
jobs across the pipeline (job → run → artifacts → logs).
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class CorrelatedLogRecord(logging.LogRecord):
    """LogRecord subclass that includes correlation context fields."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set defaults for correlation fields
        self.job_id = getattr(self, 'job_id', None)
        self.run_id = getattr(self, 'run_id', None)
        self.correlation_id = getattr(self, 'correlation_id', None)
        self.worker_id = getattr(self, 'worker_id', None)
        self.execution_mode = getattr(self, 'execution_mode', None)


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs JSON-structured log lines.
    
    Each log line includes:
    - Standard log fields (timestamp, level, message, logger)
    - Correlation fields if present (job_id, run_id, correlation_id)
    - Extra fields passed via the 'extra' parameter
    """
    
    def __init__(self, include_timestamp: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if self.include_timestamp:
            # Use record.created for consistency with when log was actually created
            log_entry["timestamp"] = datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat()
        
        # Add correlation fields if present
        for field in ['job_id', 'run_id', 'correlation_id', 'worker_id', 
                      'execution_mode', 'job_type', 'attempt']:
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Formatter that outputs human-readable log lines with correlation context.
    
    Format: TIMESTAMP - LOGGER - LEVEL - MESSAGE [correlation_id=X job_id=Y]
    """
    
    def __init__(self, include_timestamp: bool = True):
        if include_timestamp:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            fmt = "%(name)s - %(levelname)s - %(message)s"
        super().__init__(fmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with correlation context."""
        base = super().format(record)
        
        # Build correlation suffix
        context_parts = []
        for field in ['correlation_id', 'job_id', 'run_id']:
            value = getattr(record, field, None)
            if value is not None:
                context_parts.append(f"{field}={value}")
        
        if context_parts:
            return f"{base} [{' '.join(context_parts)}]"
        return base


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance for the LLM module.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Optional logging level override
        
    Returns:
        Configured logger instance
        
    Example:
        >>> from src.llm.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting derive operation", extra={"job_id": "abc123"})
    """
    logger = logging.getLogger(name)
    
    if level is not None:
        logger.setLevel(level)
    
    return logger


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
    structured: bool = False,
) -> None:
    """
    Configure logging for the LLM module.
    
    This is a thin wrapper that configures the root logger for the llm package.
    In production, this should integrate with the repository's logging configuration.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional, ignored if structured=True)
        include_timestamp: Whether to include timestamp in log messages
        structured: If True, output JSON-structured logs; if False, human-readable
        
    Example:
        >>> from src.llm.core.logging import configure_logging
        >>> configure_logging(level=logging.DEBUG, structured=True)
    """
    # Configure the llm package logger
    llm_logger = logging.getLogger("src.llm")
    llm_logger.setLevel(level)
    
    # Only add handler if none exist (avoid duplicate handlers)
    if not llm_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        if structured:
            formatter = StructuredFormatter(include_timestamp=include_timestamp)
        elif format_string:
            formatter = logging.Formatter(format_string)
        else:
            formatter = HumanReadableFormatter(include_timestamp=include_timestamp)
        
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)


class CorrelationContext:
    """
    Context manager for adding correlation fields to log records.
    
    Example:
        >>> with CorrelationContext(job_id="abc", run_id="xyz"):
        ...     logger.info("Processing job")  # Will include job_id and run_id
    """
    
    _current: Optional["CorrelationContext"] = None
    
    def __init__(
        self,
        job_id: Optional[str] = None,
        run_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        **extra: Any,
    ):
        self.context = {
            "job_id": job_id,
            "run_id": run_id,
            "correlation_id": correlation_id,
            "worker_id": worker_id,
            **extra,
        }
        # Remove None values
        self.context = {k: v for k, v in self.context.items() if v is not None}
        self._previous: Optional["CorrelationContext"] = None
    
    def __enter__(self) -> "CorrelationContext":
        self._previous = CorrelationContext._current
        CorrelationContext._current = self
        return self
    
    def __exit__(self, *args) -> None:
        CorrelationContext._current = self._previous
    
    @classmethod
    def get_current(cls) -> Dict[str, Any]:
        """Get the current correlation context."""
        if cls._current is None:
            return {}
        return cls._current.context.copy()


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra: Any,
) -> None:
    """
    Log a message with correlation context.
    
    Merges the current CorrelationContext with any extra fields provided.
    
    Args:
        logger: The logger to use
        level: Log level (e.g., logging.INFO)
        message: Log message
        **extra: Additional fields to include
    """
    context = CorrelationContext.get_current()
    context.update(extra)
    logger.log(level, message, extra=context)


# Module-level logger for this file
logger = get_logger(__name__)
