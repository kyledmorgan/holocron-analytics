#!/usr/bin/env python3
"""
Tests for the inbound link analyzer and content seeder.

Tests core functionality without requiring external APIs or the actual data lake.
"""

import json
import sys
import logging
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.analysis.inbound_link_analyzer import InboundLinkAnalyzer, load_inbound_rank
from ingest.analysis.content_seeder import create_content_work_items
from ingest.core.models import WorkItem


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_mock_page_artifact(
    page_id: int,
    title: str,
    links: list,
) -> dict:
    """Create a mock page artifact JSON structure."""
    return {
        "ingest_id": f"test-{page_id}",
        "source_system": "mediawiki",
        "source_name": "wookieepedia",
        "resource_type": "page",
        "resource_id": title,
        "request_uri": f"https://starwars.fandom.com/api.php?titles={title}",
        "request_method": "GET",
        "status_code": 200,
        "fetched_at_utc": "2025-01-01T00:00:00Z",
        "payload": {
            "query": {
                "pages": {
                    str(page_id): {
                        "pageid": page_id,
                        "title": title,
                        "links": [{"title": link} for link in links],
                    }
                }
            }
        },
    }


def test_inbound_link_analyzer():
    """Test the InboundLinkAnalyzer with mock data."""
    logger.info("Testing InboundLinkAnalyzer...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup mock data lake structure
        base_dir = Path(tmpdir)
        page_dir = base_dir / "mediawiki" / "wookieepedia" / "page"
        page_dir.mkdir(parents=True)
        
        # Create mock page artifacts
        # Page 1: Star Wars -> links to Luke Skywalker, Darth Vader
        artifact1 = create_mock_page_artifact(
            page_id=1,
            title="Star Wars",
            links=["Luke Skywalker", "Darth Vader", "The Force"],
        )
        with open(page_dir / "Star_Wars_20250101_000000_test1.json", "w") as f:
            json.dump(artifact1, f)
        
        # Page 2: Luke Skywalker -> links to Darth Vader, Yoda
        artifact2 = create_mock_page_artifact(
            page_id=2,
            title="Luke Skywalker",
            links=["Darth Vader", "Yoda", "The Force"],
        )
        with open(page_dir / "Luke_Skywalker_20250101_000000_test2.json", "w") as f:
            json.dump(artifact2, f)
        
        # Page 3: Darth Vader -> links to Luke Skywalker
        artifact3 = create_mock_page_artifact(
            page_id=3,
            title="Darth Vader",
            links=["Luke Skywalker", "The Empire"],
        )
        with open(page_dir / "Darth_Vader_20250101_000000_test3.json", "w") as f:
            json.dump(artifact3, f)
        
        # Run analysis
        analyzer = InboundLinkAnalyzer(
            source_name="wookieepedia",
            data_lake_base=base_dir,
        )
        
        results = analyzer.analyze()
        
        # Verify results
        assert len(results) > 0, "Should have results"
        
        # Find specific entries
        by_title = {r["title"]: r for r in results}
        
        # Darth Vader should have inbound count of 2 (from Star Wars and Luke Skywalker)
        assert "Darth Vader" in by_title
        assert by_title["Darth Vader"]["inbound_link_count"] == 2
        assert by_title["Darth Vader"]["page_id"] == 3
        
        # Luke Skywalker should have inbound count of 2 (from Star Wars and Darth Vader)
        assert "Luke Skywalker" in by_title
        assert by_title["Luke Skywalker"]["inbound_link_count"] == 2
        assert by_title["Luke Skywalker"]["page_id"] == 2
        
        # The Force should have inbound count of 2 but no page_id (not crawled)
        assert "The Force" in by_title
        assert by_title["The Force"]["inbound_link_count"] == 2
        assert by_title["The Force"]["page_id"] is None
        
        # Star Wars has no inbound links (no one links to it)
        assert "Star Wars" in by_title
        assert by_title["Star Wars"]["inbound_link_count"] == 0
        assert by_title["Star Wars"]["page_id"] == 1
        
        # Yoda has 1 inbound link
        assert "Yoda" in by_title
        assert by_title["Yoda"]["inbound_link_count"] == 1
        
        # Verify sorting (highest first)
        counts = [r["inbound_link_count"] for r in results]
        assert counts == sorted(counts, reverse=True), "Results should be sorted by count desc"
        
        # Test stats
        stats = analyzer.get_stats()
        assert stats["files_processed"] == 3
        assert stats["known_pages"] == 3  # 3 pages have page_ids
        
        logger.info("✓ InboundLinkAnalyzer works correctly")


def test_analyze_and_save():
    """Test saving analysis results to file."""
    logger.info("Testing analyze_and_save...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup mock data
        base_dir = Path(tmpdir)
        page_dir = base_dir / "mediawiki" / "wookieepedia" / "page"
        page_dir.mkdir(parents=True)
        
        artifact = create_mock_page_artifact(
            page_id=1,
            title="Test Page",
            links=["Other Page"],
        )
        with open(page_dir / "test_20250101_000000_test.json", "w") as f:
            json.dump(artifact, f)
        
        # Run analysis and save
        analyzer = InboundLinkAnalyzer(
            source_name="wookieepedia",
            data_lake_base=base_dir,
        )
        
        output_path = analyzer.analyze_and_save()
        
        # Verify file was created
        assert output_path.exists()
        
        # Load and verify content
        with open(output_path, "r") as f:
            data = json.load(f)
        
        assert "generated_at_utc" in data
        assert "results" in data
        assert data["source_name"] == "wookieepedia"
        assert data["files_processed"] == 1
        
        logger.info("✓ analyze_and_save works correctly")


def test_load_inbound_rank():
    """Test loading saved inbound rank file."""
    logger.info("Testing load_inbound_rank...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        analysis_dir = base_dir / "mediawiki" / "wookieepedia" / "analysis"
        analysis_dir.mkdir(parents=True)
        
        # Create mock rank file
        rank_data = {
            "generated_at_utc": "2025-01-01T00:00:00Z",
            "source_name": "wookieepedia",
            "files_processed": 10,
            "results": [
                {"page_id": 1, "title": "Luke Skywalker", "inbound_link_count": 100},
                {"page_id": 2, "title": "Darth Vader", "inbound_link_count": 90},
            ],
        }
        
        with open(analysis_dir / "inbound_link_rank.json", "w") as f:
            json.dump(rank_data, f)
        
        # Load and verify
        results = load_inbound_rank(
            source_name="wookieepedia",
            data_lake_base=base_dir,
        )
        
        assert len(results) == 2
        assert results[0]["title"] == "Luke Skywalker"
        assert results[0]["inbound_link_count"] == 100
        
        logger.info("✓ load_inbound_rank works correctly")


def test_create_content_work_items():
    """Test creating content work items from inbound rank."""
    logger.info("Testing create_content_work_items...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        analysis_dir = base_dir / "mediawiki" / "wookieepedia" / "analysis"
        analysis_dir.mkdir(parents=True)
        
        # Create mock rank file with pages
        rank_data = {
            "generated_at_utc": "2025-01-01T00:00:00Z",
            "source_name": "wookieepedia",
            "files_processed": 10,
            "results": [
                {"page_id": 123, "title": "Luke Skywalker", "inbound_link_count": 100},
                {"page_id": 456, "title": "Darth Vader", "inbound_link_count": 90},
                {"page_id": None, "title": "Unknown Page", "inbound_link_count": 50},  # No page_id
            ],
        }
        
        with open(analysis_dir / "inbound_link_rank.json", "w") as f:
            json.dump(rank_data, f)
        
        # Create work items
        work_items = create_content_work_items(
            source_name="wookieepedia",
            api_url="https://starwars.fandom.com/api.php",
            data_lake_base=base_dir,
            limit=2,  # Only top 2
            priority=1,
        )
        
        # Should have 4 items: 2 pages x 2 content types (raw + html)
        # The page with page_id=None should be excluded
        assert len(work_items) == 4
        
        # Check work item structure
        raw_items = [w for w in work_items if w.resource_type == "content_raw"]
        html_items = [w for w in work_items if w.resource_type == "content_html"]
        
        assert len(raw_items) == 2
        assert len(html_items) == 2
        
        # Verify first raw item
        luke_raw = [w for w in raw_items if w.resource_id == "Luke Skywalker"][0]
        assert luke_raw.source_system == "mediawiki"
        assert luke_raw.source_name == "wookieepedia"
        assert luke_raw.priority == 1
        assert luke_raw.metadata["page_id"] == 123
        assert "action=query" in luke_raw.request_uri
        assert "prop=revisions" in luke_raw.request_uri
        
        # Verify dedupe keys are unique
        dedupe_keys = [w.get_dedupe_key() for w in work_items]
        assert len(set(dedupe_keys)) == len(dedupe_keys), "All dedupe keys should be unique"
        
        logger.info("✓ create_content_work_items works correctly")


def test_case_sensitive_counting():
    """Test that link counting is case-sensitive."""
    logger.info("Testing case-sensitive counting...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        page_dir = base_dir / "mediawiki" / "wookieepedia" / "page"
        page_dir.mkdir(parents=True)
        
        # Create page with links to same title in different cases
        artifact = create_mock_page_artifact(
            page_id=1,
            title="Test",
            links=["the Force", "The Force", "THE FORCE"],
        )
        with open(page_dir / "test_20250101_000000_test.json", "w") as f:
            json.dump(artifact, f)
        
        analyzer = InboundLinkAnalyzer(
            source_name="wookieepedia",
            data_lake_base=base_dir,
        )
        
        results = analyzer.analyze()
        by_title = {r["title"]: r for r in results}
        
        # Each case variant should be counted separately
        assert "the Force" in by_title
        assert by_title["the Force"]["inbound_link_count"] == 1
        
        assert "The Force" in by_title
        assert by_title["The Force"]["inbound_link_count"] == 1
        
        assert "THE FORCE" in by_title
        assert by_title["THE FORCE"]["inbound_link_count"] == 1
        
        logger.info("✓ Case-sensitive counting works correctly")


def main():
    """Run all tests."""
    logger.info("Starting analysis module tests...")
    logger.info("=" * 60)
    
    try:
        test_inbound_link_analyzer()
        test_analyze_and_save()
        test_load_inbound_rank()
        test_create_content_work_items()
        test_case_sensitive_counting()
        
        logger.info("=" * 60)
        logger.info("✓ All analysis module tests passed!")
        return 0
        
    except Exception as e:
        logger.exception(f"✗ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
