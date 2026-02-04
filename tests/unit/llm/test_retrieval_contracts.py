"""
Unit tests for Phase 3 retrieval contracts.

Tests for:
- Chunk record creation and determinism
- Embedding record creation and hashing
- Retrieval query and hit creation
- Content and vector hashing
"""

import json
import pytest
from datetime import datetime, timezone

from llm.contracts.retrieval_contracts import (
    ChunkingPolicy,
    ChunkRecord,
    EmbeddingRecord,
    RetrievalHit,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalResult,
    compute_content_hash,
    compute_vector_hash,
    generate_chunk_id,
)


class TestChunkingPolicy:
    """Tests for ChunkingPolicy dataclass."""
    
    def test_default_creation(self):
        """Test default policy creation."""
        policy = ChunkingPolicy()
        
        assert policy.chunk_size == 2000
        assert policy.overlap == 200
        assert policy.max_chunks_per_source == 100
        assert policy.version == "1.0"
    
    def test_custom_creation(self):
        """Test custom policy creation."""
        policy = ChunkingPolicy(
            chunk_size=1000,
            overlap=100,
            max_chunks_per_source=50,
        )
        
        assert policy.chunk_size == 1000
        assert policy.overlap == 100
        assert policy.max_chunks_per_source == 50
    
    def test_to_dict(self):
        """Test serialization to dict."""
        policy = ChunkingPolicy(chunk_size=500)
        d = policy.to_dict()
        
        assert d["chunk_size"] == 500
        assert "version" in d
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "chunk_size": 1500,
            "overlap": 150,
        }
        
        policy = ChunkingPolicy.from_dict(data)
        
        assert policy.chunk_size == 1500
        assert policy.overlap == 150


class TestChunkRecord:
    """Tests for ChunkRecord dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        chunk = ChunkRecord(
            chunk_id="abc123",
            source_type="lake_text",
            source_ref={"lake_uri": "path/to/file.txt"},
            offsets={"chunk_index": 0, "start_offset": 0, "end_offset": 100},
            content="Test content",
            content_sha256="hash123",
            byte_count=12,
            policy={"chunk_size": 2000},
        )
        
        assert chunk.chunk_id == "abc123"
        assert chunk.source_type == "lake_text"
        assert chunk.content == "Test content"
        assert chunk.byte_count == 12
    
    def test_to_dict(self):
        """Test serialization."""
        chunk = ChunkRecord(
            chunk_id="test123",
            source_type="doc",
            source_ref={"doc_id": "123"},
            offsets={"chunk_index": 0},
            content="Content",
            content_sha256="hash",
            byte_count=7,
            policy={"version": "1.0"},
        )
        
        d = chunk.to_dict()
        assert d["chunk_id"] == "test123"
        assert d["source_type"] == "doc"
        assert "created_utc" in d
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "chunk_id": "chunk123",
            "source_type": "transcript",
            "source_ref": {"uri": "test"},
            "offsets": {"chunk_index": 1},
            "content": "Text",
            "content_sha256": "hash",
            "byte_count": 4,
            "policy": {},
        }
        
        chunk = ChunkRecord.from_dict(data)
        assert chunk.chunk_id == "chunk123"
        assert chunk.source_type == "transcript"


class TestEmbeddingRecord:
    """Tests for EmbeddingRecord dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        embedding = EmbeddingRecord(
            embedding_id="emb123",
            chunk_id="chunk123",
            embedding_model="nomic-embed-text",
            vector_dim=768,
            vector=[0.1, 0.2, 0.3],
            vector_sha256="vectorhash",
        )
        
        assert embedding.embedding_id == "emb123"
        assert embedding.chunk_id == "chunk123"
        assert embedding.embedding_model == "nomic-embed-text"
        assert embedding.vector_dim == 768
        assert len(embedding.vector) == 3
    
    def test_to_dict(self):
        """Test serialization."""
        embedding = EmbeddingRecord(
            embedding_id="emb1",
            chunk_id="chunk1",
            embedding_model="model",
            vector_dim=3,
            vector=[1.0, 2.0, 3.0],
            vector_sha256="hash",
        )
        
        d = embedding.to_dict()
        assert d["embedding_id"] == "emb1"
        assert d["vector"] == [1.0, 2.0, 3.0]
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "embedding_id": "emb2",
            "chunk_id": "chunk2",
            "embedding_model": "test-model",
            "vector_dim": 2,
            "vector": [0.5, 0.5],
            "vector_sha256": "hash2",
        }
        
        embedding = EmbeddingRecord.from_dict(data)
        assert embedding.embedding_id == "emb2"
        assert embedding.vector == [0.5, 0.5]


class TestRetrievalPolicy:
    """Tests for RetrievalPolicy dataclass."""
    
    def test_default_creation(self):
        """Test default policy creation."""
        policy = RetrievalPolicy()
        
        assert policy.scoring_method == "cosine_similarity"
        assert policy.min_score_threshold == 0.0
        assert policy.secondary_sort == "chunk_id"
    
    def test_to_dict(self):
        """Test serialization."""
        policy = RetrievalPolicy(min_score_threshold=0.5)
        d = policy.to_dict()
        
        assert d["min_score_threshold"] == 0.5


class TestRetrievalQuery:
    """Tests for RetrievalQuery dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        query = RetrievalQuery(
            retrieval_id="ret123",
            query_text="What is the Force?",
            query_embedding_model="nomic-embed-text",
            top_k=10,
        )
        
        assert query.retrieval_id == "ret123"
        assert query.query_text == "What is the Force?"
        assert query.top_k == 10
    
    def test_with_filters(self):
        """Test with filters."""
        query = RetrievalQuery(
            retrieval_id="ret456",
            query_text="Test",
            query_embedding_model="model",
            top_k=5,
            filters={"source_type": ["lake_text", "doc"]},
        )
        
        assert query.filters["source_type"] == ["lake_text", "doc"]
    
    def test_to_dict(self):
        """Test serialization."""
        query = RetrievalQuery(
            retrieval_id="ret789",
            query_text="Query",
            query_embedding_model="model",
            top_k=20,
            run_id="run123",
        )
        
        d = query.to_dict()
        assert d["retrieval_id"] == "ret789"
        assert d["run_id"] == "run123"


class TestRetrievalHit:
    """Tests for RetrievalHit dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        hit = RetrievalHit(
            retrieval_id="ret123",
            chunk_id="chunk456",
            score=0.95,
            rank=1,
        )
        
        assert hit.retrieval_id == "ret123"
        assert hit.chunk_id == "chunk456"
        assert hit.score == 0.95
        assert hit.rank == 1
    
    def test_with_metadata(self):
        """Test with metadata."""
        hit = RetrievalHit(
            retrieval_id="ret1",
            chunk_id="chunk1",
            score=0.8,
            rank=2,
            metadata={"source_type": "doc", "offsets": {"start": 0}},
        )
        
        assert hit.metadata["source_type"] == "doc"
    
    def test_to_dict(self):
        """Test serialization."""
        hit = RetrievalHit(
            retrieval_id="r1",
            chunk_id="c1",
            score=0.75,
            rank=3,
        )
        
        d = hit.to_dict()
        assert d["score"] == 0.75
        assert d["rank"] == 3


class TestRetrievalResult:
    """Tests for RetrievalResult dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        query = RetrievalQuery(
            retrieval_id="ret1",
            query_text="Test",
            query_embedding_model="model",
            top_k=5,
        )
        hits = [
            RetrievalHit(retrieval_id="ret1", chunk_id="c1", score=0.9, rank=1),
            RetrievalHit(retrieval_id="ret1", chunk_id="c2", score=0.8, rank=2),
        ]
        
        result = RetrievalResult(
            query=query,
            hits=hits,
            total_candidates=100,
            execution_ms=50,
        )
        
        assert result.query.retrieval_id == "ret1"
        assert len(result.hits) == 2
        assert result.total_candidates == 100
        assert result.execution_ms == 50
    
    def test_to_dict(self):
        """Test serialization."""
        query = RetrievalQuery(
            retrieval_id="ret2",
            query_text="Query",
            query_embedding_model="m",
            top_k=3,
        )
        result = RetrievalResult(query=query, hits=[])
        
        d = result.to_dict()
        assert "query" in d
        assert "hits" in d


class TestGenerateChunkId:
    """Tests for deterministic chunk ID generation."""
    
    def test_determinism(self):
        """Test that same inputs produce same ID."""
        id1 = generate_chunk_id("source1", 0, 0, 100, "1.0")
        id2 = generate_chunk_id("source1", 0, 0, 100, "1.0")
        
        assert id1 == id2
    
    def test_different_sources(self):
        """Test that different sources produce different IDs."""
        id1 = generate_chunk_id("source1", 0, 0, 100, "1.0")
        id2 = generate_chunk_id("source2", 0, 0, 100, "1.0")
        
        assert id1 != id2
    
    def test_different_offsets(self):
        """Test that different offsets produce different IDs."""
        id1 = generate_chunk_id("source1", 0, 0, 100, "1.0")
        id2 = generate_chunk_id("source1", 1, 100, 200, "1.0")
        
        assert id1 != id2
    
    def test_different_policy_version(self):
        """Test that different policy versions produce different IDs."""
        id1 = generate_chunk_id("source1", 0, 0, 100, "1.0")
        id2 = generate_chunk_id("source1", 0, 0, 100, "2.0")
        
        assert id1 != id2
    
    def test_id_format(self):
        """Test that ID is a valid SHA256 hex string."""
        chunk_id = generate_chunk_id("source", 0, 0, 100, "1.0")
        
        assert len(chunk_id) == 64
        assert all(c in "0123456789abcdef" for c in chunk_id)


class TestComputeVectorHash:
    """Tests for vector hashing."""
    
    def test_determinism(self):
        """Test that same vectors produce same hash."""
        vec = [0.1, 0.2, 0.3, 0.4, 0.5]
        hash1 = compute_vector_hash(vec)
        hash2 = compute_vector_hash(vec)
        
        assert hash1 == hash2
    
    def test_different_vectors(self):
        """Test that different vectors produce different hashes."""
        hash1 = compute_vector_hash([0.1, 0.2, 0.3])
        hash2 = compute_vector_hash([0.1, 0.2, 0.4])
        
        assert hash1 != hash2
    
    def test_hash_format(self):
        """Test that hash is valid SHA256."""
        vec_hash = compute_vector_hash([1.0, 2.0, 3.0])
        
        assert len(vec_hash) == 64
        assert all(c in "0123456789abcdef" for c in vec_hash)


class TestComputeContentHash:
    """Tests for content hashing."""
    
    def test_determinism(self):
        """Test that same content produces same hash."""
        content = "Test content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        
        assert hash1 == hash2
    
    def test_different_content(self):
        """Test that different content produces different hashes."""
        hash1 = compute_content_hash("Content A")
        hash2 = compute_content_hash("Content B")
        
        assert hash1 != hash2
