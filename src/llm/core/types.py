"""
Core data types for the LLM-Derived Data module.

Uses dataclasses following the pattern established in src/ingest/core/models.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class DeriveJobStatus(str, Enum):
    """Status of a derive job in the queue."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


class EvidenceSourceType(str, Enum):
    """Type of evidence source."""
    INGEST_RECORD = "ingest_record"
    SQL_RESULT = "sql_result"
    HTTP_RESPONSE = "http_response"
    DOCUMENT = "document"
    OTHER = "other"


@dataclass
class EvidenceItem:
    """
    Represents a single piece of evidence in an evidence bundle.
    
    Attributes:
        source_type: Type of evidence source (ingest_record, sql_result, etc.)
        source_ref: Reference to the source (file path, ingest_id, query hash)
        content_hash: SHA256 hash of the source content for integrity verification
        content: Optional loaded content (not always populated)
        metadata: Additional metadata about this evidence item
    """
    source_type: EvidenceSourceType
    source_ref: str
    content_hash: Optional[str] = None
    content: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    """
    Collection of evidence items used for LLM derivation.
    
    Attributes:
        items: List of evidence items
        bundle_id: Unique identifier for this bundle
        bundle_hash: Combined hash of all evidence items
        created_at: When the bundle was created
    """
    items: List[EvidenceItem] = field(default_factory=list)
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bundle_hash: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_item(self, item: EvidenceItem) -> None:
        """Add an evidence item to the bundle."""
        self.items.append(item)


@dataclass
class LLMConfig:
    """
    Configuration for LLM provider and model.
    
    Attributes:
        provider: LLM provider name (e.g., 'ollama', 'openai')
        model: Model identifier (e.g., 'llama3.2', 'gpt-4o')
        base_url: Base URL for the provider API
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        timeout_seconds: Request timeout in seconds
        stream: Whether to use streaming responses
        prompt_template_ref: Reference to the prompt template
        extra_params: Additional provider-specific parameters
    """
    provider: str
    model: str
    base_url: str = "http://localhost:11434"
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    timeout_seconds: int = 120
    stream: bool = False
    prompt_template_ref: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeriveResult:
    """
    Result of a derive operation.
    
    Attributes:
        success: Whether the derivation succeeded
        artifact_path: Path to the derived artifact file
        artifact_hash: SHA256 hash of the derived artifact
        raw_response_path: Path to the raw LLM response
        raw_response: The raw response text from the LLM
        parsed_output: Parsed JSON output (if successful)
        completed_at: When the derivation completed
        duration_ms: Time taken for derivation in milliseconds
        token_usage: Token usage statistics (if available)
        validation_errors: Schema validation errors (if any)
        error_type: Error type (if failed)
        error_message: Error message (if failed)
    """
    success: bool
    artifact_path: Optional[str] = None
    artifact_hash: Optional[str] = None
    raw_response_path: Optional[str] = None
    raw_response: Optional[str] = None
    parsed_output: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
    validation_errors: List[str] = field(default_factory=list)
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeriveManifest:
    """
    Manifest tracking a derive operation for reproducibility.
    
    Attributes:
        manifest_id: Unique identifier for this manifest
        manifest_version: Schema version for this manifest
        created_at: When the manifest was created
        evidence_bundle: References to source evidence
        llm_config: LLM configuration used
        output_schema_ref: Reference to expected output schema
        status: Current status of the derive operation
        result: Result of the derivation (if completed)
        metadata: Additional metadata
    """
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    manifest_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_bundle: Optional[EvidenceBundle] = None
    llm_config: Optional[LLMConfig] = None
    output_schema_ref: Optional[str] = None
    status: DeriveJobStatus = DeriveJobStatus.PENDING
    result: Optional[DeriveResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for serialization."""
        return {
            "manifest_version": self.manifest_version,
            "manifest_id": self.manifest_id,
            "created_at_utc": self.created_at.isoformat(),
            "evidence_bundle": {
                "items": [
                    {
                        "source_type": item.source_type.value,
                        "source_ref": item.source_ref,
                        "content_hash": item.content_hash,
                        "metadata": item.metadata,
                    }
                    for item in (self.evidence_bundle.items if self.evidence_bundle else [])
                ],
                "bundle_hash": self.evidence_bundle.bundle_hash if self.evidence_bundle else None,
            },
            "llm_config": {
                "provider": self.llm_config.provider if self.llm_config else None,
                "model": self.llm_config.model if self.llm_config else None,
                "temperature": self.llm_config.temperature if self.llm_config else None,
                "max_tokens": self.llm_config.max_tokens if self.llm_config else None,
                "prompt_template_ref": self.llm_config.prompt_template_ref if self.llm_config else None,
            },
            "output_schema_ref": self.output_schema_ref,
            "status": self.status.value,
            "result": self._result_to_dict() if self.result else None,
            "metadata": self.metadata,
        }

    def _result_to_dict(self) -> Optional[Dict[str, Any]]:
        """Convert result to dictionary."""
        if not self.result:
            return None
        return {
            "artifact_path": self.result.artifact_path,
            "artifact_hash": self.result.artifact_hash,
            "raw_response_path": self.result.raw_response_path,
            "completed_at_utc": self.result.completed_at.isoformat() if self.result.completed_at else None,
            "duration_ms": self.result.duration_ms,
            "token_usage": self.result.token_usage,
            "validation_errors": self.result.validation_errors,
        }
