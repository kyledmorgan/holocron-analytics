"""
Lake Writer - Writes artifacts to the filesystem lake.

Provides deterministic paths for artifact storage and computes
content hashes for integrity verification.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass
class ArtifactInfo:
    """Information about a written artifact."""
    lake_uri: str
    content_sha256: str
    byte_count: int
    full_path: Path


@dataclass
class LakeWriterConfig:
    """Configuration for the lake writer."""
    base_dir: str = "lake/llm_runs"
    pretty_print: bool = True
    
    @classmethod
    def from_env(cls) -> "LakeWriterConfig":
        """Create config from environment variables."""
        return cls(
            base_dir=os.environ.get("LAKE_ROOT", "lake/llm_runs"),
            pretty_print=os.environ.get("LAKE_PRETTY_PRINT", "true").lower() == "true",
        )


class LakeWriter:
    """
    Writes LLM artifacts to a structured filesystem lake.
    
    Directory structure:
        {base_dir}/{yyyy}/{mm}/{dd}/{run_id}/
            ├── request.json      # Full Ollama request payload
            ├── response.json     # Full Ollama response
            ├── evidence.json     # Evidence bundle used
            ├── prompt.txt        # Rendered prompt text
            └── output.json       # Parsed/validated output
    
    Example:
        >>> writer = LakeWriter(LakeWriterConfig())
        >>> info = writer.write_json(run_id, "request", request_data)
        >>> print(info.lake_uri)
        'lake/llm_runs/2024/01/15/abc123/request.json'
    """
    
    def __init__(self, config: Optional[LakeWriterConfig] = None):
        """
        Initialize the lake writer.
        
        Args:
            config: Configuration. If None, loads from environment.
        """
        self.config = config or LakeWriterConfig.from_env()
        self.base_dir = Path(self.config.base_dir)
        
        logger.debug(f"LakeWriter initialized: base_dir={self.base_dir}")
    
    def get_run_dir(self, run_id: str, timestamp: Optional[datetime] = None) -> Path:
        """
        Get the directory path for a run.
        
        Args:
            run_id: The run identifier
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Path to the run directory
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        
        return self.base_dir / year / month / day / run_id
    
    def ensure_run_dir(self, run_id: str, timestamp: Optional[datetime] = None) -> Path:
        """
        Ensure the run directory exists.
        
        Args:
            run_id: The run identifier
            timestamp: Optional timestamp
            
        Returns:
            Path to the run directory
        """
        run_dir = self.get_run_dir(run_id, timestamp)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    
    def _compute_lake_uri(self, file_path: Path) -> str:
        """
        Compute a relative lake URI for the given file path.
        
        Always returns a path relative to the base directory for consistency.
        """
        try:
            return str(file_path.relative_to(self.base_dir))
        except ValueError:
            # file_path is not relative to base_dir, use the filename with run info
            return str(file_path)
    
    def write_json(
        self,
        run_id: str,
        artifact_name: str,
        data: Any,
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write a JSON artifact to the lake.
        
        Args:
            run_id: The run identifier
            artifact_name: Name of the artifact (e.g., "request", "response")
            data: Data to serialize as JSON
            timestamp: Optional timestamp for directory path
            
        Returns:
            ArtifactInfo with path and hash
        """
        run_dir = self.ensure_run_dir(run_id, timestamp)
        filename = f"{artifact_name}.json"
        file_path = run_dir / filename
        
        # Serialize to JSON
        indent = 2 if self.config.pretty_print else None
        content = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
        content_bytes = content.encode("utf-8")
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        
        # Calculate hash
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        
        # Build relative lake URI
        lake_uri = self._compute_lake_uri(file_path)
        
        logger.debug(f"Wrote artifact: {file_path} ({len(content_bytes)} bytes)")
        
        return ArtifactInfo(
            lake_uri=lake_uri,
            content_sha256=content_sha256,
            byte_count=len(content_bytes),
            full_path=file_path,
        )
    
    def write_text(
        self,
        run_id: str,
        artifact_name: str,
        content: str,
        extension: str = "txt",
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write a text artifact to the lake.
        
        Args:
            run_id: The run identifier
            artifact_name: Name of the artifact
            content: Text content
            extension: File extension (default: "txt")
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo with path and hash
        """
        run_dir = self.ensure_run_dir(run_id, timestamp)
        filename = f"{artifact_name}.{extension}"
        file_path = run_dir / filename
        
        content_bytes = content.encode("utf-8")
        
        # Write file
        with open(file_path, "wb") as f:
            f.write(content_bytes)
        
        # Calculate hash
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        
        # Build relative lake URI
        lake_uri = self._compute_lake_uri(file_path)
        
        logger.debug(f"Wrote text artifact: {file_path} ({len(content_bytes)} bytes)")
        
        return ArtifactInfo(
            lake_uri=lake_uri,
            content_sha256=content_sha256,
            byte_count=len(content_bytes),
            full_path=file_path,
        )
    
    def write_request(
        self,
        run_id: str,
        request_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write the Ollama request payload.
        
        Args:
            run_id: The run identifier
            request_data: Full request payload
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo for the request artifact
        """
        return self.write_json(run_id, "request", request_data, timestamp)
    
    def write_response(
        self,
        run_id: str,
        response_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write the Ollama response.
        
        Args:
            run_id: The run identifier
            response_data: Full response from Ollama
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo for the response artifact
        """
        return self.write_json(run_id, "response", response_data, timestamp)
    
    def write_evidence(
        self,
        run_id: str,
        evidence_bundle: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write the evidence bundle.
        
        Args:
            run_id: The run identifier
            evidence_bundle: Evidence bundle data
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo for the evidence artifact
        """
        return self.write_json(run_id, "evidence", evidence_bundle, timestamp)
    
    def write_prompt(
        self,
        run_id: str,
        prompt_text: str,
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write the rendered prompt.
        
        Args:
            run_id: The run identifier
            prompt_text: Full prompt text
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo for the prompt artifact
        """
        return self.write_text(run_id, "prompt", prompt_text, "txt", timestamp)
    
    def write_output(
        self,
        run_id: str,
        output_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> ArtifactInfo:
        """
        Write the parsed output.
        
        Args:
            run_id: The run identifier
            output_data: Parsed/validated output
            timestamp: Optional timestamp
            
        Returns:
            ArtifactInfo for the output artifact
        """
        return self.write_json(run_id, "output", output_data, timestamp)
