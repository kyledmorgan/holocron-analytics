"""
Unit tests for the concurrent runner module.

These tests verify the concurrent runner's configuration and logic without 
requiring a database connection.
"""

import pytest
import threading
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

from ingest.core.models import (
    WorkItem, WorkItemStatus, IngestRecord,
    WorkerInfo, WorkerStatus, QueueStats, AcquisitionVariant
)
from ingest.runner.concurrent_runner import ConcurrentRunner, RunnerConfig, RunMetrics


class TestRunnerConfig:
    """Tests for RunnerConfig dataclass."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = RunnerConfig()
        
        assert config.max_workers == 4
        assert config.lease_seconds == 300
        assert config.heartbeat_interval == 30
        assert config.batch_size == 10
        assert config.max_items is None
        assert config.stop_after is None
        assert config.max_retries == 3
        assert config.enable_discovery is True
        assert config.source_filter is None
        assert config.base_backoff_seconds == 2.0
        assert config.max_backoff_seconds == 300.0
        assert config.respect_retry_after is True
        assert config.requests_per_second == 0.0
    
    def test_custom_values(self):
        """Test setting custom configuration values."""
        config = RunnerConfig(
            max_workers=8,
            lease_seconds=600,
            max_items=1000,
            source_filter="mediawiki",
        )
        
        assert config.max_workers == 8
        assert config.lease_seconds == 600
        assert config.max_items == 1000
        assert config.source_filter == "mediawiki"


class TestRunMetrics:
    """Tests for RunMetrics dataclass."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = RunMetrics(
            run_id="test-run-123",
            started_at=datetime.now(timezone.utc),
        )
        
        assert metrics.run_id == "test-run-123"
        assert metrics.items_processed == 0
        assert metrics.items_succeeded == 0
        assert metrics.items_failed == 0
        assert metrics.items_discovered == 0
        assert metrics.status == "running"
        assert metrics.ended_at is None


class TestConcurrentRunner:
    """Tests for ConcurrentRunner class."""
    
    @pytest.fixture
    def mock_state_store(self):
        """Create a mock state store."""
        store = Mock()
        store.recover_expired_leases.return_value = 0
        store.claim_work_item.return_value = None
        store.get_queue_stats.return_value = QueueStats()
        store.get_active_workers.return_value = []
        store.update_worker_heartbeat.return_value = True
        store.remove_worker.return_value = True
        return store
    
    @pytest.fixture
    def mock_connector(self):
        """Create a mock connector."""
        connector = Mock()
        connector.get_name.return_value = "test"
        return connector
    
    @pytest.fixture
    def mock_storage_writer(self):
        """Create a mock storage writer."""
        writer = Mock()
        writer.get_name.return_value = "test_writer"
        writer.write.return_value = True
        return writer
    
    def test_initialization(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test runner initialization."""
        config = RunnerConfig(max_workers=2)
        
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
            config=config,
        )
        
        assert runner.config.max_workers == 2
        assert len(runner.connectors) == 1
        assert len(runner.storage_writers) == 1
    
    def test_shutdown_sets_event(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test that shutdown sets the shutdown event."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        assert not runner._shutdown_event.is_set()
        runner.shutdown()
        assert runner._shutdown_event.is_set()
    
    def test_pause_resume(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test pause and resume functionality."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        assert not runner._pause_event.is_set()
        
        runner.pause()
        assert runner._pause_event.is_set()
        
        runner.resume()
        assert not runner._pause_event.is_set()
    
    def test_drain_mode(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test drain mode activation."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        assert not runner._drain_mode
        
        runner.drain()
        assert runner._drain_mode
    
    def test_get_status(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test getting runner status."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        status = runner.get_status()
        
        assert "queue" in status
        assert "workers" in status
        assert "state" in status
        assert status["state"]["paused"] is False
        assert status["state"]["draining"] is False
        assert status["state"]["shutting_down"] is False
    
    def test_should_stop_with_max_items(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test stop condition based on max_items."""
        config = RunnerConfig(max_items=100)
        
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
            config=config,
        )
        
        # Initialize run metrics
        runner._run_metrics = RunMetrics(
            run_id="test",
            started_at=datetime.now(timezone.utc),
        )
        
        # Below limit
        runner._run_metrics.items_processed = 50
        assert not runner._should_stop(0)
        
        # At limit
        runner._run_metrics.items_processed = 100
        assert runner._should_stop(0)
    
    def test_should_stop_with_stop_after(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test stop condition based on stop_after per worker."""
        config = RunnerConfig(stop_after=10)
        
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
            config=config,
        )
        
        # Below per-worker limit
        assert not runner._should_stop(5)
        
        # At per-worker limit
        assert runner._should_stop(10)
    
    def test_calculate_backoff_without_retry_after(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test backoff calculation without Retry-After header."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        # First attempt - should be around base_backoff_seconds (2)
        backoff = runner._calculate_backoff(0, None)
        assert 1 <= backoff <= 6  # 2 * (1 + 0.5 jitter)
        
        # Second attempt - should be around 4
        backoff = runner._calculate_backoff(1, None)
        assert 3 <= backoff <= 12
    
    def test_calculate_backoff_with_retry_after(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test backoff calculation respects Retry-After header."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        headers = {"Retry-After": "60"}
        backoff = runner._calculate_backoff(0, headers)
        assert backoff == 60
    
    def test_calculate_backoff_max_limit(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test that backoff respects max_backoff_seconds."""
        config = RunnerConfig(
            base_backoff_seconds=2.0,
            max_backoff_seconds=100.0,
        )
        
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
            config=config,
        )
        
        # High attempt number should be capped
        backoff = runner._calculate_backoff(10, None)
        assert backoff <= 100
    
    def test_compute_hash(self, mock_state_store, mock_connector, mock_storage_writer):
        """Test payload hash computation."""
        runner = ConcurrentRunner(
            state_store=mock_state_store,
            connectors={"test": mock_connector},
            storage_writers=[mock_storage_writer],
        )
        
        payload = {"key": "value", "nested": {"a": 1, "b": 2}}
        hash1 = runner._compute_hash(payload)
        hash2 = runner._compute_hash(payload)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex


class TestWorkItemModel:
    """Tests for WorkItem model with new fields."""
    
    def test_new_fields_default_values(self):
        """Test that new concurrent processing fields have correct defaults."""
        work_item = WorkItem(
            source_system="test",
            source_name="test_source",
            resource_type="page",
            resource_id="test_id",
            request_uri="https://example.com/test",
        )
        
        assert work_item.claimed_by is None
        assert work_item.claimed_at is None
        assert work_item.lease_expires_at is None
        assert work_item.last_error is None
        assert work_item.next_retry_at is None
    
    def test_new_fields_can_be_set(self):
        """Test that new fields can be set."""
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=300)
        
        work_item = WorkItem(
            source_system="test",
            source_name="test_source",
            resource_type="page",
            resource_id="test_id",
            request_uri="https://example.com/test",
            claimed_by="worker-1",
            claimed_at=now,
            lease_expires_at=lease_expires,
            last_error="Previous error",
            next_retry_at=now + timedelta(seconds=60),
        )
        
        assert work_item.claimed_by == "worker-1"
        assert work_item.claimed_at == now
        assert work_item.lease_expires_at == lease_expires
        assert work_item.last_error == "Previous error"


class TestQueueStatsModel:
    """Tests for QueueStats model."""
    
    def test_default_values(self):
        """Test QueueStats default values."""
        stats = QueueStats()
        
        assert stats.pending == 0
        assert stats.in_progress == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.total == 0
        assert stats.oldest_pending_at is None
        assert stats.active_workers == 0
        assert stats.estimated_completion_minutes is None
    
    def test_custom_values(self):
        """Test QueueStats with custom values."""
        now = datetime.now(timezone.utc)
        
        stats = QueueStats(
            pending=100,
            in_progress=10,
            completed=500,
            failed=5,
            total=615,
            oldest_pending_at=now,
            active_workers=4,
        )
        
        assert stats.pending == 100
        assert stats.in_progress == 10
        assert stats.completed == 500
        assert stats.failed == 5
        assert stats.total == 615
        assert stats.oldest_pending_at == now
        assert stats.active_workers == 4


class TestWorkerInfoModel:
    """Tests for WorkerInfo model."""
    
    def test_initialization(self):
        """Test WorkerInfo initialization."""
        now = datetime.now(timezone.utc)
        
        worker = WorkerInfo(
            worker_id="worker-1",
            hostname="localhost",
            pid=12345,
            started_at=now,
            last_heartbeat_at=now,
        )
        
        assert worker.worker_id == "worker-1"
        assert worker.hostname == "localhost"
        assert worker.pid == 12345
        assert worker.items_processed == 0
        assert worker.items_succeeded == 0
        assert worker.items_failed == 0
        assert worker.status == WorkerStatus.ACTIVE
        assert worker.current_work_item_id is None
