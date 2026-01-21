"""
Inbound Link Analyzer for MediaWiki page artifacts.

Scans existing page JSON artifacts and produces a consolidated report of
inbound link counts for each page, sorted by count descending.

This supports prioritizing content fetching for the most-referenced pages.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class InboundLinkAnalyzer:
    """
    Analyzes MediaWiki page artifacts to count inbound links.
    
    Scans all page JSON artifacts in a source directory and produces:
    - A mapping of title -> page_id from known pages
    - A count of how many times each title appears in other pages' links[] arrays
    
    The final output is a JSON file with page_id, title, and inbound_link_count
    sorted by inbound_link_count descending.
    
    Design decision: Titles that appear in links[] but have no corresponding
    local page artifact are INCLUDED in the output with page_id = null.
    This allows identifying popular pages that haven't been crawled yet.
    """
    
    def __init__(
        self,
        source_name: str = "wookieepedia",
        data_lake_base: Path = Path("local/data_lake"),
    ):
        """
        Initialize the analyzer.
        
        Args:
            source_name: Name of the MediaWiki source (e.g., 'wookieepedia')
            data_lake_base: Base path to the data lake directory
        """
        self.source_name = source_name
        self.data_lake_base = Path(data_lake_base)
        
        # Computed paths
        self.page_dir = self.data_lake_base / "mediawiki" / source_name / "page"
        self.analysis_dir = self.data_lake_base / "mediawiki" / source_name / "analysis"
        
        # Internal state
        self._title_to_page_id: Dict[str, int] = {}
        self._inbound_counts: Dict[str, int] = defaultdict(int)
        self._files_processed: int = 0
        self._links_counted: int = 0
    
    def analyze(self) -> List[Dict[str, Any]]:
        """
        Run the analysis on all page artifacts.
        
        Returns:
            List of dicts with page_id, title, inbound_link_count sorted by count desc.
        """
        logger.info(f"Starting inbound link analysis for source: {self.source_name}")
        logger.info(f"Scanning page artifacts in: {self.page_dir}")
        
        if not self.page_dir.exists():
            logger.warning(f"Page directory does not exist: {self.page_dir}")
            return []
        
        # Phase 1: Scan all files to build title->page_id map and count inbound links
        self._scan_page_artifacts()
        
        # Phase 2: Build the output list
        results = self._build_results()
        
        logger.info(
            f"Analysis complete. Processed {self._files_processed} files, "
            f"counted {self._links_counted} links, found {len(results)} unique titles."
        )
        
        return results
    
    def analyze_and_save(
        self,
        output_filename: str = "inbound_link_rank.json",
    ) -> Path:
        """
        Run analysis and save results to a JSON file.
        
        Args:
            output_filename: Name of the output file
            
        Returns:
            Path to the saved file
        """
        results = self.analyze()
        
        # Ensure output directory exists
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = self.analysis_dir / output_filename
        
        # Build output envelope
        output = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_name": self.source_name,
            "files_processed": self._files_processed,
            "links_counted": self._links_counted,
            "unique_titles": len(results),
            "results": results,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved inbound link rank to: {output_path}")
        return output_path
    
    def _scan_page_artifacts(self) -> None:
        """Scan all page JSON files to extract titles, page_ids, and links."""
        json_files = list(self.page_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for json_path in json_files:
            try:
                self._process_page_file(json_path)
                self._files_processed += 1
            except Exception as e:
                logger.warning(f"Failed to process {json_path}: {e}")
    
    def _process_page_file(self, json_path: Path) -> None:
        """
        Process a single page artifact file.
        
        Extracts:
        - The page's own title and page_id
        - All outbound link titles from links[]
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        payload = data.get("payload", {})
        query = payload.get("query", {})
        pages = query.get("pages", {})
        
        # In formatversion=1 (default), pages is a dict keyed by page_id string
        # In formatversion=2, pages is a list
        if isinstance(pages, dict):
            for page_id_str, page_data in pages.items():
                self._extract_page_info(page_id_str, page_data)
        elif isinstance(pages, list):
            # formatversion=2 style
            for page_data in pages:
                page_id = page_data.get("pageid")
                self._extract_page_info(str(page_id) if page_id else "-1", page_data)
    
    def _extract_page_info(self, page_id_str: str, page_data: Dict[str, Any]) -> None:
        """
        Extract page info and count outbound links.
        
        Args:
            page_id_str: String representation of page ID (may be "-1" for missing)
            page_data: The page data dictionary from the API response
        """
        # Skip missing pages
        if page_id_str == "-1":
            return
        
        title = page_data.get("title")
        if not title:
            return
        
        # Try to get numeric page_id
        page_id = page_data.get("pageid")
        if page_id is None:
            try:
                page_id = int(page_id_str)
            except ValueError:
                page_id = None
        
        # Store title -> page_id mapping (case-sensitive)
        if title not in self._title_to_page_id and page_id is not None:
            self._title_to_page_id[title] = page_id
        
        # Count outbound links as inbound for the linked pages
        links = page_data.get("links", [])
        for link in links:
            link_title = link.get("title")
            if link_title:
                # Case-sensitive counting as per requirements
                self._inbound_counts[link_title] += 1
                self._links_counted += 1
    
    def _build_results(self) -> List[Dict[str, Any]]:
        """
        Build the final results list sorted by inbound count descending.
        
        Returns:
            List of dicts with page_id, title, inbound_link_count
        """
        results = []
        
        # Get all unique titles (from both page artifacts and link targets)
        all_titles = set(self._title_to_page_id.keys()) | set(self._inbound_counts.keys())
        
        for title in all_titles:
            # page_id is null if we don't have a local artifact for this title
            page_id = self._title_to_page_id.get(title)
            inbound_count = self._inbound_counts.get(title, 0)
            
            results.append({
                "page_id": page_id,
                "title": title,
                "inbound_link_count": inbound_count,
            })
        
        # Sort by inbound_link_count descending, then by title for stability
        results.sort(key=lambda x: (-x["inbound_link_count"], x["title"]))
        
        return results
    
    def get_top_pages(
        self,
        limit: int = 100,
        require_page_id: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get the top N pages by inbound link count.
        
        Args:
            limit: Maximum number of pages to return
            require_page_id: If True, only return pages with known page_id
            
        Returns:
            List of page info dicts
        """
        results = self.analyze()
        
        if require_page_id:
            results = [r for r in results if r["page_id"] is not None]
        
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get analysis statistics.
        
        Returns:
            Dict with files_processed, links_counted, known_pages, etc.
        """
        return {
            "files_processed": self._files_processed,
            "links_counted": self._links_counted,
            "known_pages": len(self._title_to_page_id),
            "unique_linked_titles": len(self._inbound_counts),
        }


def load_inbound_rank(
    source_name: str = "wookieepedia",
    data_lake_base: Path = Path("local/data_lake"),
    filename: str = "inbound_link_rank.json",
) -> List[Dict[str, Any]]:
    """
    Load a previously saved inbound link rank file.
    
    Args:
        source_name: Name of the MediaWiki source
        data_lake_base: Base path to data lake
        filename: Name of the rank file
        
    Returns:
        List of page info dicts sorted by inbound count desc
        
    Raises:
        FileNotFoundError: If the rank file doesn't exist
    """
    rank_path = Path(data_lake_base) / "mediawiki" / source_name / "analysis" / filename
    
    if not rank_path.exists():
        raise FileNotFoundError(f"Inbound link rank file not found: {rank_path}")
    
    with open(rank_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("results", [])
