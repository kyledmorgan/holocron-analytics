#!/usr/bin/env python3
"""
Unit tests for snapshot sync operations.

Tests:
- Idempotent import (import twice → no duplicates)
- Export then import round-trip preserves hashes
- Conflict resolution strategies
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.snapshot.models import ExchangeRecord
from ingest.snapshot.manifest import SnapshotManifest
from ingest.snapshot.file_snapshot import SnapshotWriter, SnapshotReader
from ingest.snapshot.index import SnapshotIndex, IndexEntry
from ingest.snapshot.sync_engine import SyncEngine, SyncDirection, ConflictStrategy, SyncReport
from ingest.snapshot.canonical import compute_content_hash


class TestSnapshotWriter(unittest.TestCase):
    """Test cases for SnapshotWriter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        
        self.manifest = SnapshotManifest.create_default(
            dataset_name="test-dataset",
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_creates_structure(self):
        """Test that writing creates the expected directory structure."""
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
            chunk_size=10,
        )
        
        record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            response={"data": "test"},
        )
        
        writer.write(record)
        writer.close()
        
        dataset_dir = self.base_dir / "test-dataset"
        self.assertTrue(dataset_dir.exists())
        self.assertTrue((dataset_dir / "manifest.json").exists())
        self.assertTrue((dataset_dir / "index.jsonl").exists())
        self.assertTrue((dataset_dir / "records").exists())
    
    def test_write_batch(self):
        """Test writing multiple records."""
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
            chunk_size=5,
        )
        
        records = [
            ExchangeRecord.create(
                exchange_type="http",
                source_system="test",
                entity_type="page",
                natural_key=f"key-{i}",
                response={"data": f"test-{i}"},
            )
            for i in range(10)
        ]
        
        count = writer.write_batch(records)
        writer.close()
        
        self.assertEqual(count, 10)
        
        # Should have created 2 chunk files (10 records / 5 per chunk)
        ndjson_files = list((self.base_dir / "test-dataset" / "records").rglob("*.ndjson"))
        self.assertEqual(len(ndjson_files), 2)


class TestSnapshotReader(unittest.TestCase):
    """Test cases for SnapshotReader."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        
        self.manifest = SnapshotManifest.create_default(
            dataset_name="test-dataset",
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        # Create some test data
        self.records = [
            ExchangeRecord.create(
                exchange_type="http",
                source_system="test",
                entity_type="page",
                natural_key=f"key-{i}",
                response={"data": f"test-{i}"},
            )
            for i in range(5)
        ]
        
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
        )
        writer.write_batch(self.records)
        writer.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_read_all(self):
        """Test reading all records."""
        reader = SnapshotReader(self.base_dir / "test-dataset")
        
        read_records = list(reader.read_all())
        
        self.assertEqual(len(read_records), 5)
    
    def test_get_hashes(self):
        """Test getting all hashes from index."""
        reader = SnapshotReader(self.base_dir / "test-dataset")
        
        hashes = reader.get_hashes()
        
        self.assertEqual(len(hashes), 5)
        for record in self.records:
            self.assertIn(record.content_sha256, hashes)
    
    def test_round_trip_preserves_hashes(self):
        """Test that read records have same hashes as written."""
        reader = SnapshotReader(self.base_dir / "test-dataset")
        read_records = list(reader.read_all())
        
        original_hashes = {r.content_sha256 for r in self.records}
        read_hashes = {r.content_sha256 for r in read_records}
        
        self.assertEqual(original_hashes, read_hashes)


class TestSnapshotIndex(unittest.TestCase):
    """Test cases for SnapshotIndex."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = Path(self.temp_dir) / "index.jsonl"
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_and_get_entry(self):
        """Test adding and retrieving entries."""
        index = SnapshotIndex(self.index_path)
        
        entry = IndexEntry(
            content_sha256="abc123",
            hash_input_key="test|page|key1",
            exchange_id="uuid-1",
            observed_at_utc="2024-01-01T00:00:00+00:00",
        )
        
        result = index.add_entry(entry)
        self.assertTrue(result)
        
        retrieved = index.get_entry("abc123")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hash_input_key, "test|page|key1")
    
    def test_duplicate_entry_rejected(self):
        """Test that duplicate entries are rejected."""
        index = SnapshotIndex(self.index_path)
        
        entry = IndexEntry(
            content_sha256="abc123",
            hash_input_key="test|page|key1",
            exchange_id="uuid-1",
            observed_at_utc="2024-01-01T00:00:00+00:00",
        )
        
        result1 = index.add_entry(entry)
        result2 = index.add_entry(entry)
        
        self.assertTrue(result1)
        self.assertFalse(result2)
        self.assertEqual(index.count(), 1)
    
    def test_save_and_load(self):
        """Test persistence to file."""
        index = SnapshotIndex(self.index_path)
        
        for i in range(3):
            index.add_entry(IndexEntry(
                content_sha256=f"hash-{i}",
                hash_input_key=f"test|page|key-{i}",
                exchange_id=f"uuid-{i}",
                observed_at_utc="2024-01-01T00:00:00+00:00",
            ))
        
        index.save()
        
        # Load into new index
        index2 = SnapshotIndex(self.index_path)
        index2.load()
        
        self.assertEqual(index2.count(), 3)
        self.assertTrue(index2.has_hash("hash-0"))
        self.assertTrue(index2.has_hash("hash-1"))
        self.assertTrue(index2.has_hash("hash-2"))


class TestIdempotentImport(unittest.TestCase):
    """Test idempotent import (import twice → no duplicates)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        
        self.manifest = SnapshotManifest.create_default(
            dataset_name="test-dataset",
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        # Create test records
        self.records = [
            ExchangeRecord.create(
                exchange_type="http",
                source_system="test",
                entity_type="page",
                natural_key=f"key-{i}",
                response={"data": f"test-{i}"},
            )
            for i in range(5)
        ]
        
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
        )
        writer.write_batch(self.records)
        writer.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_idempotent_import_with_mock_sql(self):
        """Test that importing twice doesn't create duplicates."""
        dataset_dir = self.base_dir / "test-dataset"
        
        # Create mock SQL mirror
        mock_sql = Mock()
        
        # First import: no existing hashes
        mock_sql.get_all_hashes.return_value = set()
        mock_sql.get_records_by_natural_key.return_value = []
        mock_sql.upsert.return_value = (True, "inserted")
        
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=mock_sql,
            manifest=self.manifest,
        )
        
        report1 = engine.import_json_to_sql(dry_run=False)
        
        self.assertEqual(report1.json_to_sql_inserted, 5)
        self.assertEqual(report1.json_to_sql_skipped, 0)
        
        # Second import: all hashes now exist
        mock_sql.get_all_hashes.return_value = {r.content_sha256 for r in self.records}
        
        report2 = engine.import_json_to_sql(dry_run=False)
        
        self.assertEqual(report2.json_to_sql_inserted, 0)
        self.assertEqual(report2.json_to_sql_skipped, 5)


class TestConflictResolution(unittest.TestCase):
    """Test conflict resolution strategies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        
        self.manifest = SnapshotManifest.create_default(
            dataset_name="test-dataset",
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_conflict_prefer_newest_json_wins(self):
        """Test prefer_newest when JSON is newer."""
        dataset_dir = self.base_dir / "test-dataset"
        
        # Create JSON record with newer timestamp
        json_record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="conflict-key",
            response={"data": "json-version"},
            observed_at_utc=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
        )
        writer.write(json_record)
        writer.close()
        
        # Create SQL record with older timestamp
        sql_record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="conflict-key",
            response={"data": "sql-version"},
            observed_at_utc=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        # Mock SQL mirror
        mock_sql = Mock()
        mock_sql.get_all_hashes.return_value = set()  # Hash doesn't exist
        mock_sql.get_records_by_natural_key.return_value = [sql_record]  # But natural key does
        mock_sql.upsert.return_value = (True, "updated")
        
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=mock_sql,
            manifest=self.manifest,
        )
        
        report = engine.import_json_to_sql(
            dry_run=False,
            conflict_strategy=ConflictStrategy.PREFER_NEWEST,
        )
        
        # Should have one conflict, resolved as json_wins
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(report.conflicts[0].resolution, "json_wins")
    
    def test_conflict_fail_strategy(self):
        """Test fail strategy aborts on conflict."""
        dataset_dir = self.base_dir / "test-dataset"
        
        # Create JSON record
        json_record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="conflict-key",
            response={"data": "json-version"},
        )
        
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
        )
        writer.write(json_record)
        writer.close()
        
        # Create SQL record with same natural key but different content
        sql_record = ExchangeRecord.create(
            exchange_type="http",
            source_system="test",
            entity_type="page",
            natural_key="conflict-key",
            response={"data": "sql-version"},
        )
        
        # Mock SQL mirror
        mock_sql = Mock()
        mock_sql.get_all_hashes.return_value = set()
        mock_sql.get_records_by_natural_key.return_value = [sql_record]
        
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=mock_sql,
            manifest=self.manifest,
        )
        
        report = engine.import_json_to_sql(
            dry_run=False,
            conflict_strategy=ConflictStrategy.FAIL,
        )
        
        # Should have one conflict with failed resolution
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(report.conflicts[0].resolution, "failed")
        self.assertTrue(len(report.errors) > 0)


class TestDryRun(unittest.TestCase):
    """Test dry-run mode."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        
        self.manifest = SnapshotManifest.create_default(
            dataset_name="test-dataset",
            exchange_type="http",
            source_system="test",
            entity_type="page",
        )
        
        # Create test records
        self.records = [
            ExchangeRecord.create(
                exchange_type="http",
                source_system="test",
                entity_type="page",
                natural_key=f"key-{i}",
                response={"data": f"test-{i}"},
            )
            for i in range(3)
        ]
        
        writer = SnapshotWriter(
            base_dir=self.base_dir,
            manifest=self.manifest,
        )
        writer.write_batch(self.records)
        writer.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dry_run_no_sql_writes(self):
        """Test that dry-run doesn't write to SQL."""
        dataset_dir = self.base_dir / "test-dataset"
        
        mock_sql = Mock()
        mock_sql.get_all_hashes.return_value = set()
        mock_sql.get_records_by_natural_key.return_value = []
        
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=mock_sql,
            manifest=self.manifest,
        )
        
        report = engine.import_json_to_sql(dry_run=True)
        
        # Should report insertions but not actually call upsert
        self.assertEqual(report.json_to_sql_inserted, 3)
        mock_sql.upsert.assert_not_called()
        mock_sql.insert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
