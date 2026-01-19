"""
OpenAlex-specific discovery implementation.

Extracts references, citations, and related works from OpenAlex API responses.
"""

import logging
from typing import List, Optional, Dict, Any

from .base import Discovery
from .entity_matcher import EntityMatcher
from ..core.models import WorkItem, IngestRecord


logger = logging.getLogger(__name__)


class OpenAlexDiscovery(Discovery):
    """
    Discovery plugin for OpenAlex API responses.
    
    Extracts referenced works (citations) from OpenAlex Work payloads
    and creates new work items with controlled expansion based on:
    - Maximum depth (distance from seed)
    - Entity matching (only works that match known entities)
    - Deduplication (handled by state store)
    """
    
    def __init__(
        self,
        entity_matcher: EntityMatcher,
        max_depth: int = 1,
        discover_references: bool = True,
        discover_related: bool = False,
    ):
        """
        Initialize OpenAlex discovery.
        
        Args:
            entity_matcher: EntityMatcher for controlling expansion
            max_depth: Maximum discovery depth (0 = seeds only, 1 = first-degree)
            discover_references: Whether to discover referenced works (citations)
            discover_related: Whether to discover related works (if available)
        """
        self.entity_matcher = entity_matcher
        self.max_depth = max_depth
        self.discover_references = discover_references
        self.discover_related = discover_related
        
        logger.info(
            f"OpenAlexDiscovery initialized: max_depth={max_depth}, "
            f"discover_references={discover_references}, "
            f"discover_related={discover_related}"
        )
    
    def discover(self, record: IngestRecord, parent_work_item: WorkItem) -> List[WorkItem]:
        """
        Discover new work items from an OpenAlex API response.
        
        Args:
            record: The ingestion record to analyze
            parent_work_item: The work item that produced this record
            
        Returns:
            List of new work items discovered
        """
        work_items = []
        
        # Check depth limit
        current_depth = self._get_depth(parent_work_item)
        if current_depth >= self.max_depth:
            logger.debug(f"Max depth {self.max_depth} reached, skipping discovery")
            return work_items
        
        payload = record.payload
        
        # OpenAlex single work response has work data at root
        # OpenAlex search/list response has works in "results" array
        works_to_process = []
        
        if "results" in payload:
            # List/search response
            works_to_process = payload.get("results", [])
        elif "id" in payload or "doi" in payload:
            # Single work response
            works_to_process = [payload]
        
        # Process each work
        for work_data in works_to_process:
            # Only discover references from works that match known entities
            # This prevents "six degrees of Kevin Bacon" drift
            if not self._matches_known_entity(work_data):
                logger.debug(
                    f"Skipping reference discovery for work {work_data.get('id', 'unknown')}: "
                    "does not match known entities"
                )
                continue
            
            # Extract referenced works
            if self.discover_references:
                work_items.extend(
                    self._discover_references(work_data, parent_work_item, current_depth)
                )
            
            # Extract related works (if enabled and available)
            if self.discover_related:
                work_items.extend(
                    self._discover_related(work_data, parent_work_item, current_depth)
                )
        
        logger.debug(f"Discovered {len(work_items)} new work items")
        return work_items
    
    def _discover_references(
        self,
        work_data: Dict[str, Any],
        parent: WorkItem,
        current_depth: int,
    ) -> List[WorkItem]:
        """
        Discover work items from referenced works (citations).
        
        Args:
            work_data: OpenAlex work data
            parent: Parent work item
            current_depth: Current discovery depth
            
        Returns:
            List of new work items
        """
        work_items = []
        
        # OpenAlex provides referenced_works as a list of OpenAlex IDs
        referenced_works = work_data.get("referenced_works", [])
        
        if not referenced_works:
            return work_items
        
        logger.debug(f"Found {len(referenced_works)} referenced works")
        
        for ref_id in referenced_works:
            # Extract OpenAlex ID (format: https://openalex.org/W123456)
            if not ref_id or not isinstance(ref_id, str):
                continue
            
            # Get the ID part (e.g., W123456)
            openalex_id = ref_id.split("/")[-1] if "/" in ref_id else ref_id
            
            # For initial discovery, we don't have full metadata yet
            # We'll fetch the work first, then decide if we should continue
            # For now, create work item for fetching
            request_uri = f"https://api.openalex.org/works/{openalex_id}"
            
            # Build work item
            work_item = WorkItem(
                source_system="openalex",
                source_name="openalex",
                resource_type="work",
                resource_id=openalex_id,
                request_uri=request_uri,
                request_method="GET",
                priority=parent.priority + 10,  # Lower priority for discovered items
                run_id=parent.run_id,
                discovered_from=parent.work_item_id,
                metadata={
                    "discovered_via": "references",
                    "parent_work": parent.resource_id,
                    "depth": current_depth + 1,
                    "openalex_id": openalex_id,
                },
            )
            
            work_items.append(work_item)
        
        # Apply entity matching filter
        # For referenced works, we only have IDs initially, so we'll enqueue them
        # and let the next processing cycle determine if they should continue expanding
        # This is acceptable because state store will dedupe, and we'll check entity
        # matching on the next round
        
        return work_items
    
    def _discover_related(
        self,
        work_data: Dict[str, Any],
        parent: WorkItem,
        current_depth: int,
    ) -> List[WorkItem]:
        """
        Discover work items from related works.
        
        Args:
            work_data: OpenAlex work data
            parent: Parent work item
            current_depth: Current discovery depth
            
        Returns:
            List of new work items
        """
        # Related works discovery can be implemented when OpenAlex provides
        # an explicit "related_works" endpoint or field
        # For now, return empty list
        return []
    
    def _matches_known_entity(self, work_data: Dict[str, Any]) -> bool:
        """
        Check if a work matches a known entity.
        
        This method filters which works should have their references discovered,
        preventing unbounded expansion ("six degrees of Kevin Bacon" drift).
        Only works matching known entities will have their references extracted.
        
        Args:
            work_data: OpenAlex work data
            
        Returns:
            True if matches, False otherwise
        """
        # Extract relevant fields for matching
        title = work_data.get("title")
        display_name = work_data.get("display_name")
        
        # Extract identifiers
        identifiers = {}
        if "doi" in work_data and work_data["doi"]:
            doi = work_data["doi"]
            # Clean DOI (remove https://doi.org/ prefix if present)
            if doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")
            identifiers["doi"] = doi
        
        if "id" in work_data:
            openalex_id = work_data["id"]
            # Extract ID part
            if "/" in openalex_id:
                openalex_id = openalex_id.split("/")[-1]
            identifiers["openalex_id"] = openalex_id
        
        # Extract concepts (topics/keywords)
        concepts = []
        if "concepts" in work_data:
            for concept in work_data.get("concepts", []):
                if "display_name" in concept:
                    concepts.append(concept["display_name"])
        
        # Check title or display name
        check_title = title or display_name
        
        return self.entity_matcher.matches_entity(
            title=check_title,
            identifiers=identifiers,
            concepts=concepts,
        )
    
    def _get_depth(self, work_item: WorkItem) -> int:
        """
        Calculate the discovery depth of a work item.
        
        Args:
            work_item: The work item
            
        Returns:
            Depth level (0 = seed, 1 = first-degree, etc.)
        """
        metadata = work_item.metadata or {}
        
        # Check metadata for explicit depth
        if "depth" in metadata:
            return metadata["depth"]
        
        # If discovered from another item, it's at least depth 1
        if work_item.discovered_from:
            return 1
        
        # Otherwise, it's a seed (depth 0)
        return 0
    
    def get_name(self) -> str:
        """Return the discovery plugin name."""
        return "openalex"
