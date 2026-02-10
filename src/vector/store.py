"""
Vector Store - Database operations for the vector schema.

Provides persistence layer for the vector schema tables, including
embedding spaces, chunks, embeddings, and retrieval logging.

This is the parallel implementation for the new `vector` schema,
coexisting with the legacy `RetrievalStore` in `llm.retrieval.search`.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .contracts.models import (
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
)


logger = logging.getLogger(__name__)


class VectorStore:
    """
    Storage interface for vector schema operations.
    
    Handles persistence of embedding spaces, chunks, embeddings, and
    retrieval logs to the `vector` schema in SQL Server.
    """
    
    def __init__(self, connection=None, schema: str = "vector"):
        """
        Initialize the vector store.
        
        Args:
            connection: Database connection (pyodbc)
            schema: SQL Server schema name (default: 'vector')
        """
        self._conn = connection
        self.schema = schema
    
    def _get_connection(self):
        """Get database connection."""
        if self._conn is None:
            raise ValueError("Database connection not provided")
        return self._conn
    
    # =========================================================================
    # Embedding Space Operations
    # =========================================================================
    
    def save_embedding_space(self, space: EmbeddingSpace) -> None:
        """
        Save an embedding space to the database.
        
        Args:
            space: EmbeddingSpace to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            MERGE [{self.schema}].[embedding_space] AS target
            USING (SELECT ? AS embedding_space_id) AS source
            ON target.embedding_space_id = source.embedding_space_id
            WHEN MATCHED THEN
                UPDATE SET 
                    provider = ?,
                    model_name = ?,
                    model_tag = ?,
                    model_digest = ?,
                    dimensions = ?,
                    normalize_flag = ?,
                    distance_metric = ?,
                    preprocess_policy_json = ?,
                    transform_ref = ?,
                    description = ?,
                    is_active = ?
            WHEN NOT MATCHED THEN
                INSERT (embedding_space_id, provider, model_name, model_tag, model_digest,
                        dimensions, normalize_flag, distance_metric, preprocess_policy_json,
                        transform_ref, description, is_active, created_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME());
            """,
            (
                space.embedding_space_id,
                space.provider,
                space.model_name,
                space.model_tag,
                space.model_digest,
                space.dimensions,
                space.normalize_flag,
                space.distance_metric,
                json.dumps(space.preprocess_policy) if space.preprocess_policy else None,
                space.transform_ref,
                space.description,
                space.is_active,
                space.embedding_space_id,
                space.provider,
                space.model_name,
                space.model_tag,
                space.model_digest,
                space.dimensions,
                space.normalize_flag,
                space.distance_metric,
                json.dumps(space.preprocess_policy) if space.preprocess_policy else None,
                space.transform_ref,
                space.description,
                space.is_active,
            )
        )
        conn.commit()
    
    def get_embedding_space(self, embedding_space_id: str) -> Optional[EmbeddingSpace]:
        """
        Get an embedding space by ID.
        
        Args:
            embedding_space_id: Embedding space ID
            
        Returns:
            EmbeddingSpace if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT embedding_space_id, provider, model_name, model_tag, model_digest,
                   dimensions, normalize_flag, distance_metric, preprocess_policy_json,
                   transform_ref, description, is_active, created_utc
            FROM [{self.schema}].[embedding_space]
            WHERE embedding_space_id = ?
            """,
            (embedding_space_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return EmbeddingSpace(
            embedding_space_id=str(row[0]),
            provider=row[1],
            model_name=row[2],
            model_tag=row[3],
            model_digest=row[4],
            dimensions=row[5],
            normalize_flag=bool(row[6]),
            distance_metric=row[7],
            preprocess_policy=json.loads(row[8]) if row[8] else None,
            transform_ref=row[9],
            description=row[10],
            is_active=bool(row[11]),
            created_utc=row[12] if isinstance(row[12], datetime) else datetime.fromisoformat(str(row[12])),
        )
    
    def get_or_create_embedding_space(
        self,
        provider: str,
        model_name: str,
        dimensions: int,
        model_tag: Optional[str] = None,
        model_digest: Optional[str] = None,
        **kwargs
    ) -> EmbeddingSpace:
        """
        Get an existing embedding space or create a new one.
        
        Uses the unique constraint on (provider, model_name, model_tag, model_digest, dimensions)
        to find matching spaces.
        
        Args:
            provider: Embedding provider
            model_name: Model name
            dimensions: Vector dimensionality
            model_tag: Optional model tag
            model_digest: Optional model digest
            **kwargs: Additional EmbeddingSpace attributes
            
        Returns:
            Existing or newly created EmbeddingSpace
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try to find existing space
        cursor.execute(
            f"""
            SELECT embedding_space_id, provider, model_name, model_tag, model_digest,
                   dimensions, normalize_flag, distance_metric, preprocess_policy_json,
                   transform_ref, description, is_active, created_utc
            FROM [{self.schema}].[embedding_space]
            WHERE provider = ? AND model_name = ? AND dimensions = ?
              AND (model_tag = ? OR (model_tag IS NULL AND ? IS NULL))
              AND (model_digest = ? OR (model_digest IS NULL AND ? IS NULL))
            """,
            (provider, model_name, dimensions, model_tag, model_tag, model_digest, model_digest)
        )
        
        row = cursor.fetchone()
        if row:
            return EmbeddingSpace(
                embedding_space_id=str(row[0]),
                provider=row[1],
                model_name=row[2],
                model_tag=row[3],
                model_digest=row[4],
                dimensions=row[5],
                normalize_flag=bool(row[6]),
                distance_metric=row[7],
                preprocess_policy=json.loads(row[8]) if row[8] else None,
                transform_ref=row[9],
                description=row[10],
                is_active=bool(row[11]),
                created_utc=row[12] if isinstance(row[12], datetime) else datetime.fromisoformat(str(row[12])),
            )
        
        # Create new space
        space = EmbeddingSpace.create_new(
            provider=provider,
            model_name=model_name,
            dimensions=dimensions,
            model_tag=model_tag,
            model_digest=model_digest,
            **kwargs
        )
        self.save_embedding_space(space)
        return space
    
    def list_embedding_spaces(self, active_only: bool = True) -> List[EmbeddingSpace]:
        """
        List all embedding spaces.
        
        Args:
            active_only: If True, only return active spaces
            
        Returns:
            List of EmbeddingSpace objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = f"""
            SELECT embedding_space_id, provider, model_name, model_tag, model_digest,
                   dimensions, normalize_flag, distance_metric, preprocess_policy_json,
                   transform_ref, description, is_active, created_utc
            FROM [{self.schema}].[embedding_space]
        """
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_utc DESC"
        
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            results.append(EmbeddingSpace(
                embedding_space_id=str(row[0]),
                provider=row[1],
                model_name=row[2],
                model_tag=row[3],
                model_digest=row[4],
                dimensions=row[5],
                normalize_flag=bool(row[6]),
                distance_metric=row[7],
                preprocess_policy=json.loads(row[8]) if row[8] else None,
                transform_ref=row[9],
                description=row[10],
                is_active=bool(row[11]),
                created_utc=row[12] if isinstance(row[12], datetime) else datetime.fromisoformat(str(row[12])),
            ))
        
        return results
    
    # =========================================================================
    # Chunk Operations
    # =========================================================================
    
    def save_chunk(self, chunk: VectorChunk) -> None:
        """
        Save a chunk to the database.
        
        Args:
            chunk: VectorChunk to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            MERGE [{self.schema}].[chunk] AS target
            USING (SELECT ? AS chunk_id) AS source
            ON target.chunk_id = source.chunk_id
            WHEN MATCHED THEN
                UPDATE SET 
                    source_id = ?,
                    source_type = ?,
                    source_ref_json = ?,
                    offsets_json = ?,
                    content = ?,
                    content_sha256 = ?,
                    byte_count = ?,
                    policy_json = ?
            WHEN NOT MATCHED THEN
                INSERT (chunk_id, source_id, source_type, source_ref_json, offsets_json,
                        content, content_sha256, byte_count, policy_json, created_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME());
            """,
            (
                chunk.chunk_id,
                chunk.source_id,
                chunk.source_type,
                json.dumps(chunk.source_ref),
                json.dumps(chunk.offsets),
                chunk.content,
                chunk.content_sha256,
                chunk.byte_count,
                json.dumps(chunk.policy),
                chunk.chunk_id,
                chunk.source_id,
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
    
    def get_chunk(self, chunk_id: str) -> Optional[VectorChunk]:
        """
        Get a chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            VectorChunk if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT chunk_id, source_id, source_type, source_ref_json, offsets_json,
                   content, content_sha256, byte_count, policy_json, created_utc
            FROM [{self.schema}].[chunk]
            WHERE chunk_id = ?
            """,
            (chunk_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return VectorChunk(
            chunk_id=row[0],
            source_id=row[1],
            source_type=row[2],
            source_ref=json.loads(row[3]) if row[3] else {},
            offsets=json.loads(row[4]) if row[4] else {},
            content=row[5],
            content_sha256=row[6],
            byte_count=row[7],
            policy=json.loads(row[8]) if row[8] else {},
            created_utc=row[9] if isinstance(row[9], datetime) else datetime.fromisoformat(str(row[9])),
        )
    
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
    
    # =========================================================================
    # Embedding Operations
    # =========================================================================
    
    def save_embedding(self, embedding: VectorEmbedding) -> None:
        """
        Save an embedding to the database.
        
        Args:
            embedding: VectorEmbedding to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            INSERT INTO [{self.schema}].[embedding]
            (embedding_id, chunk_id, embedding_space_id, input_content_sha256,
             run_id, vector_json, vector_sha256, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                embedding.embedding_id,
                embedding.chunk_id,
                embedding.embedding_space_id,
                embedding.input_content_sha256,
                embedding.run_id,
                json.dumps(embedding.vector),
                embedding.vector_sha256,
            )
        )
        conn.commit()
    
    def get_embedding(self, embedding_id: str) -> Optional[VectorEmbedding]:
        """
        Get an embedding by ID.
        
        Args:
            embedding_id: Embedding ID
            
        Returns:
            VectorEmbedding if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT embedding_id, chunk_id, embedding_space_id, input_content_sha256,
                   run_id, vector_json, vector_sha256, created_utc
            FROM [{self.schema}].[embedding]
            WHERE embedding_id = ?
            """,
            (embedding_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return VectorEmbedding(
            embedding_id=str(row[0]),
            chunk_id=row[1],
            embedding_space_id=str(row[2]),
            input_content_sha256=row[3],
            run_id=str(row[4]) if row[4] else None,
            vector=json.loads(row[5]),
            vector_sha256=row[6],
            created_utc=row[7] if isinstance(row[7], datetime) else datetime.fromisoformat(str(row[7])),
        )
    
    def embedding_exists(
        self,
        chunk_id: str,
        embedding_space_id: str,
        input_content_sha256: str
    ) -> bool:
        """
        Check if an embedding exists for a chunk, space, and content version.
        
        Uses the idempotency constraint to check for existing embeddings.
        
        Args:
            chunk_id: Chunk ID
            embedding_space_id: Embedding space ID
            input_content_sha256: Content hash
            
        Returns:
            True if embedding exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT 1 FROM [{self.schema}].[embedding] 
            WHERE chunk_id = ? AND embedding_space_id = ? AND input_content_sha256 = ?
            """,
            (chunk_id, embedding_space_id, input_content_sha256)
        )
        
        return cursor.fetchone() is not None
    
    def get_embeddings_by_space(
        self,
        embedding_space_id: str,
        source_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings for an embedding space.
        
        Args:
            embedding_space_id: Embedding space ID
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
            WHERE e.embedding_space_id = ?
        """
        params = [embedding_space_id]
        
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
    
    # =========================================================================
    # Source Registry Operations
    # =========================================================================
    
    def save_source_registry(self, source: VectorSourceRegistry) -> None:
        """
        Save a source registry entry.
        
        Args:
            source: VectorSourceRegistry to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            MERGE [{self.schema}].[source_registry] AS target
            USING (SELECT ? AS source_id) AS source
            ON target.source_id = source.source_id
            WHEN MATCHED THEN
                UPDATE SET 
                    source_type = ?,
                    source_ref_json = ?,
                    content_sha256 = ?,
                    last_indexed_utc = ?,
                    chunk_count = ?,
                    tags_json = ?,
                    status = ?,
                    updated_utc = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (source_id, source_type, source_ref_json, content_sha256,
                        last_indexed_utc, chunk_count, tags_json, status,
                        created_utc, updated_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME(), SYSUTCDATETIME());
            """,
            (
                source.source_id,
                source.source_type,
                json.dumps(source.source_ref),
                source.content_sha256,
                source.last_indexed_utc,
                source.chunk_count,
                json.dumps(source.tags) if source.tags else None,
                source.status.value,
                source.source_id,
                source.source_type,
                json.dumps(source.source_ref),
                source.content_sha256,
                source.last_indexed_utc,
                source.chunk_count,
                json.dumps(source.tags) if source.tags else None,
                source.status.value,
            )
        )
        conn.commit()
    
    def get_source_registry(self, source_id: str) -> Optional[VectorSourceRegistry]:
        """
        Get a source registry entry by ID.
        
        Args:
            source_id: Source ID
            
        Returns:
            VectorSourceRegistry if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT source_id, source_type, source_ref_json, content_sha256,
                   last_indexed_utc, chunk_count, tags_json, status,
                   created_utc, updated_utc
            FROM [{self.schema}].[source_registry]
            WHERE source_id = ?
            """,
            (source_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return VectorSourceRegistry(
            source_id=row[0],
            source_type=row[1],
            source_ref=json.loads(row[2]) if row[2] else {},
            content_sha256=row[3],
            last_indexed_utc=row[4] if isinstance(row[4], datetime) else (datetime.fromisoformat(str(row[4])) if row[4] else None),
            chunk_count=row[5],
            tags=json.loads(row[6]) if row[6] else None,
            status=SourceStatus(row[7]),
            created_utc=row[8] if isinstance(row[8], datetime) else datetime.fromisoformat(str(row[8])),
            updated_utc=row[9] if isinstance(row[9], datetime) else datetime.fromisoformat(str(row[9])),
        )
    
    def source_already_indexed(self, source_id: str, content_hash: str) -> bool:
        """
        Check if a source has already been indexed with the same content.
        
        Args:
            source_id: Source identifier
            content_hash: SHA256 hash of content
            
        Returns:
            True if source is already indexed with same content
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            SELECT content_sha256 
            FROM [{self.schema}].[source_registry]
            WHERE source_id = ?
            """,
            (source_id,)
        )
        
        row = cursor.fetchone()
        return row is not None and row[0] == content_hash
    
    # =========================================================================
    # Retrieval Operations
    # =========================================================================
    
    def save_retrieval(self, retrieval: VectorRetrieval) -> None:
        """
        Save a retrieval query log.
        
        Args:
            retrieval: VectorRetrieval to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            INSERT INTO [{self.schema}].[retrieval]
            (retrieval_id, run_id, embedding_space_id, query_text,
             query_embedding_json, top_k, filters_json, policy_json, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                retrieval.retrieval_id,
                retrieval.run_id,
                retrieval.embedding_space_id,
                retrieval.query_text,
                json.dumps(retrieval.query_embedding) if retrieval.query_embedding else None,
                retrieval.top_k,
                json.dumps(retrieval.filters) if retrieval.filters else None,
                json.dumps(retrieval.policy) if retrieval.policy else None,
            )
        )
        conn.commit()
    
    def save_retrieval_hit(self, hit: VectorRetrievalHit) -> None:
        """
        Save a retrieval hit.
        
        Args:
            hit: VectorRetrievalHit to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
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
                json.dumps(hit.metadata) if hit.metadata else None,
            )
        )
        conn.commit()
    
    def save_retrieval_with_hits(
        self,
        retrieval: VectorRetrieval,
        hits: List[VectorRetrievalHit]
    ) -> None:
        """
        Save a retrieval query with all its hits in a single transaction.
        
        Args:
            retrieval: VectorRetrieval to save
            hits: List of VectorRetrievalHit to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Save retrieval
        cursor.execute(
            f"""
            INSERT INTO [{self.schema}].[retrieval]
            (retrieval_id, run_id, embedding_space_id, query_text,
             query_embedding_json, top_k, filters_json, policy_json, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                retrieval.retrieval_id,
                retrieval.run_id,
                retrieval.embedding_space_id,
                retrieval.query_text,
                json.dumps(retrieval.query_embedding) if retrieval.query_embedding else None,
                retrieval.top_k,
                json.dumps(retrieval.filters) if retrieval.filters else None,
                json.dumps(retrieval.policy) if retrieval.policy else None,
            )
        )
        
        # Save hits
        for hit in hits:
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
                    json.dumps(hit.metadata) if hit.metadata else None,
                )
            )
        
        conn.commit()
    
    # =========================================================================
    # Job/Run Operations (for completeness)
    # =========================================================================
    
    def save_job(self, job: VectorJob) -> None:
        """
        Save a vector job.
        
        Args:
            job: VectorJob to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            MERGE [{self.schema}].[job] AS target
            USING (SELECT ? AS job_id) AS source
            ON target.job_id = source.job_id
            WHEN MATCHED THEN
                UPDATE SET 
                    status = ?,
                    priority = ?,
                    job_type = ?,
                    input_json = ?,
                    embedding_space_id = ?,
                    max_attempts = ?,
                    attempt_count = ?,
                    available_utc = ?,
                    locked_by = ?,
                    locked_utc = ?,
                    last_error = ?
            WHEN NOT MATCHED THEN
                INSERT (job_id, created_utc, status, priority, job_type, input_json,
                        embedding_space_id, max_attempts, attempt_count, available_utc,
                        locked_by, locked_utc, last_error)
                VALUES (?, SYSUTCDATETIME(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                job.job_id,
                job.status.value,
                job.priority,
                job.job_type.value,
                json.dumps(job.input_json),
                job.embedding_space_id,
                job.max_attempts,
                job.attempt_count,
                job.available_utc,
                job.locked_by,
                job.locked_utc,
                job.last_error,
                job.job_id,
                job.status.value,
                job.priority,
                job.job_type.value,
                json.dumps(job.input_json),
                job.embedding_space_id,
                job.max_attempts,
                job.attempt_count,
                job.available_utc,
                job.locked_by,
                job.locked_utc,
                job.last_error,
            )
        )
        conn.commit()
    
    def save_run(self, run: VectorRun) -> None:
        """
        Save a vector run.
        
        Args:
            run: VectorRun to save
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"""
            MERGE [{self.schema}].[run] AS target
            USING (SELECT ? AS run_id) AS source
            ON target.run_id = source.run_id
            WHEN MATCHED THEN
                UPDATE SET 
                    completed_utc = ?,
                    status = ?,
                    embedding_space_id = ?,
                    endpoint_url = ?,
                    model_name = ?,
                    model_tag = ?,
                    model_digest = ?,
                    options_json = ?,
                    metrics_json = ?,
                    error = ?
            WHEN NOT MATCHED THEN
                INSERT (run_id, job_id, started_utc, completed_utc, status, worker_id,
                        embedding_space_id, endpoint_url, model_name, model_tag,
                        model_digest, options_json, metrics_json, error)
                VALUES (?, ?, SYSUTCDATETIME(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                run.run_id,
                run.completed_utc,
                run.status.value,
                run.embedding_space_id,
                run.endpoint_url,
                run.model_name,
                run.model_tag,
                run.model_digest,
                json.dumps(run.options) if run.options else None,
                json.dumps(run.metrics) if run.metrics else None,
                run.error,
                run.run_id,
                run.job_id,
                run.completed_utc,
                run.status.value,
                run.worker_id,
                run.embedding_space_id,
                run.endpoint_url,
                run.model_name,
                run.model_tag,
                run.model_digest,
                json.dumps(run.options) if run.options else None,
                json.dumps(run.metrics) if run.metrics else None,
                run.error,
            )
        )
        conn.commit()
