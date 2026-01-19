"""
Core data models for the ingestion framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class WorkItemStatus(str, Enum):
    """Status of a work item in the ingestion queue."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkItem:
    """
    Represents a single unit of work in the ingestion pipeline.
    
    Attributes:
        source_system: System identifier (e.g., 'mediawiki', 'http_scrape')
        source_name: Source name (e.g., 'wikipedia', 'wookieepedia')
        resource_type: Type of resource (e.g., 'page', 'category', 'revision')
        resource_id: Remote identifier or key for deduplication
        request_uri: Full URI to fetch
        request_method: HTTP method (GET, POST, etc.)
        request_headers: Optional headers for the request
        request_body: Optional body for POST requests
        metadata: Additional metadata for processing
        priority: Priority level (lower number = higher priority)
        status: Current status of the work item
        attempt: Number of attempts made
        run_id: Optional batch run identifier
        discovered_from: Optional reference to parent work item
        created_at: When the work item was created
        updated_at: When the work item was last updated
    """
    source_system: str
    source_name: str
    resource_type: str
    resource_id: str
    request_uri: str
    request_method: str = "GET"
    request_headers: Optional[Dict[str, str]] = None
    request_body: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    status: WorkItemStatus = WorkItemStatus.PENDING
    attempt: int = 0
    run_id: Optional[str] = None
    discovered_from: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    work_item_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_dedupe_key(self) -> str:
        """Generate a stable key for deduplication."""
        return f"{self.source_system}:{self.source_name}:{self.resource_type}:{self.resource_id}"


@dataclass
class IngestRecord:
    """
    Represents the result of an ingestion operation.
    
    Contains minimal metadata and the raw JSON payload.
    
    Attributes:
        ingest_id: Unique identifier for this ingest record
        source_system: System identifier
        source_name: Source name
        resource_type: Type of resource ingested
        resource_id: Remote identifier or key
        request_uri: URI that was requested
        request_method: HTTP method used
        request_headers: Headers sent with request
        status_code: HTTP status code received
        response_headers: Headers received in response
        payload: Raw JSON payload from the response
        fetched_at_utc: When the resource was fetched
        hash_sha256: Optional SHA256 hash of payload for change detection
        run_id: Optional batch run identifier
        work_item_id: Reference to the work item that created this
        attempt: Attempt number for this fetch
        error_message: Error message if fetch failed
        duration_ms: Time taken to fetch in milliseconds
    """
    ingest_id: str
    source_system: str
    source_name: str
    resource_type: str
    resource_id: str
    request_uri: str
    request_method: str
    status_code: int
    payload: Dict[str, Any]
    fetched_at_utc: datetime
    request_headers: Optional[Dict[str, str]] = None
    response_headers: Optional[Dict[str, str]] = None
    hash_sha256: Optional[str] = None
    run_id: Optional[str] = None
    work_item_id: Optional[str] = None
    attempt: int = 1
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
