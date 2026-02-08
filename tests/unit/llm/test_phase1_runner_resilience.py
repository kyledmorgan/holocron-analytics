"""
Integration tests for Phase1Runner resilience to invalid JSON.

Tests that the runner:
- Retries Ollama calls on invalid JSON
- Writes error artifacts
- Marks jobs as failed but continues processing
- Does not crash on JSON parse errors
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from llm.runners.phase1_runner import Phase1Runner, RunnerConfig
from llm.providers.ollama_client import OllamaResponse
from llm.core.exceptions import InvalidOllamaJsonError
from llm.contracts.phase1_contracts import Job
from llm.storage.lake_writer import LakeWriter, ArtifactInfo


@pytest.fixture
def mock_job():
    """Create a mock job."""
    job = Mock(spec=Job)
    job.job_id = "test-job-123"
    job.interrogation_key = "entity_facts"
    job.model_hint = None
    job.input_json = '{"entity_type": "person", "entity_id": "luke-skywalker"}'
    job.evidence_ref_json = None
    
    def get_input_mock():
        mock_input = Mock()
        mock_input.entity_type = "person"
        mock_input.entity_id = "luke-skywalker"
        return mock_input
    
    job.get_input = get_input_mock
    return job


@pytest.fixture
def mock_queue():
    """Create a mock job queue."""
    queue = MagicMock()
    queue.claim_next_job.return_value = None
    queue.create_run.return_value = "run-123"
    return queue


@pytest.fixture
def mock_lake_writer():
    """Create a mock lake writer."""
    writer = MagicMock(spec=LakeWriter)
    
    def make_artifact(uri):
        return ArtifactInfo(
            lake_uri=uri,
            content_sha256="abc123",
            byte_count=100,
            full_path=Path("/tmp") / uri
        )
    
    writer.write_request.return_value = make_artifact("request.json")
    writer.write_response.return_value = make_artifact("response.json")
    writer.write_evidence.return_value = make_artifact("evidence.json")
    writer.write_prompt.return_value = make_artifact("prompt.txt")
    writer.write_output.return_value = make_artifact("output.json")
    writer.write_artifact.return_value = make_artifact("error.txt")
    
    return writer


@pytest.fixture
def mock_interrogation():
    """Create a mock interrogation definition."""
    interrogation = Mock()
    interrogation.recommended_model = "llama3.2"
    interrogation.system_prompt = "You are helpful."
    interrogation.prompt_template = "Extract facts about {entity_type} {entity_id}.\n{evidence_content}"
    interrogation.output_schema = {"type": "object"}
    interrogation.validate_output.return_value = []  # No validation errors
    return interrogation


class TestPhase1RunnerInvalidJsonResilience:
    """Tests for Phase1Runner resilience to invalid JSON."""
    
    @patch('llm.runners.phase1_runner.get_interrogation')
    @patch('llm.runners.phase1_runner.build_evidence_bundle')
    @patch('llm.runners.phase1_runner.OllamaClient')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_on_invalid_json_then_succeed(
        self,
        mock_sleep,
        mock_ollama_client_class,
        mock_build_evidence,
        mock_get_interrogation,
        mock_job,
        mock_queue,
        mock_lake_writer,
        mock_interrogation,
    ):
        """Test that runner retries on invalid JSON and succeeds on second attempt."""
        # Setup
        mock_get_interrogation.return_value = mock_interrogation
        
        # Mock evidence bundle
        mock_bundle = Mock()
        mock_bundle.bundle_id = "bundle-123"
        mock_bundle.build_version = "1.0"
        mock_bundle.policy.to_dict.return_value = {}
        mock_bundle.summary = {"total_bytes": 1000}
        mock_bundle.to_dict.return_value = {}
        mock_bundle.items = []
        mock_build_evidence.return_value = mock_bundle
        
        # Mock Ollama client
        mock_client = MagicMock()
        mock_ollama_client_class.return_value = mock_client
        mock_client.get_model_info.return_value = {"digest": "abc123"}
        mock_client.extract_metrics.return_value = {}
        
        # First call returns invalid JSON, second call returns valid JSON
        invalid_response = OllamaResponse(
            success=True,
            content='not valid json at all',
            raw_response={"model": "llama3.2"},
        )
        
        valid_response = OllamaResponse(
            success=True,
            content='{"facts": ["Luke is a Jedi"]}',
            raw_response={"model": "llama3.2"},
        )
        
        mock_client.chat_with_structured_output.side_effect = [
            invalid_response,
            valid_response,
        ]
        
        # Mock queue to return our test job
        mock_queue.claim_next_job.return_value = mock_job
        
        # Create runner
        config = RunnerConfig(worker_id="test-worker")
        runner = Phase1Runner(config, queue=mock_queue, lake_writer=mock_lake_writer)
        
        # Execute
        processed = runner.run_once()
        
        # Verify
        assert processed is True
        assert mock_client.chat_with_structured_output.call_count == 2
        assert mock_sleep.call_count == 1  # One backoff between retries
        mock_queue.mark_succeeded.assert_called_once_with(mock_job.job_id, "run-123")
    
    @patch('llm.runners.phase1_runner.get_interrogation')
    @patch('llm.runners.phase1_runner.build_evidence_bundle')
    @patch('llm.runners.phase1_runner.OllamaClient')
    @patch('time.sleep')
    def test_retry_exhausted_writes_error_manifest(
        self,
        mock_sleep,
        mock_ollama_client_class,
        mock_build_evidence,
        mock_get_interrogation,
        mock_job,
        mock_queue,
        mock_lake_writer,
        mock_interrogation,
    ):
        """Test that runner writes error manifest after exhausting retries."""
        # Setup
        mock_get_interrogation.return_value = mock_interrogation
        
        # Mock evidence bundle
        mock_bundle = Mock()
        mock_bundle.bundle_id = "bundle-123"
        mock_bundle.build_version = "1.0"
        mock_bundle.policy.to_dict.return_value = {}
        mock_bundle.summary = {"total_bytes": 1000}
        mock_bundle.to_dict.return_value = {}
        mock_bundle.items = []
        mock_build_evidence.return_value = mock_bundle
        
        # Mock Ollama client - always returns invalid JSON
        mock_client = MagicMock()
        mock_ollama_client_class.return_value = mock_client
        mock_client.get_model_info.return_value = {"digest": "abc123"}
        mock_client.extract_metrics.return_value = {}
        
        invalid_response = OllamaResponse(
            success=True,
            content='not valid json',
            raw_response={"model": "llama3.2"},
        )
        
        mock_client.chat_with_structured_output.return_value = invalid_response
        
        # Mock queue to return our test job
        mock_queue.claim_next_job.return_value = mock_job
        
        # Create runner
        config = RunnerConfig(worker_id="test-worker")
        runner = Phase1Runner(config, queue=mock_queue, lake_writer=mock_lake_writer)
        
        # Execute
        processed = runner.run_once()
        
        # Verify
        assert processed is True
        assert mock_client.chat_with_structured_output.call_count == 3  # Max retries
        assert mock_sleep.call_count == 2  # Two backoffs
        
        # Check that error artifacts were written
        artifact_calls = mock_lake_writer.write_artifact.call_args_list
        assert len(artifact_calls) >= 2  # At least invalid_json_response and error_manifest
        
        # Verify job marked as failed (but runner continues)
        mock_queue.mark_failed.assert_called_once()
        assert "Invalid JSON" in str(mock_queue.mark_failed.call_args)
    
    @patch('llm.runners.phase1_runner.get_interrogation')
    @patch('llm.runners.phase1_runner.build_evidence_bundle')
    @patch('llm.runners.phase1_runner.OllamaClient')
    def test_embedded_json_extraction(
        self,
        mock_ollama_client_class,
        mock_build_evidence,
        mock_get_interrogation,
        mock_job,
        mock_queue,
        mock_lake_writer,
        mock_interrogation,
    ):
        """Test that runner can extract embedded JSON from text."""
        # Setup
        mock_get_interrogation.return_value = mock_interrogation
        
        # Mock evidence bundle
        mock_bundle = Mock()
        mock_bundle.bundle_id = "bundle-123"
        mock_bundle.build_version = "1.0"
        mock_bundle.policy.to_dict.return_value = {}
        mock_bundle.summary = {"total_bytes": 1000}
        mock_bundle.to_dict.return_value = {}
        mock_bundle.items = []
        mock_build_evidence.return_value = mock_bundle
        
        # Mock Ollama client
        mock_client = MagicMock()
        mock_ollama_client_class.return_value = mock_client
        mock_client.get_model_info.return_value = {"digest": "abc123"}
        mock_client.extract_metrics.return_value = {}
        
        # Response with embedded JSON
        response_with_embedded = OllamaResponse(
            success=True,
            content='Here is the result: {"facts": ["Luke is a Jedi"]} - done',
            raw_response={"model": "llama3.2"},
        )
        
        mock_client.chat_with_structured_output.return_value = response_with_embedded
        
        # Mock queue to return our test job
        mock_queue.claim_next_job.return_value = mock_job
        
        # Create runner
        config = RunnerConfig(worker_id="test-worker")
        runner = Phase1Runner(config, queue=mock_queue, lake_writer=mock_lake_writer)
        
        # Execute
        processed = runner.run_once()
        
        # Verify - should succeed by extracting embedded JSON
        assert processed is True
        mock_queue.mark_succeeded.assert_called_once()
    
    @patch('llm.runners.phase1_runner.get_interrogation')
    @patch('llm.runners.phase1_runner.build_evidence_bundle')
    @patch('llm.runners.phase1_runner.OllamaClient')
    @patch('time.sleep')
    def test_runner_continues_after_invalid_json_failure(
        self,
        mock_sleep,
        mock_ollama_client_class,
        mock_build_evidence,
        mock_get_interrogation,
        mock_queue,
        mock_lake_writer,
        mock_interrogation,
    ):
        """Test that runner continues processing after a job fails with invalid JSON."""
        # Setup
        mock_get_interrogation.return_value = mock_interrogation
        
        # Mock evidence bundle
        mock_bundle = Mock()
        mock_bundle.bundle_id = "bundle-123"
        mock_bundle.build_version = "1.0"
        mock_bundle.policy.to_dict.return_value = {}
        mock_bundle.summary = {"total_bytes": 1000}
        mock_bundle.to_dict.return_value = {}
        mock_bundle.items = []
        mock_build_evidence.return_value = mock_bundle
        
        # Mock Ollama client
        mock_client = MagicMock()
        mock_ollama_client_class.return_value = mock_client
        mock_client.get_model_info.return_value = {"digest": "abc123"}
        mock_client.extract_metrics.return_value = {}
        
        # Always return invalid JSON
        invalid_response = OllamaResponse(
            success=True,
            content='not valid json',
            raw_response={"model": "llama3.2"},
        )
        mock_client.chat_with_structured_output.return_value = invalid_response
        
        # Create two jobs
        job1 = Mock(spec=Job)
        job1.job_id = "job-1"
        job1.interrogation_key = "entity_facts"
        job1.model_hint = None
        job1.input_json = '{}'
        job1.evidence_ref_json = None
        job1.get_input = Mock(return_value=Mock(entity_type="person", entity_id="luke"))
        
        job2 = Mock(spec=Job)
        job2.job_id = "job-2"
        job2.interrogation_key = "entity_facts"
        job2.model_hint = None
        job2.input_json = '{}'
        job2.evidence_ref_json = None
        job2.get_input = Mock(return_value=Mock(entity_type="person", entity_id="leia"))
        
        # Queue returns job1, then job2, then None
        mock_queue.claim_next_job.side_effect = [job1, job2, None]
        mock_queue.create_run.side_effect = ["run-1", "run-2"]
        
        # Create runner
        config = RunnerConfig(worker_id="test-worker")
        runner = Phase1Runner(config, queue=mock_queue, lake_writer=mock_lake_writer)
        
        # Execute - process job 1 (should fail but not crash)
        processed1 = runner.run_once()
        assert processed1 is True
        
        # Execute - process job 2 (should also fail but runner still works)
        processed2 = runner.run_once()
        assert processed2 is True
        
        # Execute - no more jobs
        processed3 = runner.run_once()
        assert processed3 is False
        
        # Verify both jobs were marked as failed
        assert mock_queue.mark_failed.call_count == 2
        
        # Runner never crashed - it processed all jobs
        assert mock_queue.claim_next_job.call_count == 3
