#!/usr/bin/env python3
"""
Tests for the ranked queue seeder module.

Tests core functionality of creating variant work items from inbound link rank.
"""

import json
import sys
import logging
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.analysis.ranked_queue_seeder import (
    create_ranked_work_items,
    _create_variant_work_item,
)
from ingest.core.models import WorkItem, AcquisitionVariant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_mock_rank_file(base_dir: Path, results: list) -> None:
    """Create a mock inbound link rank file for testing."""
    analysis_dir = base_dir / "mediawiki" / "wookieepedia" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    rank_data = {
        "generated_at_utc": "2025-01-01T00:00:00Z",
        "source_name": "wookieepedia",
        "files_processed": len(results),
        "results": results,
    }
    
    with open(analysis_dir / "inbound_link_rank.json", "w") as f:
        json.dump(rank_data, f)


def test_create_ranked_work_items_basic():
    """Test basic creation of ranked work items."""
    logger.info("Testing create_ranked_work_items basic functionality...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create mock rank file with 3 pages
        results = [
            {"page_id": 1, "title": "Luke Skywalker", "inbound_link_count": 100},
            {"page_id": 2, "title": "Darth Vader", "inbound_link_count": 90},
            {"page_id": 3, "title": "Yoda", "inbound_link_count": 50},
        ]
        create_mock_rank_file(base_dir, results)
        
        # Create work items
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            limit=3,
        )
        
        # Should have 6 work items (3 pages x 2 variants)
        assert len(work_items) == 6, f"Expected 6 work items, got {len(work_items)}"
        
        # Verify structure: pairs of RAW + HTML for each page
        raw_items = [w for w in work_items if w.variant == AcquisitionVariant.RAW]
        html_items = [w for w in work_items if w.variant == AcquisitionVariant.HTML]
        
        assert len(raw_items) == 3, f"Expected 3 RAW items, got {len(raw_items)}"
        assert len(html_items) == 3, f"Expected 3 HTML items, got {len(html_items)}"
        
        logger.info("✓ Basic creation works correctly")


def test_work_items_have_correct_priorities():
    """Test that work items are prioritized by rank."""
    logger.info("Testing priority assignment by rank...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create mock rank file
        results = [
            {"page_id": 1, "title": "First", "inbound_link_count": 100},
            {"page_id": 2, "title": "Second", "inbound_link_count": 50},
            {"page_id": 3, "title": "Third", "inbound_link_count": 10},
        ]
        create_mock_rank_file(base_dir, results)
        
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            limit=3,
        )
        
        # Check priorities - rank 1 should have priority 1 (highest)
        first_items = [w for w in work_items if w.resource_id == "First"]
        second_items = [w for w in work_items if w.resource_id == "Second"]
        third_items = [w for w in work_items if w.resource_id == "Third"]
        
        assert all(w.priority == 1 for w in first_items), "First page should have priority 1"
        assert all(w.priority == 2 for w in second_items), "Second page should have priority 2"
        assert all(w.priority == 3 for w in third_items), "Third page should have priority 3"
        
        # Check rank metadata
        assert all(w.rank == 1 for w in first_items), "First page should have rank 1"
        assert all(w.rank == 2 for w in second_items), "Second page should have rank 2"
        assert all(w.rank == 3 for w in third_items), "Third page should have rank 3"
        
        logger.info("✓ Priority assignment works correctly")


def test_dedupe_keys_include_variant():
    """Test that dedupe keys are unique for RAW and HTML variants."""
    logger.info("Testing dedupe key uniqueness with variants...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        results = [
            {"page_id": 1, "title": "Test Page", "inbound_link_count": 100},
        ]
        create_mock_rank_file(base_dir, results)
        
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            limit=1,
        )
        
        assert len(work_items) == 2, f"Expected 2 work items, got {len(work_items)}"
        
        # Get dedupe keys
        dedupe_keys = [w.get_dedupe_key() for w in work_items]
        
        # Keys should be unique
        assert len(set(dedupe_keys)) == 2, "Dedupe keys should be unique"
        
        # Keys should include variant
        raw_item = [w for w in work_items if w.variant == AcquisitionVariant.RAW][0]
        html_item = [w for w in work_items if w.variant == AcquisitionVariant.HTML][0]
        
        assert ":raw" in raw_item.get_dedupe_key(), "RAW dedupe key should include ':raw'"
        assert ":html" in html_item.get_dedupe_key(), "HTML dedupe key should include ':html'"
        
        logger.info("✓ Dedupe keys include variant correctly")


def test_limit_parameter():
    """Test that limit parameter is respected."""
    logger.info("Testing limit parameter...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create 10 pages
        results = [
            {"page_id": i, "title": f"Page{i}", "inbound_link_count": 100 - i}
            for i in range(10)
        ]
        create_mock_rank_file(base_dir, results)
        
        # Limit to 3
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            limit=3,
        )
        
        # Should only have 6 items (3 pages x 2 variants)
        assert len(work_items) == 6, f"Expected 6 work items with limit=3, got {len(work_items)}"
        
        # Should only have the top 3 pages
        resource_ids = set(w.resource_id for w in work_items)
        assert resource_ids == {"Page0", "Page1", "Page2"}, f"Got wrong pages: {resource_ids}"
        
        logger.info("✓ Limit parameter works correctly")


def test_require_page_id():
    """Test that require_page_id filters out pages without page_id."""
    logger.info("Testing require_page_id filter...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create pages with and without page_id
        results = [
            {"page_id": 1, "title": "HasPageId", "inbound_link_count": 100},
            {"page_id": None, "title": "NoPageId", "inbound_link_count": 90},
            {"page_id": 2, "title": "AlsoHasPageId", "inbound_link_count": 50},
        ]
        create_mock_rank_file(base_dir, results)
        
        # With require_page_id=True (default)
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            require_page_id=True,
        )
        
        # Should only have 4 items (2 pages with page_id x 2 variants)
        assert len(work_items) == 4, f"Expected 4 work items, got {len(work_items)}"
        
        # Should not include "NoPageId"
        resource_ids = set(w.resource_id for w in work_items)
        assert "NoPageId" not in resource_ids, "NoPageId should be excluded"
        
        # With require_page_id=False
        work_items_all = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            require_page_id=False,
        )
        
        # Should have 6 items (3 pages x 2 variants)
        assert len(work_items_all) == 6, f"Expected 6 work items, got {len(work_items_all)}"
        
        logger.info("✓ require_page_id filter works correctly")


def test_work_item_metadata():
    """Test that work items have correct metadata."""
    logger.info("Testing work item metadata...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        results = [
            {"page_id": 123, "title": "Luke Skywalker", "inbound_link_count": 100},
        ]
        create_mock_rank_file(base_dir, results)
        
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
        )
        
        raw_item = [w for w in work_items if w.variant == AcquisitionVariant.RAW][0]
        
        # Check metadata
        assert raw_item.metadata["page_id"] == 123
        assert raw_item.metadata["inbound_link_count"] == 100
        assert raw_item.metadata["rank"] == 1
        assert raw_item.metadata["variant"] == "raw"
        
        # Check source fields
        assert raw_item.source_system == "mediawiki"
        assert raw_item.source_name == "wookieepedia"
        assert raw_item.resource_type == "content"
        assert raw_item.resource_id == "Luke Skywalker"
        
        # Check request URI contains expected params
        assert "action=query" in raw_item.request_uri
        assert "pageids=123" in raw_item.request_uri
        
        logger.info("✓ Work item metadata is correct")


def test_html_variant_request_uri():
    """Test that HTML variant uses parse action."""
    logger.info("Testing HTML variant request URI...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        results = [
            {"page_id": 456, "title": "Darth Vader", "inbound_link_count": 90},
        ]
        create_mock_rank_file(base_dir, results)
        
        work_items = create_ranked_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
        )
        
        html_item = [w for w in work_items if w.variant == AcquisitionVariant.HTML][0]
        
        # Check request URI uses parse action
        assert "action=parse" in html_item.request_uri
        assert "pageid=456" in html_item.request_uri
        
        logger.info("✓ HTML variant request URI is correct")


def main():
    """Run all tests."""
    logger.info("Starting ranked queue seeder tests...")
    logger.info("=" * 60)
    
    try:
        test_create_ranked_work_items_basic()
        test_work_items_have_correct_priorities()
        test_dedupe_keys_include_variant()
        test_limit_parameter()
        test_require_page_id()
        test_work_item_metadata()
        test_html_variant_request_uri()
        
        logger.info("=" * 60)
        logger.info("✓ All ranked queue seeder tests passed!")
        return 0
        
    except Exception as e:
        logger.exception(f"✗ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
