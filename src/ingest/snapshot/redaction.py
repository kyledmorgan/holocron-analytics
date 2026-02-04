"""
Redaction hooks for sensitive data scrubbing.

Provides configurable redaction of:
- Auth headers (Authorization, Cookie, API keys)
- Secrets embedded in payloads (best-effort patterns)
- Custom patterns defined in redaction policy
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExchangeRecord

logger = logging.getLogger(__name__)

# Default sensitive header names (case-insensitive)
DEFAULT_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "bearer",
    "x-access-token",
    "x-secret",
    "x-csrf-token",
}

# Default regex patterns for detecting secrets in payloads
DEFAULT_SECRET_PATTERNS = [
    # API keys (generic patterns)
    r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?',
    # Bearer tokens
    r'["\']?bearer\s+([a-zA-Z0-9_.-]+)["\']?',
    # JWT tokens
    r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
    # AWS keys
    r'(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}',
    # Generic secrets
    r'["\']?(?:secret|password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{8,})["\']?',
]

REDACTED_VALUE = "[REDACTED]"


class Redactor:
    """
    Redacts sensitive information from ExchangeRecords.
    """

    def __init__(
        self,
        headers_to_redact: Optional[Set[str]] = None,
        secret_patterns: Optional[List[str]] = None,
        custom_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the redactor.
        
        Args:
            headers_to_redact: Set of header names to redact (case-insensitive)
            secret_patterns: List of regex patterns for secret detection
            custom_patterns: Additional custom regex patterns
        """
        self.headers_to_redact = headers_to_redact or DEFAULT_SENSITIVE_HEADERS
        self.secret_patterns = secret_patterns or DEFAULT_SECRET_PATTERNS.copy()
        
        if custom_patterns:
            self.secret_patterns.extend(custom_patterns)
        
        # Compile patterns for efficiency
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.secret_patterns
        ]
        
        # Pre-compile URL parameter patterns for efficiency
        sensitive_params = {
            "api_key", "apikey", "key", "token", "secret",
            "password", "passwd", "pwd", "auth", "bearer",
            "access_token", "refresh_token",
        }
        self._url_param_patterns = [
            (param, re.compile(rf'([?&])({param})=([^&\s]+)', re.IGNORECASE))
            for param in sensitive_params
        ]

    def redact_record(self, record: "ExchangeRecord") -> "ExchangeRecord":
        """
        Redact sensitive data from an ExchangeRecord.
        
        Creates a copy with redacted values; does not modify the original.
        
        Args:
            record: The record to redact
            
        Returns:
            New ExchangeRecord with redacted values
        """
        from .models import ExchangeRecord, Provenance
        
        redactions_applied = list(record.redactions_applied)
        
        # Redact request
        request = record.request
        if request:
            request = self._redact_request(request)
            redactions_applied.append("request_headers")
            redactions_applied.append("request_secrets")
        
        # Redact response
        response = record.response
        if response:
            response = self._redact_value(response)
            redactions_applied.append("response_secrets")
        
        # Create new record with redacted values
        return ExchangeRecord(
            exchange_id=record.exchange_id,
            exchange_type=record.exchange_type,
            source_system=record.source_system,
            entity_type=record.entity_type,
            natural_key=record.natural_key,
            request=request,
            response=response,
            observed_at_utc=record.observed_at_utc,
            provenance=record.provenance,
            content_sha256=record.content_sha256,  # Keep original hash
            schema_version=record.schema_version,
            tags=list(record.tags),
            redactions_applied=list(set(redactions_applied)),
            response_ref=record.response_ref,
        )

    def _redact_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from a request dict."""
        result = {}
        
        for key, value in request.items():
            key_lower = key.lower()
            
            if key_lower == "headers" and isinstance(value, dict):
                # Redact sensitive headers
                result[key] = self._redact_headers(value)
            elif key_lower in {"body", "payload", "data"}:
                # Redact secrets in body
                result[key] = self._redact_value(value)
            elif key_lower in {"url", "uri"}:
                # Redact query parameters in URL
                result[key] = self._redact_url(value) if isinstance(value, str) else value
            else:
                # Recursively check for secrets
                result[key] = self._redact_value(value)
        
        return result

    def _redact_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive headers."""
        result = {}
        
        for key, value in headers.items():
            if key.lower() in self.headers_to_redact:
                result[key] = REDACTED_VALUE
            else:
                result[key] = value
        
        return result

    def _redact_url(self, url: str) -> str:
        """Redact sensitive query parameters from URL."""
        # Use pre-compiled patterns for efficiency
        for param, pattern in self._url_param_patterns:
            url = pattern.sub(rf'\1\2={REDACTED_VALUE}', url)
        
        return url

    def _redact_value(self, value: Any) -> Any:
        """Recursively redact secrets from a value."""
        if value is None:
            return None
        
        if isinstance(value, str):
            return self._redact_string(value)
        
        if isinstance(value, dict):
            return {k: self._redact_value(v) for k, v in value.items()}
        
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        
        return value

    def _redact_string(self, text: str) -> str:
        """Redact secrets from a string."""
        result = text
        
        for pattern in self._compiled_patterns:
            # Replace matches with [REDACTED]
            result = pattern.sub(REDACTED_VALUE, result)
        
        return result


def apply_redaction(
    record: "ExchangeRecord",
    headers_to_redact: Optional[Set[str]] = None,
    custom_patterns: Optional[List[str]] = None,
) -> "ExchangeRecord":
    """
    Convenience function to apply redaction to a record.
    
    Args:
        record: The record to redact
        headers_to_redact: Optional set of header names to redact
        custom_patterns: Optional additional regex patterns
        
    Returns:
        New ExchangeRecord with redacted values
    """
    redactor = Redactor(
        headers_to_redact=headers_to_redact,
        custom_patterns=custom_patterns,
    )
    return redactor.redact_record(record)
