"""
Rank-Driven Queue Seeder for MediaWiki content acquisition.

Creates work items for fetching page content (raw and HTML variants)
prioritized by inbound link rank. This is the second-phase retrieval
that follows the initial crawl and link analysis.

Features:
- Reads inbound link rank JSON artifact
- Creates 2 work items per resource (RAW + HTML variants)
- Prioritizes by inbound link count (descending rank)
- Handles deduplication via composite dedupe key (includes variant)
- Supports limiting to top N resources
"""

import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

from ..core.models import WorkItem, AcquisitionVariant
from ..analysis.inbound_link_analyzer import load_inbound_rank

logger = logging.getLogger(__name__)


def create_ranked_work_items(
    source_name: str = "wookieepedia",
    api_url: str = "https://starwars.fandom.com/api.php",
    data_lake_base: Path = Path("W:/data_lake"),
    limit: int = 50000,
    run_id: Optional[str] = None,
    require_page_id: bool = True,
) -> List[WorkItem]:
    """
    Create work items from inbound link rank for targeted second-phase retrieval.
    
    Creates two work items per ranked resource:
    - One for RAW variant (wikitext/source content via API)
    - One for HTML variant (rendered HTML via parse action)
    
    Work items are ordered by inbound link rank (descending), with the
    highest-ranked resources getting the lowest priority numbers (processed first).
    
    Args:
        source_name: Name of the MediaWiki source (e.g., 'wookieepedia')
        api_url: Base API URL for the MediaWiki instance
        data_lake_base: Base path to data lake where rank file is stored
        limit: Maximum number of resources to process (default 50,000)
        run_id: Optional run ID to associate with work items
        require_page_id: If True, skip resources without known page_id
        
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
        logger.error(f"Cannot create ranked work items: {e}")
        raise
    
    # Filter to pages with known page_id if required
    if require_page_id:
        pages = [p for p in ranked_pages if p.get("page_id") is not None]
        logger.info(f"Found {len(pages)} pages with known page_id (filtered from {len(ranked_pages)})")
    else:
        pages = ranked_pages
        logger.info(f"Found {len(pages)} total pages in rank file")
    
    # Apply limit
    if limit and len(pages) > limit:
        pages = pages[:limit]
        logger.info(f"Limited to top {limit} pages by inbound link rank")
    
    work_items = []
    
    for rank, page in enumerate(pages, start=1):
        page_id = page.get("page_id")
        title = page["title"]
        inbound_count = page.get("inbound_link_count", 0)
        
        # Priority is based on rank position (rank 1 = priority 1, highest priority)
        priority = rank
        
        # Common metadata for both variants
        base_metadata = {
            "page_id": page_id,
            "inbound_link_count": inbound_count,
            "rank": rank,
        }
        
        # Create RAW variant work item
        raw_work_item = _create_variant_work_item(
            source_name=source_name,
            api_url=api_url,
            page_id=page_id,
            title=title,
            variant=AcquisitionVariant.RAW,
            priority=priority,
            rank=rank,
            run_id=run_id,
            metadata=base_metadata,
        )
        work_items.append(raw_work_item)
        
        # Create HTML variant work item
        html_work_item = _create_variant_work_item(
            source_name=source_name,
            api_url=api_url,
            page_id=page_id,
            title=title,
            variant=AcquisitionVariant.HTML,
            priority=priority,
            rank=rank,
            run_id=run_id,
            metadata=base_metadata,
        )
        work_items.append(html_work_item)
    
    logger.info(
        f"Created {len(work_items)} work items "
        f"({len(pages)} pages x 2 variants)"
    )
    
    return work_items


def _create_variant_work_item(
    source_name: str,
    api_url: str,
    page_id: Optional[int],
    title: str,
    variant: AcquisitionVariant,
    priority: int,
    rank: int,
    run_id: Optional[str],
    metadata: dict,
) -> WorkItem:
    """
    Create a single work item for a specific variant.
    
    Args:
        source_name: Name of the MediaWiki source
        api_url: Base API URL
        page_id: MediaWiki page ID
        title: Page title
        variant: RAW or HTML variant
        priority: Priority level (lower = higher priority)
        rank: Inbound link rank
        run_id: Optional run ID
        metadata: Base metadata dict
        
    Returns:
        Configured WorkItem
    """
    # Build request URI based on variant
    if variant == AcquisitionVariant.RAW:
        # Use query action with revisions to get raw wikitext
        params = {
            "action": "query",
            "format": "json",
            "pageids": str(page_id) if page_id else None,
            "titles": title if page_id is None else None,
            "prop": "revisions",
            "rvprop": "content|ids|timestamp",
            "rvslots": "main",
            "formatversion": "2",
        }
        # Remove None params
        params = {k: v for k, v in params.items() if v is not None}
        resource_type = "content"
    else:
        # Use parse action to get rendered HTML
        params = {
            "action": "parse",
            "format": "json",
            "pageid": str(page_id) if page_id else None,
            "page": title if page_id is None else None,
            "prop": "text|displaytitle|categories|sections",
            "formatversion": "2",
        }
        # Remove None params
        params = {k: v for k, v in params.items() if v is not None}
        resource_type = "content"
    
    request_uri = f"{api_url}?{urlencode(params)}"
    
    # Copy metadata and add variant-specific info
    item_metadata = metadata.copy()
    item_metadata["variant"] = variant.value
    
    return WorkItem(
        source_system="mediawiki",
        source_name=source_name,
        resource_type=resource_type,
        resource_id=title,
        request_uri=request_uri,
        request_method="GET",
        priority=priority,
        run_id=run_id,
        metadata=item_metadata,
        variant=variant,
        rank=rank,
    )


def seed_ranked_queue(
    state_store,
    source_name: str = "wookieepedia",
    api_url: str = "https://starwars.fandom.com/api.php",
    data_lake_base: Path = Path("W:/data_lake"),
    limit: int = 50000,
    run_id: Optional[str] = None,
    require_page_id: bool = True,
) -> dict:
    """
    Create and enqueue ranked work items to the state store.
    
    Convenience function that creates work items from rank file and
    enqueues them, handling deduplication automatically.
    
    Args:
        state_store: The state store to enqueue items to
        source_name: Name of the MediaWiki source
        api_url: Base API URL for the MediaWiki instance
        data_lake_base: Base path to data lake
        limit: Maximum number of resources to process
        run_id: Optional run ID
        require_page_id: If True, skip resources without known page_id
        
    Returns:
        Dictionary with stats:
        - total_created: Total work items created
        - enqueued: Number of items successfully enqueued
        - skipped_duplicates: Number of items skipped due to deduplication
    """
    work_items = create_ranked_work_items(
        source_name=source_name,
        api_url=api_url,
        data_lake_base=data_lake_base,
        limit=limit,
        run_id=run_id,
        require_page_id=require_page_id,
    )
    
    enqueued = 0
    for item in work_items:
        if state_store.enqueue(item):
            enqueued += 1
    
    skipped = len(work_items) - enqueued
    
    logger.info(
        f"Enqueued {enqueued} ranked work items "
        f"(skipped {skipped} duplicates)"
    )
    
    return {
        "total_created": len(work_items),
        "enqueued": enqueued,
        "skipped_duplicates": skipped,
    }


def get_queue_completeness_stats(
    state_store,
    source_name: str = "wookieepedia",
) -> dict:
    """
    Get statistics on queue completeness for ranked resources.
    
    Checks how many resources have both RAW and HTML work items,
    and their current status.
    
    Args:
        state_store: The state store to query
        source_name: Name of the MediaWiki source
        
    Returns:
        Dictionary with completeness stats
    """
    # Get all work items for this source
    all_items = state_store.get_known_resources(
        source_system="mediawiki",
        source_name=source_name,
    )
    
    # Group by resource_id
    by_resource = {}
    for item in all_items:
        rid = item.resource_id
        if rid not in by_resource:
            by_resource[rid] = {"raw": None, "html": None}
        
        if item.variant:
            by_resource[rid][item.variant.value] = item.status.value
    
    # Count resources with both variants
    complete = 0
    raw_only = 0
    html_only = 0
    both_completed = 0
    
    for rid, variants in by_resource.items():
        has_raw = variants.get("raw") is not None
        has_html = variants.get("html") is not None
        
        if has_raw and has_html:
            complete += 1
            if variants["raw"] == "completed" and variants["html"] == "completed":
                both_completed += 1
        elif has_raw:
            raw_only += 1
        elif has_html:
            html_only += 1
    
    return {
        "total_resources": len(by_resource),
        "with_both_variants": complete,
        "both_variants_completed": both_completed,
        "raw_only": raw_only,
        "html_only": html_only,
    }
