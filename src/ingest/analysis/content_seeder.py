"""
Content Seeder for MediaWiki pages.

Creates work items for fetching page content (raw wikitext and HTML)
prioritized by inbound link count.
"""

import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

from ..core.models import WorkItem
from ..analysis.inbound_link_analyzer import load_inbound_rank

logger = logging.getLogger(__name__)


def create_content_work_items(
    source_name: str = "wookieepedia",
    api_url: str = "https://starwars.fandom.com/api.php",
    data_lake_base: Path = Path("W:/data_lake"),
    limit: Optional[int] = None,
    priority: int = 1,
    run_id: Optional[str] = None,
) -> List[WorkItem]:
    """
    Create work items for fetching page content based on inbound link rank.
    
    Creates two work items per page:
    - One for raw wikitext content (resource_type: content_raw)
    - One for HTML content (resource_type: content_html)
    
    Pages are prioritized by inbound link count (highest first).
    Only pages with known page_id are included.
    
    Args:
        source_name: Name of the MediaWiki source
        api_url: Base API URL for the MediaWiki instance
        data_lake_base: Base path to data lake
        limit: Maximum number of pages to create work items for (None = all)
        priority: Priority level for the work items (lower = higher priority)
        run_id: Optional run ID to associate with work items
        
    Returns:
        List of WorkItem objects ready to be enqueued
        
    Raises:
        FileNotFoundError: If inbound link rank file doesn't exist
    """
    logger.info(f"Loading inbound link rank for {source_name}...")
    
    try:
        ranked_pages = load_inbound_rank(
            source_name=source_name,
            data_lake_base=data_lake_base,
        )
    except FileNotFoundError as e:
        logger.error(f"Cannot create content work items: {e}")
        raise
    
    # Filter to pages with known page_id
    pages_with_id = [p for p in ranked_pages if p.get("page_id") is not None]
    logger.info(f"Found {len(pages_with_id)} pages with known page_id")
    
    # Apply limit
    if limit is not None:
        pages_with_id = pages_with_id[:limit]
        logger.info(f"Limited to top {limit} pages")
    
    work_items = []
    
    for page in pages_with_id:
        page_id = page["page_id"]
        title = page["title"]
        inbound_count = page.get("inbound_link_count", 0)
        
        # Create work item for raw wikitext content
        raw_params = {
            "action": "query",
            "format": "json",
            "pageids": str(page_id),
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "formatversion": "2",
        }
        raw_uri = f"{api_url}?{urlencode(raw_params)}"
        
        raw_work_item = WorkItem(
            source_system="mediawiki",
            source_name=source_name,
            resource_type="content_raw",
            resource_id=title,
            request_uri=raw_uri,
            request_method="GET",
            priority=priority,
            run_id=run_id,
            metadata={
                "page_id": page_id,
                "inbound_link_count": inbound_count,
                "content_type": "raw",
            },
        )
        work_items.append(raw_work_item)
        
        # Create work item for HTML content
        html_params = {
            "action": "parse",
            "format": "json",
            "pageid": str(page_id),
            "prop": "text",
            "formatversion": "2",
        }
        html_uri = f"{api_url}?{urlencode(html_params)}"
        
        html_work_item = WorkItem(
            source_system="mediawiki",
            source_name=source_name,
            resource_type="content_html",
            resource_id=title,
            request_uri=html_uri,
            request_method="GET",
            priority=priority,
            run_id=run_id,
            metadata={
                "page_id": page_id,
                "inbound_link_count": inbound_count,
                "content_type": "html",
            },
        )
        work_items.append(html_work_item)
    
    logger.info(f"Created {len(work_items)} work items ({len(pages_with_id)} pages x 2 content types)")
    return work_items


def seed_content_queue(
    state_store,
    source_name: str = "wookieepedia",
    api_url: str = "https://starwars.fandom.com/api.php",
    data_lake_base: Path = Path("W:/data_lake"),
    limit: Optional[int] = None,
    priority: int = 1,
    run_id: Optional[str] = None,
) -> int:
    """
    Create and enqueue content work items to the state store.
    
    Convenience function that creates work items and enqueues them,
    handling deduplication automatically.
    
    Args:
        state_store: The state store to enqueue items to
        source_name: Name of the MediaWiki source
        api_url: Base API URL for the MediaWiki instance
        data_lake_base: Base path to data lake
        limit: Maximum number of pages to process
        priority: Priority level for the work items
        run_id: Optional run ID
        
    Returns:
        Number of work items successfully enqueued
    """
    work_items = create_content_work_items(
        source_name=source_name,
        api_url=api_url,
        data_lake_base=data_lake_base,
        limit=limit,
        priority=priority,
        run_id=run_id,
    )
    
    enqueued = 0
    for item in work_items:
        if state_store.enqueue(item):
            enqueued += 1
    
    logger.info(f"Enqueued {enqueued} new content work items (skipped {len(work_items) - enqueued} duplicates)")
    return enqueued
