"""
Interrogation Registry - Maps interrogation keys to definitions.

This module provides a registry for looking up interrogation definitions
by their key. Each definition includes the prompt template, output schema,
and configuration for the interrogation.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


logger = logging.getLogger(__name__)


@dataclass
class InterrogationDefinition:
    """
    Definition for an interrogation (reusable question pattern).
    
    Attributes:
        key: Unique identifier for this interrogation (e.g., 'sw_entity_facts_v1')
        name: Human-readable name
        version: Version string
        description: Description of what this interrogation extracts
        prompt_template: The prompt template with placeholders
        output_schema: JSON schema for validating output
        system_prompt: Optional system prompt to set context
        recommended_model: Recommended model for this interrogation
        recommended_temperature: Recommended temperature setting
        validator: Optional validation function for output
    """
    key: str
    name: str
    version: str
    description: str
    prompt_template: str
    output_schema: Dict[str, Any]
    system_prompt: Optional[str] = None
    recommended_model: Optional[str] = None
    recommended_temperature: float = 0.0
    validator: Optional[Callable[[Dict[str, Any]], List[str]]] = None
    
    def get_schema_for_ollama(self) -> Dict[str, Any]:
        """
        Get the schema formatted for Ollama structured output.
        
        Ollama expects the schema in the 'format' parameter of the request.
        """
        return self.output_schema
    
    def validate_output(self, output: Dict[str, Any]) -> List[str]:
        """
        Validate output against the schema.
        
        Returns a list of validation errors (empty if valid).
        """
        if self.validator:
            return self.validator(output)
        return []


class InterrogationRegistry:
    """
    Registry for interrogation definitions.
    
    Provides lookup of interrogation definitions by their key.
    Definitions can be registered programmatically or loaded from files.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._definitions: Dict[str, InterrogationDefinition] = {}
        self._loaded = False
    
    def register(self, definition: InterrogationDefinition) -> None:
        """
        Register an interrogation definition.
        
        Args:
            definition: The definition to register
        """
        self._definitions[definition.key] = definition
        logger.debug(f"Registered interrogation: {definition.key}")
    
    def get(self, key: str) -> Optional[InterrogationDefinition]:
        """
        Get an interrogation definition by key.
        
        Args:
            key: The interrogation key
            
        Returns:
            The definition, or None if not found
        """
        # Lazy load built-in definitions
        if not self._loaded:
            self._load_builtins()
        
        return self._definitions.get(key)
    
    def list_keys(self) -> List[str]:
        """List all registered interrogation keys."""
        if not self._loaded:
            self._load_builtins()
        return list(self._definitions.keys())
    
    def _load_builtins(self) -> None:
        """Load built-in interrogation definitions."""
        if self._loaded:
            return
        
        # Register sw_entity_facts_v1
        from .definitions.sw_entity_facts import create_sw_entity_facts_v1
        definition = create_sw_entity_facts_v1()
        self.register(definition)
        
        # Register page_classification_v1
        from .definitions.page_classification import create_page_classification_v1
        definition = create_page_classification_v1()
        self.register(definition)
        
        self._loaded = True
        logger.debug(f"Loaded {len(self._definitions)} built-in interrogations")


# Global registry instance
_registry: Optional[InterrogationRegistry] = None


def get_registry() -> InterrogationRegistry:
    """Get the global interrogation registry."""
    global _registry
    if _registry is None:
        _registry = InterrogationRegistry()
    return _registry


def get_interrogation(key: str) -> Optional[InterrogationDefinition]:
    """
    Get an interrogation definition by key.
    
    Convenience function that uses the global registry.
    """
    return get_registry().get(key)
