"""
Ollama LLM provider client.

Thin HTTP client for interacting with Ollama's REST API.
Supports both native Ollama API and OpenAI-compatible endpoints.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from ..core.exceptions import LLMProviderError
from ..core.types import LLMConfig


logger = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """
    Response from Ollama API.
    
    Attributes:
        success: Whether the request succeeded
        content: The generated text content
        raw_response: Full response JSON
        model: Model that generated the response
        prompt_tokens: Number of prompt tokens (if available)
        completion_tokens: Number of completion tokens (if available)
        total_tokens: Total tokens used (if available)
        done: Whether generation is complete (for streaming)
    """
    success: bool
    content: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    done: bool = True
    error_message: Optional[str] = None


class OllamaClient:
    """
    HTTP client for Ollama LLM provider.
    
    Supports two API modes:
    - Native Ollama API (/api/generate, /api/chat)
    - OpenAI-compatible API (/v1/chat/completions)
    
    Default mode is non-streaming for deterministic capture in this system.
    
    Example:
        >>> config = LLMConfig(provider="ollama", model="llama3.2")
        >>> client = OllamaClient(config)
        >>> response = client.generate("What is 2+2?")
        >>> print(response.content)
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize the Ollama client.
        
        Args:
            config: LLM configuration with provider settings
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.timeout = config.timeout_seconds
        self.stream = config.stream
        
        # Determine API mode from config or default to native
        self.api_mode = config.extra_params.get("api_mode", "native")
        
        logger.debug(
            f"Initialized OllamaClient: base_url={self.base_url}, "
            f"model={self.model}, api_mode={self.api_mode}"
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> OllamaResponse:
        """
        Generate a response using the native /api/generate endpoint.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters passed to the API
            
        Returns:
            OllamaResponse with the generated content
            
        Raises:
            LLMProviderError: If the request fails
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": self.stream,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        # Add optional parameters
        if self.config.temperature is not None:
            payload.setdefault("options", {})["temperature"] = self.config.temperature
        
        if self.config.max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = self.config.max_tokens
        
        # Merge any additional kwargs
        payload.update(kwargs)
        
        return self._make_request(url, payload)
    
    def chat(
        self,
        messages: list,
        **kwargs
    ) -> OllamaResponse:
        """
        Generate a response using the native /api/chat endpoint.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters passed to the API
            
        Returns:
            OllamaResponse with the generated content
            
        Raises:
            LLMProviderError: If the request fails
            
        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ]
            >>> response = client.chat(messages)
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
        }
        
        # Add optional parameters
        if self.config.temperature is not None:
            payload.setdefault("options", {})["temperature"] = self.config.temperature
        
        if self.config.max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = self.config.max_tokens
        
        # Merge any additional kwargs
        payload.update(kwargs)
        
        return self._make_request(url, payload, is_chat=True)
    
    def chat_completions(
        self,
        messages: list,
        **kwargs
    ) -> OllamaResponse:
        """
        Generate a response using the OpenAI-compatible /v1/chat/completions endpoint.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters passed to the API
            
        Returns:
            OllamaResponse with the generated content
            
        Raises:
            LLMProviderError: If the request fails
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
        }
        
        # Add optional parameters (OpenAI format)
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        
        if self.config.max_tokens is not None:
            payload["max_tokens"] = self.config.max_tokens
        
        # Merge any additional kwargs
        payload.update(kwargs)
        
        return self._make_request(url, payload, is_openai_compat=True)
    
    def health_check(self) -> bool:
        """
        Check if Ollama is reachable and the model is available.
        
        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            request = Request(url, method="GET")
            
            with urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                    model_base = self.model.split(":")[0]
                    if model_base in models or self.model in [m.get("name") for m in data.get("models", [])]:
                        logger.debug(f"Health check passed: model {self.model} available")
                        return True
                    else:
                        logger.warning(f"Model {self.model} not found. Available: {models}")
                        return False
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
        
        return False
    
    def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
        is_chat: bool = False,
        is_openai_compat: bool = False,
    ) -> OllamaResponse:
        """
        Make an HTTP request to the Ollama API.
        
        Args:
            url: Full URL to request
            payload: Request payload
            is_chat: Whether this is a chat endpoint (affects response parsing)
            is_openai_compat: Whether this is an OpenAI-compatible endpoint
            
        Returns:
            OllamaResponse with the result
            
        Raises:
            LLMProviderError: If the request fails
        """
        try:
            data = json.dumps(payload).encode("utf-8")
            request = Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            logger.debug(f"Making request to {url}")
            
            with urlopen(request, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                result = json.loads(response_data)
                
                return self._parse_response(result, is_chat, is_openai_compat)
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"HTTP error from Ollama: {e.code} - {error_body}")
            raise LLMProviderError(
                f"Ollama API error: {e.code} - {error_body}",
                provider="ollama",
                status_code=e.code,
            )
        except URLError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise LLMProviderError(
                f"Failed to connect to Ollama at {self.base_url}: {e}",
                provider="ollama",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ollama: {e}")
            raise LLMProviderError(
                f"Invalid JSON response from Ollama: {e}",
                provider="ollama",
            )
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            raise LLMProviderError(
                f"Unexpected error calling Ollama: {e}",
                provider="ollama",
            )
    
    def _parse_response(
        self,
        result: Dict[str, Any],
        is_chat: bool,
        is_openai_compat: bool,
    ) -> OllamaResponse:
        """Parse API response into OllamaResponse."""
        if is_openai_compat:
            # OpenAI-compatible format
            choices = result.get("choices", [])
            content = choices[0]["message"]["content"] if choices else None
            usage = result.get("usage", {})
            
            return OllamaResponse(
                success=True,
                content=content,
                raw_response=result,
                model=result.get("model"),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                done=True,
            )
        elif is_chat:
            # Native chat format
            message = result.get("message", {})
            content = message.get("content")
            
            return OllamaResponse(
                success=True,
                content=content,
                raw_response=result,
                model=result.get("model"),
                prompt_tokens=result.get("prompt_eval_count"),
                completion_tokens=result.get("eval_count"),
                total_tokens=(result.get("prompt_eval_count", 0) or 0) + (result.get("eval_count", 0) or 0),
                done=result.get("done", True),
            )
        else:
            # Native generate format
            return OllamaResponse(
                success=True,
                content=result.get("response"),
                raw_response=result,
                model=result.get("model"),
                prompt_tokens=result.get("prompt_eval_count"),
                completion_tokens=result.get("eval_count"),
                total_tokens=(result.get("prompt_eval_count", 0) or 0) + (result.get("eval_count", 0) or 0),
                done=result.get("done", True),
            )
    
    def chat_with_structured_output(
        self,
        messages: list,
        output_schema: Dict[str, Any],
        **kwargs
    ) -> OllamaResponse:
        """
        Generate a response using structured output (JSON schema).
        
        Uses Ollama's native structured output support by passing the
        JSON schema in the 'format' field.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            output_schema: JSON schema for the expected output
            **kwargs: Additional parameters passed to the API
            
        Returns:
            OllamaResponse with structured JSON content
            
        Raises:
            LLMProviderError: If the request fails
            
        Example:
            >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
            >>> messages = [{"role": "user", "content": "Extract the name"}]
            >>> response = client.chat_with_structured_output(messages, schema)
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,  # Always non-streaming for structured output
            "format": output_schema,  # Pass schema as format for structured output
        }
        
        # Add optional parameters
        if self.config.temperature is not None:
            payload.setdefault("options", {})["temperature"] = self.config.temperature
        
        if self.config.max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = self.config.max_tokens
        
        # Merge any additional kwargs
        payload.update(kwargs)
        
        return self._make_request(url, payload, is_chat=True)
    
    def get_model_info(self, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get model information from Ollama /api/show endpoint.
        
        Args:
            model_name: Model name to query (defaults to configured model)
            
        Returns:
            Model information dict, or None if request fails
        """
        model = model_name or self.model
        url = f"{self.base_url}/api/show"
        
        try:
            payload = {"name": model}
            data = json.dumps(payload).encode("utf-8")
            request = Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result
                
        except Exception as e:
            logger.warning(f"Failed to get model info for {model}: {e}")
            return None
    
    def get_model_digest(self, model_name: Optional[str] = None) -> Optional[str]:
        """
        Get the model digest (hash) for reproducibility tracking.
        
        Args:
            model_name: Model name to query (defaults to configured model)
            
        Returns:
            Model digest string, or None if not available
        """
        info = self.get_model_info(model_name)
        if info:
            # Try to extract digest from modelinfo or details
            details = info.get("details", {})
            if "digest" in details:
                return details["digest"]
            # Also check top-level
            if "digest" in info:
                return info["digest"]
        return None
    
    def get_full_request_payload(
        self,
        messages: list,
        output_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build the full request payload for logging/artifact capture.
        
        Args:
            messages: List of message dicts
            output_schema: Optional JSON schema for structured output
            **kwargs: Additional parameters
            
        Returns:
            Complete request payload dict
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        
        if output_schema:
            payload["format"] = output_schema
        
        options = {}
        if self.config.temperature is not None:
            options["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            options["num_predict"] = self.config.max_tokens
        
        if options:
            payload["options"] = options
        
        payload.update(kwargs)
        return payload
    
    def extract_metrics(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from a raw Ollama response.
        
        Args:
            raw_response: The raw response dict from Ollama
            
        Returns:
            Dict with standardized metrics
        """
        return {
            "total_duration": raw_response.get("total_duration"),
            "load_duration": raw_response.get("load_duration"),
            "prompt_eval_count": raw_response.get("prompt_eval_count"),
            "prompt_eval_duration": raw_response.get("prompt_eval_duration"),
            "eval_count": raw_response.get("eval_count"),
            "eval_duration": raw_response.get("eval_duration"),
        }
    
    def embed(
        self,
        texts: list,
        model: Optional[str] = None,
    ) -> "EmbeddingResponse":
        """
        Generate embeddings for a list of texts using Ollama's /api/embed endpoint.
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to self.model or OLLAMA_EMBED_MODEL)
            
        Returns:
            EmbeddingResponse with embeddings and metadata
            
        Raises:
            LLMProviderError: If the request fails
            
        Example:
            >>> response = client.embed(["Hello world", "Test text"])
            >>> print(len(response.embeddings))  # 2
            >>> print(len(response.embeddings[0]))  # vector dimension
        """
        import os
        
        # Determine embedding model
        embed_model = model or os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        
        url = f"{self.base_url}/api/embed"
        
        # Ollama supports either a single prompt or array of inputs
        payload = {
            "model": embed_model,
            "input": texts,
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            request = Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            logger.debug(f"Making embedding request to {url} with model {embed_model}")
            
            with urlopen(request, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                result = json.loads(response_data)
                
                # Parse embeddings response
                embeddings = result.get("embeddings", [])
                
                return EmbeddingResponse(
                    success=True,
                    embeddings=embeddings,
                    model=result.get("model", embed_model),
                    raw_response=result,
                    total_duration=result.get("total_duration"),
                    load_duration=result.get("load_duration"),
                )
                
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"HTTP error from Ollama embed: {e.code} - {error_body}")
            raise LLMProviderError(
                f"Ollama embed API error: {e.code} - {error_body}",
                provider="ollama",
                status_code=e.code,
            )
        except URLError as e:
            logger.error(f"Failed to connect to Ollama for embedding: {e}")
            raise LLMProviderError(
                f"Failed to connect to Ollama at {self.base_url}: {e}",
                provider="ollama",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ollama embed: {e}")
            raise LLMProviderError(
                f"Invalid JSON response from Ollama embed: {e}",
                provider="ollama",
            )
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama embed: {e}")
            raise LLMProviderError(
                f"Unexpected error calling Ollama embed: {e}",
                provider="ollama",
            )


@dataclass
class EmbeddingResponse:
    """
    Response from Ollama embeddings API.
    
    Attributes:
        success: Whether the request succeeded
        embeddings: List of embedding vectors (each is list of floats)
        model: Model that generated the embeddings
        raw_response: Full response JSON
        total_duration: Total time in nanoseconds
        load_duration: Model load time in nanoseconds
        error_message: Error message if failed
    """
    success: bool
    embeddings: list = field(default_factory=list)
    model: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    error_message: Optional[str] = None
