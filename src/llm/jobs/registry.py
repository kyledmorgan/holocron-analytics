"""
Job Type Registry - Central catalog for LLM job type definitions.

This module provides a registry for job type definitions that includes:
- Job type identifier
- Display name
- Prompt template reference (via interrogation_key)
- Input/output schema references
- Handler reference
- Operational metadata (retry limits, priority defaults)

The registry extends the existing interrogation registry pattern,
adding operational and routing metadata for the dispatcher.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..interrogations.registry import get_interrogation, InterrogationDefinition


logger = logging.getLogger(__name__)


@dataclass
class JobTypeDefinition:
    """
    Definition for a job type in the LLM pipeline.
    
    Attributes:
        job_type: Unique identifier for this job type (e.g., 'page_classification')
        display_name: Human-readable name for display/logging
        interrogation_key: Key to look up the interrogation definition
        handler_ref: Import path or callable for the job handler
        max_attempts: Maximum retry attempts before deadletter (default: 3)
        default_priority: Default priority for jobs of this type (higher = processed sooner)
        timeout_seconds: Timeout for handler execution (default: 300)
        version: Optional version string for this job type definition
        description: Optional description of what this job type does
        tags: Optional tags for categorization
    """
    job_type: str
    display_name: str
    interrogation_key: str
    handler_ref: str
    max_attempts: int = 3
    default_priority: int = 100
    timeout_seconds: int = 300
    version: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def get_interrogation(self) -> Optional[InterrogationDefinition]:
        """Get the interrogation definition for this job type."""
        return get_interrogation(self.interrogation_key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_type": self.job_type,
            "display_name": self.display_name,
            "interrogation_key": self.interrogation_key,
            "handler_ref": self.handler_ref,
            "max_attempts": self.max_attempts,
            "default_priority": self.default_priority,
            "timeout_seconds": self.timeout_seconds,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobTypeDefinition":
        """Create from dictionary."""
        return cls(
            job_type=data["job_type"],
            display_name=data["display_name"],
            interrogation_key=data["interrogation_key"],
            handler_ref=data["handler_ref"],
            max_attempts=data.get("max_attempts", 3),
            default_priority=data.get("default_priority", 100),
            timeout_seconds=data.get("timeout_seconds", 300),
            version=data.get("version"),
            description=data.get("description"),
            tags=data.get("tags", []),
        )


class JobTypeRegistry:
    """
    Registry for job type definitions.
    
    Provides lookup of job type definitions by their type identifier.
    Definitions can be registered programmatically or discovered from
    the interrogation registry.
    
    Example:
        >>> registry = JobTypeRegistry()
        >>> registry.register(JobTypeDefinition(
        ...     job_type='page_classification',
        ...     display_name='Page Classification',
        ...     interrogation_key='page_classification_v1',
        ...     handler_ref='src.llm.handlers.page_classification.handle',
        ... ))
        >>> definition = registry.get('page_classification')
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._definitions: Dict[str, JobTypeDefinition] = {}
        self._loaded = False
    
    def register(self, definition: JobTypeDefinition) -> None:
        """
        Register a job type definition.
        
        Args:
            definition: The job type definition to register
            
        Raises:
            ValueError: If a definition with the same job_type already exists
        """
        if definition.job_type in self._definitions:
            logger.warning(
                f"Overwriting existing job type definition: {definition.job_type}"
            )
        self._definitions[definition.job_type] = definition
        logger.debug(f"Registered job type: {definition.job_type}")
    
    def get(self, job_type: str) -> Optional[JobTypeDefinition]:
        """
        Get a job type definition by type identifier.
        
        Args:
            job_type: The job type identifier
            
        Returns:
            The definition, or None if not found
        """
        if not self._loaded:
            self._load_builtins()
        return self._definitions.get(job_type)
    
    def list_types(self) -> List[str]:
        """List all registered job type identifiers."""
        if not self._loaded:
            self._load_builtins()
        return list(self._definitions.keys())
    
    def list_definitions(self) -> List[JobTypeDefinition]:
        """List all registered job type definitions."""
        if not self._loaded:
            self._load_builtins()
        return list(self._definitions.values())
    
    def _load_builtins(self) -> None:
        """Load built-in job type definitions."""
        if self._loaded:
            return
        
        # Register page_classification job type
        self.register(JobTypeDefinition(
            job_type="page_classification",
            display_name="Page Classification",
            interrogation_key="page_classification_v1",
            handler_ref="src.llm.handlers.page_classification.handle",
            max_attempts=3,
            default_priority=100,
            timeout_seconds=120,
            version="1.0.0",
            description="Classify wiki pages into semantic types based on title and content signals.",
            tags=["classification", "semantic"],
        ))
        
        # Register sw_entity_facts job type
        self.register(JobTypeDefinition(
            job_type="sw_entity_facts",
            display_name="Star Wars Entity Facts Extraction",
            interrogation_key="sw_entity_facts_v1",
            handler_ref="src.llm.handlers.entity_facts.handle",
            max_attempts=3,
            default_priority=100,
            timeout_seconds=180,
            version="1.0.0",
            description="Extract structured facts from Star Wars entity wiki pages.",
            tags=["extraction", "facts", "entities"],
        ))
        
        self._loaded = True
        logger.debug(f"Loaded {len(self._definitions)} built-in job type definitions")


# Global registry instance
_registry: Optional[JobTypeRegistry] = None


def get_job_type_registry() -> JobTypeRegistry:
    """Get the global job type registry."""
    global _registry
    if _registry is None:
        _registry = JobTypeRegistry()
    return _registry


def get_job_type(job_type: str) -> Optional[JobTypeDefinition]:
    """
    Get a job type definition by type identifier.
    
    Convenience function that uses the global registry.
    
    Args:
        job_type: The job type identifier
        
    Returns:
        The definition, or None if not found
    """
    return get_job_type_registry().get(job_type)


def register_job_type(definition: JobTypeDefinition) -> None:
    """
    Register a job type definition.
    
    Convenience function that uses the global registry.
    
    Args:
        definition: The job type definition to register
    """
    get_job_type_registry().register(definition)
