"""
Artifact Store - Filesystem storage for LLM-derived artifacts.

Writes derived artifacts and manifests to a data lake structure.
Follows patterns from src/ingest/storage/file_lake.py.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.types import DeriveManifest
from ..core.exceptions import LLMStorageError


logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Filesystem-based storage for LLM-derived artifacts.
    
    Stores artifacts in a structured directory hierarchy:
    {base_dir}/
    ├── manifests/          # Manifest files for reproducibility
    │   └── {manifest_id}.json
    ├── artifacts/          # Derived output artifacts
    │   └── {task_type}/
    │       └── {timestamp}_{manifest_id}.json
    └── raw_responses/      # Raw LLM responses (for debugging)
        └── {timestamp}_{manifest_id}.txt
    
    Example:
        >>> store = ArtifactStore(Path("local/llm_lake"))
        >>> store.write_manifest(manifest)
        >>> store.write_artifact(manifest_id, "entity_extraction", data)
    """
    
    def __init__(
        self,
        base_dir: Path,
        create_dirs: bool = True,
        pretty_print: bool = True,
    ):
        """
        Initialize the artifact store.
        
        Args:
            base_dir: Base directory for the artifact lake
            create_dirs: Whether to create directories automatically
            pretty_print: Whether to pretty-print JSON files
        """
        self.base_dir = Path(base_dir)
        self.create_dirs = create_dirs
        self.pretty_print = pretty_print
        
        self.manifests_dir = self.base_dir / "manifests"
        self.artifacts_dir = self.base_dir / "artifacts"
        self.raw_dir = self.base_dir / "raw_responses"
        
        if create_dirs:
            self._ensure_directories()
        
        logger.debug(f"Initialized ArtifactStore: base_dir={self.base_dir}")
    
    def _ensure_directories(self) -> None:
        """Create directory structure if it doesn't exist."""
        for dir_path in [self.manifests_dir, self.artifacts_dir, self.raw_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def write_manifest(self, manifest: DeriveManifest) -> Path:
        """
        Write a manifest to the store.
        
        Args:
            manifest: The derive manifest to persist
            
        Returns:
            Path to the written manifest file
            
        Raises:
            LLMStorageError: If write fails
        """
        try:
            file_path = self.manifests_dir / f"{manifest.manifest_id}.json"
            
            content = manifest.to_dict()
            
            indent = 2 if self.pretty_print else None
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=indent, ensure_ascii=False)
            
            logger.debug(f"Wrote manifest: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write manifest: {e}")
            raise LLMStorageError(f"Failed to write manifest: {e}")
    
    def read_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """
        Read a manifest from the store.
        
        Args:
            manifest_id: The manifest ID to read
            
        Returns:
            Manifest data as dictionary, or None if not found
        """
        file_path = self.manifests_dir / f"{manifest_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read manifest {manifest_id}: {e}")
            return None
    
    def write_artifact(
        self,
        manifest_id: str,
        task_type: str,
        data: Dict[str, Any],
    ) -> Path:
        """
        Write a derived artifact to the store.
        
        Args:
            manifest_id: Reference to the source manifest
            task_type: Type of derivation task (for directory organization)
            data: The artifact data to persist
            
        Returns:
            Path to the written artifact file
            
        Raises:
            LLMStorageError: If write fails
        """
        try:
            task_dir = self.artifacts_dir / self._sanitize_name(task_type)
            if self.create_dirs:
                task_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{manifest_id[:8]}.json"
            file_path = task_dir / filename
            
            indent = 2 if self.pretty_print else None
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            logger.debug(f"Wrote artifact: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write artifact: {e}")
            raise LLMStorageError(f"Failed to write artifact: {e}")
    
    def write_raw_response(
        self,
        manifest_id: str,
        content: str,
    ) -> Path:
        """
        Write a raw LLM response to the store.
        
        Args:
            manifest_id: Reference to the source manifest
            content: Raw response content
            
        Returns:
            Path to the written file
            
        Raises:
            LLMStorageError: If write fails
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{manifest_id[:8]}.txt"
            file_path = self.raw_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.debug(f"Wrote raw response: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write raw response: {e}")
            raise LLMStorageError(f"Failed to write raw response: {e}")
    
    def hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a string for use in directory/file names."""
        safe = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
        if len(safe) > 100:
            safe = safe[:100]
        return safe or "unknown"
    
    def list_manifests(self, limit: int = 100) -> list:
        """
        List manifest IDs in the store.
        
        Args:
            limit: Maximum number of manifests to return
            
        Returns:
            List of manifest IDs (most recent first)
        """
        try:
            files = sorted(
                self.manifests_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            return [f.stem for f in files[:limit]]
        except Exception as e:
            logger.error(f"Failed to list manifests: {e}")
            return []
