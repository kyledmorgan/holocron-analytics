"""
Ollama LLM provider client.

Thin HTTP client for interacting with Ollama's REST API.
Supports both native Ollama API and OpenAI-compatible endpoints.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
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
