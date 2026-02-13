"""
Unit tests for the relationship extraction handler.

Tests for:
- Handler initialization
- Dry-run mode
- Output validation
- Artifact writing
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from llm.handlers.relationship_extraction import (
    RelationshipExtractionHandler,
    handle,
)
from llm.jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
)


class MockJob:
    """Mock Job object for testing."""
    
    def __init__(self, job_id: str = "test-job-123", input_json: str = "{}"):
        self.job_id = job_id
        self.input_json = input_json


class MockRunContext:
    """Mock RunContext for testing."""
    
    def __init__(
        self,
        run_id: str = "test-run-456",
        job_id: str = "test-job-123",
        execution_mode: ExecutionMode = ExecutionMode.LIVE,
    ):
        self.run_id = run_id
        self.job_id = job_id
        self.execution_mode = execution_mode
        self.is_dry_run = execution_mode == ExecutionMode.DRY_RUN
    
    def get_log_context(self):
        return {"run_id": self.run_id, "job_id": self.job_id}


class TestRelationshipExtractionHandlerInit:
    """Tests for handler initialization."""
    
    def test_handler_creation_no_deps(self):
        """Test handler creation with no dependencies."""
        handler = RelationshipExtractionHandler()
        
        assert handler.ollama_client is None
        assert handler.lake_writer is None
        assert handler.relationship_store is None
    
    def test_handler_creation_with_deps(self):
        """Test handler creation with dependencies."""
        mock_client = MagicMock()
        mock_writer = MagicMock()
        mock_store = MagicMock()
        
        handler = RelationshipExtractionHandler(
            ollama_client=mock_client,
            lake_writer=mock_writer,
            relationship_store=mock_store,
        )
        
        assert handler.ollama_client is mock_client
        assert handler.lake_writer is mock_writer
        assert handler.relationship_store is mock_store
    
    def test_handler_loads_interrogation(self):
        """Test that handler loads interrogation definition lazily."""
        handler = RelationshipExtractionHandler()
        
        interrogation = handler.interrogation
        
        assert interrogation is not None
        assert interrogation.key == "relationship_extraction_v1"


class TestRelationshipExtractionDryRun:
    """Tests for handler dry-run mode."""
    
    def test_dry_run_skips_llm_call(self):
        """Test that dry-run mode skips LLM call."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json=json.dumps({
            "source_id": "test-source",
            "source_page_title": "Test Page",
            "content": "R2-D2 was owned by Luke Skywalker."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)
        
        result = handler.handle(job, ctx)
        
        assert result.status == HandlerStatus.SUCCEEDED
        assert "relationships" in result.output
        assert result.output["relationships"] == []
        assert "DRY-RUN" in result.output["extraction_metadata"]["extraction_notes"]
    
    def test_dry_run_returns_empty_relationships(self):
        """Test that dry-run returns empty relationships array."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json=json.dumps({
            "source_id": "test-source",
            "content": "Some content about droids."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)
        
        result = handler.handle(job, ctx)
        
        assert result.output["relationships"] == []
        assert result.output["extraction_metadata"]["total_relationships_found"] == 0


class TestRelationshipExtractionNoContent:
    """Tests for handler with no content."""
    
    def test_no_content_skips_job(self):
        """Test that job is skipped when no content provided."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json=json.dumps({
            "source_id": "test-source",
            "content": ""
        }))
        ctx = MockRunContext()
        
        result = handler.handle(job, ctx)
        
        assert result.status == HandlerStatus.SKIPPED
        assert "No content" in result.skipped_reason
    
    def test_missing_content_field_skips_job(self):
        """Test that job is skipped when content field is missing."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json=json.dumps({
            "source_id": "test-source"
        }))
        ctx = MockRunContext()
        
        result = handler.handle(job, ctx)
        
        assert result.status == HandlerStatus.SKIPPED


class TestRelationshipExtractionInputParsing:
    """Tests for job input parsing."""
    
    def test_invalid_json_fails(self):
        """Test that invalid JSON input fails the job."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json="not valid json")
        ctx = MockRunContext()
        
        result = handler.handle(job, ctx)
        
        assert result.status == HandlerStatus.FAILED
        assert "JSON" in result.error_message or "json" in result.error_message.lower()


class TestRelationshipExtractionPromptRendering:
    """Tests for prompt rendering."""
    
    def test_prompt_includes_source_info(self):
        """Test that rendered prompt includes source info."""
        handler = RelationshipExtractionHandler()
        
        # We can test this by checking if the handler builds prompts correctly
        # using the interrogation's prompt template
        interrogation = handler.interrogation
        
        assert "{source_id}" in interrogation.prompt_template
        assert "{source_page_title}" in interrogation.prompt_template
        assert "{content}" in interrogation.prompt_template


class TestModuleLevelHandle:
    """Tests for module-level handle function."""
    
    def test_module_handle_dry_run(self):
        """Test module-level handle function in dry-run mode."""
        job = MockJob(input_json=json.dumps({
            "source_id": "test",
            "content": "Test content"
        }))
        
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)
        
        result = handle(job, ctx)
        
        assert result.status == HandlerStatus.SUCCEEDED


class TestRelationshipExtractionMetrics:
    """Tests for handler metrics."""
    
    def test_dry_run_metrics(self):
        """Test that dry-run mode records metrics."""
        handler = RelationshipExtractionHandler()
        
        job = MockJob(input_json=json.dumps({
            "source_id": "test-source",
            "content": "R2-D2 served Luke."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)
        
        result = handler.handle(job, ctx)
        
        assert "handler" in result.metrics
        assert result.metrics["handler"] == "relationship_extraction"
        assert "source_id" in result.metrics
        assert "content_length" in result.metrics
        assert "prompt_length" in result.metrics
