"""
File-based snapshot storage for ExchangeRecords.

Provides NDJSON (newline-delimited JSON) file reading and writing
with a human-browsable directory structure.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from .models import ExchangeRecord
from .manifest import SnapshotManifest
from .index import SnapshotIndex, IndexEntry

logger = logging.getLogger(__name__)


class SnapshotWriter:
    """
    Writes ExchangeRecords to NDJSON files in a snapshot pack structure.
    
    Directory structure:
        {base_dir}/{dataset_name}/
            manifest.json
            index.jsonl
            records/
                YYYY/
                    YYYY-MM-DD/
                        chunk-0001.ndjson
                        chunk-0002.ndjson
    """

    def __init__(
        self,
        base_dir: Path,
        manifest: SnapshotManifest,
        chunk_size: int = 1000,
        create_dirs: bool = True,
    ):
        """
        Initialize the snapshot writer.
        
        Args:
            base_dir: Base directory for snapshots
            manifest: Snapshot manifest
            chunk_size: Number of records per chunk file
            create_dirs: Whether to create directories automatically
        """
        self.base_dir = Path(base_dir)
        self.manifest = manifest
        self.chunk_size = chunk_size
        self.create_dirs = create_dirs
        
        self.dataset_dir = self.base_dir / manifest.dataset_name
        self.records_dir = self.dataset_dir / "records"
        
        # Track current chunk
        self._current_chunk_records: List[ExchangeRecord] = []
        self._current_date: Optional[datetime] = None
        self._chunk_counter: int = 0
        
        # Index
        self._index = SnapshotIndex(self.dataset_dir / "index.jsonl")
        
        if create_dirs:
            self._setup_directories()

    def _setup_directories(self) -> None:
        """Set up the directory structure."""
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        
        # Save manifest
        manifest_path = self.dataset_dir / "manifest.json"
        self.manifest.save(manifest_path)

    def write(self, record: ExchangeRecord) -> bool:
        """
        Write a single record to the snapshot.
        
        Args:
            record: The ExchangeRecord to write
            
        Returns:
            True if successful
        """
        # Add to index
        self._index.add_entry(IndexEntry.from_record(record))
        
        # Add to current chunk
        self._current_chunk_records.append(record)
        
        # Check if we need to flush
        if len(self._current_chunk_records) >= self.chunk_size:
            self._flush_chunk()
        
        return True

    def write_batch(self, records: List[ExchangeRecord]) -> int:
        """
        Write multiple records to the snapshot.
        
        Args:
            records: List of ExchangeRecords to write
            
        Returns:
            Number of records written
        """
        count = 0
        for record in records:
            if self.write(record):
                count += 1
        return count

    def _flush_chunk(self) -> None:
        """Flush the current chunk to a file."""
        if not self._current_chunk_records:
            return
        
        # Determine the chunk date (use first record's date)
        chunk_date = self._current_chunk_records[0].observed_at_utc
        if chunk_date is None:
            chunk_date = datetime.now(timezone.utc)
        
        # Build path
        year_dir = self.records_dir / chunk_date.strftime("%Y")
        date_dir = year_dir / chunk_date.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Increment chunk counter
        self._chunk_counter += 1
        chunk_file = date_dir / f"chunk-{self._chunk_counter:04d}.ndjson"
        
        # Write NDJSON
        with open(chunk_file, "w", encoding="utf-8") as f:
            for record in self._current_chunk_records:
                line = json.dumps(record.to_dict(), ensure_ascii=False)
                f.write(line + "\n")
        
        logger.debug(f"Wrote {len(self._current_chunk_records)} records to {chunk_file}")
        
        # Update index entries with file reference
        for record in self._current_chunk_records:
            self._index.update_file_ref(
                record.content_sha256,
                str(chunk_file.relative_to(self.dataset_dir)),
            )
        
        # Clear buffer
        self._current_chunk_records = []

    def close(self) -> None:
        """Finalize and close the snapshot writer."""
        # Flush any remaining records
        self._flush_chunk()
        
        # Save index
        self._index.save()
        
        # Update manifest
        self.manifest.updated_at = datetime.now(timezone.utc)
        manifest_path = self.dataset_dir / "manifest.json"
        self.manifest.save(manifest_path)
        
        logger.info(f"Closed snapshot writer for {self.manifest.dataset_name}")


class SnapshotReader:
    """
    Reads ExchangeRecords from a snapshot pack.
    """

    def __init__(self, dataset_dir: Path):
        """
        Initialize the snapshot reader.
        
        Args:
            dataset_dir: Path to the dataset directory
        """
        self.dataset_dir = Path(dataset_dir)
        self.records_dir = self.dataset_dir / "records"
        
        # Load manifest
        manifest_path = self.dataset_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        self.manifest = SnapshotManifest.load(manifest_path)
        
        # Load index
        self._index = SnapshotIndex(self.dataset_dir / "index.jsonl")
        self._index.load()

    def get_manifest(self) -> SnapshotManifest:
        """Get the loaded manifest."""
        return self.manifest

    def get_index(self) -> SnapshotIndex:
        """Get the loaded index."""
        return self._index

    def read_all(self) -> Generator[ExchangeRecord, None, None]:
        """
        Read all records from the snapshot.
        
        Yields:
            ExchangeRecord objects
        """
        # Find all NDJSON files
        for ndjson_file in sorted(self.records_dir.rglob("*.ndjson")):
            yield from self._read_ndjson_file(ndjson_file)

    def _read_ndjson_file(self, path: Path) -> Generator[ExchangeRecord, None, None]:
        """Read records from a single NDJSON file."""
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    yield ExchangeRecord.from_dict(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at {path}:{line_num}: {e}")
                except Exception as e:
                    logger.warning(f"Error parsing record at {path}:{line_num}: {e}")

    def get_hashes(self) -> set:
        """Get all content hashes from the index."""
        return self._index.get_all_hashes()

    def get_record_by_hash(self, content_sha256: str) -> Optional[ExchangeRecord]:
        """
        Get a specific record by its content hash.
        
        Args:
            content_sha256: The content hash to look up
            
        Returns:
            ExchangeRecord if found, None otherwise
        """
        entry = self._index.get_entry(content_sha256)
        if entry is None or entry.file_ref is None:
            return None
        
        # Read from the referenced file
        file_path = self.dataset_dir / entry.file_ref
        if not file_path.exists():
            return None
        
        for record in self._read_ndjson_file(file_path):
            if record.content_sha256 == content_sha256:
                return record
        
        return None

    def get_records_by_natural_key(
        self,
        source_system: str,
        entity_type: str,
        natural_key: str,
    ) -> List[ExchangeRecord]:
        """
        Get all records matching a natural key.
        
        Args:
            source_system: Source system identifier
            entity_type: Entity type
            natural_key: Natural key value
            
        Returns:
            List of matching records
        """
        results = []
        hash_input_key = f"{source_system}|{entity_type}|{natural_key}"
        
        # Get entries with matching key
        entries = self._index.get_entries_by_key(hash_input_key)
        
        for entry in entries:
            record = self.get_record_by_hash(entry.content_sha256)
            if record:
                results.append(record)
        
        return results
