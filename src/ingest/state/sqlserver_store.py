"""
SQL Server-based state store for managing work item queue.

This is the default state store backend, replacing the deprecated SQLite implementation.
"""

import json
import logging
import re
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None

from ..core.state_store import StateStore
from ..core.models import WorkItem, WorkItemStatus, AcquisitionVariant, WorkerInfo, WorkerStatus, QueueStats


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
        port: int = 1434,
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
        
        self._thread_local = threading.local()
        self._connections = []
        self._connections_lock = threading.Lock()
        self.conn = _ThreadLocalConnectionProxy(self)
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
            self._get_conn()
            logger.debug(f"Connected to SQL Server state store (schema: {self.schema})")
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise

    def _get_conn(self):
        """Get (or create) a thread-local connection for safe concurrent use."""
        conn = getattr(self._thread_local, "conn", None)
        if conn is None:
            conn = pyodbc.connect(self.connection_string)
            self._thread_local.conn = conn
            with self._connections_lock:
                self._connections.append(conn)
        return conn

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
                        dedupe_key NVARCHAR(800) NOT NULL,
                        variant NVARCHAR(20),
                        rank INT
                    )
                END
            """, (self.schema,))
            
            # Add variant column if table exists but column doesn't
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'variant')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD variant NVARCHAR(20)
                END
            """, (self.schema,))
            
            # Add rank column if table exists but column doesn't
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'rank')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD rank INT
                END
            """, (self.schema,))
            
            # Add claimed_by column for concurrent processing
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'claimed_by')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD claimed_by NVARCHAR(100)
                END
            """, (self.schema,))
            
            # Add claimed_at column for tracking claim time
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'claimed_at')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD claimed_at DATETIME2
                END
            """, (self.schema,))
            
            # Add lease_expires_at column for lease management
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'lease_expires_at')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD lease_expires_at DATETIME2
                END
            """, (self.schema,))
            
            # Add last_error column for error visibility
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'last_error')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD last_error NVARCHAR(MAX)
                END
            """, (self.schema,))
            
            # Add next_retry_at column for backoff scheduling
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM sys.tables t 
                           JOIN sys.schemas s ON t.schema_id = s.schema_id 
                           WHERE t.name = 'work_items' AND s.name = ?)
                AND NOT EXISTS (SELECT * FROM sys.columns 
                               WHERE object_id = OBJECT_ID('[{self.schema}].[work_items]') 
                               AND name = 'next_retry_at')
                BEGIN
                    ALTER TABLE [{self.schema}].[work_items] ADD next_retry_at DATETIME2
                END
            """, (self.schema,))
            
            # Create worker_heartbeats table
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM sys.tables t 
                               JOIN sys.schemas s ON t.schema_id = s.schema_id 
                               WHERE t.name = 'worker_heartbeats' AND s.name = ?)
                BEGIN
                    CREATE TABLE [{self.schema}].[worker_heartbeats] (
                        worker_id NVARCHAR(100) PRIMARY KEY,
                        hostname NVARCHAR(255) NOT NULL,
                        pid INT NOT NULL,
                        started_at DATETIME2 NOT NULL,
                        last_heartbeat_at DATETIME2 NOT NULL,
                        items_processed INT NOT NULL DEFAULT 0,
                        items_succeeded INT NOT NULL DEFAULT 0,
                        items_failed INT NOT NULL DEFAULT 0,
                        status NVARCHAR(20) NOT NULL DEFAULT 'active',
                        current_work_item_id NVARCHAR(36)
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
                    created_at, updated_at, dedupe_key, variant, rank
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                work_item.variant.value if work_item.variant else None,
                work_item.rank,
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
        
        # Handle variant field
        variant = None
        if row.get("variant"):
            try:
                variant = AcquisitionVariant(row["variant"])
            except ValueError:
                pass  # Keep as None if invalid value
        
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
            variant=variant,
            rank=row.get("rank"),
            claimed_by=row.get("claimed_by"),
            claimed_at=self._parse_datetime(row.get("claimed_at")),
            lease_expires_at=self._parse_datetime(row.get("lease_expires_at")),
            last_error=row.get("last_error"),
            next_retry_at=self._parse_datetime(row.get("next_retry_at")),
        )
    
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse a datetime value from database."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return None

    # =========================================================================
    # Concurrent Processing Methods
    # =========================================================================
    
    def claim_work_item(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        source_filter: Optional[str] = None,
    ) -> Optional[WorkItem]:
        """
        Atomically claim the next available work item.
        
        Uses an atomic UPDATE with OUTPUT to prevent race conditions.
        The item is marked as in_progress with a lease that expires
        after lease_seconds.
        
        Args:
            worker_id: Unique identifier for this worker
            lease_seconds: How long the lease is valid (default 5 minutes)
            source_filter: Optional source_system filter
            
        Returns:
            The claimed WorkItem, or None if no items available
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)
        
        try:
            cursor = self.conn.cursor()
            
            # Build filter clause
            source_clause = ""
            params = [
                WorkItemStatus.IN_PROGRESS.value,
                worker_id,
                now,
                lease_expires,
                now,
                WorkItemStatus.PENDING.value,
                now,  # For next_retry_at check
            ]
            
            if source_filter:
                source_clause = "AND source_system = ?"
                params.append(source_filter)

            # For expired lease recovery
            params.append(WorkItemStatus.IN_PROGRESS.value)
            
            # Atomic claim using UPDATE with OUTPUT
            # Claims items that are:
            # 1. PENDING status, OR
            # 2. IN_PROGRESS but lease expired (stalled worker recovery)
            # Respects next_retry_at for backoff scheduling
            cursor.execute(f"""
                UPDATE TOP(1) [{self.schema}].[work_items]
                SET status = ?,
                    claimed_by = ?,
                    claimed_at = ?,
                    lease_expires_at = ?,
                    updated_at = ?,
                    attempt = attempt + 1
                OUTPUT INSERTED.*
                WHERE (
                    (status = ? AND (next_retry_at IS NULL OR next_retry_at <= ?))
                    {source_clause}
                )
                OR (
                    status = ? 
                    AND lease_expires_at IS NOT NULL 
                    AND lease_expires_at < ?
                )
            """, params + [now])
            
            columns = [column[0] for column in cursor.description] if cursor.description else []
            row = cursor.fetchone()
            
            if row:
                self.conn.commit()
                row_dict = dict(zip(columns, row))
                work_item = self._row_to_work_item(row_dict)
                logger.debug(
                    f"Worker {worker_id} claimed item {work_item.work_item_id} "
                    f"(attempt {work_item.attempt})"
                )
                return work_item
            
            self.conn.commit()
            return None
            
        except pyodbc.Error as e:
            logger.error(f"Failed to claim work item: {e}")
            self.conn.rollback()
            raise
    
    def renew_lease(
        self,
        work_item_id: str,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> bool:
        """
        Renew the lease on a work item.
        
        Only succeeds if the worker still owns the item.
        
        Args:
            work_item_id: ID of the work item
            worker_id: ID of the worker that owns the item
            lease_seconds: New lease duration
            
        Returns:
            True if lease was renewed, False if worker doesn't own item
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                UPDATE [{self.schema}].[work_items]
                SET lease_expires_at = ?,
                    updated_at = ?
                WHERE work_item_id = ?
                  AND claimed_by = ?
                  AND status = ?
            """, (
                lease_expires,
                now,
                work_item_id,
                worker_id,
                WorkItemStatus.IN_PROGRESS.value,
            ))
            
            updated = cursor.rowcount > 0
            self.conn.commit()
            
            if updated:
                logger.debug(f"Worker {worker_id} renewed lease on {work_item_id}")
            else:
                logger.warning(
                    f"Worker {worker_id} failed to renew lease on {work_item_id} "
                    "(item may have been reclaimed)"
                )
            
            return updated
            
        except pyodbc.Error as e:
            logger.error(f"Failed to renew lease: {e}")
            self.conn.rollback()
            raise
    
    def complete_work_item(
        self,
        work_item_id: str,
        worker_id: str,
    ) -> bool:
        """
        Mark a work item as completed.
        
        Only succeeds if the worker still owns the item.
        
        Args:
            work_item_id: ID of the work item
            worker_id: ID of the worker that owns the item
            
        Returns:
            True if item was marked completed
        """
        now = datetime.now(timezone.utc)
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                UPDATE [{self.schema}].[work_items]
                SET status = ?,
                    updated_at = ?,
                    claimed_by = NULL,
                    claimed_at = NULL,
                    lease_expires_at = NULL,
                    last_error = NULL
                WHERE work_item_id = ?
                  AND claimed_by = ?
            """, (
                WorkItemStatus.COMPLETED.value,
                now,
                work_item_id,
                worker_id,
            ))
            
            updated = cursor.rowcount > 0
            self.conn.commit()
            
            if updated:
                logger.debug(f"Worker {worker_id} completed item {work_item_id}")
            else:
                logger.warning(
                    f"Worker {worker_id} failed to complete {work_item_id} "
                    "(item may have been reclaimed)"
                )
            
            return updated
            
        except pyodbc.Error as e:
            logger.error(f"Failed to complete work item: {e}")
            self.conn.rollback()
            raise
    
    def fail_work_item(
        self,
        work_item_id: str,
        worker_id: str,
        error_message: str,
        retryable: bool = True,
        backoff_seconds: Optional[int] = None,
        max_retries: int = 3,
    ) -> bool:
        """
        Mark a work item as failed, optionally scheduling a retry.
        
        Args:
            work_item_id: ID of the work item
            worker_id: ID of the worker that owns the item
            error_message: Description of the failure
            retryable: Whether this error is retryable
            backoff_seconds: Seconds to wait before retry (for Retry-After)
            max_retries: Maximum retry attempts
            
        Returns:
            True if item was updated
        """
        now = datetime.now(timezone.utc)
        
        try:
            cursor = self.conn.cursor()
            
            # Get current attempt count
            cursor.execute(f"""
                SELECT attempt FROM [{self.schema}].[work_items]
                WHERE work_item_id = ? AND claimed_by = ?
            """, (work_item_id, worker_id))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(
                    f"Worker {worker_id} failed to fail {work_item_id} "
                    "(item not found or not owned)"
                )
                return False
            
            current_attempt = row[0]
            
            # Determine final status and next_retry_at
            if retryable and current_attempt < max_retries:
                status = WorkItemStatus.PENDING.value
                # Calculate backoff if not specified
                if backoff_seconds is None:
                    # Exponential backoff with jitter: 2^attempt * (1 + random(0,1))
                    import random
                    base_delay = 2 ** current_attempt
                    jitter = random.uniform(0, 1)
                    backoff_seconds = int(base_delay * (1 + jitter))
                next_retry = now + timedelta(seconds=backoff_seconds)
            else:
                status = WorkItemStatus.FAILED.value
                next_retry = None
            
            cursor.execute(f"""
                UPDATE [{self.schema}].[work_items]
                SET status = ?,
                    updated_at = ?,
                    last_error = ?,
                    error_message = ?,
                    next_retry_at = ?,
                    claimed_by = NULL,
                    claimed_at = NULL,
                    lease_expires_at = NULL
                WHERE work_item_id = ?
                  AND claimed_by = ?
            """, (
                status,
                now,
                error_message,
                error_message,
                next_retry,
                work_item_id,
                worker_id,
            ))
            
            updated = cursor.rowcount > 0
            self.conn.commit()
            
            if updated:
                if status == WorkItemStatus.PENDING.value:
                    logger.info(
                        f"Worker {worker_id} failed item {work_item_id} "
                        f"(attempt {current_attempt}/{max_retries}), "
                        f"retry in {backoff_seconds}s: {error_message}"
                    )
                else:
                    logger.warning(
                        f"Worker {worker_id} permanently failed item {work_item_id} "
                        f"after {current_attempt} attempts: {error_message}"
                    )
            
            return updated
            
        except pyodbc.Error as e:
            logger.error(f"Failed to fail work item: {e}")
            self.conn.rollback()
            raise
    
    def recover_expired_leases(self) -> int:
        """
        Recover work items with expired leases.
        
        Items that were in_progress but whose lease has expired
        are reset to pending for another worker to claim.
        
        Returns:
            Number of items recovered
        """
        now = datetime.now(timezone.utc)
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                UPDATE [{self.schema}].[work_items]
                SET status = ?,
                    updated_at = ?,
                    claimed_by = NULL,
                    claimed_at = NULL,
                    lease_expires_at = NULL
                WHERE status = ?
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at < ?
            """, (
                WorkItemStatus.PENDING.value,
                now,
                WorkItemStatus.IN_PROGRESS.value,
                now,
            ))
            
            count = cursor.rowcount
            self.conn.commit()
            
            if count > 0:
                logger.info(f"Recovered {count} items with expired leases")
            
            return count
            
        except pyodbc.Error as e:
            logger.error(f"Failed to recover expired leases: {e}")
            self.conn.rollback()
            raise
    
    # =========================================================================
    # Worker Heartbeat Methods
    # =========================================================================
    
    def update_worker_heartbeat(
        self,
        worker_id: str,
        hostname: str,
        pid: int,
        items_processed: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        status: str = "active",
        current_work_item_id: Optional[str] = None,
    ) -> bool:
        """
        Update or create a worker heartbeat record.
        
        Args:
            worker_id: Unique worker identifier
            hostname: Machine hostname
            pid: Process ID
            items_processed: Total items processed
            items_succeeded: Items succeeded
            items_failed: Items failed
            status: Worker status (active, idle, paused, stopping, stopped)
            current_work_item_id: Currently processing item
            
        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc)
        
        try:
            cursor = self.conn.cursor()
            
            # Upsert pattern using MERGE
            cursor.execute(f"""
                MERGE [{self.schema}].[worker_heartbeats] AS target
                USING (SELECT ? AS worker_id) AS source
                ON target.worker_id = source.worker_id
                WHEN MATCHED THEN
                    UPDATE SET 
                        last_heartbeat_at = ?,
                        items_processed = ?,
                        items_succeeded = ?,
                        items_failed = ?,
                        status = ?,
                        current_work_item_id = ?
                WHEN NOT MATCHED THEN
                    INSERT (worker_id, hostname, pid, started_at, last_heartbeat_at,
                            items_processed, items_succeeded, items_failed, status, current_work_item_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                worker_id,
                now,
                items_processed,
                items_succeeded,
                items_failed,
                status,
                current_work_item_id,
                worker_id,
                hostname,
                pid,
                now,
                now,
                items_processed,
                items_succeeded,
                items_failed,
                status,
                current_work_item_id,
            ))
            
            self.conn.commit()
            return True
            
        except pyodbc.Error as e:
            logger.error(f"Failed to update worker heartbeat: {e}")
            self.conn.rollback()
            raise
    
    def get_active_workers(self, timeout_seconds: int = 120) -> List[WorkerInfo]:
        """
        Get list of active workers.
        
        Args:
            timeout_seconds: Consider workers inactive after this many seconds
            
        Returns:
            List of WorkerInfo for active workers
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                SELECT * FROM [{self.schema}].[worker_heartbeats]
                WHERE last_heartbeat_at >= ?
                ORDER BY started_at
            """, (cutoff,))
            
            columns = [column[0] for column in cursor.description]
            workers = []
            
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                workers.append(WorkerInfo(
                    worker_id=row_dict["worker_id"],
                    hostname=row_dict["hostname"],
                    pid=row_dict["pid"],
                    started_at=row_dict["started_at"],
                    last_heartbeat_at=row_dict["last_heartbeat_at"],
                    items_processed=row_dict["items_processed"],
                    items_succeeded=row_dict["items_succeeded"],
                    items_failed=row_dict["items_failed"],
                    status=WorkerStatus(row_dict["status"]),
                    current_work_item_id=row_dict.get("current_work_item_id"),
                ))
            
            return workers
            
        except pyodbc.Error as e:
            logger.error(f"Failed to get active workers: {e}")
            raise
    
    def remove_worker(self, worker_id: str) -> bool:
        """
        Remove a worker heartbeat record.
        
        Args:
            worker_id: Worker to remove
            
        Returns:
            True if worker was removed
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(f"""
                DELETE FROM [{self.schema}].[worker_heartbeats]
                WHERE worker_id = ?
            """, (worker_id,))
            
            removed = cursor.rowcount > 0
            self.conn.commit()
            
            return removed
            
        except pyodbc.Error as e:
            logger.error(f"Failed to remove worker: {e}")
            self.conn.rollback()
            raise
    
    # =========================================================================
    # Queue Statistics
    # =========================================================================
    
    def get_queue_stats(self) -> QueueStats:
        """
        Get detailed queue statistics.
        
        Returns:
            QueueStats object with counts and metadata
        """
        try:
            cursor = self.conn.cursor()
            
            # Get counts by status
            cursor.execute(f"""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM [{self.schema}].[work_items]
                GROUP BY status
            """)
            
            counts = {}
            for row in cursor.fetchall():
                counts[row[0]] = row[1]
            
            # Get oldest pending
            cursor.execute(f"""
                SELECT MIN(created_at) 
                FROM [{self.schema}].[work_items]
                WHERE status = ?
            """, (WorkItemStatus.PENDING.value,))
            
            oldest_row = cursor.fetchone()
            oldest_pending = oldest_row[0] if oldest_row else None
            
            # Get active worker count
            workers = self.get_active_workers()
            
            return QueueStats(
                pending=counts.get(WorkItemStatus.PENDING.value, 0),
                in_progress=counts.get(WorkItemStatus.IN_PROGRESS.value, 0),
                completed=counts.get(WorkItemStatus.COMPLETED.value, 0),
                failed=counts.get(WorkItemStatus.FAILED.value, 0),
                total=sum(counts.values()),
                oldest_pending_at=oldest_pending,
                active_workers=len(workers),
            )
            
        except pyodbc.Error as e:
            logger.error(f"Failed to get queue stats: {e}")
            raise

    def close(self) -> None:
        """Close the database connection."""
        with self._connections_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except pyodbc.Error:
                    pass
            self._connections.clear()
        logger.debug("Closed SQL Server state store connections")


class _ThreadLocalConnectionProxy:
    """Proxy that routes cursor/commit/rollback/close to a thread-local connection."""
    def __init__(self, store: "SqlServerStateStore"):
        self._store = store

    def cursor(self):
        return self._store._get_conn().cursor()

    def commit(self):
        return self._store._get_conn().commit()

    def rollback(self):
        return self._store._get_conn().rollback()

    def close(self):
        return self._store._get_conn().close()
