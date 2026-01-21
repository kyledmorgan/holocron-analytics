"""
SQL Queue Store - SQL Server queue and persistence for LLM derive jobs.

This is a stub implementation. Full database schema and implementation
are planned for later phases.

NOTE: Exact SQL Server schema for job queue and run metadata is TBD.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.types import DeriveJobStatus, DeriveManifest
from ..core.exceptions import LLMStorageError


logger = logging.getLogger(__name__)


class SqlQueueStore:
    """
    SQL Server-based queue and metadata store for LLM derive jobs.
    
    This is a **stub implementation** providing the interface for:
    - Job queue management (enqueue, dequeue, status updates)
    - Run metadata persistence
    - Manifest storage and retrieval
    
    The actual SQL Server schema is TBD. This stub uses in-memory storage
    for interface validation.
    
    Planned Schema (not implemented):
    
    ```sql
    -- llm.DeriveJobs: Queue of pending/active jobs
    CREATE TABLE llm.DeriveJobs (
        job_id UNIQUEIDENTIFIER PRIMARY KEY,
        manifest_id UNIQUEIDENTIFIER NOT NULL,
        status VARCHAR(50) NOT NULL,
        priority INT DEFAULT 100,
        created_at_utc DATETIME2 NOT NULL,
        started_at_utc DATETIME2,
        completed_at_utc DATETIME2,
        attempt INT DEFAULT 0,
        error_message NVARCHAR(MAX),
        worker_id VARCHAR(100)
    );
    
    -- llm.DeriveManifests: Manifest metadata
    CREATE TABLE llm.DeriveManifests (
        manifest_id UNIQUEIDENTIFIER PRIMARY KEY,
        manifest_version VARCHAR(20) NOT NULL,
        created_at_utc DATETIME2 NOT NULL,
        evidence_bundle_hash VARCHAR(64),
        llm_provider VARCHAR(50),
        llm_model VARCHAR(100),
        status VARCHAR(50) NOT NULL,
        artifact_path NVARCHAR(500),
        manifest_json NVARCHAR(MAX)
    );
    ```
    
    Example:
        >>> store = SqlQueueStore(connection_string="...")
        >>> job_id = store.enqueue(manifest)
        >>> job = store.dequeue()
        >>> store.update_status(job_id, DeriveJobStatus.COMPLETED)
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        schema: str = "llm",
    ):
        """
        Initialize the SQL queue store.
        
        Args:
            connection_string: SQL Server connection string (not used in stub)
            schema: Database schema name
        """
        self.connection_string = connection_string
        self.schema = schema
        
        # In-memory storage for stub implementation
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._manifests: Dict[str, Dict[str, Any]] = {}
        
        logger.warning(
            "SqlQueueStore is a stub implementation. "
            "Full SQL Server persistence is not yet implemented."
        )
    
    def enqueue(
        self,
        manifest: DeriveManifest,
        priority: int = 100,
    ) -> str:
        """
        Add a derive job to the queue.
        
        Args:
            manifest: The derive manifest for this job
            priority: Job priority (lower = higher priority)
            
        Returns:
            Job ID
        """
        import uuid
        
        job_id = str(uuid.uuid4())
        
        self._jobs[job_id] = {
            "job_id": job_id,
            "manifest_id": manifest.manifest_id,
            "status": DeriveJobStatus.PENDING.value,
            "priority": priority,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_at_utc": None,
            "completed_at_utc": None,
            "attempt": 0,
            "error_message": None,
        }
        
        self._manifests[manifest.manifest_id] = manifest.to_dict()
        
        logger.debug(f"Enqueued job: job_id={job_id}, manifest_id={manifest.manifest_id}")
        return job_id
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending job from the queue.
        
        Returns:
            Job data dictionary, or None if queue is empty
        """
        pending_jobs = [
            j for j in self._jobs.values()
            if j["status"] == DeriveJobStatus.PENDING.value
        ]
        
        if not pending_jobs:
            return None
        
        # Sort by priority, then by created time
        pending_jobs.sort(key=lambda j: (j["priority"], j["created_at_utc"]))
        
        job = pending_jobs[0]
        job["status"] = DeriveJobStatus.IN_PROGRESS.value
        job["started_at_utc"] = datetime.now(timezone.utc).isoformat()
        job["attempt"] += 1
        
        logger.debug(f"Dequeued job: job_id={job['job_id']}")
        return job
    
    def update_status(
        self,
        job_id: str,
        status: DeriveJobStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a job.
        
        Args:
            job_id: The job ID to update
            status: New status
            error_message: Error message (for failed jobs)
            
        Returns:
            True if update succeeded
        """
        if job_id not in self._jobs:
            logger.warning(f"Job not found: {job_id}")
            return False
        
        self._jobs[job_id]["status"] = status.value
        
        if status in (DeriveJobStatus.COMPLETED, DeriveJobStatus.FAILED, DeriveJobStatus.VALIDATION_FAILED):
            self._jobs[job_id]["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        
        if error_message:
            self._jobs[job_id]["error_message"] = error_message
        
        logger.debug(f"Updated job status: job_id={job_id}, status={status.value}")
        return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        return self._jobs.get(job_id)
    
    def get_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """Get manifest data by ID."""
        return self._manifests.get(manifest_id)
    
    def list_jobs(
        self,
        status: Optional[DeriveJobStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List jobs, optionally filtered by status.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j["status"] == status.value]
        
        # Sort by created time descending
        jobs.sort(key=lambda j: j["created_at_utc"], reverse=True)
        
        return jobs[:limit]
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with counts by status
        """
        stats = {status.value: 0 for status in DeriveJobStatus}
        
        for job in self._jobs.values():
            status = job["status"]
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Remove completed/failed jobs older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of jobs removed
        
        Note: Stub implementation - does nothing
        """
        logger.warning("cleanup_old_jobs is not implemented in stub")
        return 0
