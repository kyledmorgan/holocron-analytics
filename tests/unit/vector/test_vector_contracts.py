"""
Unit tests for vector runtime contracts.

Tests for:
- EmbeddingSpace creation and serialization
- VectorChunk creation and hashing
- VectorEmbedding with lineage
- VectorRetrieval and VectorRetrievalHit
- Job and Run types
- Utility functions (hashing, chunk ID generation)
"""

import json
import pytest
from datetime import datetime, timezone
from uuid import UUID

from vector.contracts.models import (
    EmbeddingSpace,
    VectorJob,
    VectorRun,
    VectorSourceRegistry,
    VectorChunk,
    VectorEmbedding,
    VectorRetrieval,
    VectorRetrievalHit,
    JobType,
    JobStatus,
    RunStatus,
    SourceStatus,
    compute_content_hash,
    compute_vector_hash,
    generate_chunk_id,
)


class TestEmbeddingSpace:
    """Tests for EmbeddingSpace dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        space = EmbeddingSpace(
            embedding_space_id="test-space-id",
            provider="ollama",
            model_name="nomic-embed-text",
            dimensions=768,
        )
        
        assert space.embedding_space_id == "test-space-id"
        assert space.provider == "ollama"
        assert space.model_name == "nomic-embed-text"
        assert space.dimensions == 768
        assert space.normalize_flag is True
        assert space.distance_metric == "cosine"
        assert space.is_active is True
    
    def test_creation_with_optional_fields(self):
        """Test creation with all optional fields."""
        space = EmbeddingSpace(
            embedding_space_id="test-space-id",
            provider="openai",
            model_name="text-embedding-3-small",
            dimensions=1536,
            model_tag="v1",
            model_digest="sha256:abc123",
            normalize_flag=False,
            distance_metric="dot",
            preprocess_policy={"lowercase": True},
            transform_ref="pca-128",
            description="Test embedding space",
            is_active=False,
        )
        
        assert space.model_tag == "v1"
        assert space.model_digest == "sha256:abc123"
        assert space.normalize_flag is False
        assert space.distance_metric == "dot"
        assert space.preprocess_policy == {"lowercase": True}
        assert space.transform_ref == "pca-128"
        assert space.description == "Test embedding space"
        assert space.is_active is False
    
    def test_to_dict(self):
        """Test serialization to dict."""
        space = EmbeddingSpace(
            embedding_space_id="test-space-id",
            provider="ollama",
            model_name="nomic-embed-text",
            dimensions=768,
            description="Test space",
        )
        
        d = space.to_dict()
        
        assert d["embedding_space_id"] == "test-space-id"
        assert d["provider"] == "ollama"
        assert d["model_name"] == "nomic-embed-text"
        assert d["dimensions"] == 768
        assert d["description"] == "Test space"
        assert "created_utc" in d
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "embedding_space_id": "test-space-id",
            "provider": "ollama",
            "model_name": "nomic-embed-text",
            "dimensions": 768,
            "normalize_flag": True,
        }
        
        space = EmbeddingSpace.from_dict(data)
        
        assert space.embedding_space_id == "test-space-id"
        assert space.provider == "ollama"
        assert space.dimensions == 768
    
    def test_create_new(self):
        """Test create_new factory method."""
        space = EmbeddingSpace.create_new(
            provider="ollama",
            model_name="nomic-embed-text",
            dimensions=768,
        )
        
        # Should have a valid UUID
        UUID(space.embedding_space_id)
        assert space.provider == "ollama"
        assert space.model_name == "nomic-embed-text"
        assert space.dimensions == 768
    
    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = EmbeddingSpace.create_new(
            provider="ollama",
            model_name="nomic-embed-text",
            dimensions=768,
            model_tag="latest",
            description="Test space",
        )
        
        d = original.to_dict()
        restored = EmbeddingSpace.from_dict(d)
        
        assert restored.embedding_space_id == original.embedding_space_id
        assert restored.provider == original.provider
        assert restored.model_name == original.model_name
        assert restored.dimensions == original.dimensions
        assert restored.model_tag == original.model_tag
        assert restored.description == original.description


class TestVectorChunk:
    """Tests for VectorChunk dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        chunk = VectorChunk(
            chunk_id="abc123def456",
            source_type="lake_text",
            source_ref={"lake_uri": "/path/to/file.txt"},
            offsets={"start": 0, "end": 1000, "index": 0},
            content="This is test content",
            content_sha256="deadbeef",
            byte_count=20,
            policy={"chunk_size": 2000, "overlap": 200},
        )
        
        assert chunk.chunk_id == "abc123def456"
        assert chunk.source_type == "lake_text"
        assert chunk.source_ref["lake_uri"] == "/path/to/file.txt"
        assert chunk.content == "This is test content"
        assert chunk.byte_count == 20
    
    def test_with_source_id(self):
        """Test creation with source_id FK."""
        chunk = VectorChunk(
            chunk_id="abc123def456",
            source_type="lake_text",
            source_ref={"lake_uri": "/path/to/file.txt"},
            offsets={"start": 0, "end": 1000, "index": 0},
            content="This is test content",
            content_sha256="deadbeef",
            byte_count=20,
            policy={"chunk_size": 2000},
            source_id="source-123",
        )
        
        assert chunk.source_id == "source-123"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        chunk = VectorChunk(
            chunk_id="abc123",
            source_type="lake_text",
            source_ref={"lake_uri": "/test.txt"},
            offsets={"start": 0, "end": 100},
            content="test",
            content_sha256="hash",
            byte_count=4,
            policy={},
        )
        
        d = chunk.to_dict()
        
        assert d["chunk_id"] == "abc123"
        assert d["source_type"] == "lake_text"
        assert d["content"] == "test"
        assert "created_utc" in d
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "chunk_id": "abc123",
            "source_type": "lake_text",
            "source_ref": {"lake_uri": "/test.txt"},
            "offsets": {"start": 0},
            "content": "test content",
            "content_sha256": "hash123",
            "byte_count": 12,
            "policy": {"version": "1.0"},
        }
        
        chunk = VectorChunk.from_dict(data)
        
        assert chunk.chunk_id == "abc123"
        assert chunk.content == "test content"
        assert chunk.policy["version"] == "1.0"


class TestVectorEmbedding:
    """Tests for VectorEmbedding dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        embedding = VectorEmbedding(
            embedding_id="emb-123",
            chunk_id="chunk-456",
            embedding_space_id="space-789",
            input_content_sha256="content-hash",
            vector=[0.1, 0.2, 0.3, 0.4],
            vector_sha256="vector-hash",
        )
        
        assert embedding.embedding_id == "emb-123"
        assert embedding.chunk_id == "chunk-456"
        assert embedding.embedding_space_id == "space-789"
        assert embedding.input_content_sha256 == "content-hash"
        assert embedding.vector == [0.1, 0.2, 0.3, 0.4]
    
    def test_with_run_id(self):
        """Test creation with run_id for lineage."""
        embedding = VectorEmbedding(
            embedding_id="emb-123",
            chunk_id="chunk-456",
            embedding_space_id="space-789",
            input_content_sha256="content-hash",
            vector=[0.1, 0.2, 0.3],
            vector_sha256="vector-hash",
            run_id="run-abc",
        )
        
        assert embedding.run_id == "run-abc"
    
    def test_create_new(self):
        """Test create_new factory method."""
        vector = [0.1, 0.2, 0.3, 0.4]
        embedding = VectorEmbedding.create_new(
            chunk_id="chunk-456",
            embedding_space_id="space-789",
            input_content_sha256="content-hash",
            vector=vector,
        )
        
        # Should have a valid UUID
        UUID(embedding.embedding_id)
        # Should have computed vector hash
        assert embedding.vector_sha256 == compute_vector_hash(vector)
    
    def test_to_dict(self):
        """Test serialization to dict."""
        embedding = VectorEmbedding(
            embedding_id="emb-123",
            chunk_id="chunk-456",
            embedding_space_id="space-789",
            input_content_sha256="hash",
            vector=[0.1, 0.2],
            vector_sha256="vhash",
        )
        
        d = embedding.to_dict()
        
        assert d["embedding_id"] == "emb-123"
        assert d["chunk_id"] == "chunk-456"
        assert d["embedding_space_id"] == "space-789"
        assert d["input_content_sha256"] == "hash"
        assert d["vector"] == [0.1, 0.2]
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "embedding_id": "emb-123",
            "chunk_id": "chunk-456",
            "embedding_space_id": "space-789",
            "input_content_sha256": "hash",
            "vector": [0.5, 0.6, 0.7],
            "vector_sha256": "vhash",
            "run_id": "run-123",
        }
        
        embedding = VectorEmbedding.from_dict(data)
        
        assert embedding.embedding_id == "emb-123"
        assert embedding.vector == [0.5, 0.6, 0.7]
        assert embedding.run_id == "run-123"


class TestVectorRetrieval:
    """Tests for VectorRetrieval dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        retrieval = VectorRetrieval(
            retrieval_id="ret-123",
            embedding_space_id="space-789",
            query_text="What is the Force?",
            top_k=10,
        )
        
        assert retrieval.retrieval_id == "ret-123"
        assert retrieval.embedding_space_id == "space-789"
        assert retrieval.query_text == "What is the Force?"
        assert retrieval.top_k == 10
    
    def test_with_optional_fields(self):
        """Test creation with optional fields."""
        retrieval = VectorRetrieval(
            retrieval_id="ret-123",
            embedding_space_id="space-789",
            query_text="query",
            top_k=5,
            query_embedding=[0.1, 0.2, 0.3],
            filters={"source_type": "lake_text"},
            policy={"rerank": True},
            run_id="run-456",
        )
        
        assert retrieval.query_embedding == [0.1, 0.2, 0.3]
        assert retrieval.filters["source_type"] == "lake_text"
        assert retrieval.policy["rerank"] is True
        assert retrieval.run_id == "run-456"
    
    def test_create_new(self):
        """Test create_new factory method."""
        retrieval = VectorRetrieval.create_new(
            embedding_space_id="space-789",
            query_text="test query",
            top_k=10,
        )
        
        UUID(retrieval.retrieval_id)
        assert retrieval.query_text == "test query"


class TestVectorRetrievalHit:
    """Tests for VectorRetrievalHit dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        hit = VectorRetrievalHit(
            retrieval_id="ret-123",
            rank=1,
            chunk_id="chunk-456",
            score=0.95,
        )
        
        assert hit.retrieval_id == "ret-123"
        assert hit.rank == 1
        assert hit.chunk_id == "chunk-456"
        assert hit.score == 0.95
    
    def test_with_metadata(self):
        """Test creation with metadata."""
        hit = VectorRetrievalHit(
            retrieval_id="ret-123",
            rank=2,
            chunk_id="chunk-789",
            score=0.87,
            metadata={"source": "wookieepedia", "section": "History"},
        )
        
        assert hit.metadata["source"] == "wookieepedia"
        assert hit.metadata["section"] == "History"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        hit = VectorRetrievalHit(
            retrieval_id="ret-123",
            rank=1,
            chunk_id="chunk-456",
            score=0.95,
            metadata={"key": "value"},
        )
        
        d = hit.to_dict()
        
        assert d["retrieval_id"] == "ret-123"
        assert d["rank"] == 1
        assert d["score"] == 0.95
        assert d["metadata"]["key"] == "value"


class TestJobAndRunTypes:
    """Tests for VectorJob and VectorRun."""
    
    def test_job_creation(self):
        """Test VectorJob creation."""
        job = VectorJob(
            job_id="job-123",
            job_type=JobType.EMBED_CHUNKS,
            input_json={"chunk_ids": ["c1", "c2"]},
        )
        
        assert job.job_id == "job-123"
        assert job.job_type == JobType.EMBED_CHUNKS
        assert job.status == JobStatus.NEW
        assert job.priority == 100
    
    def test_job_create_new(self):
        """Test VectorJob.create_new factory."""
        job = VectorJob.create_new(
            job_type=JobType.CHUNK_SOURCE,
            input_json={"source_id": "src-123"},
            priority=50,
        )
        
        UUID(job.job_id)
        assert job.job_type == JobType.CHUNK_SOURCE
        assert job.priority == 50
    
    def test_job_types(self):
        """Test all job types are valid."""
        for job_type in JobType:
            job = VectorJob.create_new(
                job_type=job_type,
                input_json={},
            )
            assert job.job_type == job_type
    
    def test_run_creation(self):
        """Test VectorRun creation."""
        run = VectorRun(
            run_id="run-123",
            job_id="job-456",
            worker_id="worker-1",
        )
        
        assert run.run_id == "run-123"
        assert run.job_id == "job-456"
        assert run.worker_id == "worker-1"
        assert run.status == RunStatus.RUNNING
    
    def test_run_create_new(self):
        """Test VectorRun.create_new factory."""
        run = VectorRun.create_new(
            job_id="job-456",
            worker_id="worker-1",
            embedding_space_id="space-789",
        )
        
        UUID(run.run_id)
        assert run.embedding_space_id == "space-789"


class TestSourceRegistry:
    """Tests for VectorSourceRegistry."""
    
    def test_creation(self):
        """Test basic creation."""
        source = VectorSourceRegistry(
            source_id="src-123",
            source_type="lake_text",
            source_ref={"lake_uri": "/path/to/file.txt"},
        )
        
        assert source.source_id == "src-123"
        assert source.source_type == "lake_text"
        assert source.status == SourceStatus.INDEXED
    
    def test_with_indexing_info(self):
        """Test creation with indexing information."""
        now = datetime.now(timezone.utc)
        source = VectorSourceRegistry(
            source_id="src-123",
            source_type="lake_text",
            source_ref={"lake_uri": "/path/to/file.txt"},
            content_sha256="abc123hash",
            last_indexed_utc=now,
            chunk_count=15,
            tags={"franchise": "starwars"},
        )
        
        assert source.content_sha256 == "abc123hash"
        assert source.last_indexed_utc == now
        assert source.chunk_count == 15
        assert source.tags["franchise"] == "starwars"
    
    def test_status_values(self):
        """Test all status values."""
        for status in SourceStatus:
            source = VectorSourceRegistry(
                source_id="src-123",
                source_type="lake_text",
                source_ref={},
                status=status,
            )
            assert source.status == status


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_compute_content_hash(self):
        """Test content hashing."""
        hash1 = compute_content_hash("Hello, world!")
        hash2 = compute_content_hash("Hello, world!")
        hash3 = compute_content_hash("Hello, World!")
        
        # Same content = same hash
        assert hash1 == hash2
        # Different content = different hash
        assert hash1 != hash3
        # Returns 64-char hex string (SHA256)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)
    
    def test_compute_vector_hash(self):
        """Test vector hashing."""
        vec1 = [0.1, 0.2, 0.3]
        vec2 = [0.1, 0.2, 0.3]
        vec3 = [0.1, 0.2, 0.4]
        
        hash1 = compute_vector_hash(vec1)
        hash2 = compute_vector_hash(vec2)
        hash3 = compute_vector_hash(vec3)
        
        # Same vector = same hash
        assert hash1 == hash2
        # Different vector = different hash
        assert hash1 != hash3
        # Returns 64-char hex string
        assert len(hash1) == 64
    
    def test_generate_chunk_id_deterministic(self):
        """Test that chunk ID generation is deterministic."""
        id1 = generate_chunk_id("source-1", 0, 0, 1000, "1.0")
        id2 = generate_chunk_id("source-1", 0, 0, 1000, "1.0")
        id3 = generate_chunk_id("source-1", 1, 0, 1000, "1.0")
        
        # Same inputs = same ID
        assert id1 == id2
        # Different chunk index = different ID
        assert id1 != id3
        # Returns 64-char hex string
        assert len(id1) == 64
    
    def test_generate_chunk_id_varies_by_offset(self):
        """Test that chunk ID varies with offsets."""
        id1 = generate_chunk_id("source-1", 0, 0, 1000, "1.0")
        id2 = generate_chunk_id("source-1", 0, 100, 1100, "1.0")
        
        assert id1 != id2
    
    def test_generate_chunk_id_varies_by_policy(self):
        """Test that chunk ID varies with policy version."""
        id1 = generate_chunk_id("source-1", 0, 0, 1000, "1.0")
        id2 = generate_chunk_id("source-1", 0, 0, 1000, "2.0")
        
        assert id1 != id2
