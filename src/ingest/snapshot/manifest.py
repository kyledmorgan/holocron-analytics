"""
Manifest handling for snapshot packs.

The manifest defines dataset mapping, policies, and sync configuration.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SqlTarget:
    """SQL Server target configuration."""
    schema: str = "lake"
    table: str = "RawExchangeRecord"
    natural_key_column: Optional[str] = None
    hash_column: str = "content_sha256"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "table": self.table,
            "natural_key_column": self.natural_key_column,
            "hash_column": self.hash_column,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SqlTarget":
        return cls(
            schema=data.get("schema", "lake"),
            table=data.get("table", "RawExchangeRecord"),
            natural_key_column=data.get("natural_key_column"),
            hash_column=data.get("hash_column", "content_sha256"),
        )


@dataclass
class SyncPolicy:
    """Sync policy configuration."""
    direction_default: str = "bidirectional"
    conflict_strategy: str = "prefer_newest"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction_default": self.direction_default,
            "conflict_strategy": self.conflict_strategy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncPolicy":
        return cls(
            direction_default=data.get("direction_default", "bidirectional"),
            conflict_strategy=data.get("conflict_strategy", "prefer_newest"),
        )


@dataclass
class RedactionPolicy:
    """Redaction policy configuration."""
    enabled: bool = False
    patterns: List[str] = field(default_factory=list)
    headers_to_redact: List[str] = field(default_factory=lambda: [
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "bearer",
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "patterns": self.patterns,
            "headers_to_redact": self.headers_to_redact,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "RedactionPolicy":
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            patterns=data.get("patterns", []),
            headers_to_redact=data.get("headers_to_redact", cls().headers_to_redact),
        )


@dataclass
class EncryptionPolicy:
    """Encryption policy configuration."""
    enabled: bool = False
    algorithm: str = "aes-256-gcm"
    key_source: str = "env"  # 'env', 'file', 'prompt'
    key_env_var: str = "SNAPSHOT_ENCRYPTION_KEY"
    key_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "algorithm": self.algorithm,
            "key_source": self.key_source,
            "key_env_var": self.key_env_var,
            "key_file_path": self.key_file_path,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "EncryptionPolicy":
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            algorithm=data.get("algorithm", "aes-256-gcm"),
            key_source=data.get("key_source", "env"),
            key_env_var=data.get("key_env_var", "SNAPSHOT_ENCRYPTION_KEY"),
            key_file_path=data.get("key_file_path"),
        )


@dataclass
class SnapshotManifest:
    """
    Manifest for a snapshot dataset.
    
    Defines the dataset mapping, policies, and sync configuration.
    """
    dataset_name: str
    exchange_type: str
    source_system: str
    entity_type: str
    description: str = ""
    owner: str = ""
    sql_target: SqlTarget = field(default_factory=SqlTarget)
    sync_policy: SyncPolicy = field(default_factory=SyncPolicy)
    redaction_policy: RedactionPolicy = field(default_factory=RedactionPolicy)
    encryption_policy: EncryptionPolicy = field(default_factory=EncryptionPolicy)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "dataset_name": self.dataset_name,
            "description": self.description,
            "owner": self.owner,
            "exchange_type": self.exchange_type,
            "source_system": self.source_system,
            "entity_type": self.entity_type,
            "sql_target": self.sql_target.to_dict(),
            "sync_policy": self.sync_policy.to_dict(),
            "redaction_policy": self.redaction_policy.to_dict(),
            "encryption_policy": self.encryption_policy.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotManifest":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            dataset_name=data["dataset_name"],
            description=data.get("description", ""),
            owner=data.get("owner", ""),
            exchange_type=data["exchange_type"],
            source_system=data["source_system"],
            entity_type=data["entity_type"],
            sql_target=SqlTarget.from_dict(data.get("sql_target", {})),
            sync_policy=SyncPolicy.from_dict(data.get("sync_policy", {})),
            redaction_policy=RedactionPolicy.from_dict(data.get("redaction_policy")),
            encryption_policy=EncryptionPolicy.from_dict(data.get("encryption_policy")),
            created_at=created_at,
            updated_at=updated_at,
            version=data.get("version", 1),
        )

    def save(self, path: Path) -> None:
        """Save manifest to JSON file."""
        self.updated_at = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = self.updated_at
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved manifest to: {path}")

    @classmethod
    def load(cls, path: Path) -> "SnapshotManifest":
        """Load manifest from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        manifest = cls.from_dict(data)
        logger.info(f"Loaded manifest from: {path}")
        return manifest

    @classmethod
    def create_default(
        cls,
        dataset_name: str,
        exchange_type: str,
        source_system: str,
        entity_type: str,
        **kwargs
    ) -> "SnapshotManifest":
        """Create a manifest with default values."""
        return cls(
            dataset_name=dataset_name,
            exchange_type=exchange_type,
            source_system=source_system,
            entity_type=entity_type,
            created_at=datetime.now(timezone.utc),
            **kwargs,
        )
