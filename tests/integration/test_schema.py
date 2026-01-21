"""
Integration tests for SQL Server schema and table verification.

These tests verify that:
1. The ingest schema exists
2. Required tables exist in the schema
3. Indexes and constraints are properly configured
"""

import pytest


@pytest.mark.integration
class TestSchemaExists:
    """Tests to verify the ingest schema exists and is properly configured."""
    
    def test_ingest_schema_exists(self, sqlserver_state_store):
        """Test that the ingest schema exists."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM sys.schemas WHERE name = ?
        """, (store.schema,))
        
        result = cursor.fetchone()
        assert result is not None, f"Schema '{store.schema}' does not exist"
    
    def test_work_items_table_exists(self, sqlserver_state_store):
        """Test that the work_items table exists in the ingest schema."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM sys.tables t 
            JOIN sys.schemas s ON t.schema_id = s.schema_id 
            WHERE t.name = 'work_items' AND s.name = ?
        """, (store.schema,))
        
        result = cursor.fetchone()
        assert result is not None, f"Table '{store.schema}.work_items' does not exist"
    
    def test_work_items_required_columns(self, sqlserver_state_store):
        """Test that work_items table has all required columns."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        required_columns = [
            "work_item_id",
            "source_system",
            "source_name",
            "resource_type",
            "resource_id",
            "request_uri",
            "request_method",
            "status",
            "priority",
            "attempt",
            "dedupe_key",
            "created_at",
            "updated_at",
        ]
        
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'work_items'
        """, (store.schema,))
        
        actual_columns = {row[0] for row in cursor.fetchall()}
        
        for col in required_columns:
            assert col in actual_columns, f"Required column '{col}' not found in work_items table"
    
    def test_dedupe_index_exists(self, sqlserver_state_store):
        """Test that the unique dedupe index exists."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        # Check for an index on dedupe_key
        cursor.execute(f"""
            SELECT i.name, i.is_unique
            FROM sys.indexes i
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = 'work_items'
            AND i.name LIKE '%dedupe%'
        """, (store.schema,))
        
        result = cursor.fetchone()
        assert result is not None, "Dedupe index not found on work_items table"
        assert result[1] == True, "Dedupe index should be unique"
    
    def test_status_index_exists(self, sqlserver_state_store):
        """Test that the status index exists for queue operations."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        cursor.execute(f"""
            SELECT i.name
            FROM sys.indexes i
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = 'work_items'
            AND i.name LIKE '%status%'
        """, (store.schema,))
        
        result = cursor.fetchone()
        assert result is not None, "Status index not found on work_items table"


@pytest.mark.integration
class TestStateStoreOperations:
    """Tests for basic state store operations against SQL Server."""
    
    def test_enqueue_work_item(self, clean_state_store):
        """Test enqueuing a work item."""
        from ingest.core.models import WorkItem
        
        store = clean_state_store
        
        work_item = WorkItem(
            source_system="test_integration",
            source_name="test_source",
            resource_type="item",
            resource_id="integration_test_001",
            request_uri="https://example.com/test/001",
        )
        
        result = store.enqueue(work_item)
        
        assert result is True, "Failed to enqueue work item"
        assert store.exists(work_item.get_dedupe_key()), "Work item not found after enqueue"
    
    def test_enqueue_duplicate_rejected(self, clean_state_store):
        """Test that duplicate work items are rejected."""
        from ingest.core.models import WorkItem
        
        store = clean_state_store
        
        work_item = WorkItem(
            source_system="test_integration",
            source_name="test_source",
            resource_type="item",
            resource_id="duplicate_test",
            request_uri="https://example.com/test/dup",
        )
        
        # First enqueue should succeed
        result1 = store.enqueue(work_item)
        assert result1 is True
        
        # Second enqueue should fail (duplicate)
        result2 = store.enqueue(work_item)
        assert result2 is False
    
    def test_dequeue_returns_pending_items(self, clean_state_store):
        """Test that dequeue returns pending items."""
        from ingest.core.models import WorkItem
        
        store = clean_state_store
        
        work_item = WorkItem(
            source_system="test_integration",
            source_name="test_source",
            resource_type="item",
            resource_id="dequeue_test",
            request_uri="https://example.com/test/dequeue",
        )
        
        store.enqueue(work_item)
        
        items = store.dequeue(limit=1)
        
        assert len(items) == 1
        assert items[0].resource_id == "dequeue_test"
    
    def test_update_status(self, clean_state_store):
        """Test updating work item status."""
        from ingest.core.models import WorkItem, WorkItemStatus
        
        store = clean_state_store
        
        work_item = WorkItem(
            source_system="test_integration",
            source_name="test_source",
            resource_type="item",
            resource_id="status_test",
            request_uri="https://example.com/test/status",
        )
        
        store.enqueue(work_item)
        
        # Update to completed
        result = store.update_status(work_item.work_item_id, WorkItemStatus.COMPLETED)
        
        assert result is True
        
        # Verify status was updated
        retrieved = store.get_work_item(work_item.work_item_id)
        assert retrieved.status == WorkItemStatus.COMPLETED
    
    def test_get_stats(self, clean_state_store):
        """Test getting queue statistics."""
        from ingest.core.models import WorkItem, WorkItemStatus
        
        store = clean_state_store
        
        # Create and enqueue items
        for i in range(3):
            item = WorkItem(
                source_system="test_integration",
                source_name="test_source",
                resource_type="item",
                resource_id=f"stats_test_{i}",
                request_uri=f"https://example.com/test/stats/{i}",
            )
            store.enqueue(item)
        
        stats = store.get_stats()
        
        assert "pending" in stats
        assert stats["pending"] >= 3


@pytest.mark.integration
class TestDatabaseConnection:
    """Tests for database connection and availability."""
    
    def test_connection_is_active(self, sqlserver_state_store):
        """Test that the database connection is active."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        assert result[0] == 1
    
    def test_database_name_is_correct(self, sqlserver_state_store, sqlserver_config):
        """Test that we're connected to the correct database."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        cursor.execute("SELECT DB_NAME()")
        result = cursor.fetchone()
        
        expected_db = sqlserver_config["database"]
        assert result[0] == expected_db, f"Connected to wrong database: {result[0]} != {expected_db}"
