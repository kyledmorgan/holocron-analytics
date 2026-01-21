"""
Logging utilities for the LLM-Derived Data module.

Follows patterns established in the repository for consistent logging.
"""

import logging
from typing import Optional


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
        >>> logger.info("Starting derive operation")
    """
    logger = logging.getLogger(name)
    
    if level is not None:
        logger.setLevel(level)
    
    return logger


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
) -> None:
    """
    Configure logging for the LLM module.
    
    This is a thin wrapper that configures the root logger for the llm package.
    In production, this should integrate with the repository's logging configuration.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        include_timestamp: Whether to include timestamp in log messages
        
    Example:
        >>> from src.llm.core.logging import configure_logging
        >>> configure_logging(level=logging.DEBUG)
    """
    if format_string is None:
        if include_timestamp:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            format_string = "%(name)s - %(levelname)s - %(message)s"
    
    # Configure the llm package logger
    llm_logger = logging.getLogger("src.llm")
    llm_logger.setLevel(level)
    
    # Only add handler if none exist (avoid duplicate handlers)
    if not llm_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)


# Module-level logger for this file
logger = get_logger(__name__)
