"""
Unit tests for job handlers.

Tests for:
- RunContext creation and methods
- HandlerResult creation and status helpers
- ExecutionMode enum
"""

import pytest
from datetime import datetime, timezone

from llm.jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
    ArtifactReference,
)


class TestExecutionMode:
    """Tests for ExecutionMode enum."""
    
    def test_live_mode(self):
        """Test LIVE mode value."""
        assert ExecutionMode.LIVE.value == "live"
    
    def test_dry_run_mode(self):
        """Test DRY_RUN mode value."""
        assert ExecutionMode.DRY_RUN.value == "dry_run"


class TestRunContext:
    """Tests for RunContext dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        ctx = RunContext(
            job_id="job-123",
            run_id="run-456",
            correlation_id="job-123-run-456",
            worker_id="worker-1",
        )
        
        assert ctx.job_id == "job-123"
        assert ctx.run_id == "run-456"
        assert ctx.correlation_id == "job-123-run-456"
        assert ctx.worker_id == "worker-1"
        assert ctx.execution_mode == ExecutionMode.LIVE
        assert ctx.attempt_number == 1
        assert ctx.max_attempts == 3
    
    def test_create_factory(self):
        """Test create() factory method."""
        ctx = RunContext.create(
            job_id="job-123",
            worker_id="worker-1",
            job_type="page_classification",
        )
        
        assert ctx.job_id == "job-123"
        assert ctx.worker_id == "worker-1"
        assert ctx.job_type == "page_classification"
        # Generated fields
        assert ctx.run_id is not None
        assert len(ctx.run_id) == 36  # UUID format
        assert ctx.correlation_id is not None
        assert ctx.correlation_id.startswith("job-123-")
    
    def test_create_with_dry_run(self):
        """Test create() with dry-run mode."""
        ctx = RunContext.create(
            job_id="job-123",
            worker_id="worker-1",
            execution_mode=ExecutionMode.DRY_RUN,
        )
        
        assert ctx.execution_mode == ExecutionMode.DRY_RUN
        assert ctx.is_dry_run is True
    
    def test_is_dry_run_property(self):
        """Test is_dry_run property."""
        live_ctx = RunContext.create(
            job_id="job-1",
            worker_id="worker-1",
            execution_mode=ExecutionMode.LIVE,
        )
        dry_ctx = RunContext.create(
            job_id="job-2",
            worker_id="worker-1",
            execution_mode=ExecutionMode.DRY_RUN,
        )
        
        assert live_ctx.is_dry_run is False
        assert dry_ctx.is_dry_run is True
    
    def test_get_log_context(self):
        """Test get_log_context for structured logging."""
        ctx = RunContext.create(
            job_id="job-123",
            worker_id="worker-1",
            job_type="page_classification",
            execution_mode=ExecutionMode.DRY_RUN,
        )
        
        log_ctx = ctx.get_log_context()
        
        assert log_ctx["job_id"] == "job-123"
        assert log_ctx["worker_id"] == "worker-1"
        assert log_ctx["job_type"] == "page_classification"
        assert log_ctx["execution_mode"] == "dry_run"
        assert "run_id" in log_ctx
        assert "correlation_id" in log_ctx
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        ctx = RunContext.create(
            job_id="job-123",
            worker_id="worker-1",
            job_type="test",
        )
        
        result = ctx.to_dict()
        
        assert result["job_id"] == "job-123"
        assert result["worker_id"] == "worker-1"
        assert result["job_type"] == "test"
        assert "started_at" in result
        assert "run_id" in result


class TestArtifactReference:
    """Tests for ArtifactReference dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        ref = ArtifactReference(
            artifact_type="request_json",
            lake_uri="2024/01/15/run-123/request.json",
        )
        
        assert ref.artifact_type == "request_json"
        assert ref.lake_uri == "2024/01/15/run-123/request.json"
    
    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        ref = ArtifactReference(
            artifact_type="prompt_text",
            lake_uri="path/to/prompt.txt",
        )
        
        result = ref.to_dict()
        
        assert result["artifact_type"] == "prompt_text"
        assert result["lake_uri"] == "path/to/prompt.txt"
        assert "content_sha256" not in result
        assert "byte_count" not in result
    
    def test_to_dict_full(self):
        """Test to_dict with all fields."""
        ref = ArtifactReference(
            artifact_type="response_json",
            lake_uri="path/to/response.json",
            content_sha256="abc123",
            byte_count=1024,
        )
        
        result = ref.to_dict()
        
        assert result["content_sha256"] == "abc123"
        assert result["byte_count"] == 1024


class TestHandlerStatus:
    """Tests for HandlerStatus enum."""
    
    def test_values(self):
        """Test status values."""
        assert HandlerStatus.SUCCEEDED.value == "SUCCEEDED"
        assert HandlerStatus.FAILED.value == "FAILED"
        assert HandlerStatus.SKIPPED.value == "SKIPPED"


class TestHandlerResult:
    """Tests for HandlerResult dataclass."""
    
    def test_success_factory(self):
        """Test success() factory method."""
        result = HandlerResult.success(
            output={"key": "value"},
            metrics={"tokens": 100},
        )
        
        assert result.status == HandlerStatus.SUCCEEDED
        assert result.succeeded is True
        assert result.failed is False
        assert result.output == {"key": "value"}
        assert result.metrics == {"tokens": 100}
        assert result.error_message is None
    
    def test_failure_factory(self):
        """Test failure() factory method."""
        result = HandlerResult.failure(
            error_message="Something went wrong",
            validation_errors=["Invalid field X"],
        )
        
        assert result.status == HandlerStatus.FAILED
        assert result.succeeded is False
        assert result.failed is True
        assert result.error_message == "Something went wrong"
        assert result.validation_errors == ["Invalid field X"]
        assert result.output is None
    
    def test_skipped_factory(self):
        """Test skipped() factory method."""
        result = HandlerResult.skipped(
            reason="Duplicate job detected",
        )
        
        assert result.status == HandlerStatus.SKIPPED
        assert result.succeeded is False
        assert result.failed is False
        assert result.skipped_reason == "Duplicate job detected"
    
    def test_success_with_artifacts(self):
        """Test success with artifact references."""
        artifacts = [
            ArtifactReference("request_json", "path/request.json"),
            ArtifactReference("response_json", "path/response.json"),
        ]
        
        result = HandlerResult.success(
            output={"result": "ok"},
            artifacts=artifacts,
        )
        
        assert len(result.artifacts) == 2
        assert result.artifacts[0].artifact_type == "request_json"
    
    def test_to_dict_success(self):
        """Test to_dict for successful result."""
        result = HandlerResult.success(
            output={"key": "value"},
            metrics={"duration_ms": 500},
        )
        
        data = result.to_dict()
        
        assert data["status"] == "SUCCEEDED"
        assert data["output"] == {"key": "value"}
        assert data["metrics"] == {"duration_ms": 500}
        assert "error_message" not in data
    
    def test_to_dict_failure(self):
        """Test to_dict for failed result."""
        result = HandlerResult.failure(
            error_message="Failed",
            validation_errors=["Error 1", "Error 2"],
        )
        
        data = result.to_dict()
        
        assert data["status"] == "FAILED"
        assert data["error_message"] == "Failed"
        assert data["validation_errors"] == ["Error 1", "Error 2"]
        assert "output" not in data
    
    def test_to_dict_skipped(self):
        """Test to_dict for skipped result."""
        result = HandlerResult.skipped(reason="Already processed")
        
        data = result.to_dict()
        
        assert data["status"] == "SKIPPED"
        assert data["skipped_reason"] == "Already processed"
