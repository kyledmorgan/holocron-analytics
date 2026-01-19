"""
File-based storage writer for JSON data lake.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.storage import StorageWriter
from ..core.models import IngestRecord


logger = logging.getLogger(__name__)


class FileLakeWriter(StorageWriter):
    """
    Writes ingestion records as JSON files to a data lake directory.
    
    Files are organized by: {base_dir}/{source_system}/{source_name}/{resource_type}/
    Filenames: {resource_id}_{timestamp}_{ingest_id}.json
    """

    def __init__(
        self,
        base_dir: Path,
        create_dirs: bool = True,
        pretty_print: bool = True,
    ):
        """
        Initialize the file lake writer.
        
        Args:
            base_dir: Base directory for the data lake
            create_dirs: Whether to create directories automatically
            pretty_print: Whether to pretty-print JSON files
        """
        self.base_dir = Path(base_dir)
        self.create_dirs = create_dirs
        self.pretty_print = pretty_print

        if create_dirs:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: IngestRecord) -> bool:
        """
        Write an ingestion record as a JSON file.
        
        Args:
            record: The ingestion record to write
            
        Returns:
            True if successful
        """
        try:
            # Build directory structure
            dir_path = (
                self.base_dir
                / record.source_system
                / record.source_name
                / record.resource_type
            )
            
            if self.create_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = record.fetched_at_utc.strftime("%Y%m%d_%H%M%S")
            safe_resource_id = self._sanitize_filename(record.resource_id)
            filename = f"{safe_resource_id}_{timestamp}_{record.ingest_id[:8]}.json"
            file_path = dir_path / filename

            # Prepare JSON content (full record)
            content = {
                "ingest_id": record.ingest_id,
                "source_system": record.source_system,
                "source_name": record.source_name,
                "resource_type": record.resource_type,
                "resource_id": record.resource_id,
                "request_uri": record.request_uri,
                "request_method": record.request_method,
                "request_headers": record.request_headers,
                "status_code": record.status_code,
                "response_headers": record.response_headers,
                "fetched_at_utc": record.fetched_at_utc.isoformat(),
                "hash_sha256": record.hash_sha256,
                "run_id": record.run_id,
                "work_item_id": record.work_item_id,
                "attempt": record.attempt,
                "error_message": record.error_message,
                "duration_ms": record.duration_ms,
                "payload": record.payload,
            }

            # Write file
            indent = 2 if self.pretty_print else None
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=indent, ensure_ascii=False)

            logger.debug(f"Wrote ingestion record to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file lake record: {e}")
            raise

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use in filenames."""
        # Replace unsafe characters
        safe = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        # Limit length
        if len(safe) > 100:
            safe = safe[:100]
        return safe

    def get_name(self) -> str:
        """Return the storage writer name."""
        return "file_lake"
