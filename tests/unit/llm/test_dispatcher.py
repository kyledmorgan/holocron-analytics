"""
Unit tests for the job dispatcher.

Tests for:
- DispatcherConfig creation
- JobDispatcher initialization
- Handler registration and resolution
- Dry-run mode behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from llm.runners.dispatcher import (
    JobDispatcher,
    DispatcherConfig,
)
from llm.jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
)
from llm.contracts.phase1_contracts import Job, JobStatus


class TestDispatcherConfig:
    """Tests for DispatcherConfig."""
    
    def test_creation(self):
        """Test basic creation."""
        config = DispatcherConfig(
            worker_id="test-worker",
            dry_run=False,
        )
        
        assert config.worker_id == "test-worker"
        assert config.dry_run is False
        assert config.poll_seconds == 10
        assert config.lake_root == "lake/llm_runs"
    
    def test_creation_dry_run(self):
        """Test creation with dry-run mode."""
        config = DispatcherConfig(
            worker_id="test-worker",
            dry_run=True,
        )
        
        assert config.dry_run is True
        assert config.execution_mode == ExecutionMode.DRY_RUN
    
    def test_execution_mode_property(self):
        """Test execution_mode property."""
        live_config = DispatcherConfig(worker_id="w1", dry_run=False)
        dry_config = DispatcherConfig(worker_id="w2", dry_run=True)
        
        assert live_config.execution_mode == ExecutionMode.LIVE
        assert dry_config.execution_mode == ExecutionMode.DRY_RUN
    
    def test_from_env(self):
        """Test creation from environment."""
        with patch.dict('os.environ', {
            'WORKER_ID': 'env-worker',
            'POLL_SECONDS': '30',
            'LAKE_ROOT': 'custom/lake',
        }):
            config = DispatcherConfig.from_env(dry_run=True)
            
            assert config.worker_id == 'env-worker'
            assert config.poll_seconds == 30
            assert config.lake_root == 'custom/lake'
            assert config.dry_run is True


class TestJobDispatcher:
    """Tests for JobDispatcher."""
    
    @pytest.fixture
    def mock_queue(self):
        """Create a mock SQL job queue."""
        queue = Mock()
        queue.claim_next_job = Mock(return_value=None)
        queue.create_run = Mock(return_value="run-123")
        queue.complete_run = Mock()
        queue.mark_succeeded = Mock()
        queue.mark_failed = Mock()
        queue.create_artifact = Mock(return_value="artifact-123")
        return queue
    
    @pytest.fixture
    def mock_lake_writer(self):
        """Create a mock lake writer."""
        writer = Mock()
        artifact_info = Mock()
        artifact_info.lake_uri = "test/path/artifact.json"
        artifact_info.content_sha256 = "abc123"
        artifact_info.byte_count = 100
        
        writer.write_json = Mock(return_value=artifact_info)
        writer.write_text = Mock(return_value=artifact_info)
        writer.write_evidence = Mock(return_value=artifact_info)
        writer.write_prompt = Mock(return_value=artifact_info)
        return writer
    
    def test_initialization(self, mock_queue, mock_lake_writer):
        """Test dispatcher initialization."""
        config = DispatcherConfig(worker_id="test-worker")
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        assert dispatcher.config.worker_id == "test-worker"
    
    def test_register_handler(self, mock_queue, mock_lake_writer):
        """Test handler registration."""
        config = DispatcherConfig(worker_id="test-worker")
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        def test_handler(job, ctx):
            return HandlerResult.success(output={"test": True})
        
        dispatcher.register_handler("test_job", test_handler)
        
        # Handler should be registered
        assert "test_job" in dispatcher._handlers
    
    def test_dispatch_once_no_jobs(self, mock_queue, mock_lake_writer):
        """Test dispatch_once when no jobs available."""
        config = DispatcherConfig(worker_id="test-worker")
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        mock_queue.claim_next_job.return_value = None
        
        result = dispatcher.dispatch_once()
        
        assert result is False
        mock_queue.claim_next_job.assert_called_once_with("test-worker")
    
    def test_dispatch_once_with_job(self, mock_queue, mock_lake_writer):
        """Test dispatch_once with a job."""
        config = DispatcherConfig(worker_id="test-worker", dry_run=True)
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        # Create a mock job
        job = Job(
            job_id="job-123",
            interrogation_key="page_classification_v1",
            input_json='{"entity_type": "character", "entity_id": "luke"}',
            status=JobStatus.RUNNING,
            attempt_count=1,
        )
        mock_queue.claim_next_job.return_value = job
        
        # Register a simple handler
        def test_handler(job, ctx):
            return HandlerResult.success(output={"handled": True})
        
        dispatcher.register_handler("page_classification", test_handler)
        
        result = dispatcher.dispatch_once()
        
        assert result is True
        mock_queue.claim_next_job.assert_called_once()
        mock_queue.create_run.assert_called_once()
    
    def test_infer_job_type(self, mock_queue, mock_lake_writer):
        """Test job type inference from interrogation key."""
        config = DispatcherConfig(worker_id="test-worker")
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        # Test known mappings
        job1 = Mock(interrogation_key="page_classification_v1")
        assert dispatcher._infer_job_type(job1) == "page_classification"
        
        job2 = Mock(interrogation_key="sw_entity_facts_v1")
        assert dispatcher._infer_job_type(job2) == "sw_entity_facts"
        
        # Test unknown key returns key itself
        job3 = Mock(interrogation_key="custom_v1")
        assert dispatcher._infer_job_type(job3) == "custom_v1"


class TestDispatcherDryRunMode:
    """Tests for dry-run mode behavior."""
    
    @pytest.fixture
    def mock_queue(self):
        queue = Mock()
        queue.claim_next_job = Mock(return_value=None)
        queue.create_run = Mock(return_value="run-123")
        queue.complete_run = Mock()
        queue.mark_succeeded = Mock()
        queue.mark_failed = Mock()
        queue.create_artifact = Mock(return_value="artifact-123")
        return queue
    
    @pytest.fixture
    def mock_lake_writer(self):
        writer = Mock()
        artifact_info = Mock()
        artifact_info.lake_uri = "test/path/artifact.json"
        artifact_info.content_sha256 = "abc123"
        artifact_info.byte_count = 100
        
        writer.write_json = Mock(return_value=artifact_info)
        writer.write_text = Mock(return_value=artifact_info)
        writer.write_evidence = Mock(return_value=artifact_info)
        writer.write_prompt = Mock(return_value=artifact_info)
        return writer
    
    def test_dry_run_handler_receives_context(self, mock_queue, mock_lake_writer):
        """Test that handler receives dry-run context."""
        config = DispatcherConfig(worker_id="test-worker", dry_run=True)
        dispatcher = JobDispatcher(config, mock_queue, mock_lake_writer)
        
        received_context = None
        
        def capture_handler(job, ctx):
            nonlocal received_context
            received_context = ctx
            return HandlerResult.success(output={"test": True})
        
        dispatcher.register_handler("page_classification", capture_handler)
        
        # Create and dispatch a job
        job = Job(
            job_id="job-123",
            interrogation_key="page_classification_v1",
            input_json='{"entity_type": "character", "entity_id": "luke"}',
            status=JobStatus.RUNNING,
            attempt_count=1,
        )
        mock_queue.claim_next_job.return_value = job
        
        dispatcher.dispatch_once()
        
        # Verify context
        assert received_context is not None
        assert received_context.is_dry_run is True
        assert received_context.execution_mode == ExecutionMode.DRY_RUN
    
    def test_dry_run_config_mode(self, mock_queue, mock_lake_writer):
        """Test that config correctly sets dry-run mode."""
        dry_config = DispatcherConfig(worker_id="w1", dry_run=True)
        live_config = DispatcherConfig(worker_id="w2", dry_run=False)
        
        dry_dispatcher = JobDispatcher(dry_config, mock_queue, mock_lake_writer)
        live_dispatcher = JobDispatcher(live_config, mock_queue, mock_lake_writer)
        
        assert dry_dispatcher.config.execution_mode == ExecutionMode.DRY_RUN
        assert live_dispatcher.config.execution_mode == ExecutionMode.LIVE
