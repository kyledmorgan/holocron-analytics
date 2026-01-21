#!/usr/bin/env python3
"""
Basic validation script for the ingestion framework.

Tests core functionality without requiring external APIs or databases.
"""

import os
import sys
import logging
import tempfile
import warnings
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.core.models import WorkItem, IngestRecord, WorkItemStatus
from ingest.core.connector import ConnectorRequest, ConnectorResponse
from ingest.storage import FileLakeWriter
from ingest.state import SqliteStateStore, create_state_store


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


def test_state_store_sqlite():
    """Test SQLite state store operations (deprecated backend)."""
    logger.info("Testing SqliteStateStore (deprecated)...")
    
    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    # Suppress deprecation warning for this test
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        state_store = SqliteStateStore(db_path=db_path)
    
    try:
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
        
    finally:
        state_store.close()
        db_path.unlink()
    
    logger.info("✓ SqliteStateStore works correctly")


def test_create_state_store_factory():
    """Test the state store factory function."""
    logger.info("Testing create_state_store factory...")
    
    # Use temporary database for SQLite test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Test SQLite creation via factory
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            store = create_state_store(backend="sqlite", db_path=db_path)
        
        assert store is not None
        assert hasattr(store, 'enqueue')
        assert hasattr(store, 'dequeue')
        store.close()
        
        logger.info("✓ create_state_store factory works correctly")
        
    finally:
        db_path.unlink(missing_ok=True)


def test_file_lake_writer():
    """Test file lake writer."""
    logger.info("Testing FileLakeWriter...")
    
    from datetime import datetime, timezone
    import json
    
    # Use temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
    
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
            fetched_at_utc=datetime.now(timezone.utc),
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
        test_state_store_sqlite()
        test_create_state_store_factory()
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
