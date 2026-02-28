"""
Unit tests for structured output enforcement and payload lineage.

Tests that:
- RelationshipExtractionHandler uses chat_with_structured_output (not generate)
- Full request and response payloads are persisted as SQL-first artifacts
- Schema metadata (key, version) is tracked in handler metrics
- get_schema_for_ollama strips JSON Schema metadata fields
- work_context nullability is aligned across schema, examples, and validator
"""

import hashlib
import json
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from llm.handlers.relationship_extraction import RelationshipExtractionHandler
from llm.interrogations.registry import InterrogationDefinition, get_interrogation
from llm.interrogations.definitions.relationship_extraction import (
    create_relationship_extraction_v1,
    validate_relationship_extraction_output,
    SYSTEM_PROMPT,
)
from llm.jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
)


class MockJob:
    """Mock Job object for testing."""

    def __init__(self, job_id: str = "test-job-001", input_json: str = "{}"):
        self.job_id = job_id
        self.input_json = input_json


class MockRunContext:
    """Mock RunContext for testing."""

    def __init__(
        self,
        run_id: str = "test-run-001",
        job_id: str = "test-job-001",
        execution_mode: ExecutionMode = ExecutionMode.LIVE,
    ):
        self.run_id = run_id
        self.job_id = job_id
        self.execution_mode = execution_mode
        self.is_dry_run = execution_mode == ExecutionMode.DRY_RUN

    def get_log_context(self):
        return {"run_id": self.run_id, "job_id": self.job_id}


# ---------------------------------------------------------------------------
# Schema alignment tests
# ---------------------------------------------------------------------------

class TestSchemaForOllama:
    """Tests for get_schema_for_ollama stripping metadata."""

    def test_strips_json_schema_metadata(self):
        """Test that $schema, $id, title, description, version are removed."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://example.com/schema",
            "title": "Test Schema",
            "description": "A test schema",
            "version": "1.0.0",
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        defn = InterrogationDefinition(
            key="test", name="Test", version="1.0",
            description="Test", prompt_template="test",
            output_schema=schema,
        )

        ollama_schema = defn.get_schema_for_ollama()

        assert "$schema" not in ollama_schema
        assert "$id" not in ollama_schema
        assert "title" not in ollama_schema
        assert "description" not in ollama_schema
        assert "version" not in ollama_schema
        # Structural fields preserved
        assert ollama_schema["type"] == "object"
        assert ollama_schema["required"] == ["name"]
        assert ollama_schema["properties"] == {"name": {"type": "string"}}

    def test_does_not_mutate_original(self):
        """Test that original output_schema is not mutated."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
        }
        defn = InterrogationDefinition(
            key="test", name="Test", version="1.0",
            description="Test", prompt_template="test",
            output_schema=schema,
        )

        defn.get_schema_for_ollama()

        assert "$schema" in defn.output_schema

    def test_relationship_extraction_schema_ready_for_ollama(self):
        """Test relationship_extraction_v1 schema is Ollama-ready after stripping."""
        defn = create_relationship_extraction_v1()
        ollama_schema = defn.get_schema_for_ollama()

        assert "$schema" not in ollama_schema
        assert "type" in ollama_schema
        assert ollama_schema["type"] == "object"
        assert "relationships" in ollama_schema.get("required", [])


# ---------------------------------------------------------------------------
# work_context nullability alignment
# ---------------------------------------------------------------------------

class TestWorkContextNullability:
    """Tests that work_context is nullable across schema, examples, validator."""

    def test_schema_allows_null_work_context(self):
        """Test that the JSON contract allows null for work_context."""
        defn = create_relationship_extraction_v1()
        rel_items = defn.output_schema["properties"]["relationships"]["items"]
        wc = rel_items["properties"]["work_context"]
        assert wc["type"] == ["array", "null"]

    def test_validator_accepts_null_work_context(self):
        """Test that the validator accepts null work_context."""
        output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "served",
                    "confidence": 1.0,
                    "work_context": None,
                }
            ]
        }
        errors = validate_relationship_extraction_output(output)
        assert errors == []

    def test_examples_use_null_work_context(self):
        """Test that system prompt examples use null for work_context when absent."""
        assert '"work_context": null' in SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Structured output usage
# ---------------------------------------------------------------------------

class TestStructuredOutputUsage:
    """Tests that handler calls chat_with_structured_output with schema."""

    def _make_handler_with_mocks(self):
        """Create handler with mocked Ollama client and queue."""
        mock_client = MagicMock()
        mock_queue = MagicMock()
        mock_queue.create_artifact.return_value = "artifact-001"

        handler = RelationshipExtractionHandler(
            ollama_client=mock_client,
            queue=mock_queue,
        )
        return handler, mock_client, mock_queue

    def test_call_llm_uses_chat_with_structured_output(self):
        """Test that _call_llm calls chat_with_structured_output, not generate."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        # Configure mock response
        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {"message": {"content": '{"relationships": []}'}}
        mock_client.chat_with_structured_output.return_value = mock_response
        mock_client.get_full_request_payload.return_value = {"model": "llama3.2"}

        ctx = MockRunContext()
        result = handler._call_llm("test prompt", ctx)

        # Verify chat_with_structured_output was called
        mock_client.chat_with_structured_output.assert_called_once()
        call_kwargs = mock_client.chat_with_structured_output.call_args

        # Verify output_schema is passed (structured output enforcement)
        assert "output_schema" in call_kwargs.kwargs or len(call_kwargs.args) >= 2

        # Verify generate was NOT called
        mock_client.generate.assert_not_called()

    def test_call_llm_passes_stripped_schema(self):
        """Test that _call_llm passes schema without JSON Schema metadata."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {}
        mock_client.chat_with_structured_output.return_value = mock_response
        mock_client.get_full_request_payload.return_value = {}

        ctx = MockRunContext()
        handler._call_llm("test prompt", ctx)

        call_kwargs = mock_client.chat_with_structured_output.call_args
        schema = call_kwargs.kwargs.get("output_schema") or call_kwargs.args[1]
        assert "$schema" not in schema
        assert "$id" not in schema

    def test_call_llm_builds_chat_messages(self):
        """Test that _call_llm builds system + user messages."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {}
        mock_client.chat_with_structured_output.return_value = mock_response
        mock_client.get_full_request_payload.return_value = {}

        ctx = MockRunContext()
        handler._call_llm("my test prompt", ctx)

        call_kwargs = mock_client.chat_with_structured_output.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]

        # Should have system + user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "my test prompt"


# ---------------------------------------------------------------------------
# SQL-first artifact persistence
# ---------------------------------------------------------------------------

class TestSQLFirstArtifactPersistence:
    """Tests that handler persists request/response payloads to SQL."""

    def _make_handler_with_mocks(self):
        mock_client = MagicMock()
        mock_queue = MagicMock()
        mock_queue.create_artifact.return_value = "artifact-001"

        handler = RelationshipExtractionHandler(
            ollama_client=mock_client,
            queue=mock_queue,
        )
        return handler, mock_client, mock_queue

    def test_request_payload_persisted_to_sql(self):
        """Test that complete request payload is stored via queue.create_artifact."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        request_payload = {"model": "llama3.2", "messages": [], "format": {}}
        mock_client.get_full_request_payload.return_value = request_payload

        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {"done": True}
        mock_client.chat_with_structured_output.return_value = mock_response

        ctx = MockRunContext()
        handler._call_llm("test prompt", ctx)

        # Verify create_artifact was called for request_json
        create_calls = mock_queue.create_artifact.call_args_list
        request_calls = [
            c for c in create_calls
            if c.kwargs.get("artifact_type") == "request_json"
        ]
        assert len(request_calls) == 1

        req_call = request_calls[0]
        assert req_call.kwargs["stored_in_sql"] is True
        assert req_call.kwargs["content_mime_type"] == "application/json"
        assert req_call.kwargs["content"] is not None
        # Verify content is valid JSON
        parsed = json.loads(req_call.kwargs["content"])
        assert "model" in parsed

    def test_response_payload_persisted_to_sql(self):
        """Test that complete response payload is stored via queue.create_artifact."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_client.get_full_request_payload.return_value = {}

        raw_response = {
            "model": "llama3.2",
            "done": True,
            "message": {"content": '{"relationships": []}'},
            "eval_count": 100,
        }
        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = raw_response
        mock_client.chat_with_structured_output.return_value = mock_response

        ctx = MockRunContext()
        handler._call_llm("test prompt", ctx)

        # Verify create_artifact was called for response_json
        create_calls = mock_queue.create_artifact.call_args_list
        response_calls = [
            c for c in create_calls
            if c.kwargs.get("artifact_type") == "response_json"
        ]
        assert len(response_calls) == 1

        resp_call = response_calls[0]
        assert resp_call.kwargs["stored_in_sql"] is True
        assert resp_call.kwargs["content_mime_type"] == "application/json"
        # Verify response content includes Ollama wrapper metadata
        parsed = json.loads(resp_call.kwargs["content"])
        assert "model" in parsed
        assert "eval_count" in parsed

    def test_artifacts_include_sha256_and_byte_count(self):
        """Test that persisted artifacts include content hash and byte count."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_client.get_full_request_payload.return_value = {"model": "test"}
        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {"done": True}
        mock_client.chat_with_structured_output.return_value = mock_response

        ctx = MockRunContext()
        handler._call_llm("test prompt", ctx)

        for call_args in mock_queue.create_artifact.call_args_list:
            content = call_args.kwargs["content"]
            expected_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            expected_bytes = len(content.encode("utf-8"))
            assert call_args.kwargs["content_sha256"] == expected_sha
            assert call_args.kwargs["byte_count"] == expected_bytes

    def test_normalized_response_artifact_parses_message_content(self):
        """Test normalized artifact stores parsed JSON for message.content."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_client.get_full_request_payload.return_value = {
            "model": "llama3.2",
            "messages": [],
            "format": {"type": "object"},
        }
        raw_response = {
            "message": {
                "role": "assistant",
                "content": '{"relationships": []}',
                "thinking": '{"plan": ["step1"]}',
            }
        }
        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = raw_response
        mock_client.chat_with_structured_output.return_value = mock_response

        handler._call_llm("test prompt", MockRunContext())

        normalized_calls = [
            c for c in mock_queue.create_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "response_normalized_json"
        ]
        assert len(normalized_calls) == 1
        normalized = json.loads(normalized_calls[0].kwargs["content"])
        assert isinstance(normalized["message"]["content"], dict)
        assert isinstance(normalized["message"]["thinking"], dict)
        assert normalized["message"]["content"]["relationships"] == []

    def test_normalized_response_artifact_wraps_non_json_text(self):
        """Test normalized artifact wraps non-JSON message strings."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_client.get_full_request_payload.return_value = {
            "model": "llama3.2",
            "messages": [],
            "format": {"type": "object"},
        }
        mock_response = MagicMock()
        mock_response.content = "plain text output"
        mock_response.raw_response = {
            "message": {"role": "assistant", "content": "plain text output"}
        }
        mock_client.chat_with_structured_output.return_value = mock_response

        handler._call_llm("test prompt", MockRunContext())

        normalized_calls = [
            c for c in mock_queue.create_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "response_normalized_json"
        ]
        assert len(normalized_calls) == 1
        normalized = json.loads(normalized_calls[0].kwargs["content"])
        wrapped = normalized["message"]["content"]
        assert wrapped["type"] == "text"
        assert wrapped["text"] == "plain text output"
        assert "parse_error" in wrapped
        assert wrapped["original_length"] == len("plain text output")

    def test_normalized_response_not_written_without_structured_format(self):
        """Test normalization is skipped when request payload has no JSON format."""
        handler, mock_client, mock_queue = self._make_handler_with_mocks()

        mock_client.get_full_request_payload.return_value = {
            "model": "llama3.2",
            "messages": [],
        }
        mock_response = MagicMock()
        mock_response.content = '{"relationships": []}'
        mock_response.raw_response = {"message": {"content": '{"relationships": []}'}}
        mock_client.chat_with_structured_output.return_value = mock_response

        handler._call_llm("test prompt", MockRunContext())

        normalized_calls = [
            c for c in mock_queue.create_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "response_normalized_json"
        ]
        assert len(normalized_calls) == 0


# ---------------------------------------------------------------------------
# Schema/contract metadata tracking
# ---------------------------------------------------------------------------

class TestSchemaMetadataTracking:
    """Tests that handler tracks schema key and version in metrics."""

    def test_metrics_include_schema_key(self):
        """Test that handler metrics include the interrogation key."""
        handler = RelationshipExtractionHandler()

        job = MockJob(input_json=json.dumps({
            "source_id": "test-src",
            "content": "R2-D2 served Luke Skywalker."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)

        result = handler.handle(job, ctx)

        assert result.metrics["schema_key"] == "relationship_extraction_v1"

    def test_metrics_include_schema_version(self):
        """Test that handler metrics include the schema version."""
        handler = RelationshipExtractionHandler()

        job = MockJob(input_json=json.dumps({
            "source_id": "test-src",
            "content": "R2-D2 served Luke Skywalker."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)

        result = handler.handle(job, ctx)

        assert result.metrics["schema_version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Write artifact with SQL queue
# ---------------------------------------------------------------------------

class TestWriteArtifactWithQueue:
    """Tests that _write_artifact writes to SQL when queue is configured."""

    def test_write_artifact_sql_only(self):
        """Test that _write_artifact works with queue only (no lake_writer)."""
        mock_queue = MagicMock()
        mock_queue.create_artifact.return_value = "art-001"

        handler = RelationshipExtractionHandler(queue=mock_queue)

        timestamp = datetime.now(timezone.utc)
        ref = handler._write_artifact("run-1", "prompt", "test content", timestamp)

        assert ref is not None
        assert ref.artifact_type == "prompt"
        assert ref.content_sha256 == hashlib.sha256(b"test content").hexdigest()
        assert ref.byte_count == len(b"test content")

        mock_queue.create_artifact.assert_called_once()
        call_kwargs = mock_queue.create_artifact.call_args.kwargs
        assert call_kwargs["content"] == "test content"
        assert call_kwargs["stored_in_sql"] is True
        assert call_kwargs["mirrored_to_lake"] is False

    def test_write_artifact_both_lake_and_sql(self):
        """Test that _write_artifact writes to both lake and SQL."""
        mock_queue = MagicMock()
        mock_queue.create_artifact.return_value = "art-002"

        mock_writer = MagicMock()
        mock_lake_result = MagicMock()
        mock_lake_result.lake_uri = "2026/02/21/run-1/prompt.txt"
        mock_lake_result.content_sha256 = "abc123"
        mock_lake_result.byte_count = 12
        mock_writer.write_text.return_value = mock_lake_result

        handler = RelationshipExtractionHandler(
            lake_writer=mock_writer, queue=mock_queue
        )

        timestamp = datetime.now(timezone.utc)
        ref = handler._write_artifact("run-1", "prompt", "test content", timestamp)

        assert ref.lake_uri == "2026/02/21/run-1/prompt.txt"
        mock_writer.write_text.assert_called_once()
        mock_queue.create_artifact.assert_called_once()

        call_kwargs = mock_queue.create_artifact.call_args.kwargs
        assert call_kwargs["mirrored_to_lake"] is True
        assert call_kwargs["lake_uri"] == "2026/02/21/run-1/prompt.txt"

    def test_dry_run_writes_artifacts_with_queue(self):
        """Test that dry-run writes artifacts to SQL when queue configured."""
        mock_queue = MagicMock()
        mock_queue.create_artifact.return_value = "art-003"

        handler = RelationshipExtractionHandler(queue=mock_queue)

        job = MockJob(input_json=json.dumps({
            "source_id": "test-src",
            "content": "R2-D2 served Luke."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)

        result = handler.handle(job, ctx)

        assert result.status == HandlerStatus.SUCCEEDED
        # Should have written prompt, input, and output artifacts
        assert mock_queue.create_artifact.call_count == 3
        artifact_types = [
            c.kwargs["artifact_type"]
            for c in mock_queue.create_artifact.call_args_list
        ]
        assert "prompt" in artifact_types
        assert "input" in artifact_types
        assert "output" in artifact_types


# ---------------------------------------------------------------------------
# Handler backward compatibility
# ---------------------------------------------------------------------------

class TestHandlerBackwardCompatibility:
    """Tests that handler still works without queue (backward compatibility)."""

    def test_handler_works_without_queue(self):
        """Test handler works with no queue and no lake_writer."""
        handler = RelationshipExtractionHandler()

        job = MockJob(input_json=json.dumps({
            "source_id": "test-src",
            "content": "R2-D2 served Luke."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)

        result = handler.handle(job, ctx)
        assert result.status == HandlerStatus.SUCCEEDED

    def test_handler_with_lake_writer_only(self):
        """Test handler works with lake_writer but no queue."""
        mock_writer = MagicMock()
        mock_lake_result = MagicMock()
        mock_lake_result.lake_uri = "test/path.txt"
        mock_lake_result.content_sha256 = "abc"
        mock_lake_result.byte_count = 10
        mock_writer.write_text.return_value = mock_lake_result

        handler = RelationshipExtractionHandler(lake_writer=mock_writer)

        job = MockJob(input_json=json.dumps({
            "source_id": "test-src",
            "content": "R2-D2 served Luke."
        }))
        ctx = MockRunContext(execution_mode=ExecutionMode.DRY_RUN)

        result = handler.handle(job, ctx)
        assert result.status == HandlerStatus.SUCCEEDED
        # Verify lake_writer was used
        assert mock_writer.write_text.call_count >= 1
