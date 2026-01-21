"""
Derive Runner - Orchestrates LLM derive operations.

This is a stub implementation providing the skeleton for derive operations.
Full implementation is planned for Phase 1.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.types import (
    DeriveJobStatus,
    DeriveManifest,
    DeriveResult,
    EvidenceBundle,
    LLMConfig,
)
from ..core.exceptions import LLMConfigError, LLMProviderError, LLMValidationError
from ..providers.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


class DeriveRunner:
    """
    Orchestrates LLM derive operations.
    
    Responsibilities:
    1. Load configuration
    2. Assemble evidence into prompts
    3. Call the LLM provider
    4. Validate and parse responses
    5. Persist artifacts and manifests
    
    This is a stub implementation. Full logic is planned for Phase 1.
    
    Example:
        >>> config = load_config("config/llm.yaml")
        >>> runner = DeriveRunner(config)
        >>> manifest = runner.derive(evidence_bundle, prompt_template)
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the derive runner.
        
        Args:
            config: Configuration dictionary (from YAML)
            output_dir: Directory for output artifacts
        """
        self.config = config
        self.output_dir = output_dir or Path("local/llm_artifacts")
        
        # Parse LLM config
        llm_section = config.get("llm", {})
        self.llm_config = LLMConfig(
            provider=llm_section.get("provider", "ollama"),
            model=llm_section.get("model", "llama3.2"),
            base_url=llm_section.get("base_url", "http://localhost:11434"),
            temperature=llm_section.get("temperature", 0.0),
            max_tokens=llm_section.get("max_tokens"),
            timeout_seconds=llm_section.get("timeout", 120),
            stream=llm_section.get("stream", False),
        )
        
        # Initialize provider client
        self.client: Optional[OllamaClient] = None
        
        logger.info(
            f"Initialized DeriveRunner: provider={self.llm_config.provider}, "
            f"model={self.llm_config.model}"
        )
    
    def _get_client(self) -> OllamaClient:
        """Get or create the LLM provider client."""
        if self.client is None:
            if self.llm_config.provider == "ollama":
                self.client = OllamaClient(self.llm_config)
            else:
                raise LLMConfigError(f"Unsupported provider: {self.llm_config.provider}")
        return self.client
    
    def derive(
        self,
        evidence_bundle: EvidenceBundle,
        prompt_template: str,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> DeriveManifest:
        """
        Execute a derive operation.
        
        Args:
            evidence_bundle: Evidence to use for derivation
            prompt_template: Prompt template with {evidence_content} placeholder
            output_schema: Expected JSON schema for validation (optional)
            
        Returns:
            DeriveManifest with operation results
            
        Raises:
            LLMProviderError: If LLM call fails
            LLMValidationError: If output validation fails
        """
        # Create manifest
        manifest = DeriveManifest(
            evidence_bundle=evidence_bundle,
            llm_config=self.llm_config,
            status=DeriveJobStatus.PENDING,
        )
        
        try:
            manifest.status = DeriveJobStatus.IN_PROGRESS
            start_time = datetime.now(timezone.utc)
            
            # Assemble prompt (stub - just concatenate evidence content)
            evidence_content = self._assemble_evidence(evidence_bundle)
            prompt = prompt_template.replace("{evidence_content}", evidence_content)
            
            # Call LLM
            client = self._get_client()
            response = client.generate(prompt)
            
            if not response.success:
                raise LLMProviderError(
                    response.error_message or "Unknown error",
                    provider=self.llm_config.provider,
                )
            
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Parse JSON response
            parsed_output = self._parse_json_response(response.content)
            
            # Validate against schema (stub - just check it's valid JSON)
            validation_errors = []
            if output_schema:
                validation_errors = self._validate_output(parsed_output, output_schema)
                if validation_errors:
                    manifest.status = DeriveJobStatus.VALIDATION_FAILED
            
            # Persist artifacts
            artifact_path, raw_path = self._persist_artifacts(
                manifest.manifest_id,
                response.content,
                parsed_output,
            )
            
            # Update manifest with results
            manifest.result = DeriveResult(
                success=len(validation_errors) == 0,
                artifact_path=str(artifact_path) if artifact_path else None,
                artifact_hash=self._hash_content(json.dumps(parsed_output)) if parsed_output else None,
                raw_response_path=str(raw_path) if raw_path else None,
                raw_response=response.content,
                parsed_output=parsed_output,
                completed_at=end_time,
                duration_ms=duration_ms,
                token_usage={
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                } if response.total_tokens else None,
                validation_errors=validation_errors,
            )
            
            if not validation_errors:
                manifest.status = DeriveJobStatus.COMPLETED
            
            logger.info(
                f"Derive completed: manifest_id={manifest.manifest_id}, "
                f"status={manifest.status.value}, duration_ms={duration_ms}"
            )
            
        except Exception as e:
            manifest.status = DeriveJobStatus.FAILED
            manifest.result = DeriveResult(
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            logger.error(f"Derive failed: {e}")
            raise
        
        return manifest
    
    def _assemble_evidence(self, bundle: EvidenceBundle) -> str:
        """Assemble evidence items into a single text block."""
        parts = []
        for i, item in enumerate(bundle.items, 1):
            parts.append(f"--- Evidence Item {i} ({item.source_type.value}) ---")
            if item.content:
                if isinstance(item.content, dict):
                    parts.append(json.dumps(item.content, indent=2))
                else:
                    parts.append(str(item.content))
            else:
                parts.append(f"[Content not loaded: {item.source_ref}]")
            parts.append("")
        return "\n".join(parts)
    
    def _parse_json_response(self, content: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse LLM response as JSON."""
        if not content:
            return None
        
        # Try to extract JSON from response (may have markdown code blocks)
        text = content.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            raise LLMValidationError(f"Response is not valid JSON: {e}")
    
    def _validate_output(
        self,
        output: Optional[Dict[str, Any]],
        schema: Dict[str, Any],
    ) -> list:
        """
        Validate output against JSON schema.
        
        Stub implementation - returns empty list.
        Full validation will use jsonschema or similar.
        """
        # TODO: Implement proper JSON schema validation
        if output is None:
            return ["Output is null"]
        return []
    
    def _persist_artifacts(
        self,
        manifest_id: str,
        raw_response: Optional[str],
        parsed_output: Optional[Dict[str, Any]],
    ) -> tuple:
        """
        Persist artifacts to the output directory.
        
        Returns:
            Tuple of (artifact_path, raw_response_path)
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            base_name = f"{timestamp}_{manifest_id[:8]}"
            
            raw_path = None
            artifact_path = None
            
            # Save raw response
            if raw_response:
                raw_path = self.output_dir / f"{base_name}_raw.txt"
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw_response)
            
            # Save parsed output
            if parsed_output:
                artifact_path = self.output_dir / f"{base_name}_output.json"
                with open(artifact_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_output, f, indent=2, ensure_ascii=False)
            
            return artifact_path, raw_path
            
        except Exception as e:
            logger.error(f"Failed to persist artifacts: {e}")
            return None, None
    
    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def health_check(self) -> bool:
        """
        Check if the LLM provider is healthy.
        
        Returns:
            True if provider is reachable and model is available
        """
        try:
            client = self._get_client()
            return client.health_check()
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
