"""
Unit tests for retry logic and utilities.

Tests for:
- RetryConfig
- retry_with_backoff
- parse_json_with_retry
- calculate_delay
"""

import json
import pytest
import time
from unittest.mock import patch

from llm.utils.retry import (
    RetryConfig,
    RetryResult,
    retry_with_backoff,
    parse_json_with_retry,
    calculate_delay,
)


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.initial_delay_ms == 250.0
        assert config.max_delay_ms == 1000.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay_ms=100.0,
            max_delay_ms=2000.0,
            backoff_multiplier=3.0,
            jitter=False,
        )
        
        assert config.max_attempts == 5
        assert config.initial_delay_ms == 100.0
        assert config.max_delay_ms == 2000.0
        assert config.backoff_multiplier == 3.0
        assert config.jitter is False


class TestCalculateDelay:
    """Tests for calculate_delay function."""
    
    def test_exponential_backoff_no_jitter(self):
        """Test exponential backoff without jitter."""
        config = RetryConfig(
            initial_delay_ms=100.0,
            max_delay_ms=1000.0,
            backoff_multiplier=2.0,
            jitter=False,
        )
        
        # Attempt 0: 100ms
        delay = calculate_delay(0, config)
        assert delay == 0.1
        
        # Attempt 1: 200ms
        delay = calculate_delay(1, config)
        assert delay == 0.2
        
        # Attempt 2: 400ms
        delay = calculate_delay(2, config)
        assert delay == 0.4
        
        # Attempt 3: 800ms
        delay = calculate_delay(3, config)
        assert delay == 0.8
        
        # Attempt 4: 1000ms (capped at max)
        delay = calculate_delay(4, config)
        assert delay == 1.0
    
    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter."""
        config = RetryConfig(
            initial_delay_ms=100.0,
            max_delay_ms=1000.0,
            backoff_multiplier=2.0,
            jitter=True,
        )
        
        # With jitter, delays should be in range [75% to 125%] of base
        for attempt in range(5):
            delay = calculate_delay(attempt, config)
            base = min(100.0 * (2.0 ** attempt), 1000.0) / 1000.0
            assert delay >= base * 0.75
            assert delay <= base * 1.25


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""
    
    def test_success_on_first_attempt(self):
        """Test successful operation on first attempt."""
        def always_success():
            return "success"
        
        config = RetryConfig(max_attempts=3)
        result = retry_with_backoff(always_success, config)
        
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
        assert len(result.error_history) == 0
    
    def test_success_after_retries(self):
        """Test successful operation after some failures."""
        call_count = []
        
        def succeed_on_third():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not yet")
            return "success"
        
        config = RetryConfig(max_attempts=3, initial_delay_ms=10.0)
        result = retry_with_backoff(
            succeed_on_third,
            config,
            retry_on=(ValueError,),
        )
        
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 3
        assert len(result.error_history) == 2
    
    def test_failure_after_max_attempts(self):
        """Test failure after exhausting retries."""
        def always_fail():
            raise ValueError("Always fails")
        
        config = RetryConfig(max_attempts=3, initial_delay_ms=10.0)
        result = retry_with_backoff(
            always_fail,
            config,
            retry_on=(ValueError,),
        )
        
        assert result.success is False
        assert result.attempts == 3
        assert len(result.error_history) == 3
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions abort immediately."""
        call_count = []
        
        def fail_with_runtime_error():
            call_count.append(1)
            raise RuntimeError("Non-retryable")
        
        config = RetryConfig(max_attempts=3)
        result = retry_with_backoff(
            fail_with_runtime_error,
            config,
            retry_on=(ValueError,),  # Only retry on ValueError
        )
        
        assert result.success is False
        assert result.attempts == 1  # Should not retry
        assert isinstance(result.error, RuntimeError)
    
    @patch('time.sleep')
    def test_backoff_delay_called(self, mock_sleep):
        """Test that backoff delays are applied."""
        call_count = []
        
        def fail_twice():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not yet")
            return "success"
        
        config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=100.0,
            jitter=False,
        )
        result = retry_with_backoff(
            fail_twice,
            config,
            retry_on=(ValueError,),
        )
        
        assert result.success is True
        assert mock_sleep.call_count == 2  # Two retries = two sleeps


class TestParseJsonWithRetry:
    """Tests for parse_json_with_retry function."""
    
    def test_valid_json(self):
        """Test parsing valid JSON."""
        content = '{"key": "value", "number": 42}'
        success, data, errors = parse_json_with_retry(content)
        
        assert success is True
        assert data == {"key": "value", "number": 42}
        assert len(errors) == 0
    
    def test_valid_json_with_whitespace(self):
        """Test parsing JSON with leading/trailing whitespace."""
        content = '  \n  {"key": "value"}  \n  '
        success, data, errors = parse_json_with_retry(content)
        
        assert success is True
        assert data == {"key": "value"}
    
    def test_embedded_json(self):
        """Test extracting embedded JSON from text."""
        content = 'Some text before {"key": "value"} some text after'
        success, data, errors = parse_json_with_retry(
            content,
            extract_embedded=True
        )
        
        assert success is True
        assert data == {"key": "value"}
    
    def test_complex_embedded_json(self):
        """Test extracting complex embedded JSON."""
        content = 'Here is the result: {"outer": {"inner": "value"}, "count": 3} - done'
        success, data, errors = parse_json_with_retry(
            content,
            extract_embedded=True
        )
        
        assert success is True
        assert data == {"outer": {"inner": "value"}, "count": 3}
    
    def test_invalid_json_no_extraction(self):
        """Test that invalid JSON fails without extraction."""
        content = 'not json at all'
        success, data, errors = parse_json_with_retry(
            content,
            extract_embedded=False
        )
        
        assert success is False
        assert data is None
        assert len(errors) > 0
    
    def test_invalid_json_with_extraction(self):
        """Test that invalid JSON without braces fails even with extraction."""
        content = 'no json here either'
        success, data, errors = parse_json_with_retry(
            content,
            extract_embedded=True
        )
        
        assert success is False
        assert data is None
        assert len(errors) > 0
    
    def test_malformed_json_with_extraction(self):
        """Test malformed JSON with extraction enabled."""
        content = 'Text {"incomplete": json...'
        success, data, errors = parse_json_with_retry(
            content,
            extract_embedded=True
        )
        
        assert success is False
        assert data is None
        assert len(errors) > 0
    
    def test_custom_config(self):
        """Test using custom retry config."""
        content = '{"valid": "json"}'
        config = RetryConfig(max_attempts=5)
        success, data, errors = parse_json_with_retry(content, config)
        
        assert success is True
        assert data == {"valid": "json"}


class TestRetryResult:
    """Tests for RetryResult dataclass."""
    
    def test_success_result(self):
        """Test successful result."""
        result = RetryResult(
            success=True,
            result="data",
            attempts=1,
        )
        
        assert result.success is True
        assert result.result == "data"
        assert result.attempts == 1
        assert result.error is None
        assert result.error_history == []
    
    def test_failure_result(self):
        """Test failure result."""
        result = RetryResult(
            success=False,
            attempts=3,
            error=ValueError("Failed"),
            error_history=["Error 1", "Error 2", "Error 3"],
        )
        
        assert result.success is False
        assert result.result is None
        assert result.attempts == 3
        assert isinstance(result.error, ValueError)
        assert len(result.error_history) == 3
