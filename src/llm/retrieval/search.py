"""
Retrieval Search - Find relevant chunks for queries.

Implements:
- Cosine similarity scoring
- Top-K retrieval
- Deterministic ordering with tie-breaks
- Persistence of retrieval queries and hits

DEPRECATED (Phase 2): RetrievalStore class is deprecated.
Use VectorStore from src/vector/store.py instead.
The legacy llm.* vector tables have been renamed to *_legacy and are no longer accessible.
See docs/llm/schema-refactor-migration-notes.md for migration details.
"""

import json
import logging
import math
import time
import uuid
import warnings
from typing import Any, Dict, List, Optional

from ..contracts.retrieval_contracts import (
    RetrievalHit,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalResult,
)

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec_a: First vector
        vec_b: Second vector
        
    Returns:
        Cosine similarity score between -1 and 1
        
    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if not vec_a or not vec_b:
        raise ValueError("Vectors cannot be empty")
    
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimensions must match: {len(vec_a)} != {len(vec_b)}")
    
    # Compute dot product and magnitudes
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    
    # Handle zero vectors
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)


def retrieve_chunks(
    query_embedding: List[float],
    candidate_embeddings: List[Dict[str, Any]],
    query_text: str,
    embedding_model: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    policy: Optional[RetrievalPolicy] = None,
    run_id: Optional[str] = None,
) -> RetrievalResult:
    """
    Retrieve top-K relevant chunks for a query.
    
    Computes cosine similarity between the query embedding and all candidate
    embeddings, then returns the top-K most similar chunks.
    
    Args:
        query_embedding: Embedding vector for the query
        candidate_embeddings: List of dicts with 'chunk_id', 'vector', and optional metadata
        query_text: Original query text (for logging)
        embedding_model: Name of embedding model used
        top_k: Number of results to return
        filters: Optional filter criteria (not applied here, assumed pre-filtered)
        policy: Retrieval policy for scoring and tie-breaks
        run_id: Optional LLM run ID for linking
        
    Returns:
        RetrievalResult with query and hits
    """
    start_time = time.time()
    policy = policy or RetrievalPolicy()
    filters = filters or {}
    
    # Create retrieval query record
    retrieval_id = str(uuid.uuid4())
    query = RetrievalQuery(
        retrieval_id=retrieval_id,
        query_text=query_text,
        query_embedding_model=embedding_model,
        top_k=top_k,
        filters=filters,
        policy=policy.to_dict(),
        run_id=run_id,
    )
    
    # Score all candidates
    scored_candidates = []
    for candidate in candidate_embeddings:
        chunk_id = candidate["chunk_id"]
        vector = candidate["vector"]
        
        try:
            score = cosine_similarity(query_embedding, vector)
        except ValueError as e:
            logger.warning(f"Skipping chunk {chunk_id}: {e}")
            continue
        
        # Apply minimum score threshold
        if score < policy.min_score_threshold:
            continue
        
        scored_candidates.append({
            "chunk_id": chunk_id,
            "score": score,
            "metadata": candidate.get("metadata", {}),
        })
    
    # Sort by score descending, then by chunk_id for deterministic tie-breaking
    scored_candidates.sort(
        key=lambda x: (-x["score"], x["chunk_id"])
    )
    
    # Take top-K
    top_candidates = scored_candidates[:top_k]
    
    # Create hit records
    hits = []
    for rank, candidate in enumerate(top_candidates, start=1):
        hit = RetrievalHit(
            retrieval_id=retrieval_id,
            chunk_id=candidate["chunk_id"],
            score=candidate["score"],
            rank=rank,
            metadata=candidate["metadata"],
        )
        hits.append(hit)
    
    execution_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"Retrieved {len(hits)} chunks from {len(candidate_embeddings)} candidates "
        f"in {execution_ms}ms (query: {query_text[:50]}...)"
    )
    
    return RetrievalResult(
        query=query,
        hits=hits,
        total_candidates=len(candidate_embeddings),
        execution_ms=execution_ms,
    )


class RetrievalStore:
    """
    Storage interface for retrieval operations.
    
    DEPRECATED: This class is deprecated as of Phase 2 of the schema refactor.
    Use VectorStore from src/vector/store.py instead.
    
    The legacy llm.* vector tables (chunk, embedding, retrieval, retrieval_hit,
    source_registry) have been renamed to *_legacy and are no longer accessible.
    
    Handles persistence of chunks, embeddings, and retrieval logs to SQL Server.
    Uses Python-side cosine similarity (Option 2 from the design).
    """
    
    def __init__(self, connection=None, schema: str = "llm"):
        """
        Initialize the retrieval store.
        
        Args:
            connection: Database connection (pyodbc)
            schema: SQL Server schema name
            
        .. deprecated::
            Use VectorStore from src/vector/store.py instead.
        """
        warnings.warn(
            "RetrievalStore is deprecated. Use VectorStore from src/vector/store.py instead. "
            "The legacy llm.* vector tables have been renamed to *_legacy.",
            DeprecationWarning,
            stacklevel=2
        )
        self._conn = connection
        self.schema = schema
    
    def _get_connection(self):
        """Get database connection."""
        if self._conn is None:
            raise ValueError("Database connection not provided")
        return self._conn
    
    def save_chunk(self, chunk: "ChunkRecord") -> None:
        """
        Save a chunk record to the database.
        
        Args:
            chunk: ChunkRecord to save
        """
        from ..contracts.retrieval_contracts import ChunkRecord
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Upsert: insert or update if chunk_id exists
        cursor.execute(
            f"""
            MERGE [{self.schema}].[chunk] AS target
            USING (SELECT ? AS chunk_id) AS source
            ON target.chunk_id = source.chunk_id
            WHEN MATCHED THEN
                UPDATE SET 
                    source_type = ?,
                    source_ref_json = ?,
                    offsets_json = ?,
                    content = ?,
                    content_sha256 = ?,
                    byte_count = ?,
                    policy_json = ?
            WHEN NOT MATCHED THEN
                INSERT (chunk_id, source_type, source_ref_json, offsets_json, 
                        content, content_sha256, byte_count, policy_json, created_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME());
            """,
            (
                chunk.chunk_id,
                chunk.source_type,
                json.dumps(chunk.source_ref),
                json.dumps(chunk.offsets),
                chunk.content,
                chunk.content_sha256,
                chunk.byte_count,
                json.dumps(chunk.policy),
                chunk.chunk_id,
                chunk.source_type,
                json.dumps(chunk.source_ref),
                json.dumps(chunk.offsets),
                chunk.content,
                chunk.content_sha256,
                chunk.byte_count,
                json.dumps(chunk.policy),
            )
        )
        conn.commit()
    
    def save_embedding(self, embedding: "EmbeddingRecord") -> None:
        """
        Save an embedding record to the database.
        
        Args:
            embedding: EmbeddingRecord to save
        """
        from ..contracts.retrieval_contracts import EmbeddingRecord
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            INSERT INTO [{self.schema}].[embedding]
            (embedding_id, chunk_id, embedding_model, vector_dim, vector_json, 
             vector_sha256, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                embedding.embedding_id,
                embedding.chunk_id,
                embedding.embedding_model,
                embedding.vector_dim,
                json.dumps(embedding.vector),
                embedding.vector_sha256,
            )
        )
        conn.commit()
    
    def get_embeddings_by_filter(
        self,
        embedding_model: str,
        source_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings matching filter criteria.
        
        Args:
            embedding_model: Embedding model to filter by
            source_types: Optional list of source types to include
            
        Returns:
            List of dicts with chunk_id, vector, and metadata
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = f"""
            SELECT e.chunk_id, e.vector_json, c.source_type, c.source_ref_json, c.offsets_json
            FROM [{self.schema}].[embedding] e
            JOIN [{self.schema}].[chunk] c ON e.chunk_id = c.chunk_id
            WHERE e.embedding_model = ?
        """
        params = [embedding_model]
        
        if source_types:
            placeholders = ", ".join("?" * len(source_types))
            query += f" AND c.source_type IN ({placeholders})"
            params.extend(source_types)
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            chunk_id, vector_json, source_type, source_ref_json, offsets_json = row
            results.append({
                "chunk_id": chunk_id,
                "vector": json.loads(vector_json),
                "metadata": {
                    "source_type": source_type,
                    "source_ref": json.loads(source_ref_json) if source_ref_json else {},
                    "offsets": json.loads(offsets_json) if offsets_json else {},
                },
            })
        
        return results
    
    def save_retrieval_result(self, result: RetrievalResult) -> None:
        """
        Save a retrieval result to the database.
        
        Args:
            result: RetrievalResult to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Save the query
        cursor.execute(
            f"""
            INSERT INTO [{self.schema}].[retrieval]
            (retrieval_id, run_id, query_text, query_embedding_model, top_k,
             filters_json, policy_json, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                result.query.retrieval_id,
                result.query.run_id,
                result.query.query_text,
                result.query.query_embedding_model,
                result.query.top_k,
                json.dumps(result.query.filters),
                json.dumps(result.query.policy),
            )
        )
        
        # Save the hits
        for hit in result.hits:
            cursor.execute(
                f"""
                INSERT INTO [{self.schema}].[retrieval_hit]
                (retrieval_id, rank, chunk_id, score, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hit.retrieval_id,
                    hit.rank,
                    hit.chunk_id,
                    hit.score,
                    json.dumps(hit.metadata),
                )
            )
        
        conn.commit()
    
    def get_chunk_content(self, chunk_id: str) -> Optional[str]:
        """
        Get the content of a chunk by ID.
        
        Args:
            chunk_id: Chunk ID to look up
            
        Returns:
            Chunk content, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"SELECT content FROM [{self.schema}].[chunk] WHERE chunk_id = ?",
            (chunk_id,)
        )
        
        row = cursor.fetchone()
        return row[0] if row else None
    
    def chunk_exists(self, chunk_id: str) -> bool:
        """
        Check if a chunk exists.
        
        Args:
            chunk_id: Chunk ID to check
            
        Returns:
            True if chunk exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"SELECT 1 FROM [{self.schema}].[chunk] WHERE chunk_id = ?",
            (chunk_id,)
        )
        
        return cursor.fetchone() is not None
    
    def embedding_exists(self, chunk_id: str, embedding_model: str) -> bool:
        """
        Check if an embedding exists for a chunk and model.
        
        Args:
            chunk_id: Chunk ID
            embedding_model: Embedding model name
            
        Returns:
            True if embedding exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT 1 FROM [{self.schema}].[embedding] 
            WHERE chunk_id = ? AND embedding_model = ?
            """,
            (chunk_id, embedding_model)
        )
        
        return cursor.fetchone() is not None
