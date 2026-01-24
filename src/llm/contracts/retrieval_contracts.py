"""
Retrieval Contracts - Phase 3 data models for RAG (Retrieval Augmented Generation).

These models define the structure for chunk records, embedding records, retrieval
queries, and retrieval results used by the Phase 3 retrieval system.

Uses dataclasses following the pattern established in phase1_contracts.py and
evidence_contracts.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid


@dataclass
class ChunkingPolicy:
    """
    Policy for chunking documents into searchable units.
    
    Defines how source documents are split into chunks for indexing.
    Policy parameters are stored with chunks for reproducibility.
    
    Attributes:
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        max_chunks_per_source: Maximum chunks to generate per source
        version: Policy version identifier
    """
    chunk_size: int = 2000
    overlap: int = 200
    max_chunks_per_source: int = 100
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "max_chunks_per_source": self.max_chunks_per_source,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkingPolicy":
        """Create from dictionary."""
        return cls(
            chunk_size=data.get("chunk_size", 2000),
            overlap=data.get("overlap", 200),
            max_chunks_per_source=data.get("max_chunks_per_source", 100),
            version=data.get("version", "1.0"),
        )


@dataclass
class ChunkRecord:
    """
    A single chunk of source content for retrieval.
    
    Represents a bounded unit of text extracted from a source document,
    ready for embedding and retrieval. Each chunk has a deterministic ID
    based on its source and position.
    
    Attributes:
        chunk_id: Deterministic ID (sha256 of source_id + offsets + policy_version)
        source_type: Type of source (lake_text, lake_http, doc, transcript, sql_result)
        source_ref: Source identity metadata (lake_uri, url, doc_id, etc.)
        offsets: Byte/line range and chunk index
        content: Bounded text content
        content_sha256: SHA256 hash of content
        byte_count: Size of content in bytes
        policy: Chunking policy used
        created_utc: When the chunk was created
    """
    chunk_id: str
    source_type: str
    source_ref: Dict[str, Any]
    offsets: Dict[str, Any]
    content: str
    content_sha256: str
    byte_count: int
    policy: Dict[str, Any]
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "offsets": self.offsets,
            "content": self.content,
            "content_sha256": self.content_sha256,
            "byte_count": self.byte_count,
            "policy": self.policy,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkRecord":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            chunk_id=data["chunk_id"],
            source_type=data["source_type"],
            source_ref=data.get("source_ref", {}),
            offsets=data.get("offsets", {}),
            content=data["content"],
            content_sha256=data["content_sha256"],
            byte_count=data["byte_count"],
            policy=data.get("policy", {}),
            created_utc=created,
        )


@dataclass
class EmbeddingRecord:
    """
    Embedding vector for a chunk.
    
    Stores the vector representation of a chunk along with model information
    for reproducibility and auditing.
    
    Attributes:
        embedding_id: Unique identifier for this embedding
        chunk_id: ID of the chunk this embedding represents
        embedding_model: Name of the embedding model used
        vector_dim: Dimensionality of the embedding vector
        vector: The embedding vector as list of floats
        vector_sha256: SHA256 hash of the vector for integrity
        created_utc: When the embedding was created
    """
    embedding_id: str
    chunk_id: str
    embedding_model: str
    vector_dim: int
    vector: List[float]
    vector_sha256: str
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "embedding_id": self.embedding_id,
            "chunk_id": self.chunk_id,
            "embedding_model": self.embedding_model,
            "vector_dim": self.vector_dim,
            "vector": self.vector,
            "vector_sha256": self.vector_sha256,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingRecord":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            embedding_id=data["embedding_id"],
            chunk_id=data["chunk_id"],
            embedding_model=data["embedding_model"],
            vector_dim=data["vector_dim"],
            vector=data["vector"],
            vector_sha256=data["vector_sha256"],
            created_utc=created,
        )


@dataclass
class RetrievalPolicy:
    """
    Policy for retrieval scoring and filtering.
    
    Defines how retrieval is performed and scored.
    
    Attributes:
        scoring_method: Method for scoring (cosine_similarity)
        min_score_threshold: Minimum score to include in results
        secondary_sort: Secondary sort field for tie-breaking (chunk_id)
        version: Policy version identifier
    """
    scoring_method: str = "cosine_similarity"
    min_score_threshold: float = 0.0
    secondary_sort: str = "chunk_id"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scoring_method": self.scoring_method,
            "min_score_threshold": self.min_score_threshold,
            "secondary_sort": self.secondary_sort,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalPolicy":
        """Create from dictionary."""
        return cls(
            scoring_method=data.get("scoring_method", "cosine_similarity"),
            min_score_threshold=data.get("min_score_threshold", 0.0),
            secondary_sort=data.get("secondary_sort", "chunk_id"),
            version=data.get("version", "1.0"),
        )


@dataclass
class RetrievalQuery:
    """
    A retrieval query with metadata for reproducibility.
    
    Captures everything needed to reproduce a retrieval operation.
    
    Attributes:
        retrieval_id: Unique identifier for this retrieval
        run_id: ID of the LLM run this retrieval is for (optional)
        query_text: The retrieval query text
        query_embedding_model: Embedding model used for the query
        top_k: Number of results requested
        filters: Filter criteria (source_type allowlist, tags, etc.)
        policy: Retrieval scoring policy
        created_utc: When the query was executed
    """
    retrieval_id: str
    query_text: str
    query_embedding_model: str
    top_k: int
    filters: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    run_id: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "retrieval_id": self.retrieval_id,
            "query_text": self.query_text,
            "query_embedding_model": self.query_embedding_model,
            "top_k": self.top_k,
            "filters": self.filters,
            "policy": self.policy,
            "created_utc": self.created_utc.isoformat(),
        }
        if self.run_id:
            result["run_id"] = self.run_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalQuery":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            retrieval_id=data["retrieval_id"],
            query_text=data["query_text"],
            query_embedding_model=data["query_embedding_model"],
            top_k=data["top_k"],
            filters=data.get("filters", {}),
            policy=data.get("policy", {}),
            run_id=data.get("run_id"),
            created_utc=created,
        )


@dataclass
class RetrievalHit:
    """
    A single retrieval result.
    
    Represents a chunk that matched a retrieval query with its score and rank.
    
    Attributes:
        retrieval_id: ID of the retrieval query
        chunk_id: ID of the matched chunk
        score: Similarity score (e.g., cosine similarity)
        rank: Position in result ranking (1-indexed)
        metadata: Additional metadata (source refs, offsets)
    """
    retrieval_id: str
    chunk_id: str
    score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "retrieval_id": self.retrieval_id,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "rank": self.rank,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalHit":
        """Create from dictionary."""
        return cls(
            retrieval_id=data["retrieval_id"],
            chunk_id=data["chunk_id"],
            score=data["score"],
            rank=data["rank"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class RetrievalResult:
    """
    Complete result of a retrieval operation.
    
    Bundles the query with its hits for serialization and persistence.
    
    Attributes:
        query: The retrieval query
        hits: List of retrieval hits
        total_candidates: Total number of candidates before filtering
        execution_ms: Time taken for retrieval in milliseconds
    """
    query: RetrievalQuery
    hits: List[RetrievalHit]
    total_candidates: int = 0
    execution_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query.to_dict(),
            "hits": [h.to_dict() for h in self.hits],
            "total_candidates": self.total_candidates,
            "execution_ms": self.execution_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalResult":
        """Create from dictionary."""
        query = RetrievalQuery.from_dict(data["query"])
        hits = [RetrievalHit.from_dict(h) for h in data.get("hits", [])]
        return cls(
            query=query,
            hits=hits,
            total_candidates=data.get("total_candidates", 0),
            execution_ms=data.get("execution_ms"),
        )


def generate_chunk_id(
    source_id: str,
    chunk_index: int,
    start_offset: int,
    end_offset: int,
    policy_version: str
) -> str:
    """
    Generate a deterministic chunk ID.
    
    The chunk ID is a SHA256 hash of the source ID, offsets, and policy version,
    ensuring that identical chunks always have the same ID.
    
    Args:
        source_id: Unique identifier for the source (e.g., lake_uri)
        chunk_index: Index of this chunk within the source
        start_offset: Starting character offset
        end_offset: Ending character offset
        policy_version: Chunking policy version
        
    Returns:
        Deterministic chunk ID (64-char hex string)
    """
    id_input = f"{source_id}:{chunk_index}:{start_offset}:{end_offset}:{policy_version}"
    return hashlib.sha256(id_input.encode()).hexdigest()


# Import from shared utilities and re-export for backward compatibility
from ..core.utils import compute_content_hash, compute_vector_hash

__all__ = [
    "ChunkingPolicy",
    "ChunkRecord",
    "EmbeddingRecord",
    "RetrievalPolicy",
    "RetrievalQuery",
    "RetrievalHit",
    "RetrievalResult",
    "generate_chunk_id",
    "compute_content_hash",
    "compute_vector_hash",
]
