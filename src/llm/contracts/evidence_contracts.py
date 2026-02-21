"""
Evidence Contracts - Phase 2 data models for evidence bundles.

These models define the structure for evidence items, evidence bundles, and
evidence bounding policies used by the Phase 2 evidence assembly system.

Uses dataclasses following the pattern established in phase1_contracts.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid


@dataclass
class EvidencePolicy:
    """
    Bounding policy for evidence bundles.
    
    Defines limits and rules for how evidence is bounded to fit within
    model context windows and ensure deterministic, auditable processing.
    
    Attributes:
        max_items: Maximum number of evidence items in a bundle
        max_total_bytes: Maximum total bytes across all items
        max_item_bytes: Maximum bytes per individual item
        max_sql_rows: Maximum rows for SQL result evidence
        max_sql_cols: Maximum columns for SQL result evidence (optional)
        chunk_size: Default chunk size for chunkable sources (bytes)
        chunk_overlap: Overlap between chunks (bytes)
        sampling_strategy: Strategy for deterministic sampling ("first_last", "stride", "first_only")
        enable_redaction: Whether to apply redaction hooks
        version: Policy version identifier
    """
    max_items: int = 50
    max_total_bytes: int = 100000  # ~100KB default
    max_item_bytes: int = 10000    # ~10KB per item
    max_sql_rows: int = 100
    max_sql_cols: Optional[int] = 20
    chunk_size: int = 5000
    chunk_overlap: int = 200
    sampling_strategy: str = "first_last"  # "first_last", "stride", "first_only"
    enable_redaction: bool = False
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_items": self.max_items,
            "max_total_bytes": self.max_total_bytes,
            "max_item_bytes": self.max_item_bytes,
            "max_sql_rows": self.max_sql_rows,
            "max_sql_cols": self.max_sql_cols,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "sampling_strategy": self.sampling_strategy,
            "enable_redaction": self.enable_redaction,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePolicy":
        """Create from dictionary."""
        return cls(
            max_items=data.get("max_items", 50),
            max_total_bytes=data.get("max_total_bytes", 100000),
            max_item_bytes=data.get("max_item_bytes", 10000),
            max_sql_rows=data.get("max_sql_rows", 100),
            max_sql_cols=data.get("max_sql_cols"),
            chunk_size=data.get("chunk_size", 5000),
            chunk_overlap=data.get("chunk_overlap", 200),
            sampling_strategy=data.get("sampling_strategy", "first_last"),
            enable_redaction=data.get("enable_redaction", False),
            version=data.get("version", "1.0"),
        )


@dataclass
class EvidenceItem:
    """
    A single piece of evidence in an evidence bundle.
    
    Represents one bounded unit of evidence that will be provided to the LLM.
    Each item has a deterministic ID and content hash for auditability.
    
    Attributes:
        evidence_id: Stable identifier within bundle (e.g., "inline:0", "sql:query1:0:0-100")
        evidence_type: Type of evidence (inline_text, lake_text, lake_http, sql_result, etc.)
        source_ref: Source identity metadata (lake_uri, url, sql, etc.)
        content: Bounded text content provided to LLM
        content_sha256: SHA256 hash of content
        byte_count: Size of content in bytes
        metadata: Additional metadata (row counts, mime type, offsets, bounding info, etc.)
        offsets: Optional line/byte ranges or chunk index
        full_ref: Optional pointer to full unbounded artifact if stored separately
        source_system: Normalized origin system (wikipedia, youtube, pdf, sql, etc.)
        source_uri: Canonical URL when applicable (external sources)
        selector_json: Structured selection details (offsets, page ranges, timestamps, etc.)
        ordinal: Ordering within the bundle for deterministic assembly
        role: How this evidence is used (primary, supporting, counter, context)
        excerpt_hash: Hash of the excerpt used if different from full content
    """
    evidence_id: str
    evidence_type: str
    source_ref: Dict[str, Any]
    content: str
    content_sha256: str
    byte_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    offsets: Optional[Dict[str, Any]] = None
    full_ref: Optional[Dict[str, Any]] = None
    source_system: Optional[str] = None
    source_uri: Optional[str] = None
    selector_json: Optional[Dict[str, Any]] = None
    ordinal: Optional[int] = None
    role: Optional[str] = None
    excerpt_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_ref": self.source_ref,
            "content": self.content,
            "content_sha256": self.content_sha256,
            "byte_count": self.byte_count,
            "metadata": self.metadata,
        }
        if self.offsets:
            result["offsets"] = self.offsets
        if self.full_ref:
            result["full_ref"] = self.full_ref
        if self.source_system is not None:
            result["source_system"] = self.source_system
        if self.source_uri is not None:
            result["source_uri"] = self.source_uri
        if self.selector_json is not None:
            result["selector_json"] = self.selector_json
        if self.ordinal is not None:
            result["ordinal"] = self.ordinal
        if self.role is not None:
            result["role"] = self.role
        if self.excerpt_hash is not None:
            result["excerpt_hash"] = self.excerpt_hash
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceItem":
        """Create from dictionary."""
        return cls(
            evidence_id=data["evidence_id"],
            evidence_type=data["evidence_type"],
            source_ref=data["source_ref"],
            content=data["content"],
            content_sha256=data["content_sha256"],
            byte_count=data["byte_count"],
            metadata=data.get("metadata", {}),
            offsets=data.get("offsets"),
            full_ref=data.get("full_ref"),
            source_system=data.get("source_system"),
            source_uri=data.get("source_uri"),
            selector_json=data.get("selector_json"),
            ordinal=data.get("ordinal"),
            role=data.get("role"),
            excerpt_hash=data.get("excerpt_hash"),
        )


@dataclass
class EvidenceBundle:
    """
    Collection of evidence items for a derive operation.
    
    Represents a complete, bounded evidence bundle that will be used for
    an LLM interrogation. Includes summary statistics and policy information.
    
    Attributes:
        bundle_id: Unique identifier for this bundle
        created_utc: When the bundle was created
        build_version: Evidence builder version string
        policy: Bounding policy used to create this bundle
        items: List of evidence items
        summary: Summary statistics (counts by type, total bytes, token estimate)
        bundle_sha256: Deterministic hash of ordered membership + content hashes
        bundle_kind: Bundle category (llm_input, human_review_packet, etc.)
        created_by: Worker/user identifier that assembled the bundle
        notes: Optional human commentary about why these sources were assembled
    """
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    build_version: str = "2.0"
    policy: EvidencePolicy = field(default_factory=EvidencePolicy)
    items: List[EvidenceItem] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    bundle_sha256: Optional[str] = None
    bundle_kind: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    
    def compute_summary(self) -> None:
        """Compute summary statistics for the bundle."""
        # Count by evidence type
        type_counts: Dict[str, int] = {}
        for item in self.items:
            type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
        
        # Total bytes
        total_bytes = sum(item.byte_count for item in self.items)
        
        # Rough token estimate (average ~4 chars per token)
        approx_tokens = total_bytes // 4
        
        self.summary = {
            "item_count": len(self.items),
            "type_counts": type_counts,
            "total_bytes": total_bytes,
            "approx_tokens": approx_tokens,
        }
    
    def compute_bundle_hash(self) -> str:
        """
        Compute a deterministic hash of bundle composition.
        
        The hash is derived from ordered item content hashes to enable
        deduplication and reuse of identical bundles.
        
        Returns:
            SHA256 hex digest of the bundle's ordered content.
        """
        hasher = hashlib.sha256()
        for item in self.items:
            hasher.update(item.content_sha256.encode())
        self.bundle_sha256 = hasher.hexdigest()
        return self.bundle_sha256
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "bundle_id": self.bundle_id,
            "created_utc": self.created_utc.isoformat(),
            "build_version": self.build_version,
            "policy": self.policy.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary,
        }
        if self.bundle_sha256 is not None:
            result["bundle_sha256"] = self.bundle_sha256
        if self.bundle_kind is not None:
            result["bundle_kind"] = self.bundle_kind
        if self.created_by is not None:
            result["created_by"] = self.created_by
        if self.notes is not None:
            result["notes"] = self.notes
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceBundle":
        """Create from dictionary."""
        items = [EvidenceItem.from_dict(i) for i in data.get("items", [])]
        policy = EvidencePolicy.from_dict(data.get("policy", {}))
        
        return cls(
            bundle_id=data.get("bundle_id", str(uuid.uuid4())),
            created_utc=datetime.fromisoformat(data["created_utc"]) if "created_utc" in data else datetime.now(timezone.utc),
            build_version=data.get("build_version", "2.0"),
            policy=policy,
            items=items,
            summary=data.get("summary", {}),
            bundle_sha256=data.get("bundle_sha256"),
            bundle_kind=data.get("bundle_kind"),
            created_by=data.get("created_by"),
            notes=data.get("notes"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "EvidenceBundle":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


def generate_evidence_id(evidence_type: str, source_identifier: str, chunk_index: int = 0) -> str:
    """
    Generate a deterministic evidence ID.
    
    Evidence IDs follow a stable convention:
    - inline:{n}
    - lake:{sha256_prefix}:{chunk_index}
    - sql:{query_key}:{page_index}:{row_range}
    - doc:{doc_id}:{chunk_index}
    
    Args:
        evidence_type: Type of evidence (inline_text, lake_text, sql_result, etc.)
        source_identifier: Source-specific identifier (content, lake_uri, query_key, etc.)
        chunk_index: Index of chunk for multi-chunk sources
        
    Returns:
        Deterministic evidence ID string
    """
    if evidence_type == "inline_text":
        return f"inline:{chunk_index}"
    
    # Generate a stable prefix from source identifier
    source_hash = hashlib.sha256(source_identifier.encode()).hexdigest()
    prefix = source_hash[:12]
    
    if evidence_type in ["lake_text", "lake_http"]:
        return f"lake:{prefix}:{chunk_index}"
    elif evidence_type == "sql_result":
        return f"sql:{prefix}:{chunk_index}"
    elif evidence_type in ["doc_chunk", "transcript_chunk"]:
        return f"doc:{prefix}:{chunk_index}"
    elif evidence_type == "sql_query_def":
        return f"sqldef:{prefix}"
    else:
        # Generic fallback
        return f"{evidence_type}:{prefix}:{chunk_index}"


# Import from shared utilities and re-export for backward compatibility
from ..core.utils import compute_content_hash

__all__ = [
    "EvidencePolicy",
    "EvidenceItem", 
    "EvidenceBundle",
    "generate_evidence_id",
    "compute_content_hash",
]
