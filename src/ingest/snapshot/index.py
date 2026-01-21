"""
Index management for snapshot packs.

The index provides fast lookup of records by content hash and natural key
without having to scan all NDJSON files.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExchangeRecord

logger = logging.getLogger(__name__)


@dataclass
class IndexEntry:
    """
    Entry in the snapshot index.
    
    Provides fast lookup of records by hash and key.
    """
    content_sha256: str
    hash_input_key: str  # source_system|entity_type|natural_key
    exchange_id: str
    observed_at_utc: str
    file_ref: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "h": self.content_sha256,
            "k": self.hash_input_key,
            "id": self.exchange_id,
            "t": self.observed_at_utc,
            "f": self.file_ref,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "IndexEntry":
        return cls(
            content_sha256=data["h"],
            hash_input_key=data["k"],
            exchange_id=data["id"],
            observed_at_utc=data["t"],
            file_ref=data.get("f"),
        )

    @classmethod
    def from_record(cls, record: "ExchangeRecord") -> "IndexEntry":
        """Create an index entry from an ExchangeRecord."""
        return cls(
            content_sha256=record.content_sha256,
            hash_input_key=record.get_hash_input_key(),
            exchange_id=record.exchange_id,
            observed_at_utc=record.observed_at_utc.isoformat() if record.observed_at_utc else "",
        )


class SnapshotIndex:
    """
    In-memory index for snapshot records.
    
    Backed by a JSONL file for persistence.
    """

    def __init__(self, path: Path):
        """
        Initialize the index.
        
        Args:
            path: Path to the index.jsonl file
        """
        self.path = Path(path)
        self._entries_by_hash: Dict[str, IndexEntry] = {}
        self._entries_by_key: Dict[str, List[IndexEntry]] = {}
        self._dirty = False

    def load(self) -> None:
        """Load index from file."""
        if not self.path.exists():
            logger.debug(f"Index file does not exist: {self.path}")
            return
        
        with open(self.path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = IndexEntry.from_dict(data)
                    self._add_to_memory(entry)
                except Exception as e:
                    logger.warning(f"Error loading index entry at line {line_num}: {e}")
        
        logger.info(f"Loaded {len(self._entries_by_hash)} entries from index")

    def save(self) -> None:
        """Save index to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.path, "w", encoding="utf-8") as f:
            for entry in self._entries_by_hash.values():
                line = json.dumps(entry.to_dict(), ensure_ascii=False)
                f.write(line + "\n")
        
        self._dirty = False
        logger.info(f"Saved {len(self._entries_by_hash)} entries to index")

    def add_entry(self, entry: IndexEntry) -> bool:
        """
        Add an entry to the index.
        
        Returns:
            True if entry was added (new), False if it already exists
        """
        if entry.content_sha256 in self._entries_by_hash:
            return False
        
        self._add_to_memory(entry)
        self._dirty = True
        return True

    def _add_to_memory(self, entry: IndexEntry) -> None:
        """Add entry to in-memory indexes."""
        self._entries_by_hash[entry.content_sha256] = entry
        
        if entry.hash_input_key not in self._entries_by_key:
            self._entries_by_key[entry.hash_input_key] = []
        self._entries_by_key[entry.hash_input_key].append(entry)

    def update_file_ref(self, content_sha256: str, file_ref: str) -> None:
        """Update the file reference for an entry."""
        if content_sha256 in self._entries_by_hash:
            self._entries_by_hash[content_sha256].file_ref = file_ref
            self._dirty = True

    def get_entry(self, content_sha256: str) -> Optional[IndexEntry]:
        """Get an entry by content hash."""
        return self._entries_by_hash.get(content_sha256)

    def get_entries_by_key(self, hash_input_key: str) -> List[IndexEntry]:
        """Get all entries with a given hash input key."""
        return self._entries_by_key.get(hash_input_key, [])

    def has_hash(self, content_sha256: str) -> bool:
        """Check if a content hash exists in the index."""
        return content_sha256 in self._entries_by_hash

    def get_all_hashes(self) -> Set[str]:
        """Get all content hashes in the index."""
        return set(self._entries_by_hash.keys())

    def get_all_entries(self) -> List[IndexEntry]:
        """Get all entries in the index."""
        return list(self._entries_by_hash.values())

    def count(self) -> int:
        """Get the number of entries in the index."""
        return len(self._entries_by_hash)

    def is_dirty(self) -> bool:
        """Check if the index has unsaved changes."""
        return self._dirty
