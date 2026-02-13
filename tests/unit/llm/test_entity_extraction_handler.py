"""
Unit tests for the droid entity extraction handler.

Tests for:
- Handler creation and initialization
- Job input parsing
- Prompt rendering
- Dry-run mode behavior
- Result handling
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from llm.contracts.phase1_contracts import Job
from llm.jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
)
from llm.handlers.entity_extraction_droid import (
    EntityExtractionDroidHandler,
    handle,
)


class TestEntityExtractionDroidHandler:
    """Tests for EntityExtractionDroidHandler."""
    
    @pytest.fixture
    def mock_job(self):
        """Create a mock job for testing."""
        return Job(
            job_id="test-job-001",
            interrogation_key="entity_extraction_droid_v1",
            input_json=json.dumps({
                "source_id": "test-source-001",
                "source_page_title": "R2-D2",
                "content": "R2-D2 was an astromech droid manufactured by Industrial Automaton."
            }),
        )
    
    @pytest.fixture
    def mock_ctx_dry_run(self):
        """Create a dry-run context for testing."""
        return RunContext(
            job_id="test-job-001",
            run_id="test-run-001",
            correlation_id="test-job-001-test-run",
            worker_id="test-worker",
            execution_mode=ExecutionMode.DRY_RUN,
            job_type="entity_extraction_droid",
            interrogation_key="entity_extraction_droid_v1",
        )
    
    @pytest.fixture
    def mock_ctx_live(self):
        """Create a live context for testing."""
        return RunContext(
            job_id="test-job-001",
            run_id="test-run-001",
            correlation_id="test-job-001-test-run",
            worker_id="test-worker",
            execution_mode=ExecutionMode.LIVE,
            job_type="entity_extraction_droid",
            interrogation_key="entity_extraction_droid_v1",
        )
    
    def test_handler_creation(self):
        """Test handler can be created."""
        handler = EntityExtractionDroidHandler()
        
        assert handler is not None
        assert handler.ollama_client is None
        assert handler.lake_writer is None
    
    def test_handler_creation_with_dependencies(self):
        """Test handler can be created with dependencies."""
        mock_client = Mock()
        mock_writer = Mock()
        mock_store = Mock()
        
        handler = EntityExtractionDroidHandler(
            ollama_client=mock_client,
            lake_writer=mock_writer,
            entity_store=mock_store,
        )
        
        assert handler.ollama_client is mock_client
        assert handler.lake_writer is mock_writer
        assert handler.entity_store is mock_store
    
    def test_handler_lazy_loads_interrogation(self):
        """Test handler lazily loads interrogation definition."""
        handler = EntityExtractionDroidHandler()
        
        # Access interrogation property
        interrogation = handler.interrogation
        
        assert interrogation is not None
        assert interrogation.key == "entity_extraction_droid_v1"
    
    def test_dry_run_mode_skips_llm_call(self, mock_job, mock_ctx_dry_run):
        """Test that dry-run mode skips LLM call."""
        mock_client = Mock()
        handler = EntityExtractionDroidHandler(ollama_client=mock_client)
        
        result = handler.handle(mock_job, mock_ctx_dry_run)
        
        # LLM should not be called in dry-run mode
        mock_client.generate.assert_not_called()
        
        # Result should indicate dry-run
        assert result.succeeded
        assert result.output.get("extraction_metadata", {}).get("extraction_notes") == "DRY-RUN: LLM call skipped"
    
    def test_dry_run_mode_writes_artifacts(self, mock_job, mock_ctx_dry_run):
        """Test that dry-run mode still writes artifacts."""
        mock_writer = Mock()
        mock_writer.write_text.return_value = Mock(
            lake_uri="lake://test/artifact.txt",
            content_sha256="abc123",
            byte_count=100,
        )
        
        handler = EntityExtractionDroidHandler(lake_writer=mock_writer)
        
        result = handler.handle(mock_job, mock_ctx_dry_run)
        
        # Artifacts should be written
        assert mock_writer.write_text.called or mock_writer.write_json.called
        assert result.succeeded
    
    def test_empty_content_returns_skipped(self, mock_ctx_dry_run):
        """Test that empty content returns skipped result."""
        job = Job(
            job_id="test-job-002",
            interrogation_key="entity_extraction_droid_v1",
            input_json=json.dumps({
                "source_id": "test-source-002",
                "content": ""
            }),
        )
        
        handler = EntityExtractionDroidHandler()
        
        result = handler.handle(job, mock_ctx_dry_run)
        
        assert result.status == HandlerStatus.SKIPPED
        assert "content" in result.skipped_reason.lower()
    
    def test_invalid_json_input_fails(self, mock_ctx_dry_run):
        """Test that invalid JSON input fails."""
        job = Job(
            job_id="test-job-003",
            interrogation_key="entity_extraction_droid_v1",
            input_json="not valid json",
        )
        
        handler = EntityExtractionDroidHandler()
        
        result = handler.handle(job, mock_ctx_dry_run)
        
        assert result.failed
        assert "JSON" in result.error_message or "json" in result.error_message.lower()
    
    def test_prompt_rendering(self, mock_job, mock_ctx_dry_run):
        """Test that prompt is rendered correctly."""
        handler = EntityExtractionDroidHandler()
        
        job_input = json.loads(mock_job.input_json)
        prompt = handler._render_prompt(
            source_id=job_input["source_id"],
            source_title=job_input["source_page_title"],
            content=job_input["content"],
        )
        
        assert "test-source-001" in prompt
        assert "R2-D2" in prompt
        assert "astromech droid" in prompt
    
    def test_live_mode_calls_llm(self, mock_job, mock_ctx_live):
        """Test that live mode calls LLM."""
        mock_client = Mock()
        mock_client.generate.return_value = {
            "response": json.dumps({
                "entities": [
                    {"name": "R2-D2", "type": "Droid", "confidence": 1.0}
                ],
                "relationships": [],
                "extraction_metadata": {}
            })
        }
        
        handler = EntityExtractionDroidHandler(ollama_client=mock_client)
        
        result = handler.handle(mock_job, mock_ctx_live)
        
        # LLM should be called in live mode
        mock_client.generate.assert_called_once()
        assert result.succeeded
    
    def test_validation_errors_fail_handler(self, mock_job, mock_ctx_live):
        """Test that validation errors cause handler to fail."""
        mock_client = Mock()
        # Return invalid output (missing required fields)
        mock_client.generate.return_value = {
            "response": json.dumps({
                "entities": [
                    {"name": "R2-D2"}  # Missing type and confidence
                ]
            })
        }
        
        handler = EntityExtractionDroidHandler(ollama_client=mock_client)
        
        result = handler.handle(mock_job, mock_ctx_live)
        
        assert result.failed
        assert len(result.validation_errors) > 0
    
    def test_metrics_tracked(self, mock_job, mock_ctx_dry_run):
        """Test that metrics are tracked."""
        handler = EntityExtractionDroidHandler()
        
        result = handler.handle(mock_job, mock_ctx_dry_run)
        
        assert "handler" in result.metrics
        assert "execution_mode" in result.metrics
        assert "content_length" in result.metrics
    
    def test_parse_llm_output_extracts_json(self):
        """Test that _parse_llm_output handles markdown-wrapped JSON."""
        handler = EntityExtractionDroidHandler()
        
        # Test plain JSON
        plain_json = '{"entities": []}'
        result = handler._parse_llm_output(plain_json)
        assert result == {"entities": []}
        
        # Test markdown-wrapped JSON
        markdown_json = '''```json
        {"entities": []}
        ```'''
        result = handler._parse_llm_output(markdown_json)
        assert result == {"entities": []}


class TestModuleLevelHandle:
    """Tests for the module-level handle function."""
    
    def test_handle_function_exists(self):
        """Test that handle function exists and is callable."""
        assert callable(handle)
    
    def test_handle_creates_handler(self):
        """Test that handle creates a handler and delegates."""
        job = Job(
            job_id="test-job-010",
            interrogation_key="entity_extraction_droid_v1",
            input_json=json.dumps({
                "source_id": "test-source-010",
                "content": ""  # Empty to trigger skip
            }),
        )
        
        ctx = RunContext(
            job_id="test-job-010",
            run_id="test-run-010",
            correlation_id="test-job-010-test-run",
            worker_id="test-worker",
            execution_mode=ExecutionMode.DRY_RUN,
        )
        
        result = handle(job, ctx)
        
        # Should return a HandlerResult
        assert isinstance(result, HandlerResult)


class TestJobTypeRegistration:
    """Tests for job type registration in the registry."""
    
    def test_entity_extraction_droid_job_type_registered(self):
        """Test that entity_extraction_droid is registered in job type registry."""
        from llm.jobs.registry import get_job_type
        
        definition = get_job_type("entity_extraction_droid")
        
        assert definition is not None
        assert definition.job_type == "entity_extraction_droid"
        assert definition.display_name == "Droid Entity Extraction"
        assert definition.interrogation_key == "entity_extraction_droid_v1"
    
    def test_entity_extraction_droid_has_valid_interrogation(self):
        """Test that entity_extraction_droid points to valid interrogation."""
        from llm.jobs.registry import get_job_type
        
        definition = get_job_type("entity_extraction_droid")
        
        assert definition is not None
        interrogation = definition.get_interrogation()
        
        assert interrogation is not None
        assert interrogation.key == "entity_extraction_droid_v1"
