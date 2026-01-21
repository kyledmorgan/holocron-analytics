"""
State store implementations for managing work queue.

The default backend is SQL Server (SqlServerStateStore).
SQLite (SqliteStateStore) is deprecated and should only be used for 
testing or when SQL Server is not available.

To select backend, set the DB_BACKEND environment variable:
    - DB_BACKEND=sqlserver (default)
    - DB_BACKEND=sqlite (deprecated)
"""

import logging
import os
import warnings
from pathlib import Path
from typing import Optional, Union

from ..core.state_store import StateStore


logger = logging.getLogger(__name__)


# Lazy imports to avoid import errors when dependencies are missing
def _get_sqlite_store():
    from .sqlite_store import SqliteStateStore
    return SqliteStateStore


def _get_sqlserver_store():
    from .sqlserver_store import SqlServerStateStore
    return SqlServerStateStore


def create_state_store(
    backend: Optional[str] = None,
    # SQLite options
    db_path: Optional[Union[str, Path]] = None,
    # SQL Server options
    connection_string: Optional[str] = None,
    host: str = "localhost",
    port: int = 1433,
    database: str = "Holocron",
    username: str = "sa",
    password: Optional[str] = None,
    driver: str = "ODBC Driver 18 for SQL Server",
    schema: str = "ingest",
    trust_server_certificate: bool = True,
    auto_init: bool = True,
) -> StateStore:
    """
    Factory function to create the appropriate state store based on configuration.
    
    Args:
        backend: Backend type ('sqlserver' or 'sqlite'). Defaults to DB_BACKEND env var or 'sqlserver'.
        
        SQLite options:
            db_path: Path to SQLite database file
            
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
        StateStore instance
        
    Raises:
        ValueError: If backend is not recognized
        ImportError: If required dependencies are missing
    """
    # Determine backend
    if backend is None:
        backend = os.environ.get("DB_BACKEND", "sqlserver").lower()
    
    if backend == "sqlite":
        warnings.warn(
            "SQLite backend is deprecated and will be removed in a future version. "
            "Please migrate to SQL Server backend (DB_BACKEND=sqlserver).",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning(
            "SQLite backend is deprecated. Use SQL Server backend for production workloads."
        )
        
        SqliteStateStore = _get_sqlite_store()
        
        if db_path is None:
            db_path = Path("local/state/ingest_state.db")
        
        return SqliteStateStore(db_path=Path(db_path), auto_init=auto_init)
    
    elif backend == "sqlserver":
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
    
    else:
        raise ValueError(
            f"Unknown backend: {backend}. "
            "Supported backends: 'sqlserver' (default), 'sqlite' (deprecated)"
        )


# Re-export for backward compatibility
from .sqlite_store import SqliteStateStore

# Conditional import of SqlServerStateStore
try:
    from .sqlserver_store import SqlServerStateStore
    __all__ = ["SqliteStateStore", "SqlServerStateStore", "create_state_store"]
except ImportError:
    # pyodbc not installed
    __all__ = ["SqliteStateStore", "create_state_store"]
