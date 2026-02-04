"""
State store implementations for managing work queue.

The backend is SQL Server (SqlServerStateStore).
"""

import logging
import os
from pathlib import Path
from typing import Optional

from ..core.state_store import StateStore


logger = logging.getLogger(__name__)


# Lazy import to avoid import errors when dependencies are missing
def _get_sqlserver_store():
    from .sqlserver_store import SqlServerStateStore
    return SqlServerStateStore


def create_state_store(
    backend: Optional[str] = None,
    # SQL Server options
    connection_string: Optional[str] = None,
    host: str = "localhost",
    port: int = 1434,
    database: str = "Holocron",
    username: str = "sa",
    password: Optional[str] = None,
    driver: str = "ODBC Driver 18 for SQL Server",
    schema: str = "ingest",
    trust_server_certificate: bool = True,
    auto_init: bool = True,
    # Deprecated parameters (kept for API compatibility, raise errors if used)
    db_path: Optional[str] = None,
) -> StateStore:
    """
    Factory function to create a SQL Server state store.
    
    Args:
        backend: Backend type (must be 'sqlserver'). Defaults to DB_BACKEND env var or 'sqlserver'.
            
        SQL Server options:
            connection_string: Full ODBC connection string
            host: SQL Server host
            port: SQL Server port
            database: Database name
            username: Database username
            password: Database password
            driver: ODBC driver name
            schema: Schema name for tables
            trust_server_certificate: Trust self-signed certs
            auto_init: Auto-create schema/tables
            
    Returns:
        SqlServerStateStore instance
        
    Raises:
        ValueError: If backend is not 'sqlserver' or if deprecated parameters are used
        ImportError: If required dependencies are missing
    """
    # Check for deprecated parameters
    if db_path is not None:
        raise ValueError(
            "SQLite backend has been removed. The 'db_path' parameter is no longer supported. "
            "Use SQL Server backend with appropriate connection parameters."
        )
    
    # Determine backend
    if backend is None:
        backend = os.environ.get("DB_BACKEND", "sqlserver").lower()
    
    if backend != "sqlserver":
        raise ValueError(
            f"SQLite backend has been removed. Only 'sqlserver' backend is supported. "
            f"Received: {backend}. "
            f"Update DB_BACKEND environment variable to 'sqlserver' and configure SQL Server connection."
        )
    
    SqlServerStateStore = _get_sqlserver_store()
    
    # Get password from environment if not provided
    if password is None:
        password = os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD")
    
    # Get connection string from environment if not provided
    if connection_string is None:
        connection_string = os.environ.get("INGEST_SQLSERVER_STATE_CONN_STR")
    
    return SqlServerStateStore(
        connection_string=connection_string,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        driver=driver,
        schema=schema,
        auto_init=auto_init,
        trust_server_certificate=trust_server_certificate,
    )


# Export SqlServerStateStore
try:
    from .sqlserver_store import SqlServerStateStore
    __all__ = ["SqlServerStateStore", "create_state_store"]
except ImportError:
    # pyodbc not installed
    __all__ = ["create_state_store"]
