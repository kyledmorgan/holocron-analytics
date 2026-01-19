"""
MediaWiki-specific discovery implementation.
"""

import logging
from typing import List, Optional

from .base import Discovery
from ..core.models import WorkItem, IngestRecord


logger = logging.getLogger(__name__)


class MediaWikiDiscovery(Discovery):
    """
    Discovery plugin for MediaWiki API responses.
    
    Extracts page links, categories, and other relationships
    from MediaWiki query results.
    """

    def __init__(
        self,
        api_url: str,
        source_name: str,
        discover_links: bool = True,
        discover_categories: bool = False,
        max_depth: Optional[int] = None,
    ):
        """
        Initialize MediaWiki discovery.
        
        Args:
            api_url: Base MediaWiki API URL
            source_name: Source name (e.g., 'wikipedia')
            discover_links: Whether to discover page links
            discover_categories: Whether to discover categories
            max_depth: Maximum discovery depth (None = unlimited)
        """
        self.api_url = api_url
        self.source_name = source_name
        self.discover_links = discover_links
        self.discover_categories = discover_categories
        self.max_depth = max_depth

    def discover(self, record: IngestRecord, parent_work_item: WorkItem) -> List[WorkItem]:
        """
        Discover new work items from a MediaWiki API response.
        
        Args:
            record: The ingestion record to analyze
            parent_work_item: The work item that produced this record
            
        Returns:
            List of new work items discovered
        """
        work_items = []
        
        # Check depth limit
        if self.max_depth is not None:
            current_depth = self._get_depth(parent_work_item)
            if current_depth >= self.max_depth:
                logger.debug(f"Max depth {self.max_depth} reached, skipping discovery")
                return work_items
        
        # Extract pages from query response
        payload = record.payload
        
        if "query" not in payload:
            return work_items
        
        query = payload["query"]
        
        # Handle 'pages' structure
        if "pages" in query:
            pages = query["pages"]
            
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    # Page doesn't exist
                    continue
                
                # Discover links
                if self.discover_links and "links" in page_data:
                    work_items.extend(
                        self._discover_links(page_data["links"], parent_work_item)
                    )
                
                # Discover categories
                if self.discover_categories and "categories" in page_data:
                    work_items.extend(
                        self._discover_categories(page_data["categories"], parent_work_item)
                    )
        
        logger.debug(f"Discovered {len(work_items)} new work items")
        return work_items

    def _discover_links(self, links: List[dict], parent: WorkItem) -> List[WorkItem]:
        """Discover work items from page links."""
        work_items = []
        
        for link in links:
            if "title" not in link:
                continue
            
            title = link["title"]
            
            # Build API URL for this page
            from urllib.parse import urlencode
            params = {
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "links",
                "pllimit": 500,
            }
            request_uri = f"{self.api_url}?{urlencode(params)}"
            
            # Create work item
            work_item = WorkItem(
                source_system="mediawiki",
                source_name=self.source_name,
                resource_type="page",
                resource_id=title,
                request_uri=request_uri,
                request_method="GET",
                priority=parent.priority + 10,  # Lower priority for discovered items
                run_id=parent.run_id,
                discovered_from=parent.work_item_id,
                metadata={"discovered_via": "links", "parent_page": parent.resource_id},
            )
            
            work_items.append(work_item)
        
        return work_items

    def _discover_categories(self, categories: List[dict], parent: WorkItem) -> List[WorkItem]:
        """Discover work items from categories."""
        work_items = []
        
        for category in categories:
            if "title" not in category:
                continue
            
            title = category["title"]
            
            # Build API URL for this category
            from urllib.parse import urlencode
            params = {
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "categories",
                "cllimit": 500,
            }
            request_uri = f"{self.api_url}?{urlencode(params)}"
            
            # Create work item
            work_item = WorkItem(
                source_system="mediawiki",
                source_name=self.source_name,
                resource_type="category",
                resource_id=title,
                request_uri=request_uri,
                request_method="GET",
                priority=parent.priority + 20,  # Even lower priority for categories
                run_id=parent.run_id,
                discovered_from=parent.work_item_id,
                metadata={"discovered_via": "categories", "parent_page": parent.resource_id},
            )
            
            work_items.append(work_item)
        
        return work_items

    def _get_depth(self, work_item: WorkItem) -> int:
        """Calculate the discovery depth of a work item."""
        depth = 0
        metadata = work_item.metadata or {}
        
        # Simple depth tracking based on metadata
        if "depth" in metadata:
            depth = metadata["depth"]
        elif work_item.discovered_from:
            # If discovered, it's at least depth 1
            depth = 1
        
        return depth

    def get_name(self) -> str:
        """Return the discovery plugin name."""
        return f"mediawiki_{self.source_name}"
