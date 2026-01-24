"""
Phase 1 Contracts - Data models for LLM derive jobs and outputs.

These models define the structure for job inputs, evidence bundles, and
structured outputs used by the Phase 1 runner.

Uses dataclasses following the pattern established in src/llm/core/types.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import uuid


class JobStatus(str, Enum):
    """Status of a job in the queue."""
    NEW = "NEW"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEADLETTER = "DEADLETTER"


@dataclass
class EvidenceSnippet:
    """
    A single piece of evidence for LLM interrogation.
    
    Attributes:
        evidence_id: Unique identifier for this snippet
        source_uri: Reference to the source (file path, URL, etc.)
        text: The actual text content of the evidence
        offsets: Optional start/end character offsets in source
        metadata: Additional metadata about this snippet
    """
    evidence_id: str
    source_uri: str
    text: str
    offsets: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "evidence_id": self.evidence_id,
            "source_uri": self.source_uri,
            "text": self.text,
        }
        if self.offsets:
            result["offsets"] = self.offsets
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSnippet":
        """Create from dictionary."""
        return cls(
            evidence_id=data["evidence_id"],
            source_uri=data["source_uri"],
            text=data["text"],
            offsets=data.get("offsets"),
            metadata=data.get("metadata"),
        )


@dataclass
class EvidenceBundleV1:
    """
    Collection of evidence snippets for a derive operation.
    
    Attributes:
        snippets: List of evidence snippets
        bundle_id: Unique identifier for this bundle
        created_utc: When the bundle was created
    """
    snippets: List[EvidenceSnippet] = field(default_factory=list)
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bundle_id": self.bundle_id,
            "created_utc": self.created_utc.isoformat(),
            "snippets": [s.to_dict() for s in self.snippets],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceBundleV1":
        """Create from dictionary."""
        snippets = [EvidenceSnippet.from_dict(s) for s in data.get("snippets", [])]
        return cls(
            snippets=snippets,
            bundle_id=data.get("bundle_id", str(uuid.uuid4())),
            created_utc=datetime.fromisoformat(data["created_utc"]) if "created_utc" in data else datetime.now(timezone.utc),
        )


@dataclass
class JobInputEnvelope:
    """
    Input envelope for a derive job.
    
    Attributes:
        entity_type: Type of entity being interrogated (e.g., "character", "planet")
        entity_id: Identifier for the entity
        source_refs: List of source references to use as evidence
        extra_params: Additional parameters for the interrogation
    """
    entity_type: str
    entity_id: str
    source_refs: List[str] = field(default_factory=list)
    extra_params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "source_refs": self.source_refs,
        }
        if self.extra_params:
            result["extra_params"] = self.extra_params
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobInputEnvelope":
        """Create from dictionary."""
        return cls(
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            source_refs=data.get("source_refs", []),
            extra_params=data.get("extra_params"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "JobInputEnvelope":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ExtractedFact:
    """
    A single extracted fact from evidence.
    
    Attributes:
        fact_key: Identifier for the type of fact (e.g., "birth_year", "homeworld")
        value: The extracted value (can be string, number, etc.)
        unit: Optional unit for numeric values (e.g., "BBY", "meters")
        confidence: Confidence score from 0.0 to 1.0
        evidence_ids: List of evidence snippet IDs that support this fact
        notes: Optional notes about the extraction
    """
    fact_key: str
    value: Optional[Any]
    confidence: float
    evidence_ids: List[str]
    unit: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "fact_key": self.fact_key,
            "value": self.value,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
        }
        if self.unit is not None:
            result["unit"] = self.unit
        if self.notes is not None:
            result["notes"] = self.notes
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedFact":
        """Create from dictionary."""
        return cls(
            fact_key=data["fact_key"],
            value=data.get("value"),
            confidence=data.get("confidence", 0.0),
            evidence_ids=data.get("evidence_ids", []),
            unit=data.get("unit"),
            notes=data.get("notes"),
        )


@dataclass
class EntityFactsOutput:
    """
    Output contract for sw_entity_facts_v1 interrogation.
    
    Attributes:
        entity_type: Type of entity
        entity_id: Identifier for the entity
        entity_name: Canonical name of the entity
        facts: List of extracted facts
        metadata: Additional output metadata
    """
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    facts: List[ExtractedFact]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "facts": [f.to_dict() for f in self.facts],
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityFactsOutput":
        """Create from dictionary."""
        facts = [ExtractedFact.from_dict(f) for f in data.get("facts", [])]
        return cls(
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            entity_name=data.get("entity_name"),
            facts=facts,
            metadata=data.get("metadata"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "EntityFactsOutput":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Job:
    """
    Represents a job from the queue.
    
    Attributes:
        job_id: Unique identifier for this job
        created_utc: When the job was created
        status: Current status of the job
        priority: Job priority (higher = processed sooner)
        interrogation_key: Which interrogation definition to use
        input_json: Job input parameters as JSON string
        evidence_ref_json: Evidence references as JSON string (optional)
        model_hint: Suggested model to use (optional)
        max_attempts: Maximum number of attempts before deadletter
        attempt_count: Current attempt number
        available_utc: When the job becomes available for processing
        locked_by: Worker ID that claimed this job
        locked_utc: When the job was claimed
        last_error: Last error message if failed
    """
    job_id: str
    interrogation_key: str
    input_json: str
    created_utc: Optional[datetime] = None
    status: JobStatus = JobStatus.NEW
    priority: int = 100
    evidence_ref_json: Optional[str] = None
    model_hint: Optional[str] = None
    max_attempts: int = 3
    attempt_count: int = 0
    available_utc: Optional[datetime] = None
    locked_by: Optional[str] = None
    locked_utc: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def get_input(self) -> JobInputEnvelope:
        """Parse input_json into JobInputEnvelope."""
        return JobInputEnvelope.from_json(self.input_json)
    
    def get_evidence_refs(self) -> Optional[List[str]]:
        """Parse evidence_ref_json into list of references."""
        if not self.evidence_ref_json:
            return None
        return json.loads(self.evidence_ref_json)
    
    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Job":
        """Create from database row."""
        return cls(
            job_id=str(row["job_id"]),
            created_utc=row.get("created_utc"),
            status=JobStatus(row.get("status", "NEW")),
            priority=row.get("priority", 100),
            interrogation_key=row["interrogation_key"],
            input_json=row["input_json"],
            evidence_ref_json=row.get("evidence_ref_json"),
            model_hint=row.get("model_hint"),
            max_attempts=row.get("max_attempts", 3),
            attempt_count=row.get("attempt_count", 0),
            available_utc=row.get("available_utc"),
            locked_by=row.get("locked_by"),
            locked_utc=row.get("locked_utc"),
            last_error=row.get("last_error"),
        )


def validate_entity_facts_output(data: Dict[str, Any]) -> List[str]:
    """
    Validate a dictionary against the EntityFactsOutput schema.
    
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    
    # Required fields
    if "entity_type" not in data:
        errors.append("Missing required field: entity_type")
    elif not isinstance(data["entity_type"], str):
        errors.append("entity_type must be a string")
    
    if "entity_id" not in data:
        errors.append("Missing required field: entity_id")
    elif not isinstance(data["entity_id"], str):
        errors.append("entity_id must be a string")
    
    if "facts" not in data:
        errors.append("Missing required field: facts")
    elif not isinstance(data["facts"], list):
        errors.append("facts must be an array")
    else:
        # Validate each fact
        for i, fact in enumerate(data["facts"]):
            if not isinstance(fact, dict):
                errors.append(f"facts[{i}] must be an object")
                continue
            
            if "fact_key" not in fact:
                errors.append(f"facts[{i}]: Missing required field: fact_key")
            elif not isinstance(fact["fact_key"], str):
                errors.append(f"facts[{i}].fact_key must be a string")
            
            if "confidence" in fact:
                conf = fact["confidence"]
                if not isinstance(conf, (int, float)):
                    errors.append(f"facts[{i}].confidence must be a number")
                elif conf < 0.0 or conf > 1.0:
                    errors.append(f"facts[{i}].confidence must be between 0.0 and 1.0")
            
            if "evidence_ids" in fact and not isinstance(fact["evidence_ids"], list):
                errors.append(f"facts[{i}].evidence_ids must be an array")
    
    return errors
