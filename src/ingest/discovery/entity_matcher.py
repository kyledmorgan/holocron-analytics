"""
Entity matching service for controlling discovery expansion.

This service determines whether discovered works should be enqueued
based on matching against known entities (franchises, topics, subjects).
"""

import logging
from typing import Dict, List, Optional, Set


logger = logging.getLogger(__name__)


class EntityMatcher:
    """
    Service for matching discovered content against known entities.
    
    This prevents "six degrees of Kevin Bacon" drift by only enqueuing
    work items that match known entities from our structured tables.
    
    Initially implemented with a config-driven list of known entities.
    Can be extended later to query from database dimension tables.
    """
    
    def __init__(
        self,
        known_entities: Optional[List[str]] = None,
        known_identifiers: Optional[Dict[str, Set[str]]] = None,
        case_sensitive: bool = False,
    ):
        """
        Initialize the entity matcher.
        
        Args:
            known_entities: List of known entity names (e.g., franchise names, topics)
            known_identifiers: Dictionary mapping identifier types to sets of known IDs
                              (e.g., {"doi": {"10.1234/..."}, "openalex_id": {"W123..."}})
            case_sensitive: Whether entity name matching should be case-sensitive
        """
        self.known_entities = set(known_entities or [])
        self.known_identifiers = known_identifiers or {}
        self.case_sensitive = case_sensitive
        
        # Normalize entity names for matching if not case-sensitive
        if not self.case_sensitive:
            self.known_entities = {e.lower() for e in self.known_entities}
        
        logger.info(
            f"EntityMatcher initialized with {len(self.known_entities)} known entities "
            f"and {sum(len(v) for v in self.known_identifiers.values())} identifiers"
        )
    
    def matches_entity(
        self,
        title: Optional[str] = None,
        identifiers: Optional[Dict[str, str]] = None,
        concepts: Optional[List[str]] = None,
    ) -> bool:
        """
        Check if a work matches any known entity.
        
        Args:
            title: Work title to check
            identifiers: Dictionary of identifiers (e.g., {"doi": "...", "openalex_id": "..."})
            concepts: List of concept names/keywords from the work
            
        Returns:
            True if the work matches a known entity, False otherwise
        """
        # Check identifier matches (most precise)
        if identifiers:
            for id_type, id_value in identifiers.items():
                if id_type in self.known_identifiers:
                    if id_value in self.known_identifiers[id_type]:
                        logger.debug(f"Match found via {id_type}: {id_value}")
                        return True
        
        # Check title matches
        if title:
            title_normalized = title if self.case_sensitive else title.lower()
            for entity in self.known_entities:
                if entity in title_normalized:
                    logger.debug(f"Match found in title: {entity}")
                    return True
        
        # Check concept matches
        if concepts:
            concepts_normalized = (
                concepts if self.case_sensitive 
                else [c.lower() for c in concepts]
            )
            for concept in concepts_normalized:
                if concept in self.known_entities:
                    logger.debug(f"Match found in concepts: {concept}")
                    return True
        
        return False
    
    def add_entity(self, entity: str) -> None:
        """
        Add a known entity at runtime.
        
        Args:
            entity: Entity name to add
        """
        entity_normalized = entity if self.case_sensitive else entity.lower()
        self.known_entities.add(entity_normalized)
        logger.debug(f"Added entity: {entity}")
    
    def add_identifier(self, id_type: str, id_value: str) -> None:
        """
        Add a known identifier at runtime.
        
        Args:
            id_type: Type of identifier (e.g., "doi", "openalex_id")
            id_value: The identifier value
        """
        if id_type not in self.known_identifiers:
            self.known_identifiers[id_type] = set()
        self.known_identifiers[id_type].add(id_value)
        logger.debug(f"Added {id_type}: {id_value}")
    
    @classmethod
    def from_config(cls, config: Dict) -> "EntityMatcher":
        """
        Create an EntityMatcher from a configuration dictionary.
        
        Expected config format:
        {
            "entities": ["Star Wars", "Star Trek", ...],
            "identifiers": {
                "doi": ["10.1234/...", ...],
                "openalex_id": ["W123...", ...]
            },
            "case_sensitive": false
        }
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configured EntityMatcher instance
        """
        entities = config.get("entities", [])
        identifiers = config.get("identifiers", {})
        case_sensitive = config.get("case_sensitive", False)
        
        # Convert identifier lists to sets
        identifiers_sets = {
            k: set(v) for k, v in identifiers.items()
        }
        
        return cls(
            known_entities=entities,
            known_identifiers=identifiers_sets,
            case_sensitive=case_sensitive,
        )
