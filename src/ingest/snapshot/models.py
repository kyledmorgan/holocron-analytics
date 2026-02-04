"""
Core data models for the snapshot/interchange framework.

Defines the ExchangeRecord envelope format that serves as the portable unit
for data interchange between JSON files and SQL Server.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ExchangeType(str, Enum):
    """Type of exchange/connector that produced this record."""
    HTTP = "http"
    MEDIAWIKI = "mediawiki"
    OPENALEX = "openalex"
    LLM = "llm"
    FILE = "file"
    GENERIC = "generic"


@dataclass
class Provenance:
    """
    Provenance information for audit/lineage tracking.
    
    Attributes:
        runner_name: Name of the runner/process that created this record
        host: Hostname where the record was created
        git_sha: Git commit SHA if available
        connector_version: Version of the connector used
    """
    runner_name: Optional[str] = None
    host: Optional[str] = None
    git_sha: Optional[str] = None
    connector_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "runner_name": self.runner_name,
            "host": self.host,
            "git_sha": self.git_sha,
            "connector_version": self.connector_version,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Provenance":
        """Create from dictionary."""
        if data is None:
            return cls()
        return cls(
            runner_name=data.get("runner_name"),
            host=data.get("host"),
            git_sha=data.get("git_sha"),
            connector_version=data.get("connector_version"),
        )


@dataclass
class ExchangeRecord:
    """
    Universal envelope format for data exchange.
    
    This is the portable unit that can be stored as JSON and mirrored in SQL.
    
    Attributes:
        exchange_id: Unique identifier (UUID) for this record
        exchange_type: Type of exchange (http, mediawiki, openalex, llm, etc.)
        source_system: System identifier (e.g., 'wookieepedia', 'openalex')
        entity_type: Type of entity (e.g., 'page', 'work', 'completion')
        natural_key: Stable identifier if available (page_id, DOI, etc.)
        request: Request payload/URL/headers/params/prompt (sanitized)
        response: Response payload (JSON/text) plus parse metadata
        observed_at_utc: When the data was observed/fetched
        provenance: Runner/host/git info for audit trail
        content_sha256: SHA256 over canonical hash input
        schema_version: Version of this envelope schema
        tags: Optional tags for categorization
        redactions_applied: List of redaction rules applied
        response_ref: Optional pointer to separate blob file for large payloads
    """
    exchange_id: str
    exchange_type: str
    source_system: str
    entity_type: str
    observed_at_utc: datetime
    content_sha256: str
    natural_key: Optional[str] = None
    request: Optional[Dict[str, Any]] = None
    response: Optional[Any] = None
    provenance: Optional[Provenance] = None
    schema_version: int = 1
    tags: List[str] = field(default_factory=list)
    redactions_applied: List[str] = field(default_factory=list)
    response_ref: Optional[str] = None

    @classmethod
    def create(
        cls,
        exchange_type: str,
        source_system: str,
        entity_type: str,
        request: Optional[Dict[str, Any]] = None,
        response: Optional[Any] = None,
        natural_key: Optional[str] = None,
        provenance: Optional[Provenance] = None,
        tags: Optional[List[str]] = None,
        observed_at_utc: Optional[datetime] = None,
    ) -> "ExchangeRecord":
        """
        Create a new ExchangeRecord with auto-generated ID and hash.
        
        The content_sha256 is computed after creation via compute_content_hash().
        """
        from .canonical import compute_content_hash
        
        exchange_id = str(uuid.uuid4())
        observed = observed_at_utc or datetime.now(timezone.utc)
        
        # Create record with placeholder hash
        record = cls(
            exchange_id=exchange_id,
            exchange_type=exchange_type,
            source_system=source_system,
            entity_type=entity_type,
            natural_key=natural_key,
            request=request,
            response=response,
            observed_at_utc=observed,
            provenance=provenance,
            content_sha256="",  # Will be computed
            tags=tags or [],
        )
        
        # Compute content hash
        record.content_sha256 = compute_content_hash(record)
        
        return record

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "exchange_id": self.exchange_id,
            "exchange_type": self.exchange_type,
            "source_system": self.source_system,
            "entity_type": self.entity_type,
            "natural_key": self.natural_key,
            "request": self.request,
            "response": self.response,
            "observed_at_utc": self.observed_at_utc.isoformat() if self.observed_at_utc else None,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "content_sha256": self.content_sha256,
            "schema_version": self.schema_version,
            "tags": self.tags,
            "redactions_applied": self.redactions_applied,
            "response_ref": self.response_ref,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExchangeRecord":
        """Create from dictionary."""
        observed_at = data.get("observed_at_utc")
        if isinstance(observed_at, str):
            # Parse ISO format datetime
            observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        
        return cls(
            exchange_id=data["exchange_id"],
            exchange_type=data["exchange_type"],
            source_system=data["source_system"],
            entity_type=data["entity_type"],
            natural_key=data.get("natural_key"),
            request=data.get("request"),
            response=data.get("response"),
            observed_at_utc=observed_at,
            provenance=Provenance.from_dict(data.get("provenance")),
            content_sha256=data["content_sha256"],
            schema_version=data.get("schema_version", 1),
            tags=data.get("tags", []),
            redactions_applied=data.get("redactions_applied", []),
            response_ref=data.get("response_ref"),
        )

    def get_dedupe_key(self) -> str:
        """Get stable deduplication key based on source and natural key."""
        return f"{self.source_system}:{self.entity_type}:{self.natural_key or self.exchange_id}"

    def get_hash_input_key(self) -> str:
        """Get the composite key used for hashing (for index lookups)."""
        return f"{self.source_system}|{self.entity_type}|{self.natural_key or ''}"
