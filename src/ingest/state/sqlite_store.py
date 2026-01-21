"""
SQLite-based state store for managing work item queue.

.. deprecated::
    SQLite backend is deprecated. Use SQL Server backend instead.
    Set DB_BACKEND=sqlserver environment variable or use create_state_store() factory.
"""

import logging
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..core.state_store import StateStore
from ..core.models import WorkItem, WorkItemStatus


logger = logging.getLogger(__name__)


class SqliteStateStore(StateStore):
    """
    SQLite-based implementation of the state store.
    
    .. deprecated::
        This class is deprecated. Use SqlServerStateStore instead.
        SQLite is only suitable for local testing and development.
    
    Manages the work queue and tracks status using a local SQLite database.
    """

    def __init__(self, db_path: Path, auto_init: bool = True):
        """
        Initialize the SQLite state store.
        
        .. deprecated::
            SQLite backend is deprecated. Use SQL Server backend.
        
        Args:
            db_path: Path to the SQLite database file
            auto_init: Whether to create tables automatically
        """
        warnings.warn(
            "SqliteStateStore is deprecated. Use SqlServerStateStore instead. "
            "Set DB_BACKEND=sqlserver or use create_state_store() factory.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning(
            "SQLite backend is deprecated; use SQL Server backend. "
            "See docs/sqlserver-backend.md for migration instructions."
        )
        
        self.db_path = Path(db_path)
        self.conn = None
        self._connect()
        
        if auto_init:
            self._init_schema()

    def _connect(self) -> None:
        """Establish database connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        logger.debug(f"Connected to SQLite state store: {self.db_path}")

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_items (
                work_item_id TEXT PRIMARY KEY,
                source_system TEXT NOT NULL,
                source_name TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                request_uri TEXT NOT NULL,
                request_method TEXT NOT NULL,
                request_headers TEXT,
                request_body TEXT,
                metadata TEXT,
                priority INTEGER NOT NULL DEFAULT 100,
                status TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0,
                run_id TEXT,
                discovered_from TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT,
                dedupe_key TEXT NOT NULL
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_work_items_status 
            ON work_items (status, priority, created_at)
        """)
        
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_work_items_dedupe 
            ON work_items (dedupe_key)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_work_items_run_id 
            ON work_items (run_id)
        """)
        
        self.conn.commit()
        logger.debug("Initialized state store schema")

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
            import json
            request_headers = json.dumps(work_item.request_headers) if work_item.request_headers else None
            metadata_json = json.dumps(work_item.metadata) if work_item.metadata else None
            
            cursor.execute("""
                INSERT INTO work_items (
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
                work_item.created_at.isoformat(),
                work_item.updated_at.isoformat(),
                dedupe_key,
            ))
            
            self.conn.commit()
            logger.debug(f"Enqueued work item: {dedupe_key}")
            return True
            
        except sqlite3.IntegrityError:
            logger.debug(f"Work item already exists (race condition): {dedupe_key}")
            return False
        except Exception as e:
            logger.error(f"Failed to enqueue work item: {e}")
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
            cursor.execute("""
                SELECT * FROM work_items
                WHERE status = ?
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
            """, (WorkItemStatus.PENDING.value, limit))
            
            rows = cursor.fetchall()
            work_items = []
            
            for row in rows:
                work_item = self._row_to_work_item(row)
                work_items.append(work_item)
                
                # Mark as in progress
                self.update_status(work_item.work_item_id, WorkItemStatus.IN_PROGRESS)
            
            return work_items
            
        except Exception as e:
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
            
            cursor.execute("""
                UPDATE work_items
                SET status = ?, updated_at = ?, error_message = ?
                WHERE work_item_id = ?
            """, (
                status.value,
                datetime.now(timezone.utc).isoformat(),
                error_message,
                work_item_id,
            ))
            
            self.conn.commit()
            logger.debug(f"Updated work item {work_item_id} to status {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update work item status: {e}")
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
            
            cursor.execute("""
                SELECT * FROM work_items WHERE work_item_id = ?
            """, (work_item_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_work_item(row)
            return None
            
        except Exception as e:
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
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM work_items WHERE dedupe_key = ? LIMIT 1
        """, (dedupe_key,))
        return cursor.fetchone() is not None

    def get_stats(self) -> dict:
        """
        Get statistics about the work queue.
        
        Returns:
            Dictionary with counts by status
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM work_items
            GROUP BY status
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row["status"]] = row["count"]
        
        return stats

    def _row_to_work_item(self, row: sqlite3.Row) -> WorkItem:
        """Convert a database row to a WorkItem object."""
        import json
        
        # Parse JSON fields
        request_headers = json.loads(row["request_headers"]) if row["request_headers"] else None
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        
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
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQLite state store connection")
