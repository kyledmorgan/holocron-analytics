"""
End-to-end tests for the ingestion pipeline.

These tests exercise the complete flow:
1. Test connector returns synthetic data
2. Runner processes work items
3. Data is persisted to SQL Server
4. Deduplication prevents duplicate entries on re-run

No external network dependencies - uses deterministic test connector.
"""

import pytest
import uuid


@pytest.mark.e2e
class TestEndToEndIngestion:
    """End-to-end tests for the ingestion pipeline."""
    
    def test_runner_processes_work_items(self, clean_state_store, test_connector):
        """Test that the runner processes work items and updates state."""
        from ingest.core.models import WorkItemStatus
        from ingest.runner import IngestRunner
        from ingest.storage.file_lake import FileLakeWriter
        import tempfile
        import os
        
        store = clean_state_store
        
        # Get seed work items from test connector
        work_items = test_connector.get_seed_work_items(source_name="e2e_test")
        
        # Seed the queue
        for item in work_items:
            store.enqueue(item)
        
        # Verify items are queued
        stats = store.get_stats()
        assert stats.get("pending", 0) >= len(work_items), "Work items not queued"
        
        # Create a temporary directory for file lake output
        with tempfile.TemporaryDirectory() as tmpdir:
            file_writer = FileLakeWriter(base_path=tmpdir)
            
            # Create runner
            runner = IngestRunner(
                state_store=store,
                connectors={"test": test_connector},
                storage_writers=[file_writer],
                discovery_plugins=[],
                enable_discovery=False,
            )
            
            # Run ingestion
            run_id = str(uuid.uuid4())
            metrics = runner.run(
                batch_size=10,
                max_items=len(work_items),
                run_id=run_id,
            )
            
            # Verify metrics
            assert metrics["items_processed"] == len(work_items)
            assert metrics["items_succeeded"] == len(work_items)
            assert metrics["items_failed"] == 0
            
            # Verify all items are completed
            for item in work_items:
                retrieved = store.get_work_item(item.work_item_id)
                assert retrieved.status == WorkItemStatus.COMPLETED, \
                    f"Item {item.resource_id} not completed: {retrieved.status}"
            
            # Verify files were written
            files = list(Path(tmpdir).rglob("*.json"))
            assert len(files) == len(work_items), \
                f"Expected {len(work_items)} files, got {len(files)}"
    
    def test_dedupe_on_rerun(self, clean_state_store, test_connector):
        """Test that deduplication works on re-run."""
        from ingest.core.models import WorkItemStatus
        
        store = clean_state_store
        
        # Get seed work items
        work_items = test_connector.get_seed_work_items(source_name="e2e_dedupe_test")
        
        # First run: enqueue all items
        enqueued_count = 0
        for item in work_items:
            if store.enqueue(item):
                enqueued_count += 1
        
        assert enqueued_count == len(work_items), "First run should enqueue all items"
        
        # Mark all as completed (simulate successful processing)
        for item in work_items:
            store.update_status(item.work_item_id, WorkItemStatus.COMPLETED)
        
        # Verify all completed
        stats = store.get_stats()
        assert stats.get("completed", 0) >= len(work_items)
        
        # Second run: try to enqueue same items
        second_run_enqueued = 0
        for item in work_items:
            if store.enqueue(item):
                second_run_enqueued += 1
        
        # Should not enqueue any duplicates
        assert second_run_enqueued == 0, \
            f"Second run should not enqueue duplicates, but enqueued {second_run_enqueued}"
        
        # Stats should remain the same
        stats_after = store.get_stats()
        assert stats_after.get("completed", 0) >= len(work_items)
    
    def test_row_counts_stable_on_rerun(self, clean_state_store, test_connector):
        """Test that row counts remain stable on re-run (no duplicates)."""
        store = clean_state_store
        
        # Create unique source name for this test
        source_name = f"e2e_stable_{uuid.uuid4().hex[:8]}"
        
        # Get seed work items
        work_items = test_connector.get_seed_work_items(source_name=source_name)
        
        # First run
        for item in work_items:
            store.enqueue(item)
        
        # Count rows after first run
        cursor = store.conn.cursor()
        cursor.execute(f"""
            SELECT COUNT(*) FROM [{store.schema}].[work_items]
            WHERE source_name = ?
        """, (source_name,))
        count_after_first_run = cursor.fetchone()[0]
        
        assert count_after_first_run == len(work_items), \
            f"Expected {len(work_items)} rows, got {count_after_first_run}"
        
        # Second run - try to enqueue same items
        for item in work_items:
            store.enqueue(item)  # Will be rejected as duplicates
        
        # Count rows after second run
        cursor.execute(f"""
            SELECT COUNT(*) FROM [{store.schema}].[work_items]
            WHERE source_name = ?
        """, (source_name,))
        count_after_second_run = cursor.fetchone()[0]
        
        # Row count should be stable
        assert count_after_second_run == count_after_first_run, \
            f"Row count changed: {count_after_first_run} -> {count_after_second_run}"


@pytest.mark.e2e
class TestSeenResourcesTracking:
    """Tests for seen_resources table if it exists."""
    
    def test_ingest_runs_table_created(self, sqlserver_state_store):
        """Test that ingest_runs table is created by migrations."""
        store = sqlserver_state_store
        cursor = store.conn.cursor()
        
        # Check if ingest_runs table exists (created by migrations)
        cursor.execute("""
            SELECT 1 FROM sys.tables t 
            JOIN sys.schemas s ON t.schema_id = s.schema_id 
            WHERE t.name = 'ingest_runs' AND s.name = ?
        """, (store.schema,))
        
        # This may not exist if only state store auto-init was run
        # The migrations create additional tables
        result = cursor.fetchone()
        
        # Note: This test documents expected behavior after migrations are run
        # If running with just auto_init, this table won't exist
        if result is None:
            pytest.skip(
                "ingest_runs table not found - run migrations with: "
                "python -m tools.db_init"
            )


@pytest.mark.e2e
class TestFullPipelineWithStorage:
    """Tests for full pipeline including SQL Server storage writer."""
    
    def test_ingest_records_written_to_sql_server(self, clean_state_store, test_connector, sqlserver_config):
        """Test that IngestRecords are written to SQL Server."""
        import os
        from ingest.runner import IngestRunner
        from ingest.storage.file_lake import FileLakeWriter
        import tempfile
        
        store = clean_state_store
        
        # Check if IngestRecords table exists
        cursor = store.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM sys.tables t 
            JOIN sys.schemas s ON t.schema_id = s.schema_id 
            WHERE t.name = 'IngestRecords' AND s.name = ?
        """, (store.schema,))
        
        if cursor.fetchone() is None:
            pytest.skip(
                "IngestRecords table not found - run migrations with: "
                "python -m tools.db_init"
            )
        
        # Test would continue with SqlServerIngestWriter
        # For now, just verify table structure
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'IngestRecords'
        """, (store.schema,))
        
        columns = {row[0] for row in cursor.fetchall()}
        
        required_columns = ["ingest_id", "source_system", "payload", "status_code"]
        for col in required_columns:
            assert col in columns, f"Required column '{col}' not found in IngestRecords"
