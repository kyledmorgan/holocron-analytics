"""
SQL Job Queue - SQL Server queue for LLM derive jobs.

This module provides the production implementation of the job queue
using SQL Server stored procedures for atomic job claiming and updates.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None  # Defer error to runtime when connection is attempted

from ..contracts.phase1_contracts import Job, JobStatus
from ..core.exceptions import LLMStorageError


logger = logging.getLogger(__name__)
_DOTENV_LOADED = False


def _load_dotenv_if_present() -> None:
    """
    Load .env into process env for local runs.

    Existing shell environment variables take precedence.
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    # sql_job_queue.py -> storage -> llm -> src -> repo root
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        _DOTENV_LOADED = True
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and os.environ.get(key) is None:
            os.environ[key] = value

    _DOTENV_LOADED = True


def _first_non_empty_env(*keys: str) -> Optional[str]:
    """Return the first non-empty env var value for the given keys."""
    for key in keys:
        value = os.environ.get(key)
        if value is not None and value.strip() != "":
            return value
    return None


@dataclass
class QueueConfig:
    """Configuration for the SQL job queue."""
    host: str = "localhost"
    port: int = 1433
    database: str = "Holocron"
    username: str = "sa"
    password: str = ""
    driver: str = "ODBC Driver 18 for SQL Server"
    schema: str = "llm"
    connection_string: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "QueueConfig":
        """Create config from environment variables."""
        _load_dotenv_if_present()

        # Check for full connection string first
        conn_str = _first_non_empty_env("LLM_SQLSERVER_CONN_STR")
        if conn_str:
            return cls(connection_string=conn_str)
        
        # Fall back to discrete variables
        host = _first_non_empty_env("LLM_SQLSERVER_HOST", "INGEST_SQLSERVER_HOST") or "localhost"
        port_str = _first_non_empty_env("LLM_SQLSERVER_PORT", "INGEST_SQLSERVER_PORT") or "1433"
        database = _first_non_empty_env(
            "LLM_SQLSERVER_DATABASE",
            "INGEST_SQLSERVER_DATABASE",
            "MSSQL_DATABASE",
        ) or "Holocron"
        username = _first_non_empty_env("LLM_SQLSERVER_USER", "INGEST_SQLSERVER_USER") or "sa"
        password = _first_non_empty_env(
            "LLM_SQLSERVER_PASSWORD",
            "INGEST_SQLSERVER_PASSWORD",
            "MSSQL_SA_PASSWORD",
        ) or ""
        driver = _first_non_empty_env("LLM_SQLSERVER_DRIVER", "INGEST_SQLSERVER_DRIVER") or "ODBC Driver 18 for SQL Server"
        schema = _first_non_empty_env("LLM_SQLSERVER_SCHEMA") or "llm"

        return cls(
            host=host,
            port=int(port_str),
            database=database,
            username=username,
            password=password,
            driver=driver,
            schema=schema,
        )
    
    def get_connection_string(self) -> str:
        """Build the ODBC connection string."""
        if self.connection_string:
            return self.connection_string
        
        return (
            f"Driver={{{self.driver}}};"
            f"Server={self.host},{self.port};"
            f"Database={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"Encrypt=no;"
            f"TrustServerCertificate=yes"
        )


class SqlJobQueue:
    """
    SQL Server-based job queue for LLM derive operations.
    
    Uses stored procedures for atomic operations:
    - usp_claim_next_job: Atomically claim the next available job
    - usp_complete_job: Mark a job as completed or failed
    - usp_enqueue_job: Add a new job to the queue
    - usp_create_run: Create a run record
    - usp_complete_run: Complete a run with metrics
    - usp_create_artifact: Record an artifact
    
    Example:
        >>> config = QueueConfig.from_env()
        >>> queue = SqlJobQueue(config)
        >>> job = queue.claim_next_job("worker-1")
        >>> if job:
        ...     # Process job
        ...     queue.mark_succeeded(job.job_id, run_id, artifacts)
    """
    
    def __init__(self, config: Optional[QueueConfig] = None):
        """
        Initialize the SQL job queue.
        
        Args:
            config: Queue configuration. If None, loads from environment.
        """
        self.config = config or QueueConfig.from_env()
        self._conn = None
        
        logger.debug(f"SqlJobQueue initialized for {self.config.host}:{self.config.port}/{self.config.database}")
    
    def _get_connection(self):
        """Get or create a database connection."""
        if self._conn is None:
            if pyodbc is None:
                raise LLMStorageError(
                    "pyodbc is not installed. Install it with: pip install pyodbc"
                )
            try:
                self._conn = pyodbc.connect(
                    self.config.get_connection_string(),
                    autocommit=True
                )
                logger.debug("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise LLMStorageError(f"Failed to connect to database: {e}")
        return self._conn
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
    
    def claim_next_job(self, worker_id: str) -> Optional[Job]:
        """
        Claim the next available job from the queue.
        
        Uses the usp_claim_next_job stored procedure for atomic claiming.
        
        Args:
            worker_id: Identifier for this worker
            
        Returns:
            The claimed Job, or None if no jobs available
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_claim_next_job] @worker_id = ?",
                (worker_id,)
            )
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            # Convert row to dictionary
            columns = [column[0] for column in cursor.description]
            row_dict = dict(zip(columns, row))
            
            job = Job.from_row(row_dict)
            logger.info(f"Claimed job {job.job_id} (attempt {job.attempt_count})")
            return job
            
        except Exception as e:
            logger.error(f"Failed to claim job: {e}")
            raise LLMStorageError(f"Failed to claim job: {e}")
    
    def mark_succeeded(
        self,
        job_id: str,
        run_id: Optional[str] = None,
    ) -> None:
        """
        Mark a job as succeeded.
        
        Args:
            job_id: The job ID to mark
            run_id: Optional run ID for this attempt
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_complete_job] @job_id = ?, @status = ?",
                (job_id, "SUCCEEDED")
            )
            
            logger.info(f"Job {job_id} marked as SUCCEEDED")
            
        except Exception as e:
            logger.error(f"Failed to mark job succeeded: {e}")
            raise LLMStorageError(f"Failed to mark job succeeded: {e}")
    
    def mark_failed(
        self,
        job_id: str,
        error: str,
        run_id: Optional[str] = None,
        backoff_seconds: int = 60,
    ) -> str:
        """
        Mark a job as failed.
        
        If more attempts remain, the job will be reset to NEW with a backoff delay.
        Otherwise, it will be moved to DEADLETTER.
        
        Args:
            job_id: The job ID to mark
            error: Error message
            run_id: Optional run ID for this attempt
            backoff_seconds: Base backoff time in seconds
            
        Returns:
            The final status of the job
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_complete_job] "
                f"@job_id = ?, @status = ?, @error = ?, @backoff_seconds = ?",
                (job_id, "FAILED", error, backoff_seconds)
            )
            
            row = cursor.fetchone()
            final_status = row[0] if row else "FAILED"
            
            logger.info(f"Job {job_id} marked as {final_status}: {error[:100]}")
            return final_status
            
        except Exception as e:
            logger.error(f"Failed to mark job failed: {e}")
            raise LLMStorageError(f"Failed to mark job failed: {e}")
    
    def enqueue_job(
        self,
        interrogation_key: str,
        input_json: str,
        priority: int = 100,
        evidence_ref_json: Optional[str] = None,
        model_hint: Optional[str] = None,
        max_attempts: int = 3,
        dedupe_key: Optional[str] = None,
    ) -> str:
        """
        Enqueue a new job.
        
        Args:
            interrogation_key: Which interrogation to run
            input_json: Job input as JSON string
            priority: Job priority (higher = processed sooner)
            evidence_ref_json: Evidence references as JSON string
            model_hint: Suggested model to use
            max_attempts: Maximum attempts before deadletter
            dedupe_key: Optional idempotency key to prevent duplicate jobs
            
        Returns:
            The created job_id
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_enqueue_job] "
                f"@priority = ?, @interrogation_key = ?, @input_json = ?, "
                f"@evidence_ref_json = ?, @model_hint = ?, @max_attempts = ?, @dedupe_key = ?",
                (priority, interrogation_key, input_json, evidence_ref_json, model_hint, max_attempts, dedupe_key)
            )
            
            row = cursor.fetchone()
            job_id = str(row[0]) if row else str(uuid.uuid4())
            
            # Check if this was a duplicate (stored proc returns: job_id, is_duplicate, existing_status)
            # Column indices: 0=job_id, 1=is_duplicate, 2=existing_status
            COL_JOB_ID = 0
            COL_IS_DUPLICATE = 1
            is_duplicate = bool(row[COL_IS_DUPLICATE]) if row and len(row) > COL_IS_DUPLICATE else False
            if is_duplicate:
                logger.info(f"Found existing job {job_id} for dedupe_key={dedupe_key}")
            else:
                logger.info(f"Enqueued job {job_id} for {interrogation_key}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            raise LLMStorageError(f"Failed to enqueue job: {e}")
    
    def enqueue_job_idempotent(
        self,
        interrogation_key: str,
        dedupe_key: str,
        input_json: str,
        priority: int = 100,
        evidence_ref_json: Optional[str] = None,
        model_hint: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Enqueue a new job with idempotency guarantee.
        
        If a job with the same (interrogation_key, dedupe_key) already exists,
        returns the existing job_id instead of creating a duplicate.
        
        Args:
            interrogation_key: Which interrogation to run
            dedupe_key: Idempotency key (required)
            input_json: Job input as JSON string
            priority: Job priority (higher = processed sooner)
            evidence_ref_json: Evidence references as JSON string
            model_hint: Suggested model to use
            max_attempts: Maximum attempts before deadletter
            
        Returns:
            Dict with 'job_id', 'is_duplicate', and optionally 'existing_status'
        """
        if not dedupe_key:
            raise ValueError("dedupe_key is required for idempotent enqueue")
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_enqueue_job] "
                f"@priority = ?, @interrogation_key = ?, @input_json = ?, "
                f"@evidence_ref_json = ?, @model_hint = ?, @max_attempts = ?, @dedupe_key = ?",
                (priority, interrogation_key, input_json, evidence_ref_json, model_hint, max_attempts, dedupe_key)
            )
            
            row = cursor.fetchone()
            result = {
                "job_id": str(row[0]) if row else str(uuid.uuid4()),
                "is_duplicate": bool(row[1]) if row and len(row) > 1 else False,
                "existing_status": row[2] if row and len(row) > 2 else None,
            }
            
            if result["is_duplicate"]:
                logger.info(
                    f"Idempotent enqueue found existing job {result['job_id']} "
                    f"(status={result['existing_status']}) for dedupe_key={dedupe_key}"
                )
            else:
                logger.info(f"Idempotent enqueue created job {result['job_id']} for {interrogation_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to enqueue job idempotently: {e}")
            raise LLMStorageError(f"Failed to enqueue job: {e}")
    
    def get_job_by_dedupe_key(
        self,
        interrogation_key: str,
        dedupe_key: str,
    ) -> Optional[Job]:
        """
        Look up a job by its dedupe key.
        
        Args:
            interrogation_key: The interrogation key
            dedupe_key: The dedupe key to search for
            
        Returns:
            The Job if found, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_get_job_by_dedupe_key] "
                f"@interrogation_key = ?, @dedupe_key = ?",
                (interrogation_key, dedupe_key)
            )
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            columns = [column[0] for column in cursor.description]
            row_dict = dict(zip(columns, row))
            
            return Job.from_row(row_dict)
            
        except Exception as e:
            logger.error(f"Failed to get job by dedupe key: {e}")
            raise LLMStorageError(f"Failed to get job by dedupe key: {e}")
    
    def create_run(
        self,
        job_id: str,
        worker_id: str,
        ollama_base_url: str,
        model_name: str,
        model_tag: Optional[str] = None,
        model_digest: Optional[str] = None,
        options_json: Optional[str] = None,
    ) -> str:
        """
        Create a run record for a job attempt.
        
        Args:
            job_id: The job ID this run is for
            worker_id: Worker processing this run
            ollama_base_url: Ollama API URL
            model_name: Model being used
            model_tag: Model tag (e.g., "7b")
            model_digest: Model digest from Ollama
            options_json: LLM options as JSON
            
        Returns:
            The created run_id
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_create_run] "
                f"@job_id = ?, @worker_id = ?, @ollama_base_url = ?, "
                f"@model_name = ?, @model_tag = ?, @model_digest = ?, @options_json = ?",
                (job_id, worker_id, ollama_base_url, model_name, model_tag, model_digest, options_json)
            )
            
            row = cursor.fetchone()
            run_id = str(row[0]) if row else str(uuid.uuid4())
            
            logger.debug(f"Created run {run_id} for job {job_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Failed to create run: {e}")
            raise LLMStorageError(f"Failed to create run: {e}")
    
    def complete_run(
        self,
        run_id: str,
        status: str,
        metrics_json: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Complete a run with status and metrics.
        
        Args:
            run_id: The run ID to complete
            status: Final status (SUCCEEDED or FAILED)
            metrics_json: Metrics as JSON string
            error: Error message if failed
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_complete_run] "
                f"@run_id = ?, @status = ?, @metrics_json = ?, @error = ?",
                (run_id, status, metrics_json, error)
            )
            
            logger.debug(f"Completed run {run_id} with status {status}")
            
        except Exception as e:
            logger.error(f"Failed to complete run: {e}")
            raise LLMStorageError(f"Failed to complete run: {e}")
    
    def create_artifact(
        self,
        run_id: str,
        artifact_type: str,
        lake_uri: Optional[str] = None,
        content_sha256: Optional[str] = None,
        byte_count: Optional[int] = None,
        content: Optional[str] = None,
        content_mime_type: Optional[str] = None,
        stored_in_sql: bool = False,
        mirrored_to_lake: bool = False,
    ) -> str:
        """
        Record an artifact, optionally with literal content stored in SQL.
        
        SQL is the system of record. The lake is additive/optional.
        When ``content`` is provided the payload is persisted directly
        in the ``llm.artifact`` row so runs can be reconstructed from
        SQL alone without the data lake.
        
        Args:
            run_id: The run ID this artifact belongs to
            artifact_type: Type of artifact (e.g., "request_json", "response_json")
            lake_uri: Path to the artifact in the lake (optional when SQL-first)
            content_sha256: SHA256 hash of the content
            byte_count: Size in bytes
            content: Literal artifact payload (JSON or text)
            content_mime_type: MIME type of the content (e.g., "application/json")
            stored_in_sql: Whether the content is stored in SQL
            mirrored_to_lake: Whether the content is also in the lake
            
        Returns:
            The created artifact_id
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"EXEC [{self.config.schema}].[usp_create_artifact] "
                f"@run_id = ?, @artifact_type = ?, @lake_uri = ?, "
                f"@content_sha256 = ?, @byte_count = ?, "
                f"@content = ?, @content_mime_type = ?, "
                f"@stored_in_sql = ?, @mirrored_to_lake = ?",
                (
                    run_id, artifact_type, lake_uri,
                    content_sha256, byte_count,
                    content, content_mime_type,
                    1 if stored_in_sql else 0,
                    1 if mirrored_to_lake else 0,
                )
            )
            
            row = cursor.fetchone()
            artifact_id = str(row[0]) if row else str(uuid.uuid4())
            
            logger.debug(f"Created artifact {artifact_id} ({artifact_type}) for run {run_id}")
            return artifact_id
            
        except Exception as e:
            logger.error(f"Failed to create artifact: {e}")
            raise LLMStorageError(f"Failed to create artifact: {e}")
    
    def create_evidence_bundle(
        self,
        bundle_id: str,
        build_version: str,
        policy_json: str,
        summary_json: str,
        lake_uri: Optional[str] = None,
        bundle_json: Optional[str] = None,
    ) -> None:
        """
        Record an evidence bundle used for runs.
        
        When ``bundle_json`` is provided the full evidence payload is
        persisted in SQL so the bundle can be recovered without the lake.
        
        Args:
            bundle_id: UUID of the evidence bundle
            build_version: Evidence builder version
            policy_json: JSON string of the evidence policy
            summary_json: JSON string of the bundle summary
            lake_uri: Path to the bundle artifact in the lake (optional)
            bundle_json: Full evidence bundle JSON content (optional)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"""
                INSERT INTO [{self.config.schema}].[evidence_bundle] 
                (bundle_id, created_utc, build_version, policy_json, summary_json, lake_uri, bundle_json)
                VALUES (?, SYSUTCDATETIME(), ?, ?, ?, ?, ?)
                """,
                (bundle_id, build_version, policy_json, summary_json, lake_uri, bundle_json)
            )
            
            conn.commit()
            logger.debug(f"Created evidence bundle record {bundle_id}")
            
        except Exception as e:
            logger.error(f"Failed to create evidence bundle record: {e}")
            # Don't fail the whole run if evidence bundle metadata can't be saved
            # The bundle artifact is already in the lake
    
    def link_run_to_evidence_bundle(
        self,
        run_id: str,
        bundle_id: str,
    ) -> None:
        """
        Link a run to an evidence bundle.
        
        Args:
            run_id: The run ID
            bundle_id: The evidence bundle ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                f"""
                INSERT INTO [{self.config.schema}].[run_evidence] 
                (run_id, bundle_id, attached_utc)
                VALUES (?, ?, SYSUTCDATETIME())
                """,
                (run_id, bundle_id)
            )
            
            conn.commit()
            logger.debug(f"Linked run {run_id} to evidence bundle {bundle_id}")
            
        except Exception as e:
            logger.error(f"Failed to link run to evidence bundle: {e}")
            # Don't fail the whole run if the link can't be created
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with counts by status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT status, COUNT(*) as cnt
                FROM [{self.config.schema}].[job]
                GROUP BY status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
