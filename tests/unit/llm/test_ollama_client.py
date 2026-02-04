"""
Unit tests for the Ollama client.

Tests for:
- Structured output generation
- Model info retrieval
- Request payload building
- Metrics extraction
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from llm.core.types import LLMConfig
from llm.core.exceptions import LLMProviderError
from llm.providers.ollama_client import OllamaClient, OllamaResponse


@pytest.fixture
def llm_config():
    """Create a test LLM config."""
    return LLMConfig(
        provider="ollama",
        model="llama3.2",
        base_url="http://localhost:11434",
        temperature=0.0,
        timeout_seconds=60,
        stream=False,
    )


@pytest.fixture
def client(llm_config):
    """Create a test client."""
    return OllamaClient(llm_config)


class TestOllamaClient:
    """Tests for OllamaClient."""
    
    def test_initialization(self, llm_config):
        """Test client initialization."""
        client = OllamaClient(llm_config)
        
        assert client.base_url == "http://localhost:11434"
        assert client.model == "llama3.2"
        assert client.timeout == 60
        assert client.stream is False
    
    def test_get_full_request_payload_basic(self, client):
        """Test building basic request payload."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"}
        ]
        
        payload = client.get_full_request_payload(messages)
        
        assert payload["model"] == "llama3.2"
        assert payload["messages"] == messages
        assert payload["stream"] is False
        assert "format" not in payload
    
    def test_get_full_request_payload_with_schema(self, client):
        """Test building payload with structured output schema."""
        messages = [{"role": "user", "content": "Extract data"}]
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        
        payload = client.get_full_request_payload(messages, output_schema=schema)
        
        assert payload["format"] == schema
    
    def test_get_full_request_payload_with_options(self, client):
        """Test building payload includes options."""
        messages = [{"role": "user", "content": "Test"}]
        
        payload = client.get_full_request_payload(messages)
        
        assert "options" in payload
        assert payload["options"]["temperature"] == 0.0
    
    def test_extract_metrics_full(self, client):
        """Test extracting metrics from full response."""
        raw_response = {
            "total_duration": 5000000000,
            "load_duration": 1000000000,
            "prompt_eval_count": 100,
            "prompt_eval_duration": 500000000,
            "eval_count": 50,
            "eval_duration": 2500000000,
        }
        
        metrics = client.extract_metrics(raw_response)
        
        assert metrics["total_duration"] == 5000000000
        assert metrics["load_duration"] == 1000000000
        assert metrics["prompt_eval_count"] == 100
        assert metrics["eval_count"] == 50
    
    def test_extract_metrics_partial(self, client):
        """Test extracting metrics from partial response."""
        raw_response = {
            "total_duration": 3000000000,
        }
        
        metrics = client.extract_metrics(raw_response)
        
        assert metrics["total_duration"] == 3000000000
        assert metrics["load_duration"] is None
        assert metrics["prompt_eval_count"] is None
    
    def test_extract_metrics_empty(self, client):
        """Test extracting metrics from empty response."""
        metrics = client.extract_metrics({})
        
        assert metrics["total_duration"] is None
        assert metrics["eval_count"] is None


class TestOllamaClientStructuredOutput:
    """Tests for structured output functionality."""
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_chat_with_structured_output_success(self, mock_urlopen, client):
        """Test successful structured output call."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "model": "llama3.2",
            "message": {"role": "assistant", "content": '{"name": "Luke"}'},
            "done": True,
            "total_duration": 1000000000,
            "prompt_eval_count": 10,
            "eval_count": 5,
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        messages = [{"role": "user", "content": "Extract name"}]
        schema = {"type": "object"}
        
        response = client.chat_with_structured_output(messages, schema)
        
        assert response.success is True
        assert response.content == '{"name": "Luke"}'
        assert response.model == "llama3.2"
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_chat_with_structured_output_uses_format_field(self, mock_urlopen, client):
        """Test that schema is passed in format field."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "{}"},
            "done": True
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test"}]
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}
        
        client.chat_with_structured_output(messages, schema)
        
        # Check that the request included the format field
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode('utf-8'))
        
        assert "format" in payload
        assert payload["format"] == schema
        assert payload["stream"] is False


class TestOllamaClientModelInfo:
    """Tests for model info retrieval."""
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_get_model_info_success(self, mock_urlopen, client):
        """Test successful model info retrieval."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "modelfile": "# Modelfile",
            "parameters": "temperature 0.8",
            "template": "{{ .Prompt }}",
            "details": {
                "parent_model": "",
                "format": "gguf",
                "family": "llama",
                "families": ["llama"],
                "parameter_size": "8B",
                "quantization_level": "Q4_0"
            }
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        info = client.get_model_info()
        
        assert info is not None
        assert "details" in info
        assert info["details"]["family"] == "llama"
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_get_model_info_failure(self, mock_urlopen, client):
        """Test model info retrieval failure returns None."""
        mock_urlopen.side_effect = Exception("Connection refused")
        
        info = client.get_model_info()
        
        assert info is None
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_get_model_digest_success(self, mock_urlopen, client):
        """Test successful digest retrieval."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "details": {
                "digest": "sha256:abc123"
            }
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        digest = client.get_model_digest()
        
        assert digest == "sha256:abc123"
    
    @patch('llm.providers.ollama_client.urlopen')
    def test_get_model_digest_not_found(self, mock_urlopen, client):
        """Test digest not found in response."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "details": {}
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        digest = client.get_model_digest()
        
        assert digest is None


class TestOllamaResponse:
    """Tests for OllamaResponse dataclass."""
    
    def test_success_response(self):
        """Test successful response."""
        response = OllamaResponse(
            success=True,
            content='{"result": "ok"}',
            raw_response={"model": "llama3.2"},
            model="llama3.2",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            done=True,
        )
        
        assert response.success is True
        assert response.content == '{"result": "ok"}'
        assert response.total_tokens == 15
    
    def test_error_response(self):
        """Test error response."""
        response = OllamaResponse(
            success=False,
            error_message="Model not found"
        )
        
        assert response.success is False
        assert response.error_message == "Model not found"
        assert response.content is None
