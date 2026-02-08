"""
Retry logic with exponential backoff for LLM operations.

Provides resilient retry patterns for operations that may fail transiently,
particularly JSON parsing of LLM responses.
"""

import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of attempts (including first try)
        initial_delay_ms: Initial delay in milliseconds
        max_delay_ms: Maximum delay in milliseconds
        backoff_multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delay
    """
    max_attempts: int = 3
    initial_delay_ms: float = 250.0
    max_delay_ms: float = 1000.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class RetryResult:
    """
    Result of a retry operation.
    
    Attributes:
        success: Whether the operation succeeded
        result: The result value if successful
        attempts: Number of attempts made
        error: The final error if failed
        error_history: List of errors from each attempt
    """
    success: bool
    result: Any = None
    attempts: int = 0
    error: Optional[Exception] = None
    error_history: list = None
    
    def __post_init__(self):
        if self.error_history is None:
            self.error_history = []


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for a given attempt with exponential backoff.
    
    Args:
        attempt: Attempt number (0-based)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Calculate exponential backoff
    delay_ms = min(
        config.initial_delay_ms * (config.backoff_multiplier ** attempt),
        config.max_delay_ms
    )
    
    # Add jitter if enabled (±25% random variation)
    if config.jitter:
        jitter_factor = 0.75 + (random.random() * 0.5)  # Range: 0.75 to 1.25
        delay_ms *= jitter_factor
    
    # Convert to seconds
    return delay_ms / 1000.0


def retry_with_backoff(
    operation: Callable[[], Any],
    config: RetryConfig,
    retry_on: tuple = (Exception,),
    operation_name: str = "operation",
) -> RetryResult:
    """
    Execute an operation with retry and exponential backoff.
    
    Args:
        operation: Callable to execute (should take no arguments)
        config: Retry configuration
        retry_on: Tuple of exception types to retry on
        operation_name: Name for logging
        
    Returns:
        RetryResult with success/failure info
        
    Example:
        >>> config = RetryConfig(max_attempts=3)
        >>> result = retry_with_backoff(lambda: risky_operation(), config)
        >>> if result.success:
        ...     print(f"Success after {result.attempts} attempts")
    """
    error_history = []
    
    for attempt in range(config.max_attempts):
        try:
            logger.debug(f"{operation_name}: attempt {attempt + 1}/{config.max_attempts}")
            result = operation()
            
            if attempt > 0:
                logger.info(
                    f"{operation_name} succeeded after {attempt + 1} attempts"
                )
            
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt + 1,
                error_history=error_history,
            )
            
        except retry_on as e:
            error_history.append(str(e))
            logger.warning(
                f"{operation_name} failed on attempt {attempt + 1}/{config.max_attempts}: {e}"
            )
            
            # Don't sleep after the last attempt
            if attempt < config.max_attempts - 1:
                delay = calculate_delay(attempt, config)
                logger.debug(f"Backing off for {delay:.3f}s before retry")
                time.sleep(delay)
        
        except Exception as e:
            # Non-retryable error
            logger.error(f"{operation_name} failed with non-retryable error: {e}")
            error_history.append(str(e))
            return RetryResult(
                success=False,
                attempts=attempt + 1,
                error=e,
                error_history=error_history,
            )
    
    # All retries exhausted
    final_error = Exception(f"Failed after {config.max_attempts} attempts")
    logger.error(f"{operation_name} exhausted all {config.max_attempts} attempts")
    
    return RetryResult(
        success=False,
        attempts=config.max_attempts,
        error=final_error,
        error_history=error_history,
    )


def parse_json_with_retry(
    content: str,
    config: Optional[RetryConfig] = None,
    extract_embedded: bool = False,
) -> Tuple[bool, Optional[Dict[str, Any]], list]:
    """
    Parse JSON with retry logic and optional extraction of embedded JSON.
    
    This function handles:
    1. Direct JSON parsing
    2. Whitespace trimming
    3. Optional extraction of first {...} block if embedded in text
    
    Args:
        content: String content to parse
        config: Retry configuration (uses defaults if None)
        extract_embedded: If True, try to extract first JSON object from text
        
    Returns:
        Tuple of (success, parsed_dict, error_list)
        
    Example:
        >>> success, data, errors = parse_json_with_retry('{"key": "value"}')
        >>> if success:
        ...     print(data["key"])
    """
    if config is None:
        config = RetryConfig()
    
    errors = []
    
    def try_parse():
        # First, try direct parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"Direct parse failed: {e}")
        
        # Try with stripped whitespace
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            errors.append(f"Stripped parse failed: {e}")
        
        # If extraction enabled, try to find embedded JSON
        if extract_embedded:
            try:
                # Find first { and last matching }
                start = content.find('{')
                if start >= 0:
                    # Simple bracket counting to find matching close
                    depth = 0
                    for i in range(start, len(content)):
                        if content[i] == '{':
                            depth += 1
                        elif content[i] == '}':
                            depth -= 1
                            if depth == 0:
                                extracted = content[start:i+1]
                                return json.loads(extracted)
                    errors.append("Embedded parse failed: no matching closing brace")
                else:
                    errors.append("Embedded parse failed: no opening brace found")
            except json.JSONDecodeError as e:
                errors.append(f"Embedded parse failed: {e}")
        
        # All parsing strategies failed
        raise json.JSONDecodeError(
            "All parsing strategies exhausted",
            content[:100],
            0
        )
    
    # Note: We don't actually retry the JSON parsing itself since it's deterministic,
    # but we keep this structure for consistency and future expansion (e.g., could
    # retry the LLM call itself)
    try:
        result = try_parse()
        return True, result, errors
    except json.JSONDecodeError as e:
        errors.append(f"Final parse failed: {e}")
        return False, None, errors
