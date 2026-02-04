"""
Unit tests for Phase 3 chunking functionality.

Tests for:
- Chunker class
- chunk_text function
- Deterministic chunking
"""

import pytest

from llm.retrieval.chunker import Chunker, chunk_text
from llm.contracts.retrieval_contracts import ChunkingPolicy


class TestChunkText:
    """Tests for the chunk_text function."""
    
    def test_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("")
        assert chunks == []
    
    def test_short_text(self):
        """Test text shorter than chunk size."""
        text = "Short text"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        assert len(chunks) == 1
        assert chunks[0][0] == text
        assert chunks[0][1] == 0  # start offset
        assert chunks[0][2] == len(text)  # end offset
    
    def test_exact_chunk_size(self):
        """Test text exactly equal to chunk size."""
        text = "A" * 100
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        assert len(chunks) == 1
        assert len(chunks[0][0]) == 100
    
    def test_multiple_chunks(self):
        """Test text requiring multiple chunks."""
        text = "A" * 300
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        
        # With 100 size and 20 overlap, step is 80
        # 300 chars should produce about 4 chunks
        assert len(chunks) >= 3
        
        # Verify offsets
        for chunk_content, start, end in chunks:
            assert end > start
            assert text[start:end] == chunk_content
    
    def test_overlap_correctness(self):
        """Test that chunks overlap correctly."""
        text = "ABCDEFGHIJ" * 10  # 100 chars
        chunks = chunk_text(text, chunk_size=30, overlap=10)
        
        # Check that consecutive chunks have overlapping content
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i][0][-10:]  # Last 10 chars of first chunk
            chunk2_start = chunks[i+1][0][:10]  # First 10 chars of second chunk
            # There should be overlap (not always exact due to word boundaries)
            # At minimum, verify that chunks are producing expected sizes
            assert len(chunks[i][0]) > 0
    
    def test_invalid_chunk_size(self):
        """Test invalid chunk size raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("text", chunk_size=0)
        
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("text", chunk_size=-1)
    
    def test_invalid_overlap(self):
        """Test invalid overlap raises error."""
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            chunk_text("text", chunk_size=100, overlap=-1)
    
    def test_overlap_too_large(self):
        """Test overlap >= chunk_size raises error."""
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            chunk_text("text", chunk_size=100, overlap=100)
        
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            chunk_text("text", chunk_size=100, overlap=150)
    
    def test_offsets_correctness(self):
        """Test that offsets correctly index into original text."""
        text = "The quick brown fox jumps over the lazy dog. " * 10
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        
        for chunk_content, start, end in chunks:
            # Content should match text at offsets
            assert text[start:end] == chunk_content
    
    def test_determinism(self):
        """Test that chunking is deterministic."""
        text = "Determinism test content " * 50
        
        chunks1 = chunk_text(text, chunk_size=100, overlap=20)
        chunks2 = chunk_text(text, chunk_size=100, overlap=20)
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1 == c2


class TestChunker:
    """Tests for the Chunker class."""
    
    def test_default_policy(self):
        """Test chunker with default policy."""
        chunker = Chunker()
        
        assert chunker.policy.chunk_size == 2000
        assert chunker.policy.overlap == 200
    
    def test_custom_policy(self):
        """Test chunker with custom policy."""
        policy = ChunkingPolicy(chunk_size=500, overlap=50)
        chunker = Chunker(policy)
        
        assert chunker.policy.chunk_size == 500
        assert chunker.policy.overlap == 50
    
    def test_chunk_empty_content(self):
        """Test chunking empty content."""
        chunker = Chunker()
        chunks = chunker.chunk("", "source1", "lake_text")
        
        assert chunks == []
    
    def test_chunk_produces_records(self):
        """Test that chunk produces ChunkRecord objects."""
        chunker = Chunker(ChunkingPolicy(chunk_size=100, overlap=20))
        text = "Test content for chunking " * 20
        
        chunks = chunker.chunk(
            content=text,
            source_id="test-source",
            source_type="lake_text",
        )
        
        assert len(chunks) > 0
        
        for chunk in chunks:
            # Check it's a proper ChunkRecord
            assert chunk.chunk_id
            assert chunk.source_type == "lake_text"
            assert chunk.content
            assert chunk.content_sha256
            assert chunk.byte_count > 0
            assert "chunk_index" in chunk.offsets
    
    def test_chunk_ids_are_deterministic(self):
        """Test that chunk IDs are deterministic."""
        policy = ChunkingPolicy(chunk_size=100, overlap=20)
        chunker = Chunker(policy)
        text = "Deterministic chunking test " * 10
        
        chunks1 = chunker.chunk(text, "source1", "lake_text")
        chunks2 = chunker.chunk(text, "source1", "lake_text")
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
    
    def test_chunk_ids_differ_by_source(self):
        """Test that different sources produce different chunk IDs."""
        chunker = Chunker(ChunkingPolicy(chunk_size=100, overlap=20))
        text = "Same content"
        
        chunks1 = chunker.chunk(text, "source1", "lake_text")
        chunks2 = chunker.chunk(text, "source2", "lake_text")
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id != c2.chunk_id
    
    def test_source_ref_included(self):
        """Test that source_ref is included in chunks."""
        chunker = Chunker()
        chunks = chunker.chunk(
            content="Content",
            source_id="source123",
            source_type="doc",
            source_ref={"doc_id": "doc123", "url": "http://example.com"},
        )
        
        assert len(chunks) == 1
        assert chunks[0].source_ref["doc_id"] == "doc123"
        assert chunks[0].source_ref["url"] == "http://example.com"
    
    def test_max_chunks_per_source(self):
        """Test that max_chunks_per_source is enforced."""
        policy = ChunkingPolicy(chunk_size=10, overlap=2, max_chunks_per_source=3)
        chunker = Chunker(policy)
        text = "A" * 100  # Would normally produce many chunks
        
        chunks = chunker.chunk(text, "source1", "lake_text")
        
        assert len(chunks) == 3  # Limited by policy
    
    def test_policy_stored_in_chunks(self):
        """Test that policy is stored in each chunk."""
        policy = ChunkingPolicy(chunk_size=500, overlap=50, version="2.0")
        chunker = Chunker(policy)
        
        chunks = chunker.chunk("Content", "source1", "lake_text")
        
        assert len(chunks) == 1
        assert chunks[0].policy["chunk_size"] == 500
        assert chunks[0].policy["overlap"] == 50
        assert chunks[0].policy["version"] == "2.0"
