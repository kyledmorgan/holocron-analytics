#!/usr/bin/env python3
"""
Unit tests for redaction hooks.
"""

import sys
import unittest
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.snapshot.redaction import Redactor, apply_redaction, REDACTED_VALUE
from ingest.snapshot.models import ExchangeRecord


class TestRedactor(unittest.TestCase):
    """Test cases for Redactor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.redactor = Redactor()
    
    def test_redact_authorization_header(self):
        """Test that Authorization header is redacted."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "url": "https://api.example.com",
                "headers": {
                    "Authorization": "Bearer token123abc",
                    "Content-Type": "application/json",
                }
            },
        )
        
        redacted = self.redactor.redact_record(record)
        
        self.assertEqual(
            redacted.request["headers"]["Authorization"],
            REDACTED_VALUE,
        )
        # Non-sensitive headers should be preserved
        self.assertEqual(
            redacted.request["headers"]["Content-Type"],
            "application/json",
        )
    
    def test_redact_cookie_header(self):
        """Test that Cookie header is redacted."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "headers": {
                    "Cookie": "session=abc123; user=test",
                }
            },
        )
        
        redacted = self.redactor.redact_record(record)
        
        self.assertEqual(
            redacted.request["headers"]["Cookie"],
            REDACTED_VALUE,
        )
    
    def test_redact_api_key_in_url(self):
        """Test that API key in URL is redacted."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "url": "https://api.example.com?api_key=secret123&format=json",
            },
        )
        
        redacted = self.redactor.redact_record(record)
        
        self.assertIn(REDACTED_VALUE, redacted.request["url"])
        self.assertNotIn("secret123", redacted.request["url"])
        # Other params should be preserved
        self.assertIn("format=json", redacted.request["url"])
    
    def test_redact_jwt_in_response(self):
        """Test that JWT tokens in response are redacted."""
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={
                "token": jwt_token,
                "data": "some data",
            },
        )
        
        redacted = self.redactor.redact_record(record)
        
        self.assertEqual(redacted.response["token"], REDACTED_VALUE)
        self.assertEqual(redacted.response["data"], "some data")
    
    def test_redact_nested_secrets(self):
        """Test that secrets in nested structures are redacted."""
        # The pattern expects format like: api_key=value or "api_key": "value"
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={
                "user": {
                    "name": "John",
                    "auth_string": 'api_key=supersecretkey12345678',
                }
            },
        )
        
        redacted = self.redactor.redact_record(record)
        
        # The api_key pattern should be redacted
        self.assertNotIn(
            "supersecretkey12345678",
            str(redacted.response),
        )
    
    def test_preserves_exchange_id(self):
        """Test that exchange_id is preserved after redaction."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "headers": {"Authorization": "secret"},
            },
        )
        
        original_id = record.exchange_id
        redacted = self.redactor.redact_record(record)
        
        self.assertEqual(redacted.exchange_id, original_id)
    
    def test_preserves_content_hash(self):
        """Test that content_sha256 is preserved (not recomputed)."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "headers": {"Authorization": "secret"},
            },
        )
        
        original_hash = record.content_sha256
        redacted = self.redactor.redact_record(record)
        
        # Hash should be preserved from original (for traceability)
        self.assertEqual(redacted.content_sha256, original_hash)
    
    def test_tracks_redactions_applied(self):
        """Test that redactions_applied is updated."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={"headers": {"Authorization": "secret"}},
            response={"data": "test"},
        )
        
        redacted = self.redactor.redact_record(record)
        
        self.assertIn("request_headers", redacted.redactions_applied)
        self.assertIn("response_secrets", redacted.redactions_applied)
    
    def test_custom_patterns(self):
        """Test custom redaction patterns."""
        redactor = Redactor(
            custom_patterns=[r"CUSTOM-[A-Z0-9]{8}"],
        )
        
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={"id": "CUSTOM-ABC12345"},
        )
        
        redacted = redactor.redact_record(record)
        
        self.assertEqual(redacted.response["id"], REDACTED_VALUE)


class TestApplyRedaction(unittest.TestCase):
    """Test cases for apply_redaction convenience function."""
    
    def test_apply_redaction(self):
        """Test the convenience function."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "headers": {"Authorization": "secret"},
            },
        )
        
        redacted = apply_redaction(record)
        
        self.assertEqual(
            redacted.request["headers"]["Authorization"],
            REDACTED_VALUE,
        )
    
    def test_apply_redaction_with_custom_headers(self):
        """Test with custom headers to redact."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={
                "headers": {
                    "X-Custom-Secret": "secret-value",
                    "Authorization": "bearer token",
                },
            },
        )
        
        redacted = apply_redaction(
            record,
            headers_to_redact={"x-custom-secret"},
        )
        
        self.assertEqual(
            redacted.request["headers"]["X-Custom-Secret"],
            REDACTED_VALUE,
        )
        # Authorization not in custom set, so preserved
        self.assertEqual(
            redacted.request["headers"]["Authorization"],
            "bearer token",
        )


if __name__ == "__main__":
    unittest.main()
