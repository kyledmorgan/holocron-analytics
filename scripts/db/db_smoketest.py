#!/usr/bin/env python3
"""
SQL Server connectivity smoke test.

Verifies that:
1. Connection to SQL Server can be established
2. Schema and tables can be created
3. Basic read/write operations work
4. Dedupe logic functions correctly

Usage:
    python scripts/db/db_smoketest.py
    python -m scripts.db.db_smoketest

Exit codes:
    0: All tests passed
    1: Connection or test failure
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_connection_info() -> dict:
    """Get connection info from environment variables."""
    return {
        "host": os.environ.get("INGEST_SQLSERVER_HOST", os.environ.get("SEED_SQLSERVER_HOST", "localhost")),
        "port": int(os.environ.get("INGEST_SQLSERVER_PORT", os.environ.get("SEED_SQLSERVER_PORT", "1434"))),
        "database": os.environ.get("INGEST_SQLSERVER_DATABASE", os.environ.get("SEED_SQLSERVER_DATABASE", os.environ.get("MSSQL_DATABASE", "Holocron"))),
        "username": os.environ.get("INGEST_SQLSERVER_USER", os.environ.get("SEED_SQLSERVER_USER", "sa")),
        "password": os.environ.get("INGEST_SQLSERVER_PASSWORD", os.environ.get("MSSQL_SA_PASSWORD")),
        "driver": os.environ.get("INGEST_SQLSERVER_DRIVER", os.environ.get("SEED_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")),
        "schema": os.environ.get("INGEST_SQLSERVER_SCHEMA", "ingest"),
    }


def print_connection_info(info: dict) -> None:
    """Print connection info (without secrets)."""
    logger.info("=" * 60)
    logger.info("SQL Server Connection Info")
    logger.info("=" * 60)
    logger.info(f"  Host:     {info['host']}")
    logger.info(f"  Port:     {info['port']}")
    logger.info(f"  Database: {info['database']}")
    logger.info(f"  Username: {info['username']}")
    logger.info(f"  Driver:   {info['driver']}")
    logger.info(f"  Schema:   {info['schema']}")
    logger.info(f"  Password: {'***' if info['password'] else '(not set)'}")
    logger.info("=" * 60)


def test_connection(info: dict) -> bool:
    """Test basic SQL Server connection."""
    logger.info("Test 1: Establishing connection...")
    
    try:
        from ingest.state import SqlServerStateStore
    except ImportError as e:
        logger.error(f"Failed to import SqlServerStateStore: {e}")
        logger.error("Make sure pyodbc is installed: pip install pyodbc")
        return False
    
    try:
        store = SqlServerStateStore(
            host=info["host"],
            port=info["port"],
            database=info["database"],
            username=info["username"],
            password=info["password"],
            driver=info["driver"],
            schema=info["schema"],
            auto_init=True,
        )
        logger.info("✓ Connection established successfully")
        return store
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return None


def test_schema_creation(store) -> bool:
    """Test that schema and tables were created."""
    logger.info("Test 2: Verifying schema creation...")
    
    try:
        cursor = store.conn.cursor()
        
        # Check schema exists
        cursor.execute("""
            SELECT 1 FROM sys.schemas WHERE name = ?
        """, (store.schema,))
        
        if not cursor.fetchone():
            logger.error(f"✗ Schema '{store.schema}' not found")
            return False
        
        # Check table exists
        cursor.execute("""
            SELECT 1 FROM sys.tables t 
            JOIN sys.schemas s ON t.schema_id = s.schema_id 
            WHERE t.name = 'work_items' AND s.name = ?
        """, (store.schema,))
        
        if not cursor.fetchone():
            logger.error(f"✗ Table '{store.schema}.work_items' not found")
            return False
        
        logger.info("✓ Schema and tables verified")
        return True
        
    except Exception as e:
        logger.error(f"✗ Schema verification failed: {e}")
        return False


def test_write_read(store) -> bool:
    """Test basic write and read operations."""
    logger.info("Test 3: Testing write/read operations...")
    
    try:
        from ingest.core.models import WorkItem, WorkItemStatus
        
        # Create a test work item
        test_id = f"smoketest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        work_item = WorkItem(
            source_system="smoketest",
            source_name="db_smoketest",
            resource_type="test",
            resource_id=test_id,
            request_uri=f"https://example.com/test/{test_id}",
            request_method="GET",
            priority=1,
            metadata={"test": True, "timestamp": datetime.now(timezone.utc).isoformat()},
        )
        
        # Enqueue
        if not store.enqueue(work_item):
            logger.error("✗ Failed to enqueue work item")
            return False
        
        logger.info(f"  - Enqueued work item: {work_item.work_item_id}")
        
        # Check it exists
        if not store.exists(work_item.get_dedupe_key()):
            logger.error("✗ Work item not found after enqueue")
            return False
        
        logger.info("  - Verified work item exists")
        
        # Get work item
        retrieved = store.get_work_item(work_item.work_item_id)
        if not retrieved:
            logger.error("✗ Failed to retrieve work item")
            return False
        
        if retrieved.resource_id != test_id:
            logger.error(f"✗ Resource ID mismatch: {retrieved.resource_id} != {test_id}")
            return False
        
        logger.info("  - Retrieved work item successfully")
        
        # Update status
        if not store.update_status(work_item.work_item_id, WorkItemStatus.COMPLETED):
            logger.error("✗ Failed to update status")
            return False
        
        logger.info("  - Updated status to COMPLETED")
        
        # Check stats
        stats = store.get_stats()
        if "completed" not in stats or stats["completed"] < 1:
            logger.warning("  - Stats may not reflect update (delayed visibility)")
        else:
            logger.info(f"  - Stats: {stats}")
        
        logger.info("✓ Write/read operations successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Write/read test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dedupe(store) -> bool:
    """Test deduplication logic."""
    logger.info("Test 4: Testing deduplication...")
    
    try:
        from ingest.core.models import WorkItem
        
        # Create a work item with known dedupe key
        test_id = f"dedupe_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        work_item = WorkItem(
            source_system="smoketest",
            source_name="db_smoketest",
            resource_type="dedupe",
            resource_id=test_id,
            request_uri=f"https://example.com/dedupe/{test_id}",
            request_method="GET",
        )
        
        # First enqueue should succeed
        result1 = store.enqueue(work_item)
        if not result1:
            logger.error("✗ First enqueue should have succeeded")
            return False
        
        logger.info("  - First enqueue succeeded")
        
        # Second enqueue should fail (duplicate)
        result2 = store.enqueue(work_item)
        if result2:
            logger.error("✗ Second enqueue should have been rejected (duplicate)")
            return False
        
        logger.info("  - Second enqueue correctly rejected (dedupe working)")
        
        logger.info("✓ Deduplication working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Dedupe test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data(store) -> None:
    """Clean up test data (optional)."""
    try:
        cursor = store.conn.cursor()
        cursor.execute(f"""
            DELETE FROM [{store.schema}].[work_items]
            WHERE source_system = 'smoketest'
        """)
        store.conn.commit()
        logger.info("  Cleaned up test data")
    except Exception as e:
        logger.warning(f"  Cleanup failed (non-fatal): {e}")


def main() -> int:
    """Run all smoke tests."""
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║       SQL Server State Store - Smoke Test                  ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Get and display connection info
    info = get_connection_info()
    print_connection_info(info)
    
    # Check password is set
    if not info["password"]:
        logger.error("✗ No password configured!")
        logger.error("  Set INGEST_SQLSERVER_PASSWORD or MSSQL_SA_PASSWORD environment variable")
        return 1
    
    # Run tests
    all_passed = True
    store = None
    
    try:
        # Test 1: Connection
        store = test_connection(info)
        if not store:
            return 1
        
        # Test 2: Schema
        if not test_schema_creation(store):
            all_passed = False
        
        # Test 3: Write/Read
        if not test_write_read(store):
            all_passed = False
        
        # Test 4: Dedupe
        if not test_dedupe(store):
            all_passed = False
        
        # Cleanup
        cleanup_test_data(store)
        
    finally:
        if store:
            store.close()
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    if all_passed:
        logger.info("✓ All smoke tests passed!")
        logger.info("  SQL Server state store is ready for use.")
        return 0
    else:
        logger.error("✗ Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
