"""
SQL Server mirror for ExchangeRecords.

Provides read/write operations for storing ExchangeRecords in SQL Server
with support for delta synchronization.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from .models import ExchangeRecord, Provenance
from .manifest import SnapshotManifest

logger = logging.getLogger(__name__)

# Optional pyodbc import
try:
    import pyodbc
except ImportError:
    pyodbc = None


class SqlMirror:
    """
    SQL Server storage for ExchangeRecords.
    
    Supports bidirectional sync with JSON snapshots via content hashing.
    """

    def __init__(
        self,
        connection_string: str,
        schema: str = "lake",
        table: str = "RawExchangeRecord",
        auto_commit: bool = False,
    ):
        """
        Initialize the SQL mirror.
        
        Args:
            connection_string: SQL Server connection string
            schema: Database schema name
            table: Table name
            auto_commit: Whether to auto-commit after each operation
        """
        if pyodbc is None:
            raise ImportError(
                "pyodbc is required for SqlMirror. "
                "Install with: pip install pyodbc"
            )
        
        # Validate identifiers
        if not self._is_valid_identifier(schema):
            raise ValueError(f"Invalid schema name: {schema}")
        if not self._is_valid_identifier(table):
            raise ValueError(f"Invalid table name: {table}")
        
        self.connection_string = connection_string
        self.schema = schema
        self.table = table
        self.auto_commit = auto_commit
        self.conn = None
        self._connect()

    def _is_valid_identifier(self, name: str) -> bool:
        """Validate that a name is a safe SQL identifier."""
        return bool(name and name.replace('_', '').isalnum() and not name[0].isdigit())

    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = pyodbc.connect(self.connection_string, autocommit=self.auto_commit)
            logger.debug("Connected to SQL Server")
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise

    def insert(self, record: ExchangeRecord) -> bool:
        """
        Insert a single record.
        
        Args:
            record: The ExchangeRecord to insert
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            # Serialize full envelope to JSON
            payload_json = json.dumps(record.to_dict(), ensure_ascii=False)
            
            sql = f"""
                INSERT INTO [{self.schema}].[{self.table}] (
                    exchange_id,
                    exchange_type,
                    source_system,
                    entity_type,
                    natural_key,
                    observed_at_utc,
                    content_sha256,
                    payload_json,
                    schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(
                sql,
                (
                    record.exchange_id,
                    record.exchange_type,
                    record.source_system,
                    record.entity_type,
                    record.natural_key,
                    record.observed_at_utc,
                    record.content_sha256,
                    payload_json,
                    record.schema_version,
                )
            )
            
            if not self.auto_commit:
                self.conn.commit()
            
            logger.debug(f"Inserted record {record.exchange_id}")
            return True

        except pyodbc.Error as e:
            logger.error(f"Failed to insert record: {e}")
            if not self.auto_commit:
                self.conn.rollback()
            raise

    def insert_batch(self, records: List[ExchangeRecord]) -> int:
        """
        Insert multiple records.
        
        Args:
            records: List of ExchangeRecords to insert
            
        Returns:
            Number of records inserted
        """
        count = 0
        for record in records:
            try:
                if self.insert(record):
                    count += 1
            except Exception as e:
                logger.error(f"Failed to insert record {record.exchange_id}: {e}")
        return count

    def upsert(self, record: ExchangeRecord) -> Tuple[bool, str]:
        """
        Insert or update a record.
        
        Uses content_sha256 for deduplication. If a record with the same hash
        exists, it is skipped. If a record with the same natural key but
        different hash exists, it is updated.
        
        Args:
            record: The ExchangeRecord to upsert
            
        Returns:
            Tuple of (success, action) where action is 'inserted', 'updated', 'skipped'
        """
        try:
            cursor = self.conn.cursor()
            
            # Check if hash already exists (skip duplicate)
            cursor.execute(
                f"SELECT 1 FROM [{self.schema}].[{self.table}] WHERE content_sha256 = ?",
                (record.content_sha256,)
            )
            if cursor.fetchone():
                return (True, "skipped")
            
            # Check for natural key conflict
            if record.natural_key:
                cursor.execute(
                    f"""SELECT exchange_id FROM [{self.schema}].[{self.table}] 
                        WHERE source_system = ? AND entity_type = ? AND natural_key = ?""",
                    (record.source_system, record.entity_type, record.natural_key)
                )
                existing = cursor.fetchone()
                if existing:
                    # Update existing record
                    payload_json = json.dumps(record.to_dict(), ensure_ascii=False)
                    cursor.execute(
                        f"""UPDATE [{self.schema}].[{self.table}]
                            SET exchange_id = ?,
                                exchange_type = ?,
                                observed_at_utc = ?,
                                content_sha256 = ?,
                                payload_json = ?,
                                schema_version = ?,
                                updated_at_utc = SYSUTCDATETIME()
                            WHERE source_system = ? AND entity_type = ? AND natural_key = ?""",
                        (
                            record.exchange_id,
                            record.exchange_type,
                            record.observed_at_utc,
                            record.content_sha256,
                            payload_json,
                            record.schema_version,
                            record.source_system,
                            record.entity_type,
                            record.natural_key,
                        )
                    )
                    if not self.auto_commit:
                        self.conn.commit()
                    return (True, "updated")
            
            # Insert new record
            self.insert(record)
            return (True, "inserted")

        except pyodbc.Error as e:
            logger.error(f"Failed to upsert record: {e}")
            if not self.auto_commit:
                self.conn.rollback()
            raise

    def get_all_hashes(
        self,
        source_system: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> Set[str]:
        """
        Get all content hashes in the table.
        
        Args:
            source_system: Optional filter by source system
            entity_type: Optional filter by entity type
            
        Returns:
            Set of content hashes
        """
        cursor = self.conn.cursor()
        
        sql = f"SELECT content_sha256 FROM [{self.schema}].[{self.table}]"
        params = []
        
        conditions = []
        if source_system:
            conditions.append("source_system = ?")
            params.append(source_system)
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(sql, params)
        return {row[0] for row in cursor.fetchall()}

    def get_records_by_scope(
        self,
        source_system: str,
        entity_type: str,
    ) -> List[ExchangeRecord]:
        """
        Get all records matching a source system and entity type.
        
        Args:
            source_system: Source system identifier
            entity_type: Entity type
            
        Returns:
            List of ExchangeRecords
        """
        cursor = self.conn.cursor()
        
        sql = f"""SELECT payload_json FROM [{self.schema}].[{self.table}]
                  WHERE source_system = ? AND entity_type = ?
                  ORDER BY observed_at_utc DESC"""
        
        cursor.execute(sql, (source_system, entity_type))
        
        records = []
        for row in cursor.fetchall():
            try:
                data = json.loads(row[0])
                records.append(ExchangeRecord.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to parse record: {e}")
        
        return records

    def get_record_by_hash(self, content_sha256: str) -> Optional[ExchangeRecord]:
        """
        Get a record by content hash.
        
        Args:
            content_sha256: The content hash
            
        Returns:
            ExchangeRecord if found, None otherwise
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            f"SELECT payload_json FROM [{self.schema}].[{self.table}] WHERE content_sha256 = ?",
            (content_sha256,)
        )
        row = cursor.fetchone()
        
        if row:
            data = json.loads(row[0])
            return ExchangeRecord.from_dict(data)
        
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
            List of ExchangeRecords
        """
        cursor = self.conn.cursor()
        
        sql = f"""SELECT payload_json FROM [{self.schema}].[{self.table}]
                  WHERE source_system = ? AND entity_type = ? AND natural_key = ?
                  ORDER BY observed_at_utc DESC"""
        
        cursor.execute(sql, (source_system, entity_type, natural_key))
        
        records = []
        for row in cursor.fetchall():
            try:
                data = json.loads(row[0])
                records.append(ExchangeRecord.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to parse record: {e}")
        
        return records

    def count(
        self,
        source_system: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> int:
        """Get the count of records."""
        cursor = self.conn.cursor()
        
        sql = f"SELECT COUNT(*) FROM [{self.schema}].[{self.table}]"
        params = []
        
        conditions = []
        if source_system:
            conditions.append("source_system = ?")
            params.append(source_system)
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(sql, params)
        return cursor.fetchone()[0]

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQL Server connection")
