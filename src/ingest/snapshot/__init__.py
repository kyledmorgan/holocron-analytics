"""
Snapshot module for JSON ⇄ SQL data interchange.

This module provides:
- ExchangeRecord: Universal envelope format for data exchange
- Canonical hashing: Stable, platform-independent content hashing
- Snapshot packs: File-based snapshot storage and retrieval
- SQL mirror: SQL Server storage for exchange records
- Sync engine: Bidirectional delta synchronization
- Pack/unpack: Cold storage with optional encryption
"""

from .models import ExchangeRecord, ExchangeType
from .canonical import canonicalize, compute_content_hash
from .manifest import SnapshotManifest
from .file_snapshot import SnapshotWriter, SnapshotReader
from .sync_engine import SyncEngine, SyncDirection, ConflictStrategy

__all__ = [
    "ExchangeRecord",
    "ExchangeType",
    "canonicalize",
    "compute_content_hash",
    "SnapshotManifest",
    "SnapshotWriter",
    "SnapshotReader",
    "SyncEngine",
    "SyncDirection",
    "ConflictStrategy",
]
