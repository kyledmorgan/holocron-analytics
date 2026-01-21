#!/usr/bin/env python3
"""
Unit tests for canonical serialization and content hashing.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.snapshot.canonical import (
    canonicalize,
    compute_content_hash,
    build_hash_input,
    verify_content_hash,
)
from ingest.snapshot.models import ExchangeRecord, Provenance


class TestCanonicalize(unittest.TestCase):
    """Test cases for canonical JSON serialization."""
    
    def test_basic_dict(self):
        """Test canonicalization of a simple dict."""
        obj = {"b": 1, "a": 2}
        result = canonicalize(obj)
        # Keys should be sorted
        self.assertEqual(result, '{"a":2,"b":1}')
    
    def test_nested_dict(self):
        """Test canonicalization of nested dicts."""
        obj = {"z": {"b": 1, "a": 2}, "a": 0}
        result = canonicalize(obj)
        # All keys sorted at all levels
        self.assertEqual(result, '{"a":0,"z":{"a":2,"b":1}}')
    
    def test_list_order_preserved(self):
        """Test that list order is preserved."""
        obj = {"items": [3, 1, 2]}
        result = canonicalize(obj)
        self.assertEqual(result, '{"items":[3,1,2]}')
    
    def test_unicode_normalization(self):
        """Test unicode NFC normalization."""
        # é can be represented as single char or e + combining accent
        composed = "\u00e9"  # é as single char
        decomposed = "e\u0301"  # e + combining acute accent
        
        result1 = canonicalize({"name": composed})
        result2 = canonicalize({"name": decomposed})
        
        # Both should normalize to same form
        self.assertEqual(result1, result2)
    
    def test_no_whitespace(self):
        """Test that no insignificant whitespace is added."""
        obj = {"a": 1, "b": [1, 2, 3]}
        result = canonicalize(obj)
        self.assertNotIn(" ", result)
        self.assertNotIn("\n", result)
    
    def test_null_handling(self):
        """Test null values are serialized correctly."""
        obj = {"a": None, "b": 1}
        result = canonicalize(obj)
        self.assertEqual(result, '{"a":null,"b":1}')
    
    def test_boolean_handling(self):
        """Test boolean values."""
        obj = {"t": True, "f": False}
        result = canonicalize(obj)
        self.assertEqual(result, '{"f":false,"t":true}')
    
    def test_stability(self):
        """Test that canonicalization is stable across multiple calls."""
        obj = {"c": 1, "a": 2, "b": [3, 4]}
        
        results = [canonicalize(obj) for _ in range(10)]
        
        # All results should be identical
        self.assertEqual(len(set(results)), 1)


class TestContentHash(unittest.TestCase):
    """Test cases for content hashing."""
    
    def test_hash_format(self):
        """Test that hash is a 64-char hex string (SHA256)."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            request={"url": "http://example.com"},
            response={"data": "test"},
        )
        
        self.assertEqual(len(record.content_sha256), 64)
        # Should be valid hex
        int(record.content_sha256, 16)
    
    def test_same_content_same_hash(self):
        """Test that identical content produces identical hash."""
        kwargs = {
            "exchange_type": "http",
            "source_system": "test",
            "entity_type": "page",
            "natural_key": "123",
            "request": {"url": "http://example.com"},
            "response": {"data": "test"},
        }
        
        hash1 = compute_content_hash(ExchangeRecord.create(**kwargs))
        hash2 = compute_content_hash(ExchangeRecord.create(**kwargs))
        
        self.assertEqual(hash1, hash2)
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        record1 = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={"data": "test1"},
        )
        
        record2 = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={"data": "test2"},
        )
        
        self.assertNotEqual(record1.content_sha256, record2.content_sha256)
    
    def test_timestamp_excluded_from_hash(self):
        """Test that observed_at_utc doesn't affect hash."""
        base_kwargs = {
            "exchange_type": "http",
            "source_system": "test",
            "entity_type": "page",
            "request": {"url": "http://example.com"},
            "response": {"data": "test"},
        }
        
        record1 = ExchangeRecord.create(
            **base_kwargs,
            observed_at_utc=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        record2 = ExchangeRecord.create(
            **base_kwargs,
            observed_at_utc=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        
        self.assertEqual(record1.content_sha256, record2.content_sha256)
    
    def test_verify_hash_valid(self):
        """Test hash verification succeeds for valid record."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        self.assertTrue(verify_content_hash(record))
    
    def test_verify_hash_invalid(self):
        """Test hash verification fails for tampered record."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        # Tamper with the response
        record.response = {"modified": True}
        
        self.assertFalse(verify_content_hash(record))
    
    def test_hash_input_components(self):
        """Test that hash input includes all required fields."""
        hash_input = build_hash_input(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="123",
            request={"url": "http://example.com"},
            response={"data": "test"},
        )
        
        self.assertIn("exchange_type", hash_input)
        self.assertIn("source_system", hash_input)
        self.assertIn("entity_type", hash_input)
        self.assertIn("natural_key", hash_input)
        self.assertIn("request", hash_input)
        self.assertIn("response", hash_input)


class TestExchangeRecord(unittest.TestCase):
    """Test cases for ExchangeRecord model."""
    
    def test_create_generates_uuid(self):
        """Test that create generates a UUID."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        # Should be a valid UUID format
        import uuid
        uuid.UUID(record.exchange_id)
    
    def test_to_dict_and_from_dict(self):
        """Test round-trip serialization."""
        original = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="123",
            request={"url": "http://example.com"},
            response={"data": "test"},
            provenance=Provenance(runner_name="test-runner"),
            tags=["tag1", "tag2"],
        )
        
        data = original.to_dict()
        restored = ExchangeRecord.from_dict(data)
        
        self.assertEqual(original.exchange_id, restored.exchange_id)
        self.assertEqual(original.exchange_type, restored.exchange_type)
        self.assertEqual(original.source_system, restored.source_system)
        self.assertEqual(original.entity_type, restored.entity_type)
        self.assertEqual(original.natural_key, restored.natural_key)
        self.assertEqual(original.content_sha256, restored.content_sha256)
        self.assertEqual(original.tags, restored.tags)
    
    def test_get_dedupe_key(self):
        """Test deduplication key generation."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="wookieepedia",
            entity_type="page",
            natural_key="Luke_Skywalker",
        )
        
        key = record.get_dedupe_key()
        self.assertEqual(key, "wookieepedia:page:Luke_Skywalker")
    
    def test_get_hash_input_key(self):
        """Test hash input key generation."""
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="wookieepedia",
            entity_type="page",
            natural_key="Luke_Skywalker",
        )
        
        key = record.get_hash_input_key()
        self.assertEqual(key, "wookieepedia|page|Luke_Skywalker")


if __name__ == "__main__":
    unittest.main()
