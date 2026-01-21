"""
SQL Server-based state store for managing work item queue.

This is the default state store backend, replacing the deprecated SQLite implementation.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None

from ..core.state_store import StateStore
from ..core.models import WorkItem, WorkItemStatus


logger = logging.getLogger(__name__)


class SqlServerStateStore(StateStore):
    """
    SQL Server-based implementation of the state store.
    
    Manages the work queue and tracks status using SQL Server database.
    This is the default/recommended backend for production workloads.
    
    Features:
    - Full concurrency support for multiple runners
    - ACID transactions for reliable state management  
    - Scalable for large workloads
    - Proper dedupe semantics with unique constraints
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "localhost",
        port: int = 1433,
        database: str = "Holocron",
        username: str = "sa",
        password: Optional[str] = None,
        driver: str = "ODBC Driver 18 for SQL Server",
        schema: str = "ingest",
        auto_init: bool = True,
        trust_server_certificate: bool = True,
    ):
        """
        Initialize the SQL Server state store.
        
        Args:
            connection_string: Full ODBC connection string (if provided, other params ignored)
            host: SQL Server host
            port: SQL Server port
            database: Database name
            username: Database username
            password: Database password
            driver: ODBC driver name
            schema: Schema name for tables (default: 'ingest')
            auto_init: Whether to create schema and tables automatically
            trust_server_certificate: Whether to trust self-signed certificates (for local Docker)
        """
        if pyodbc is None:
            raise ImportError(
                "pyodbc is required for SqlServerStateStore. "
                "Install with: pip install pyodbc"
            )
        
        # Validate schema name
        if not self._is_valid_identifier(schema):
            raise ValueError(f"Invalid schema name: {schema}")
        
        self.schema = schema
        self.auto_init = auto_init
        
        # Build connection string if not provided
        if connection_string:
            self.connection_string = connection_string
        else:
            trust_cert = "yes" if trust_server_certificate else "no"
            self.connection_string = (
                f"Driver={{{driver}}};"
                f"Server={host},{port};"
                f"Database={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate={trust_cert}"
            )
        
        self.conn = None
        self._connect()
        
        if auto_init:
            self._init_schema()

    def _is_valid_identifier(self, name: str) -> bool:
        """
        Validate that a name is a safe SQL identifier.
        
        Uses a strict whitelist approach to prevent SQL injection:
        - Must start with a letter or underscore
        - Can only contain letters, digits, and underscores
        - Maximum length of 128 characters (SQL Server limit)
        - Cannot be a SQL reserved word
        
        Args:
            name: The identifier to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not name or len(name) > 128:
            return False
        
        # Strict regex: start with letter/underscore, followed by alphanumerics/underscores
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        if not re.match(pattern, name):
            return False
        
        # Block common SQL reserved words that could be dangerous
        reserved_words = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'exec', 'execute', 'union', 'where', 'from', 'table', 'database',
            'schema', 'index', 'grant', 'revoke', 'truncate', 'declare', 'set'
        }
        if name.lower() in reserved_words:
            return False
        
        return True

    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = pyodbc.connect(self.connection_string)
            logger.debug(f"Connected to SQL Server state store (schema: {self.schema})")
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise

    def _init_schema(self) -> None:
        """Initialize database schema and tables."""
        cursor = self.conn.cursor()
        
        try:
            # Create schema if not exists
            # Note: Schema name is validated in __init__ via _is_valid_identifier()
            # which uses strict whitelist validation. The schema comes from trusted
            # configuration (env vars or config file), not user input. Using EXEC
            # is necessary because CREATE SCHEMA cannot use parameters directly.
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = ?)
                BEGIN
                    EXEC('CREATE SCHEMA [{self.schema}]')
                END
            """, (self.schema,))
            
            # Create work_items table
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.tables t 
                               JOIN sys.schemas s ON t.schema_id = s.schema_id 
                               WHERE t.name = 'work_items' AND s.name = ?)
                BEGIN
                    CREATE TABLE [{self.schema}].[work_items] (
                        work_item_id NVARCHAR(36) PRIMARY KEY,
                        source_system NVARCHAR(100) NOT NULL,
                        source_name NVARCHAR(100) NOT NULL,
                        resource_type NVARCHAR(100) NOT NULL,
                        resource_id NVARCHAR(500) NOT NULL,
                        request_uri NVARCHAR(2000) NOT NULL,
                        request_method NVARCHAR(10) NOT NULL,
                        request_headers NVARCHAR(MAX),
                        request_body NVARCHAR(MAX),
                        metadata NVARCHAR(MAX),
                        priority INT NOT NULL DEFAULT 100,
                        status NVARCHAR(20) NOT NULL,
                        attempt INT NOT NULL DEFAULT 0,
                        run_id NVARCHAR(36),
                        discovered_from NVARCHAR(36),
                        created_at DATETIME2 NOT NULL,
                        updated_at DATETIME2 NOT NULL,
                        error_message NVARCHAR(MAX),
                        dedupe_key NVARCHAR(800) NOT NULL
                    )
                END
            """, (self.schema,))
            
            # Create indexes
            # Index for queue dequeue operations
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes 
                               WHERE name = 'ix_work_items_status' 
                               AND object_id = OBJECT_ID('[{self.schema}].[work_items]'))
                BEGIN
                    CREATE INDEX ix_work_items_status 
                    ON [{self.schema}].[work_items] (status, priority, created_at)
                END
            """)
            
            # Unique index for deduplication
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes 
                               WHERE name = 'ix_work_items_dedupe' 
                               AND object_id = OBJECT_ID('[{self.schema}].[work_items]'))
                BEGIN
                    CREATE UNIQUE INDEX ix_work_items_dedupe 
                    ON [{self.schema}].[work_items] (dedupe_key)
                END
            """)
            
            # Index for run_id queries
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes 
                               WHERE name = 'ix_work_items_run_id' 
                               AND object_id = OBJECT_ID('[{self.schema}].[work_items]'))
                BEGIN
                    CREATE INDEX ix_work_items_run_id 
                    ON [{self.schema}].[work_items] (run_id)
                END
            """)
            
            # Index for source system queries (useful for re-crawl)
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes 
                               WHERE name = 'ix_work_items_source' 
                               AND object_id = OBJECT_ID('[{self.schema}].[work_items]'))
                BEGIN
                    CREATE INDEX ix_work_items_source 
                    ON [{self.schema}].[work_items] (source_system, source_name)
                END
            """)
            
            self.conn.commit()
            logger.debug("Initialized SQL Server state store schema")
            
        except pyodbc.Error as e:
            logger.error(f"Failed to initialize schema: {e}")
            self.conn.rollback()
            raise

    def enqueue(self, work_item: WorkItem) -> bool:
        """
        Add a work item to the queue if it doesn't already exist.
        
        Args:
            work_item: The work item to enqueue
            
        Returns:
            True if enqueued, False if already exists
        """
        dedupe_key = work_item.get_dedupe_key()
        
        # Check if already exists
        if self.exists(dedupe_key):
            logger.debug(f"Work item already exists: {dedupe_key}")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Convert headers and metadata to JSON strings
            request_headers = json.dumps(work_item.request_headers) if work_item.request_headers else None
            metadata_json = json.dumps(work_item.metadata) if work_item.metadata else None
            
            cursor.execute(f"""
                INSERT INTO [{self.schema}].[work_items] (
                    work_item_id, source_system, source_name, resource_type, resource_id,
                    request_uri, request_method, request_headers, request_body, metadata,
                    priority, status, attempt, run_id, discovered_from,
                    created_at, updated_at, dedupe_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work_item.work_item_id,
                work_item.source_system,
                work_item.source_name,
                work_item.resource_type,
                work_item.resource_id,
                work_item.request_uri,
                work_item.request_method,
                request_headers,
                work_item.request_body,
                metadata_json,
                work_item.priority,
                work_item.status.value,
                work_item.attempt,
                work_item.run_id,
                work_item.discovered_from,
                work_item.created_at,
                work_item.updated_at,
                dedupe_key,
            ))
            
            self.conn.commit()
            logger.debug(f"Enqueued work item: {dedupe_key}")
            return True
            
        except pyodbc.IntegrityError:
            logger.debug(f"Work item already exists (race condition): {dedupe_key}")
            self.conn.rollback()
            return False
        except pyodbc.Error as e:
            logger.error(f"Failed to enqueue work item: {e}")
            self.conn.rollback()
            raise

    def dequeue(self, limit: int = 1) -> List[WorkItem]:
        """
        Get pending work items from the queue.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of work items
        """
        try:
            cursor = self.conn.cursor()
            
            # Get pending items, ordered by priority and creation time
            cursor.execute(f"""
                SELECT TOP (?) * FROM [{self.schema}].[work_items]
                WHERE status = ?
                ORDER BY priority ASC, created_at ASC
            """, (limit, WorkItemStatus.PENDING.value))
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            work_items = []
            
            for row in rows:
                row_dict = dict(zip(columns, row))
                work_item = self._row_to_work_item(row_dict)
                work_items.append(work_item)
                
                # Mark as in progress
                self.update_status(work_item.work_item_id, WorkItemStatus.IN_PROGRESS)
            
            return work_items
            
        except pyodbc.Error as e:
            logger.error(f"Failed to dequeue work items: {e}")
            raise

    def update_status(
        self,
        work_item_id: str,
        status: WorkItemStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of a work item.
        
        Args:
            work_item_id: ID of the work item
            status: New status
            error_message: Optional error message for failed items
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                UPDATE [{self.schema}].[work_items]
                SET status = ?, updated_at = ?, error_message = ?
                WHERE work_item_id = ?
            """, (
                status.value,
                datetime.now(timezone.utc),
                error_message,
                work_item_id,
            ))
            
            self.conn.commit()
            logger.debug(f"Updated work item {work_item_id} to status {status.value}")
            return True
            
        except pyodbc.Error as e:
            logger.error(f"Failed to update work item status: {e}")
            self.conn.rollback()
            raise

    def get_work_item(self, work_item_id: str) -> Optional[WorkItem]:
        """
        Get a specific work item by ID.
        
        Args:
            work_item_id: ID of the work item
            
        Returns:
            WorkItem if found, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                SELECT * FROM [{self.schema}].[work_items] WHERE work_item_id = ?
            """, (work_item_id,))
            
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            
            if row:
                row_dict = dict(zip(columns, row))
                return self._row_to_work_item(row_dict)
            return None
            
        except pyodbc.Error as e:
            logger.error(f"Failed to get work item: {e}")
            raise

    def exists(self, dedupe_key: str) -> bool:
        """
        Check if a work item with the given dedupe key already exists.
        
        Args:
            dedupe_key: The deduplication key to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT TOP 1 1 FROM [{self.schema}].[work_items] WHERE dedupe_key = ?
            """, (dedupe_key,))
            return cursor.fetchone() is not None
        except pyodbc.Error as e:
            logger.error(f"Failed to check existence: {e}")
            raise

    def get_stats(self) -> dict:
        """
        Get statistics about the work queue.
        
        Returns:
            Dictionary with counts by status
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT status, COUNT(*) as count
                FROM [{self.schema}].[work_items]
                GROUP BY status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats
        except pyodbc.Error as e:
            logger.error(f"Failed to get stats: {e}")
            raise

    def get_known_resources(
        self,
        source_system: Optional[str] = None,
        source_name: Optional[str] = None,
        status: Optional[WorkItemStatus] = None,
    ) -> List[WorkItem]:
        """
        Get known resources for re-crawl without re-seeding.
        
        This enables querying previously seen resources for targeted re-fetch
        without needing to re-discover them.
        
        Args:
            source_system: Filter by source system
            source_name: Filter by source name
            status: Filter by status
            
        Returns:
            List of work items matching the criteria
        """
        try:
            cursor = self.conn.cursor()
            
            query = f"SELECT * FROM [{self.schema}].[work_items] WHERE 1=1"
            params = []
            
            if source_system:
                query += " AND source_system = ?"
                params.append(source_system)
            
            if source_name:
                query += " AND source_name = ?"
                params.append(source_name)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            cursor.execute(query, params)
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            
            return [
                self._row_to_work_item(dict(zip(columns, row)))
                for row in rows
            ]
            
        except pyodbc.Error as e:
            logger.error(f"Failed to get known resources: {e}")
            raise

    def reset_for_recrawl(
        self,
        source_system: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> int:
        """
        Reset completed items to pending for re-crawl.
        
        Args:
            source_system: Filter by source system (optional)
            source_name: Filter by source name (optional)
            
        Returns:
            Number of items reset
        """
        try:
            cursor = self.conn.cursor()
            
            query = f"""
                UPDATE [{self.schema}].[work_items]
                SET status = ?, updated_at = ?, attempt = 0
                WHERE status = ?
            """
            params = [
                WorkItemStatus.PENDING.value,
                datetime.now(timezone.utc),
                WorkItemStatus.COMPLETED.value,
            ]
            
            if source_system:
                query += " AND source_system = ?"
                params.append(source_system)
            
            if source_name:
                query += " AND source_name = ?"
                params.append(source_name)
            
            cursor.execute(query, params)
            count = cursor.rowcount
            self.conn.commit()
            
            logger.info(f"Reset {count} items for re-crawl")
            return count
            
        except pyodbc.Error as e:
            logger.error(f"Failed to reset for re-crawl: {e}")
            self.conn.rollback()
            raise

    def _row_to_work_item(self, row: dict) -> WorkItem:
        """Convert a database row to a WorkItem object."""
        # Parse JSON fields
        request_headers = json.loads(row["request_headers"]) if row["request_headers"] else None
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
        # Handle datetime conversion
        created_at = row["created_at"]
        updated_at = row["updated_at"]
        
        # If already datetime, use as-is; otherwise parse
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return WorkItem(
            work_item_id=row["work_item_id"],
            source_system=row["source_system"],
            source_name=row["source_name"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            request_uri=row["request_uri"],
            request_method=row["request_method"],
            request_headers=request_headers,
            request_body=row["request_body"],
            metadata=metadata,
            priority=row["priority"],
            status=WorkItemStatus(row["status"]),
            attempt=row["attempt"],
            run_id=row["run_id"],
            discovered_from=row["discovered_from"],
            created_at=created_at,
            updated_at=updated_at,
        )

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQL Server state store connection")
