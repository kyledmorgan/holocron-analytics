"""
Unit tests for evidence bounding rules.

Tests for:
- Item bounding (max bytes per item)
- Bundle bounding (max items, max total bytes)
- Policy validation
- Bounding metadata recording
"""

import pytest

from llm.contracts.evidence_contracts import EvidenceItem, EvidencePolicy
from llm.evidence.bounding import (
    apply_item_bounding,
    apply_bundle_bounding,
    validate_policy,
)


class TestApplyItemBounding:
    """Tests for item-level bounding."""
    
    def test_content_under_limit(self):
        """Test content that doesn't need bounding."""
        content = "Short content"
        bounded, meta = apply_item_bounding(content, 1000, "inline_text")
        
        assert bounded == content
        assert meta["applied"] is False
        assert meta["original_size"] == len(content.encode('utf-8'))
    
    def test_content_over_limit(self):
        """Test content that exceeds limit."""
        content = "A" * 1000
        bounded, meta = apply_item_bounding(content, 100, "inline_text")
        
        assert len(bounded.encode('utf-8')) <= 100
        assert meta["applied"] is True
        assert meta["original_size"] == 1000
        assert meta["bounded_size"] <= 100
    
    def test_utf8_handling(self):
        """Test proper UTF-8 character handling."""
        # Content with multi-byte characters
        content = "Hello 世界" * 100
        bounded, meta = apply_item_bounding(content, 50, "inline_text")
        
        # Should not cut in middle of UTF-8 character
        assert bounded == bounded  # Should be valid UTF-8
        assert meta["applied"] is True


class TestApplyBundleBounding:
    """Tests for bundle-level bounding."""
    
    def test_within_limits(self):
        """Test bundle within limits."""
        items = [
            EvidenceItem(
                evidence_id="item1",
                evidence_type="inline_text",
                source_ref={},
                content="A" * 50,
                content_sha256="hash1",
                byte_count=50,
            ),
            EvidenceItem(
                evidence_id="item2",
                evidence_type="inline_text",
                source_ref={},
                content="B" * 50,
                content_sha256="hash2",
                byte_count=50,
            ),
        ]
        
        policy = EvidencePolicy(max_items=10, max_total_bytes=1000)
        bounded, meta = apply_bundle_bounding(items, policy)
        
        assert len(bounded) == 2
        assert meta["applied"] is False
        assert meta["items_dropped"] == 0
    
    def test_max_items_exceeded(self):
        """Test bundle with too many items."""
        items = [
            EvidenceItem(
                evidence_id=f"item{i}",
                evidence_type="inline_text",
                source_ref={},
                content=f"Content {i}",
                content_sha256=f"hash{i}",
                byte_count=10,
            )
            for i in range(10)
        ]
        
        policy = EvidencePolicy(max_items=5, max_total_bytes=10000)
        bounded, meta = apply_bundle_bounding(items, policy)
        
        assert len(bounded) == 5
        assert meta["items_dropped"] == 5
        assert meta["applied"] is True
    
    def test_max_bytes_exceeded(self):
        """Test bundle with too many bytes."""
        items = [
            EvidenceItem(
                evidence_id=f"item{i}",
                evidence_type="inline_text",
                source_ref={},
                content="X" * 100,
                content_sha256=f"hash{i}",
                byte_count=100,
            )
            for i in range(10)
        ]
        
        policy = EvidencePolicy(max_items=100, max_total_bytes=500)
        bounded, meta = apply_bundle_bounding(items, policy)
        
        # Should keep only items that fit in 500 bytes
        assert len(bounded) == 5
        assert meta["total_bytes"] == 500
        assert meta["items_dropped"] == 5
    
    def test_preserves_order(self):
        """Test that bounding preserves item order."""
        items = [
            EvidenceItem(
                evidence_id=f"item{i}",
                evidence_type="inline_text",
                source_ref={},
                content=f"Content {i}",
                content_sha256=f"hash{i}",
                byte_count=10,
            )
            for i in range(10)
        ]
        
        policy = EvidencePolicy(max_items=5, max_total_bytes=10000)
        bounded, meta = apply_bundle_bounding(items, policy)
        
        # Should keep first 5 items
        assert [item.evidence_id for item in bounded] == ["item0", "item1", "item2", "item3", "item4"]


class TestValidatePolicy:
    """Tests for policy validation."""
    
    def test_valid_policy(self):
        """Test valid policy."""
        policy = EvidencePolicy()
        errors = validate_policy(policy)
        
        assert errors == []
    
    def test_max_items_too_low(self):
        """Test max_items validation."""
        policy = EvidencePolicy(max_items=0)
        errors = validate_policy(policy)
        
        assert any("max_items" in e for e in errors)
    
    def test_max_total_bytes_too_low(self):
        """Test max_total_bytes validation."""
        policy = EvidencePolicy(max_total_bytes=100)
        errors = validate_policy(policy)
        
        assert any("max_total_bytes" in e for e in errors)
    
    def test_max_item_bytes_too_low(self):
        """Test max_item_bytes validation."""
        policy = EvidencePolicy(max_item_bytes=50)
        errors = validate_policy(policy)
        
        assert any("max_item_bytes" in e for e in errors)
    
    def test_max_item_exceeds_total(self):
        """Test max_item_bytes > max_total_bytes."""
        policy = EvidencePolicy(max_item_bytes=10000, max_total_bytes=5000)
        errors = validate_policy(policy)
        
        assert any("exceed" in e for e in errors)
    
    def test_invalid_sampling_strategy(self):
        """Test invalid sampling strategy."""
        policy = EvidencePolicy(sampling_strategy="invalid")
        errors = validate_policy(policy)
        
        assert any("sampling_strategy" in e for e in errors)
    
    def test_chunk_overlap_too_large(self):
        """Test chunk overlap >= chunk size."""
        policy = EvidencePolicy(chunk_size=100, chunk_overlap=100)
        errors = validate_policy(policy)
        
        assert any("chunk_overlap" in e for e in errors)
    
    def test_multiple_errors(self):
        """Test multiple validation errors."""
        policy = EvidencePolicy(
            max_items=0,
            max_total_bytes=100,
            sampling_strategy="invalid"
        )
        errors = validate_policy(policy)
        
        assert len(errors) >= 3
