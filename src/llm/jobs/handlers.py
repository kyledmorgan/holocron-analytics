"""
Job Handlers - Base types and utilities for job handlers.

This module provides the base types for job execution:
- RunContext: Execution context passed to handlers
- HandlerResult: Structured result returned by handlers
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Mode of job execution."""
    LIVE = "live"        # Full execution with domain writes
    DRY_RUN = "dry_run"  # Execute but skip domain writes


class HandlerStatus(str, Enum):
    """Status of handler execution."""
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class RunContext:
    """
    Execution context for a job handler.
    
    Provides all contextual information needed by a handler:
    - Correlation identifiers for tracing
    - Execution mode (live vs dry-run)
    - Timestamps
    - Configuration
    
    Attributes:
        job_id: The job identifier
        run_id: The run identifier (unique per execution attempt)
        correlation_id: Correlation ID for tracing across logs/artifacts
        worker_id: Identifier of the worker executing the job
        execution_mode: Whether this is a live or dry-run execution
        started_at: When this run started
        job_type: The job type being executed
        interrogation_key: The interrogation key for this job
        attempt_number: Current attempt number (1-indexed)
        max_attempts: Maximum attempts allowed
        extra: Additional context data
    """
    job_id: str
    run_id: str
    correlation_id: str
    worker_id: str
    execution_mode: ExecutionMode = ExecutionMode.LIVE
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    job_type: Optional[str] = None
    interrogation_key: Optional[str] = None
    attempt_number: int = 1
    max_attempts: int = 3
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        job_id: str,
        worker_id: str,
        job_type: Optional[str] = None,
        interrogation_key: Optional[str] = None,
        execution_mode: ExecutionMode = ExecutionMode.LIVE,
        attempt_number: int = 1,
        max_attempts: int = 3,
        **extra: Any,
    ) -> "RunContext":
        """
        Create a new run context with generated identifiers.
        
        Args:
            job_id: The job identifier
            worker_id: Worker identifier
            job_type: Optional job type
            interrogation_key: Optional interrogation key
            execution_mode: Execution mode (live or dry-run)
            attempt_number: Current attempt number
            max_attempts: Maximum attempts
            **extra: Additional context data
            
        Returns:
            New RunContext instance
        """
        run_id = str(uuid.uuid4())
        correlation_id = f"{job_id}-{run_id[:8]}"
        
        return cls(
            job_id=job_id,
            run_id=run_id,
            correlation_id=correlation_id,
            worker_id=worker_id,
            execution_mode=execution_mode,
            job_type=job_type,
            interrogation_key=interrogation_key,
            attempt_number=attempt_number,
            max_attempts=max_attempts,
            extra=extra,
        )
    
    @property
    def is_dry_run(self) -> bool:
        """Check if this is a dry-run execution."""
        return self.execution_mode == ExecutionMode.DRY_RUN
    
    def get_log_context(self) -> Dict[str, Any]:
        """
        Get context fields for structured logging.
        
        Returns a dict of fields that should be included in log messages
        for traceability.
        """
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "worker_id": self.worker_id,
            "execution_mode": self.execution_mode.value,
            "job_type": self.job_type,
            "attempt": self.attempt_number,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "worker_id": self.worker_id,
            "execution_mode": self.execution_mode.value,
            "started_at": self.started_at.isoformat(),
            "job_type": self.job_type,
            "interrogation_key": self.interrogation_key,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "extra": self.extra,
        }


@dataclass
class ArtifactReference:
    """Reference to an artifact written during job execution."""
    artifact_type: str
    lake_uri: str
    content_sha256: Optional[str] = None
    byte_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "artifact_type": self.artifact_type,
            "lake_uri": self.lake_uri,
        }
        if self.content_sha256:
            result["content_sha256"] = self.content_sha256
        if self.byte_count is not None:
            result["byte_count"] = self.byte_count
        return result


@dataclass
class HandlerResult:
    """
    Result returned by a job handler.
    
    Provides structured information about what happened during execution,
    including status, artifacts produced, validation results, and any errors.
    
    Attributes:
        status: Final status of the handler execution
        artifacts: List of artifacts written during execution
        output: Parsed output from the handler (if successful)
        validation_errors: List of validation errors (if any)
        error_message: Error message (if failed)
        metrics: Execution metrics (tokens, timing, etc.)
        domain_writes: Records written to domain tables (empty in dry-run)
        skipped_reason: Reason for skipping (if status is SKIPPED)
    """
    status: HandlerStatus
    artifacts: List[ArtifactReference] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    domain_writes: List[Dict[str, Any]] = field(default_factory=list)
    skipped_reason: Optional[str] = None
    
    @classmethod
    def success(
        cls,
        output: Dict[str, Any],
        artifacts: Optional[List[ArtifactReference]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        domain_writes: Optional[List[Dict[str, Any]]] = None,
    ) -> "HandlerResult":
        """Create a successful result."""
        return cls(
            status=HandlerStatus.SUCCEEDED,
            artifacts=artifacts or [],
            output=output,
            metrics=metrics or {},
            domain_writes=domain_writes or [],
        )
    
    @classmethod
    def failure(
        cls,
        error_message: str,
        artifacts: Optional[List[ArtifactReference]] = None,
        validation_errors: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> "HandlerResult":
        """Create a failed result."""
        return cls(
            status=HandlerStatus.FAILED,
            artifacts=artifacts or [],
            error_message=error_message,
            validation_errors=validation_errors or [],
            metrics=metrics or {},
        )
    
    @classmethod
    def skipped(
        cls,
        reason: str,
        artifacts: Optional[List[ArtifactReference]] = None,
    ) -> "HandlerResult":
        """Create a skipped result."""
        return cls(
            status=HandlerStatus.SKIPPED,
            artifacts=artifacts or [],
            skipped_reason=reason,
        )
    
    @property
    def succeeded(self) -> bool:
        """Check if the handler succeeded."""
        return self.status == HandlerStatus.SUCCEEDED
    
    @property
    def failed(self) -> bool:
        """Check if the handler failed."""
        return self.status == HandlerStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "status": self.status.value,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "metrics": self.metrics,
        }
        if self.output:
            result["output"] = self.output
        if self.validation_errors:
            result["validation_errors"] = self.validation_errors
        if self.error_message:
            result["error_message"] = self.error_message
        if self.domain_writes:
            result["domain_writes"] = self.domain_writes
        if self.skipped_reason:
            result["skipped_reason"] = self.skipped_reason
        return result
