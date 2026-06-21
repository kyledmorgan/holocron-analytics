"""
Vector Runtime Data Models

Data models for the vector schema tables, providing first-class embedding
space identity and improved lineage tracking.

These models map to the tables in the `vector` schema:
- vector.embedding_space
- vector.job
- vector.run
- vector.source_registry
- vector.chunk
- vector.embedding
- vector.retrieval
- vector.retrieval_hit
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid


class JobType(Enum):
    """Types of vector jobs."""
    CHUNK_SOURCE = "CHUNK_SOURCE"
    EMBED_CHUNKS = "EMBED_CHUNKS"
    REEMBED_SPACE = "REEMBED_SPACE"
    RETRIEVE_TEST = "RETRIEVE_TEST"
    DRIFT_TEST = "DRIFT_TEST"


class JobStatus(Enum):
    """Status of vector jobs."""
    NEW = "NEW"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEADLETTER = "DEADLETTER"


class RunStatus(Enum):
    """Status of vector runs."""
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class SourceStatus(Enum):
    """Status of sources in the registry."""
    INDEXED = "indexed"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class EmbeddingSpace:
    """
    First-class embedding space identity.
    
    An embedding space defines where cosine/dot-product distance is meaningful.
    Vectors from different spaces must not be compared.
    
    Attributes:
        embedding_space_id: Unique identifier (GUID)
        provider: Embedding provider ('ollama', 'openai', etc.)
        model_name: Model name ('nomic-embed-text', etc.)
        model_tag: Optional model tag ('latest')
        model_digest: Optional SHA256 of model weights
        dimensions: Vector dimensionality (768, 1024, etc.)
        normalize_flag: Whether vectors are L2 normalized
        distance_metric: Distance metric ('cosine', 'dot', 'euclidean')
        preprocess_policy: Optional text preprocessing config
        transform_ref: Optional PCA/projection reference
        description: Human-readable description
        is_active: Whether this space is active
        created_utc: Creation timestamp
    """
    embedding_space_id: str
    provider: str
    model_name: str
    dimensions: int
    model_tag: Optional[str] = None
    model_digest: Optional[str] = None
    normalize_flag: bool = True
    distance_metric: str = "cosine"
    preprocess_policy: Optional[Dict[str, Any]] = None
    transform_ref: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "embedding_space_id": self.embedding_space_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_tag": self.model_tag,
            "model_digest": self.model_digest,
            "dimensions": self.dimensions,
            "normalize_flag": self.normalize_flag,
            "distance_metric": self.distance_metric,
            "preprocess_policy": self.preprocess_policy,
            "transform_ref": self.transform_ref,
            "description": self.description,
            "is_active": self.is_active,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingSpace":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            embedding_space_id=data["embedding_space_id"],
            provider=data["provider"],
            model_name=data["model_name"],
            model_tag=data.get("model_tag"),
            model_digest=data.get("model_digest"),
            dimensions=data["dimensions"],
            normalize_flag=data.get("normalize_flag", True),
            distance_metric=data.get("distance_metric", "cosine"),
            preprocess_policy=data.get("preprocess_policy"),
            transform_ref=data.get("transform_ref"),
            description=data.get("description"),
            is_active=data.get("is_active", True),
            created_utc=created,
        )
    
    @classmethod
    def create_new(
        cls,
        provider: str,
        model_name: str,
        dimensions: int,
        **kwargs
    ) -> "EmbeddingSpace":
        """Create a new embedding space with a generated ID."""
        return cls(
            embedding_space_id=str(uuid.uuid4()),
            provider=provider,
            model_name=model_name,
            dimensions=dimensions,
            **kwargs
        )


@dataclass
class VectorJob:
    """
    Vector job queue entry.
    
    Mirrors llm.job pattern but for vector operations.
    
    Attributes:
        job_id: Unique job identifier
        job_type: Type of vector operation
        input_json: Job input parameters
        status: Current job status
        priority: Job priority (higher = more urgent)
        embedding_space_id: Optional embedding space for this job
        max_attempts: Maximum retry attempts
        attempt_count: Current attempt count
        available_utc: When job becomes available
        locked_by: Worker holding the lock
        locked_utc: When lock was acquired
        last_error: Last error message
        created_utc: Creation timestamp
    """
    job_id: str
    job_type: JobType
    input_json: Dict[str, Any]
    status: JobStatus = JobStatus.NEW
    priority: int = 100
    embedding_space_id: Optional[str] = None
    max_attempts: int = 3
    attempt_count: int = 0
    available_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    locked_by: Optional[str] = None
    locked_utc: Optional[datetime] = None
    last_error: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "input_json": self.input_json,
            "status": self.status.value,
            "priority": self.priority,
            "embedding_space_id": self.embedding_space_id,
            "max_attempts": self.max_attempts,
            "attempt_count": self.attempt_count,
            "available_utc": self.available_utc.isoformat(),
            "locked_by": self.locked_by,
            "locked_utc": self.locked_utc.isoformat() if self.locked_utc else None,
            "last_error": self.last_error,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorJob":
        """Create from dictionary."""
        def parse_dt(val):
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return val
        
        return cls(
            job_id=data["job_id"],
            job_type=JobType(data["job_type"]),
            input_json=data["input_json"],
            status=JobStatus(data.get("status", "NEW")),
            priority=data.get("priority", 100),
            embedding_space_id=data.get("embedding_space_id"),
            max_attempts=data.get("max_attempts", 3),
            attempt_count=data.get("attempt_count", 0),
            available_utc=parse_dt(data.get("available_utc")) or datetime.now(timezone.utc),
            locked_by=data.get("locked_by"),
            locked_utc=parse_dt(data.get("locked_utc")),
            last_error=data.get("last_error"),
            created_utc=parse_dt(data.get("created_utc")) or datetime.now(timezone.utc),
        )
    
    @classmethod
    def create_new(
        cls,
        job_type: JobType,
        input_json: Dict[str, Any],
        **kwargs
    ) -> "VectorJob":
        """Create a new job with a generated ID."""
        return cls(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            input_json=input_json,
            **kwargs
        )


@dataclass
class VectorRun:
    """
    Vector run execution record.
    
    Tracks individual vector operation attempts with lineage.
    
    Attributes:
        run_id: Unique run identifier
        job_id: Parent job ID
        worker_id: Worker executing this run
        status: Current run status
        embedding_space_id: Embedding space used
        endpoint_url: Provider endpoint
        model_name: Model name
        model_tag: Model tag
        model_digest: Model digest
        options: Run options
        metrics: Performance metrics
        error: Error message if failed
        started_utc: Start timestamp
        completed_utc: Completion timestamp
    """
    run_id: str
    job_id: str
    worker_id: str
    status: RunStatus = RunStatus.RUNNING
    embedding_space_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    model_name: Optional[str] = None
    model_tag: Optional[str] = None
    model_digest: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_utc: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "worker_id": self.worker_id,
            "status": self.status.value,
            "embedding_space_id": self.embedding_space_id,
            "endpoint_url": self.endpoint_url,
            "model_name": self.model_name,
            "model_tag": self.model_tag,
            "model_digest": self.model_digest,
            "options": self.options,
            "metrics": self.metrics,
            "error": self.error,
            "started_utc": self.started_utc.isoformat(),
            "completed_utc": self.completed_utc.isoformat() if self.completed_utc else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRun":
        """Create from dictionary."""
        def parse_dt(val):
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return val
        
        return cls(
            run_id=data["run_id"],
            job_id=data["job_id"],
            worker_id=data["worker_id"],
            status=RunStatus(data.get("status", "RUNNING")),
            embedding_space_id=data.get("embedding_space_id"),
            endpoint_url=data.get("endpoint_url"),
            model_name=data.get("model_name"),
            model_tag=data.get("model_tag"),
            model_digest=data.get("model_digest"),
            options=data.get("options"),
            metrics=data.get("metrics"),
            error=data.get("error"),
            started_utc=parse_dt(data.get("started_utc")) or datetime.now(timezone.utc),
            completed_utc=parse_dt(data.get("completed_utc")),
        )
    
    @classmethod
    def create_new(
        cls,
        job_id: str,
        worker_id: str,
        **kwargs
    ) -> "VectorRun":
        """Create a new run with a generated ID."""
        return cls(
            run_id=str(uuid.uuid4()),
            job_id=job_id,
            worker_id=worker_id,
            **kwargs
        )


@dataclass
class VectorSourceRegistry:
    """
    Source registry entry for incremental indexing.
    
    Tracks sources that have been indexed with lifecycle and content hash
    for change detection.
    
    Attributes:
        source_id: Unique source identifier
        source_type: Type of source (lake_text, lake_http, etc.)
        source_ref: Source identity metadata
        content_sha256: Content hash for change detection
        last_indexed_utc: Last indexing timestamp
        chunk_count: Number of chunks created
        tags: Source tags for filtering
        status: Current source status
        created_utc: Creation timestamp
        updated_utc: Last update timestamp
    """
    source_id: str
    source_type: str
    source_ref: Dict[str, Any]
    content_sha256: Optional[str] = None
    last_indexed_utc: Optional[datetime] = None
    chunk_count: Optional[int] = None
    tags: Optional[Dict[str, Any]] = None
    status: SourceStatus = SourceStatus.INDEXED
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "content_sha256": self.content_sha256,
            "last_indexed_utc": self.last_indexed_utc.isoformat() if self.last_indexed_utc else None,
            "chunk_count": self.chunk_count,
            "tags": self.tags,
            "status": self.status.value,
            "created_utc": self.created_utc.isoformat(),
            "updated_utc": self.updated_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorSourceRegistry":
        """Create from dictionary."""
        def parse_dt(val):
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return val
        
        return cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            source_ref=data.get("source_ref", {}),
            content_sha256=data.get("content_sha256"),
            last_indexed_utc=parse_dt(data.get("last_indexed_utc")),
            chunk_count=data.get("chunk_count"),
            tags=data.get("tags"),
            status=SourceStatus(data.get("status", "indexed")),
            created_utc=parse_dt(data.get("created_utc")) or datetime.now(timezone.utc),
            updated_utc=parse_dt(data.get("updated_utc")) or datetime.now(timezone.utc),
        )


@dataclass
class VectorChunk:
    """
    Chunk for embedding and retrieval.
    
    Improved version with source registry linkage and version coupling.
    
    Attributes:
        chunk_id: Deterministic SHA256 hash
        source_type: Type of source
        source_ref: Source identity metadata
        offsets: Byte/line range, chunk index
        content: Bounded text content
        content_sha256: Content hash for version coupling
        byte_count: Size in bytes
        policy: Chunking policy used
        source_id: Optional FK to source_registry
        created_utc: Creation timestamp
    """
    chunk_id: str
    source_type: str
    source_ref: Dict[str, Any]
    offsets: Dict[str, Any]
    content: str
    content_sha256: str
    byte_count: int
    policy: Dict[str, Any]
    source_id: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
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
    def from_dict(cls, data: Dict[str, Any]) -> "VectorChunk":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            chunk_id=data["chunk_id"],
            source_id=data.get("source_id"),
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
class VectorEmbedding:
    """
    Embedding with lineage and idempotency.
    
    Key improvements over legacy:
    - embedding_space_id for explicit space identity
    - input_content_sha256 for version coupling
    - run_id for execution lineage
    
    Attributes:
        embedding_id: Unique identifier
        chunk_id: FK to chunk
        embedding_space_id: FK to embedding_space
        input_content_sha256: Must match chunk version
        vector: Embedding vector
        vector_sha256: Vector hash for integrity
        run_id: Optional FK to run
        created_utc: Creation timestamp
    """
    embedding_id: str
    chunk_id: str
    embedding_space_id: str
    input_content_sha256: str
    vector: List[float]
    vector_sha256: str
    run_id: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "embedding_id": self.embedding_id,
            "chunk_id": self.chunk_id,
            "embedding_space_id": self.embedding_space_id,
            "input_content_sha256": self.input_content_sha256,
            "vector": self.vector,
            "vector_sha256": self.vector_sha256,
            "run_id": self.run_id,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorEmbedding":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            embedding_id=data["embedding_id"],
            chunk_id=data["chunk_id"],
            embedding_space_id=data["embedding_space_id"],
            input_content_sha256=data["input_content_sha256"],
            vector=data["vector"],
            vector_sha256=data["vector_sha256"],
            run_id=data.get("run_id"),
            created_utc=created,
        )
    
    @classmethod
    def create_new(
        cls,
        chunk_id: str,
        embedding_space_id: str,
        input_content_sha256: str,
        vector: List[float],
        **kwargs
    ) -> "VectorEmbedding":
        """Create a new embedding with generated ID and computed hash."""
        vector_sha256 = compute_vector_hash(vector)
        return cls(
            embedding_id=str(uuid.uuid4()),
            chunk_id=chunk_id,
            embedding_space_id=embedding_space_id,
            input_content_sha256=input_content_sha256,
            vector=vector,
            vector_sha256=vector_sha256,
            **kwargs
        )


@dataclass
class VectorRetrieval:
    """
    Retrieval query log for audit/evaluation.
    
    Attributes:
        retrieval_id: Unique identifier
        embedding_space_id: Space for query embedding
        query_text: Query text
        top_k: Number of results requested
        query_embedding: Optional query vector
        filters: Filter criteria
        policy: Retrieval policy (rerank, MMR, etc.)
        run_id: Optional FK to run
        created_utc: Creation timestamp
    """
    retrieval_id: str
    embedding_space_id: str
    query_text: str
    top_k: int
    query_embedding: Optional[List[float]] = None
    filters: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "retrieval_id": self.retrieval_id,
            "embedding_space_id": self.embedding_space_id,
            "query_text": self.query_text,
            "top_k": self.top_k,
            "query_embedding": self.query_embedding,
            "filters": self.filters,
            "policy": self.policy,
            "run_id": self.run_id,
            "created_utc": self.created_utc.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRetrieval":
        """Create from dictionary."""
        created = data.get("created_utc")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        elif created is None:
            created = datetime.now(timezone.utc)
        
        return cls(
            retrieval_id=data["retrieval_id"],
            embedding_space_id=data["embedding_space_id"],
            query_text=data["query_text"],
            top_k=data["top_k"],
            query_embedding=data.get("query_embedding"),
            filters=data.get("filters"),
            policy=data.get("policy"),
            run_id=data.get("run_id"),
            created_utc=created,
        )
    
    @classmethod
    def create_new(
        cls,
        embedding_space_id: str,
        query_text: str,
        top_k: int,
        **kwargs
    ) -> "VectorRetrieval":
        """Create a new retrieval with a generated ID."""
        return cls(
            retrieval_id=str(uuid.uuid4()),
            embedding_space_id=embedding_space_id,
            query_text=query_text,
            top_k=top_k,
            **kwargs
        )


@dataclass
class VectorRetrievalHit:
    """
    Retrieval result for analytics.
    
    Attributes:
        retrieval_id: FK to retrieval
        rank: Position in results (1-indexed)
        chunk_id: FK to chunk
        score: Similarity score
        metadata: Additional metadata
    """
    retrieval_id: str
    rank: int
    chunk_id: str
    score: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "retrieval_id": self.retrieval_id,
            "rank": self.rank,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRetrievalHit":
        """Create from dictionary."""
        return cls(
            retrieval_id=data["retrieval_id"],
            rank=data["rank"],
            chunk_id=data["chunk_id"],
            score=data["score"],
            metadata=data.get("metadata"),
        )


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content string.
    
    Args:
        content: Text content to hash
        
    Returns:
        64-character hex string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_vector_hash(vector: List[float]) -> str:
    """
    Compute SHA256 hash of embedding vector.
    
    Uses JSON serialization for consistent hashing.
    
    Args:
        vector: Embedding vector
        
    Returns:
        64-character hex string
    """
    vector_str = json.dumps(vector, separators=(',', ':'))
    return hashlib.sha256(vector_str.encode('utf-8')).hexdigest()


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
        source_id: Unique identifier for the source
        chunk_index: Index of this chunk within the source
        start_offset: Starting character offset
        end_offset: Ending character offset
        policy_version: Chunking policy version
        
    Returns:
        Deterministic chunk ID (64-char hex string)
    """
    id_input = f"{source_id}:{chunk_index}:{start_offset}:{end_offset}:{policy_version}"
    return hashlib.sha256(id_input.encode()).hexdigest()


__all__ = [
    # Enums
    "JobType",
    "JobStatus",
    "RunStatus",
    "SourceStatus",
    # Data classes
    "EmbeddingSpace",
    "VectorJob",
    "VectorRun",
    "VectorSourceRegistry",
    "VectorChunk",
    "VectorEmbedding",
    "VectorRetrieval",
    "VectorRetrievalHit",
    # Utilities
    "compute_content_hash",
    "compute_vector_hash",
    "generate_chunk_id",
]
