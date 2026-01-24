"""
Unit tests for Phase 2 evidence contracts.

Tests for:
- Evidence item and bundle creation
- Evidence policy validation
- Deterministic evidence ID generation
- Content hashing
"""

import json
import pytest
from datetime import datetime, timezone

from llm.contracts.evidence_contracts import (
    EvidenceItem,
    EvidenceBundle,
    EvidencePolicy,
    generate_evidence_id,
    compute_content_hash,
)


class TestEvidencePolicy:
    """Tests for EvidencePolicy dataclass."""
    
    def test_default_creation(self):
        """Test default policy creation."""
        policy = EvidencePolicy()
        
        assert policy.max_items == 50
        assert policy.max_total_bytes == 100000
        assert policy.max_item_bytes == 10000
        assert policy.max_sql_rows == 100
        assert policy.sampling_strategy == "first_last"
        assert policy.enable_redaction is False
    
    def test_custom_creation(self):
        """Test custom policy creation."""
        policy = EvidencePolicy(
            max_items=20,
            max_total_bytes=50000,
            max_sql_rows=50,
            enable_redaction=True
        )
        
        assert policy.max_items == 20
        assert policy.max_total_bytes == 50000
        assert policy.max_sql_rows == 50
        assert policy.enable_redaction is True
    
    def test_to_dict(self):
        """Test serialization to dict."""
        policy = EvidencePolicy(max_items=10, enable_redaction=True)
        d = policy.to_dict()
        
        assert d["max_items"] == 10
        assert d["enable_redaction"] is True
        assert "version" in d
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "max_items": 25,
            "max_total_bytes": 75000,
            "enable_redaction": True,
        }
        
        policy = EvidencePolicy.from_dict(data)
        
        assert policy.max_items == 25
        assert policy.max_total_bytes == 75000
        assert policy.enable_redaction is True


class TestEvidenceItem:
    """Tests for EvidenceItem dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        item = EvidenceItem(
            evidence_id="inline:0",
            evidence_type="inline_text",
            source_ref={"source_uri": "test"},
            content="Test content",
            content_sha256="abc123",
            byte_count=12,
        )
        
        assert item.evidence_id == "inline:0"
        assert item.evidence_type == "inline_text"
        assert item.content == "Test content"
        assert item.byte_count == 12
        assert item.metadata == {}
    
    def test_with_metadata(self):
        """Test item with metadata."""
        item = EvidenceItem(
            evidence_id="test:1",
            evidence_type="lake_text",
            source_ref={"lake_uri": "path/to/file"},
            content="Content",
            content_sha256="hash",
            byte_count=7,
            metadata={"bounding": {"applied": True}},
            offsets={"start": 0, "end": 100},
        )
        
        assert item.metadata["bounding"]["applied"] is True
        assert item.offsets == {"start": 0, "end": 100}
    
    def test_to_dict(self):
        """Test serialization."""
        item = EvidenceItem(
            evidence_id="test:0",
            evidence_type="inline_text",
            source_ref={"source": "test"},
            content="Content",
            content_sha256="hash",
            byte_count=7,
            full_ref={"full_size": 1000},
        )
        
        d = item.to_dict()
        assert d["evidence_id"] == "test:0"
        assert d["evidence_type"] == "inline_text"
        assert d["full_ref"] == {"full_size": 1000}
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "evidence_id": "sql:abc:0",
            "evidence_type": "sql_result",
            "source_ref": {"query_key": "test"},
            "content": "Result data",
            "content_sha256": "hash123",
            "byte_count": 11,
            "metadata": {"rows": 100},
        }
        
        item = EvidenceItem.from_dict(data)
        assert item.evidence_id == "sql:abc:0"
        assert item.metadata["rows"] == 100


class TestEvidenceBundle:
    """Tests for EvidenceBundle dataclass."""
    
    def test_empty_bundle(self):
        """Test empty bundle creation."""
        bundle = EvidenceBundle()
        
        assert bundle.bundle_id is not None
        assert bundle.build_version == "2.0"
        assert len(bundle.items) == 0
        assert isinstance(bundle.policy, EvidencePolicy)
    
    def test_bundle_with_items(self):
        """Test bundle with items."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="inline_text",
                source_ref={},
                content="Content 1",
                content_sha256="hash1",
                byte_count=9,
            ),
            EvidenceItem(
                evidence_id="item2",
                evidence_type="inline_text",
                source_ref={},
                content="Content 2",
                content_sha256="hash2",
                byte_count=9,
            ),
        ]
        
        bundle = EvidenceBundle(items=items)
        assert len(bundle.items) == 2
    
    def test_compute_summary(self):
        """Test summary computation."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="inline_text",
                source_ref={},
                content="A" * 100,
                content_sha256="hash1",
                byte_count=100,
            ),
            EvidenceItem(
                evidence_id="item2",
                evidence_type="sql_result",
                source_ref={},
                content="B" * 200,
                content_sha256="hash2",
                byte_count=200,
            ),
        ]
        
        bundle = EvidenceBundle(items=items)
        bundle.compute_summary()
        
        assert bundle.summary["item_count"] == 2
        assert bundle.summary["total_bytes"] == 300
        assert bundle.summary["type_counts"]["inline_text"] == 1
        assert bundle.summary["type_counts"]["sql_result"] == 1
        assert "approx_tokens" in bundle.summary
    
    def test_to_json(self):
        """Test JSON serialization."""
        bundle = EvidenceBundle()
        bundle.compute_summary()
        
        json_str = bundle.to_json()
        parsed = json.loads(json_str)
        
        assert "bundle_id" in parsed
        assert "policy" in parsed
        assert "items" in parsed
        assert "summary" in parsed
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "bundle_id": "test-bundle",
            "created_utc": "2024-01-01T00:00:00+00:00",
            "build_version": "2.0",
            "policy": {"max_items": 10},
            "items": [
                {
                    "evidence_id": "test:0",
                    "evidence_type": "inline_text",
                    "source_ref": {},
                    "content": "Test",
                    "content_sha256": "hash",
                    "byte_count": 4,
                }
            ],
            "summary": {"item_count": 1},
        }
        
        bundle = EvidenceBundle.from_dict(data)
        assert bundle.bundle_id == "test-bundle"
        assert len(bundle.items) == 1
        assert bundle.policy.max_items == 10


class TestGenerateEvidenceId:
    """Tests for deterministic evidence ID generation."""
    
    def test_inline_id(self):
        """Test inline evidence ID."""
        eid = generate_evidence_id("inline_text", "content", 0)
        assert eid == "inline:0"
        
        eid = generate_evidence_id("inline_text", "content", 5)
        assert eid == "inline:5"
    
    def test_lake_text_id(self):
        """Test lake text evidence ID."""
        eid1 = generate_evidence_id("lake_text", "path/to/file.txt", 0)
        eid2 = generate_evidence_id("lake_text", "path/to/file.txt", 0)
        
        # Should be deterministic
        assert eid1 == eid2
        assert eid1.startswith("lake:")
        assert ":0" in eid1
    
    def test_lake_text_chunks(self):
        """Test lake text with different chunks."""
        eid1 = generate_evidence_id("lake_text", "file.txt", 0)
        eid2 = generate_evidence_id("lake_text", "file.txt", 1)
        
        # Different chunk index
        assert eid1 != eid2
        assert eid1.endswith(":0")
        assert eid2.endswith(":1")
    
    def test_sql_result_id(self):
        """Test SQL result evidence ID."""
        eid = generate_evidence_id("sql_result", "query_key_1", 0)
        
        assert eid.startswith("sql:")
        assert ":0" in eid
    
    def test_determinism(self):
        """Test that IDs are deterministic for same inputs."""
        eid1 = generate_evidence_id("lake_http", "url", 0)
        eid2 = generate_evidence_id("lake_http", "url", 0)
        
        assert eid1 == eid2
    
    def test_different_sources(self):
        """Test that different sources produce different IDs."""
        eid1 = generate_evidence_id("lake_text", "source1", 0)
        eid2 = generate_evidence_id("lake_text", "source2", 0)
        
        assert eid1 != eid2


class TestComputeContentHash:
    """Tests for content hashing."""
    
    def test_hash_computation(self):
        """Test hash is computed."""
        hash1 = compute_content_hash("test content")
        
        assert len(hash1) == 64  # SHA256 hex length
        assert hash1.isalnum()
    
    def test_determinism(self):
        """Test hashing is deterministic."""
        content = "Same content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        
        assert hash1 == hash2
    
    def test_different_content(self):
        """Test different content produces different hash."""
        hash1 = compute_content_hash("content A")
        hash2 = compute_content_hash("content B")
        
        assert hash1 != hash2
