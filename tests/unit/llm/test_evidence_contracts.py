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


class TestEvidenceItemProvenance:
    """Tests for EvidenceItem provenance fields (source_system, source_uri, etc.)."""

    def test_item_with_provenance_fields(self):
        """Test item creation with all provenance fields."""
        item = EvidenceItem(
            evidence_id="lake:abc123:0",
            evidence_type="lake_text",
            source_ref={"lake_uri": "path/to/article.txt"},
            content="Sebulba was a Dug podracer.",
            content_sha256="abc123",
            byte_count=27,
            source_system="wookieepedia",
            source_uri="https://starwars.fandom.com/wiki/Sebulba",
            selector_json={"paragraph_ids": [3, 4, 5]},
            ordinal=0,
            role="primary",
            excerpt_hash="def456",
        )

        assert item.source_system == "wookieepedia"
        assert item.source_uri == "https://starwars.fandom.com/wiki/Sebulba"
        assert item.selector_json == {"paragraph_ids": [3, 4, 5]}
        assert item.ordinal == 0
        assert item.role == "primary"
        assert item.excerpt_hash == "def456"

    def test_provenance_fields_default_to_none(self):
        """Test that provenance fields default to None for backward compatibility."""
        item = EvidenceItem(
            evidence_id="inline:0",
            evidence_type="inline_text",
            source_ref={},
            content="Test",
            content_sha256="hash",
            byte_count=4,
        )

        assert item.source_system is None
        assert item.source_uri is None
        assert item.selector_json is None
        assert item.ordinal is None
        assert item.role is None
        assert item.excerpt_hash is None

    def test_provenance_fields_to_dict(self):
        """Test that provenance fields are serialized when set."""
        item = EvidenceItem(
            evidence_id="sql:abc:0",
            evidence_type="sql_result",
            source_ref={"query_key": "entities"},
            content="Result data",
            content_sha256="hash",
            byte_count=11,
            source_system="sql",
            source_uri=None,
            selector_json={"query_params": {"limit": 100}},
            ordinal=2,
            role="supporting",
        )

        d = item.to_dict()
        assert d["source_system"] == "sql"
        assert "source_uri" not in d  # None values are omitted
        assert d["selector_json"] == {"query_params": {"limit": 100}}
        assert d["ordinal"] == 2
        assert d["role"] == "supporting"

    def test_provenance_fields_omitted_when_none(self):
        """Test that None provenance fields are not serialized."""
        item = EvidenceItem(
            evidence_id="inline:0",
            evidence_type="inline_text",
            source_ref={},
            content="Test",
            content_sha256="hash",
            byte_count=4,
        )

        d = item.to_dict()
        assert "source_system" not in d
        assert "source_uri" not in d
        assert "selector_json" not in d
        assert "ordinal" not in d
        assert "role" not in d
        assert "excerpt_hash" not in d

    def test_provenance_fields_from_dict(self):
        """Test deserialization of provenance fields."""
        data = {
            "evidence_id": "lake:abc:0",
            "evidence_type": "lake_text",
            "source_ref": {"lake_uri": "path/to/file"},
            "content": "Content",
            "content_sha256": "hash",
            "byte_count": 7,
            "source_system": "wikipedia",
            "source_uri": "https://en.wikipedia.org/wiki/Test",
            "selector_json": {"revision_id": 12345},
            "ordinal": 1,
            "role": "context",
            "excerpt_hash": "xyz789",
        }

        item = EvidenceItem.from_dict(data)
        assert item.source_system == "wikipedia"
        assert item.source_uri == "https://en.wikipedia.org/wiki/Test"
        assert item.selector_json == {"revision_id": 12345}
        assert item.ordinal == 1
        assert item.role == "context"
        assert item.excerpt_hash == "xyz789"

    def test_provenance_fields_from_dict_without_new_fields(self):
        """Test backward-compatible deserialization without provenance fields."""
        data = {
            "evidence_id": "inline:0",
            "evidence_type": "inline_text",
            "source_ref": {},
            "content": "Test",
            "content_sha256": "hash",
            "byte_count": 4,
        }

        item = EvidenceItem.from_dict(data)
        assert item.source_system is None
        assert item.ordinal is None
        assert item.role is None


class TestEvidenceBundleProvenance:
    """Tests for EvidenceBundle provenance fields (bundle_sha256, bundle_kind, etc.)."""

    def test_bundle_with_provenance_fields(self):
        """Test bundle creation with provenance metadata."""
        bundle = EvidenceBundle(
            bundle_kind="llm_input",
            created_by="worker-01",
            notes="Sebulba article extraction",
        )

        assert bundle.bundle_kind == "llm_input"
        assert bundle.created_by == "worker-01"
        assert bundle.notes == "Sebulba article extraction"
        assert bundle.bundle_sha256 is None

    def test_compute_bundle_hash(self):
        """Test deterministic bundle hash computation."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="inline_text",
                source_ref={},
                content="Content 1",
                content_sha256="aaa111",
                byte_count=9,
            ),
            EvidenceItem(
                evidence_id="item2",
                evidence_type="inline_text",
                source_ref={},
                content="Content 2",
                content_sha256="bbb222",
                byte_count=9,
            ),
        ]

        bundle = EvidenceBundle(items=items)
        hash1 = bundle.compute_bundle_hash()

        assert hash1 is not None
        assert len(hash1) == 64
        assert bundle.bundle_sha256 == hash1

    def test_bundle_hash_determinism(self):
        """Test that the same items produce the same bundle hash."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="inline_text",
                source_ref={},
                content="Content 1",
                content_sha256="aaa111",
                byte_count=9,
            ),
        ]

        bundle1 = EvidenceBundle(items=items)
        bundle2 = EvidenceBundle(items=items)

        assert bundle1.compute_bundle_hash() == bundle2.compute_bundle_hash()

    def test_bundle_hash_order_sensitive(self):
        """Test that item order affects the bundle hash."""
        item_a = EvidenceItem(
            evidence_id="a", evidence_type="inline_text", source_ref={},
            content="A", content_sha256="aaa", byte_count=1,
        )
        item_b = EvidenceItem(
            evidence_id="b", evidence_type="inline_text", source_ref={},
            content="B", content_sha256="bbb", byte_count=1,
        )

        bundle_ab = EvidenceBundle(items=[item_a, item_b])
        bundle_ba = EvidenceBundle(items=[item_b, item_a])

        assert bundle_ab.compute_bundle_hash() != bundle_ba.compute_bundle_hash()

    def test_provenance_fields_default_to_none(self):
        """Test that provenance fields default to None."""
        bundle = EvidenceBundle()

        assert bundle.bundle_sha256 is None
        assert bundle.bundle_kind is None
        assert bundle.created_by is None
        assert bundle.notes is None

    def test_provenance_fields_to_dict(self):
        """Test that provenance fields are serialized when set."""
        bundle = EvidenceBundle(
            bundle_kind="llm_input",
            created_by="pipeline-worker",
            notes="Test extraction run",
        )
        bundle.compute_bundle_hash()

        d = bundle.to_dict()
        assert d["bundle_kind"] == "llm_input"
        assert d["created_by"] == "pipeline-worker"
        assert d["notes"] == "Test extraction run"
        assert "bundle_sha256" in d

    def test_provenance_fields_omitted_when_none(self):
        """Test that None provenance fields are not serialized."""
        bundle = EvidenceBundle()

        d = bundle.to_dict()
        assert "bundle_sha256" not in d
        assert "bundle_kind" not in d
        assert "created_by" not in d
        assert "notes" not in d

    def test_provenance_fields_from_dict(self):
        """Test deserialization of provenance fields."""
        data = {
            "bundle_id": "test-bundle",
            "created_utc": "2024-01-01T00:00:00+00:00",
            "build_version": "2.0",
            "policy": {},
            "items": [],
            "summary": {},
            "bundle_sha256": "abc123def456",
            "bundle_kind": "human_review_packet",
            "created_by": "reviewer-02",
            "notes": "Manual review bundle",
        }

        bundle = EvidenceBundle.from_dict(data)
        assert bundle.bundle_sha256 == "abc123def456"
        assert bundle.bundle_kind == "human_review_packet"
        assert bundle.created_by == "reviewer-02"
        assert bundle.notes == "Manual review bundle"

    def test_provenance_fields_from_dict_backward_compat(self):
        """Test backward-compatible deserialization without new fields."""
        data = {
            "bundle_id": "old-bundle",
            "created_utc": "2024-01-01T00:00:00+00:00",
            "policy": {},
            "items": [],
            "summary": {},
        }

        bundle = EvidenceBundle.from_dict(data)
        assert bundle.bundle_sha256 is None
        assert bundle.bundle_kind is None
        assert bundle.created_by is None
        assert bundle.notes is None

    def test_bundle_json_roundtrip_with_provenance(self):
        """Test full JSON roundtrip preserving provenance fields."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="lake_text",
                source_ref={"lake_uri": "path/to/file"},
                content="Content 1",
                content_sha256="hash1",
                byte_count=9,
                source_system="wookieepedia",
                ordinal=0,
                role="primary",
            ),
        ]

        original = EvidenceBundle(
            items=items,
            bundle_kind="llm_input",
            created_by="test-worker",
            notes="Roundtrip test",
        )
        original.compute_summary()
        original.compute_bundle_hash()

        json_str = original.to_json()
        restored = EvidenceBundle.from_json(json_str)

        assert restored.bundle_kind == original.bundle_kind
        assert restored.created_by == original.created_by
        assert restored.notes == original.notes
        assert restored.bundle_sha256 == original.bundle_sha256
        assert len(restored.items) == 1
        assert restored.items[0].source_system == "wookieepedia"
        assert restored.items[0].ordinal == 0
        assert restored.items[0].role == "primary"
