#!/usr/bin/env python3
"""
Basic validation script for the ingestion framework.

Tests core functionality without requiring external APIs or databases.
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.core.models import WorkItem, IngestRecord, WorkItemStatus
from ingest.core.connector import ConnectorRequest, ConnectorResponse
from ingest.storage import FileLakeWriter
from ingest.state import SqliteStateStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def test_work_item():
    """Test WorkItem creation and deduplication key."""
    logger.info("Testing WorkItem...")
    
    work_item = WorkItem(
        source_system="mediawiki",
        source_name="wikipedia",
        resource_type="page",
        resource_id="Star_Wars",
        request_uri="https://en.wikipedia.org/w/api.php?action=query&titles=Star_Wars",
        request_method="GET",
    )
    
    assert work_item.source_system == "mediawiki"
    assert work_item.get_dedupe_key() == "mediawiki:wikipedia:page:Star_Wars"
    logger.info("✓ WorkItem works correctly")


def test_state_store():
    """Test SQLite state store operations."""
    logger.info("Testing SqliteStateStore...")
    
    # Use temporary database
    db_path = Path("/tmp/test_state.db")
    if db_path.exists():
        db_path.unlink()
    
    state_store = SqliteStateStore(db_path=db_path)
    
    # Create and enqueue work item
    work_item = WorkItem(
        source_system="mediawiki",
        source_name="test",
        resource_type="page",
        resource_id="Test_Page",
        request_uri="https://example.com/test",
    )
    
    assert state_store.enqueue(work_item) == True
    assert state_store.enqueue(work_item) == False  # Duplicate
    
    # Check stats
    stats = state_store.get_stats()
    assert stats.get("pending") == 1
    
    # Dequeue
    items = state_store.dequeue(limit=1)
    assert len(items) == 1
    assert items[0].resource_id == "Test_Page"
    
    # Update status
    state_store.update_status(items[0].work_item_id, WorkItemStatus.COMPLETED)
    
    stats = state_store.get_stats()
    assert stats.get("completed") == 1
    
    state_store.close()
    db_path.unlink()
    
    logger.info("✓ SqliteStateStore works correctly")


def test_file_lake_writer():
    """Test file lake writer."""
    logger.info("Testing FileLakeWriter...")
    
    from datetime import datetime
    import json
    
    # Use temporary directory
    base_dir = Path("/tmp/test_lake")
    if base_dir.exists():
        import shutil
        shutil.rmtree(base_dir)
    
    writer = FileLakeWriter(base_dir=base_dir, create_dirs=True)
    
    # Create ingest record
    record = IngestRecord(
        ingest_id="test-123",
        source_system="mediawiki",
        source_name="wikipedia",
        resource_type="page",
        resource_id="Test_Page",
        request_uri="https://example.com/test",
        request_method="GET",
        status_code=200,
        payload={"test": "data", "nested": {"value": 123}},
        fetched_at_utc=datetime.utcnow(),
    )
    
    # Write record
    assert writer.write(record) == True
    
    # Verify file was created
    expected_dir = base_dir / "mediawiki" / "wikipedia" / "page"
    assert expected_dir.exists()
    
    files = list(expected_dir.glob("*.json"))
    assert len(files) == 1
    
    # Verify content
    with open(files[0], "r") as f:
        content = json.load(f)
        assert content["ingest_id"] == "test-123"
        assert content["payload"]["test"] == "data"
    
    # Cleanup
    import shutil
    shutil.rmtree(base_dir)
    
    logger.info("✓ FileLakeWriter works correctly")


def test_connector_request_response():
    """Test connector request/response models."""
    logger.info("Testing ConnectorRequest and ConnectorResponse...")
    
    request = ConnectorRequest(
        uri="https://example.com/api",
        method="GET",
        headers={"User-Agent": "Test"},
    )
    
    assert request.uri == "https://example.com/api"
    assert request.method == "GET"
    
    response = ConnectorResponse(
        status_code=200,
        payload={"result": "success"},
        duration_ms=100,
    )
    
    assert response.status_code == 200
    assert response.payload["result"] == "success"
    
    logger.info("✓ ConnectorRequest and ConnectorResponse work correctly")


def main():
    """Run all validation tests."""
    logger.info("Starting validation tests...")
    logger.info("=" * 60)
    
    try:
        test_work_item()
        test_state_store()
        test_file_lake_writer()
        test_connector_request_response()
        
        logger.info("=" * 60)
        logger.info("✓ All validation tests passed!")
        return 0
        
    except Exception as e:
        logger.exception(f"✗ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
