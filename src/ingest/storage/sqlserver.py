"""
SQL Server storage writer for ingestion records.
"""

import json
import logging
from typing import Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None

from ..core.storage import StorageWriter
from ..core.models import IngestRecord


logger = logging.getLogger(__name__)


class SqlServerIngestWriter(StorageWriter):
    """
    Writes ingestion records to SQL Server.
    
    Stores metadata as columns and the full payload as JSON (NVARCHAR(MAX)).
    """

    def __init__(
        self,
        connection_string: str,
        schema: str = "ingest",
        table: str = "IngestRecords",
        auto_commit: bool = False,
    ):
        """
        Initialize the SQL Server writer.
        
        Args:
            connection_string: SQL Server connection string
            schema: Database schema name
            table: Table name
            auto_commit: Whether to auto-commit after each write
        """
        if pyodbc is None:
            raise ImportError(
                "pyodbc is required for SqlServerIngestWriter. "
                "Install with: pip install pyodbc"
            )
        
        self.connection_string = connection_string
        self.schema = schema
        self.table = table
        self.auto_commit = auto_commit
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = pyodbc.connect(self.connection_string, autocommit=self.auto_commit)
            logger.debug("Connected to SQL Server")
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise

    def write(self, record: IngestRecord) -> bool:
        """
        Write an ingestion record to SQL Server.
        
        Args:
            record: The ingestion record to write
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            # Prepare payload as JSON string
            payload_json = json.dumps(record.payload, ensure_ascii=False)
            
            # Prepare headers as JSON strings
            request_headers_json = json.dumps(record.request_headers) if record.request_headers else None
            response_headers_json = json.dumps(record.response_headers) if record.response_headers else None
            
            # Insert statement
            sql = f"""
                INSERT INTO [{self.schema}].[{self.table}] (
                    ingest_id,
                    source_system,
                    source_name,
                    resource_type,
                    resource_id,
                    request_uri,
                    request_method,
                    request_headers,
                    status_code,
                    response_headers,
                    payload,
                    fetched_at_utc,
                    hash_sha256,
                    run_id,
                    work_item_id,
                    attempt,
                    error_message,
                    duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(
                sql,
                (
                    record.ingest_id,
                    record.source_system,
                    record.source_name,
                    record.resource_type,
                    record.resource_id,
                    record.request_uri,
                    record.request_method,
                    request_headers_json,
                    record.status_code,
                    response_headers_json,
                    payload_json,
                    record.fetched_at_utc,
                    record.hash_sha256,
                    record.run_id,
                    record.work_item_id,
                    record.attempt,
                    record.error_message,
                    record.duration_ms,
                )
            )
            
            if not self.auto_commit:
                self.conn.commit()
            
            logger.debug(f"Wrote ingest record {record.ingest_id} to SQL Server")
            return True

        except pyodbc.Error as e:
            logger.error(f"Failed to write SQL Server record: {e}")
            if not self.auto_commit:
                self.conn.rollback()
            raise

    def get_name(self) -> str:
        """Return the storage writer name."""
        return "sqlserver"

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQL Server connection")
