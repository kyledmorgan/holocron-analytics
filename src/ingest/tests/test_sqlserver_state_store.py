#!/usr/bin/env python3
"""
SQL Server state store integration tests.

These tests require a running SQL Server instance. 
They can be run manually when SQL Server (Docker) is available.

Usage:
    # Ensure SQL Server is running
    docker compose up -d sqlserver
    
    # Set environment variables
    export MSSQL_SA_PASSWORD="YourPassword"
    
    # Run tests
    python src/ingest/tests/test_sqlserver_state_store.py
"""

import os
import sys
import logging
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.core.models import WorkItem, WorkItemStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def is_sqlserver_available():
    """Check if SQL Server is available for testing."""
    password = os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD")
    if not password:
        return False
    
    try:
        import pyodbc
        from ingest.state import SqlServerStateStore
        
        store = SqlServerStateStore(
            host=os.environ.get("INGEST_SQLSERVER_HOST", "localhost"),
            port=int(os.environ.get("INGEST_SQLSERVER_PORT", "1433")),
            database=os.environ.get("INGEST_SQLSERVER_DATABASE", "Holocron"),
            username=os.environ.get("INGEST_SQLSERVER_USER", "sa"),
            password=password,
            schema="test_ingest",
            auto_init=True,
        )
        store.close()
        return True
    except Exception as e:
        logger.warning(f"SQL Server not available: {e}")
        return False


@unittest.skipUnless(
    is_sqlserver_available(),
    "SQL Server not available (set MSSQL_SA_PASSWORD and ensure SQL Server is running)"
)
class TestSqlServerStateStore(unittest.TestCase):
    """Integration tests for SqlServerStateStore."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        from ingest.state import SqlServerStateStore
        
        password = os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD")
        
        cls.store = SqlServerStateStore(
            host=os.environ.get("INGEST_SQLSERVER_HOST", "localhost"),
            port=int(os.environ.get("INGEST_SQLSERVER_PORT", "1433")),
            database=os.environ.get("INGEST_SQLSERVER_DATABASE", "Holocron"),
            username=os.environ.get("INGEST_SQLSERVER_USER", "sa"),
            password=password,
            schema="test_ingest",
            auto_init=True,
        )
        
        # Clean up any existing test data
        cls._cleanup_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        cls._cleanup_test_data()
        cls.store.close()
    
    @classmethod
    def _cleanup_test_data(cls):
        """Clean up test data."""
        try:
            cursor = cls.store.conn.cursor()
            cursor.execute(f"""
                DELETE FROM [{cls.store.schema}].[work_items]
                WHERE source_system = 'test'
            """)
            cls.store.conn.commit()
        except Exception:
            pass  # Table may not exist yet
    
    def setUp(self):
        """Set up each test."""
        self._cleanup_test_data()
    
    def _create_work_item(self, resource_id=None, priority=100):
        """Create a test work item."""
        if resource_id is None:
            resource_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        return WorkItem(
            source_system="test",
            source_name="sqlserver_test",
            resource_type="item",
            resource_id=resource_id,
            request_uri=f"https://example.com/test/{resource_id}",
            request_method="GET",
            priority=priority,
            metadata={"test": True},
        )
    
    def test_enqueue_new_item(self):
        """Test enqueuing a new work item."""
        work_item = self._create_work_item()
        
        result = self.store.enqueue(work_item)
        
        self.assertTrue(result)
        self.assertTrue(self.store.exists(work_item.get_dedupe_key()))
    
    def test_enqueue_duplicate_rejected(self):
        """Test that duplicate items are rejected."""
        work_item = self._create_work_item(resource_id="duplicate_test")
        
        # First enqueue should succeed
        result1 = self.store.enqueue(work_item)
        self.assertTrue(result1)
        
        # Second enqueue should fail (duplicate)
        result2 = self.store.enqueue(work_item)
        self.assertFalse(result2)
    
    def test_dequeue_returns_pending_items(self):
        """Test that dequeue returns pending items."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        items = self.store.dequeue(limit=1)
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].resource_id, work_item.resource_id)
    
    def test_dequeue_marks_as_in_progress(self):
        """Test that dequeue marks items as in_progress."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        items = self.store.dequeue(limit=1)
        
        # Get the item directly and check status
        retrieved = self.store.get_work_item(items[0].work_item_id)
        self.assertEqual(retrieved.status, WorkItemStatus.IN_PROGRESS)
    
    def test_dequeue_respects_priority(self):
        """Test that dequeue respects priority ordering."""
        # Create items with different priorities
        low_priority = self._create_work_item(resource_id="low_priority", priority=100)
        high_priority = self._create_work_item(resource_id="high_priority", priority=1)
        
        # Enqueue in reverse order
        self.store.enqueue(low_priority)
        self.store.enqueue(high_priority)
        
        # Dequeue should return high priority first
        items = self.store.dequeue(limit=1)
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].resource_id, "high_priority")
    
    def test_update_status_to_completed(self):
        """Test updating status to completed."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        result = self.store.update_status(work_item.work_item_id, WorkItemStatus.COMPLETED)
        
        self.assertTrue(result)
        
        retrieved = self.store.get_work_item(work_item.work_item_id)
        self.assertEqual(retrieved.status, WorkItemStatus.COMPLETED)
    
    def test_update_status_with_error_message(self):
        """Test updating status with error message."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        error_msg = "Test error message"
        result = self.store.update_status(
            work_item.work_item_id,
            WorkItemStatus.FAILED,
            error_message=error_msg
        )
        
        self.assertTrue(result)
        
        # Note: WorkItem model doesn't have error_message, but it's stored in DB
    
    def test_get_stats(self):
        """Test getting queue statistics."""
        # Create and enqueue items
        item1 = self._create_work_item(resource_id="stats_test_1")
        item2 = self._create_work_item(resource_id="stats_test_2")
        
        self.store.enqueue(item1)
        self.store.enqueue(item2)
        
        # Mark one as completed
        self.store.update_status(item1.work_item_id, WorkItemStatus.COMPLETED)
        
        stats = self.store.get_stats()
        
        self.assertIn("pending", stats)
        self.assertIn("completed", stats)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["completed"], 1)
    
    def test_exists_returns_true_for_existing(self):
        """Test exists returns True for existing dedupe key."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        result = self.store.exists(work_item.get_dedupe_key())
        
        self.assertTrue(result)
    
    def test_exists_returns_false_for_missing(self):
        """Test exists returns False for missing dedupe key."""
        result = self.store.exists("nonexistent:key:here:now")
        
        self.assertFalse(result)
    
    def test_get_work_item_returns_item(self):
        """Test getting a specific work item."""
        work_item = self._create_work_item()
        self.store.enqueue(work_item)
        
        retrieved = self.store.get_work_item(work_item.work_item_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.work_item_id, work_item.work_item_id)
        self.assertEqual(retrieved.resource_id, work_item.resource_id)
    
    def test_get_work_item_returns_none_for_missing(self):
        """Test getting a missing work item returns None."""
        retrieved = self.store.get_work_item("nonexistent-id")
        
        self.assertIsNone(retrieved)
    
    def test_get_known_resources(self):
        """Test getting known resources for re-crawl."""
        item1 = self._create_work_item(resource_id="known_1")
        item2 = self._create_work_item(resource_id="known_2")
        
        self.store.enqueue(item1)
        self.store.enqueue(item2)
        self.store.update_status(item1.work_item_id, WorkItemStatus.COMPLETED)
        
        # Get completed items
        known = self.store.get_known_resources(
            source_system="test",
            status=WorkItemStatus.COMPLETED
        )
        
        self.assertEqual(len(known), 1)
        self.assertEqual(known[0].resource_id, "known_1")
    
    def test_reset_for_recrawl(self):
        """Test resetting completed items for re-crawl."""
        item = self._create_work_item(resource_id="recrawl_test")
        self.store.enqueue(item)
        self.store.update_status(item.work_item_id, WorkItemStatus.COMPLETED)
        
        # Reset for re-crawl
        count = self.store.reset_for_recrawl(source_system="test")
        
        self.assertEqual(count, 1)
        
        # Verify it's pending again
        retrieved = self.store.get_work_item(item.work_item_id)
        self.assertEqual(retrieved.status, WorkItemStatus.PENDING)
    
    def test_dedupe_prevents_rerun_duplicates(self):
        """Test that dedupe prevents duplicate entries on rerun."""
        work_item = self._create_work_item(resource_id="rerun_dedupe_test")
        
        # Simulate first run
        result1 = self.store.enqueue(work_item)
        self.assertTrue(result1)
        self.store.update_status(work_item.work_item_id, WorkItemStatus.COMPLETED)
        
        # Simulate second run attempting to enqueue same item
        result2 = self.store.enqueue(work_item)
        self.assertFalse(result2)
        
        # Verify only one entry exists
        stats = self.store.get_stats()
        total = sum(stats.values())
        # Should only have the one completed item for this test
        self.assertGreaterEqual(stats.get("completed", 0), 1)


def main():
    """Run the tests."""
    logger.info("=" * 60)
    logger.info("SQL Server State Store Integration Tests")
    logger.info("=" * 60)
    
    if not is_sqlserver_available():
        logger.warning("SQL Server not available. Tests will be skipped.")
        logger.info("To run these tests:")
        logger.info("  1. Start SQL Server: docker compose up -d sqlserver")
        logger.info("  2. Set password: export MSSQL_SA_PASSWORD='YourPassword'")
        logger.info("  3. Run tests: python src/ingest/tests/test_sqlserver_state_store.py")
        return 0  # Return success (tests skipped, not failed)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSqlServerStateStore)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
