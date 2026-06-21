"""
SQL Server State Administration Utilities

REPLACEMENT FOR REMOVED SQLITE SCRIPTS:
- mark_openalex_failed.py (removed)
- reset_wookieepedia_pending.py (removed)

SQLite backend has been fully removed. This module provides SQL Server replacements
for common state store administration tasks.

WHAT THE REMOVED SCRIPTS DID:
1. mark_openalex_failed.py: 
   - Connected to SQLite state DB (local/state/ingest_state.db)
   - Queried work_items table grouped by status and source_system
   - Updated all pending openalex items to failed status
   
2. reset_wookieepedia_pending.py:
   - Connected to SQLite state DB
   - Found last 50 completed wookieepedia work items
   - Reset them to pending status with attempt=0

SQL SERVER REPLACEMENT PLAN:

Database: Holocron
Schema: ingest (configurable via INGEST_SQLSERVER_SCHEMA)
Table: ingest.work_items

Connection approach:
- Use pyodbc with ODBC Driver 18 for SQL Server
- Get connection parameters from environment variables:
  - INGEST_SQLSERVER_HOST (default: localhost)
  - INGEST_SQLSERVER_PORT (default: 1433)
  - INGEST_SQLSERVER_DATABASE (default: Holocron)
  - INGEST_SQLSERVER_USER (default: sa)
  - INGEST_SQLSERVER_PASSWORD (required)
  - INGEST_SQLSERVER_SCHEMA (default: ingest)

Schema expectations:
- Table: {schema}.work_items
- Columns match SqlServerStateStore schema:
  - work_item_id (varchar/nvarchar, PK)
  - source_system (varchar/nvarchar)
  - source_name (varchar/nvarchar)
  - resource_type (varchar/nvarchar)
  - resource_id (varchar/nvarchar)
  - status (varchar/nvarchar) - values: 'pending', 'in_progress', 'completed', 'failed'
  - attempt (int)
  - updated_at (datetime2)
  - created_at (datetime2)
  - error_message (nvarchar, nullable)
  - (additional columns as per SqlServerStateStore)

Example queries:
1. View status counts by source:
   SELECT status, source_system, COUNT(*) as count
   FROM ingest.work_items
   GROUP BY status, source_system
   ORDER BY status, source_system;

2. Mark pending openalex items as failed:
   UPDATE ingest.work_items
   SET status = 'failed',
       updated_at = GETUTCDATE(),
       error_message = 'Bulk marked as failed via admin script'
   WHERE status = 'pending'
   AND source_system = 'openalex';

3. Reset completed wookieepedia items to pending:
   WITH LastCompleted AS (
       SELECT TOP 50 work_item_id
       FROM ingest.work_items
       WHERE status = 'completed'
       AND source_name = 'wookieepedia'
       ORDER BY updated_at DESC
   )
   UPDATE wi
   SET status = 'pending',
       attempt = 0,
       updated_at = GETUTCDATE(),
       error_message = NULL
   FROM ingest.work_items wi
   INNER JOIN LastCompleted lc ON wi.work_item_id = lc.work_item_id;

NEXT PR WORK / OPEN QUESTIONS:
- [ ] Implement connection helper using environment variables
- [ ] Add mark_failed_by_source(source_system, reason) function
- [ ] Add reset_to_pending(source_name, limit, status_filter) function
- [ ] Add get_status_summary() for dashboard-style reporting
- [ ] Consider adding transaction handling for bulk updates
- [ ] Add dry-run mode for safety
- [ ] Add logging of operations for audit trail
- [ ] Consider if these should be integrated into ingest CLI as subcommands
- [ ] Add validation that work items aren't in_progress before resetting

For now, use SQL Server Management Studio, Azure Data Studio, or psql equivalent
to manually run the SQL queries above when needed.
"""

import os
import logging
from typing import Optional


logger = logging.getLogger(__name__)


# TODO: Implement SQL Server connection and admin functions
# See comment block above for SQL queries to adapt

def get_connection_string() -> str:
    """
    Build SQL Server connection string from environment variables.
    
    Raises ValueError if required variables are missing.
    """
    raise NotImplementedError(
        "SQL Server state administration not yet implemented. "
        "See docstring for SQL queries to run manually."
    )


def mark_source_as_failed(source_system: str, reason: Optional[str] = None) -> int:
    """
    Mark all pending work items from a source system as failed.
    
    Args:
        source_system: Source system identifier (e.g., 'openalex')
        reason: Optional reason for marking as failed
        
    Returns:
        Number of rows updated
    """
    raise NotImplementedError(
        "SQL Server state administration not yet implemented. "
        "Use SQL query from docstring directly in SQL Server client."
    )


def reset_completed_to_pending(
    source_name: str,
    limit: int = 50,
) -> int:
    """
    Reset recently completed work items back to pending status.
    
    Args:
        source_name: Source name (e.g., 'wookieepedia')
        limit: Maximum number of items to reset
        
    Returns:
        Number of rows updated
    """
    raise NotImplementedError(
        "SQL Server state administration not yet implemented. "
        "Use SQL query from docstring directly in SQL Server client."
    )


if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*80)
    print("This is a stub module. See docstring for SQL queries to run manually.")
    print("="*80)
