"""
Shared test fixtures and configuration for pytest.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Generator, Optional

import pytest

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


logger = logging.getLogger(__name__)


# ============================================================================
# Environment detection
# ============================================================================

def is_sqlserver_available() -> bool:
    """Check if SQL Server is available for testing."""
    password = os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD")
    if not password:
        return False
    
    try:
        import pyodbc
        
        host = os.environ.get("INGEST_SQLSERVER_HOST", "localhost")
        port = int(os.environ.get("INGEST_SQLSERVER_PORT", "1433"))
        database = os.environ.get("INGEST_SQLSERVER_DATABASE", 
                                  os.environ.get("MSSQL_DATABASE", "Holocron"))
        username = os.environ.get("INGEST_SQLSERVER_USER", "sa")
        driver = os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        
        conn_str = (
            f"Driver={{{driver}}};"
            f"Server={host},{port};"
            f"Database={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes"
        )
        
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return True
        
    except Exception as e:
        logger.debug(f"SQL Server not available: {e}")
        return False


def wait_for_sqlserver(timeout: int = 60, interval: int = 2) -> bool:
    """
    Wait for SQL Server to become available.
    
    Args:
        timeout: Maximum time to wait in seconds
        interval: Time between retries in seconds
        
    Returns:
        True if SQL Server became available, False otherwise
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if is_sqlserver_available():
            return True
        time.sleep(interval)
    
    return False


# ============================================================================
# Pytest hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (requires SQL Server)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (requires full stack)")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")


def pytest_collection_modifyitems(config, items):
    """Automatically skip integration/e2e tests if SQL Server is not available."""
    if is_sqlserver_available():
        return
    
    skip_sqlserver = pytest.mark.skip(
        reason="SQL Server not available (set MSSQL_SA_PASSWORD and ensure SQL Server is running)"
    )
    
    for item in items:
        # Skip tests marked as integration or e2e
        if "integration" in item.keywords or "e2e" in item.keywords:
            item.add_marker(skip_sqlserver)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sqlserver_available() -> bool:
    """Session-scoped fixture to check if SQL Server is available."""
    return is_sqlserver_available()


@pytest.fixture(scope="session")
def sqlserver_config() -> dict:
    """Session-scoped fixture providing SQL Server connection configuration."""
    return {
        "host": os.environ.get("INGEST_SQLSERVER_HOST", "localhost"),
        "port": int(os.environ.get("INGEST_SQLSERVER_PORT", "1433")),
        "database": os.environ.get("INGEST_SQLSERVER_DATABASE", 
                                   os.environ.get("MSSQL_DATABASE", "Holocron")),
        "username": os.environ.get("INGEST_SQLSERVER_USER", "sa"),
        "password": os.environ.get("INGEST_SQLSERVER_PASSWORD", 
                                   os.environ.get("MSSQL_SA_PASSWORD")),
        "driver": os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
        "schema": os.environ.get("INGEST_SQLSERVER_SCHEMA", "test_ingest"),
    }


@pytest.fixture(scope="function")
def test_schema_name() -> str:
    """Fixture providing a unique test schema name."""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def sqlserver_state_store(sqlserver_config: dict):
    """
    Session-scoped fixture providing a SQL Server state store for testing.
    
    Uses a dedicated test schema that is cleaned up after tests.
    """
    if not sqlserver_config["password"]:
        pytest.skip("SQL Server password not configured")
    
    from ingest.state import SqlServerStateStore
    
    store = SqlServerStateStore(
        host=sqlserver_config["host"],
        port=sqlserver_config["port"],
        database=sqlserver_config["database"],
        username=sqlserver_config["username"],
        password=sqlserver_config["password"],
        driver=sqlserver_config["driver"],
        schema=sqlserver_config["schema"],
        auto_init=True,
    )
    
    yield store
    
    # Cleanup: Delete test data but keep schema
    try:
        cursor = store.conn.cursor()
        cursor.execute(f"""
            DELETE FROM [{store.schema}].[work_items]
            WHERE source_system LIKE 'test%'
        """)
        store.conn.commit()
    except Exception:
        pass
    
    store.close()


@pytest.fixture(scope="function")
def clean_state_store(sqlserver_state_store):
    """
    Function-scoped fixture that cleans up test data before and after each test.
    """
    store = sqlserver_state_store
    
    # Cleanup before test
    try:
        cursor = store.conn.cursor()
        cursor.execute(f"""
            DELETE FROM [{store.schema}].[work_items]
            WHERE source_system LIKE 'test%'
        """)
        store.conn.commit()
    except Exception:
        pass
    
    yield store
    
    # Cleanup after test
    try:
        cursor = store.conn.cursor()
        cursor.execute(f"""
            DELETE FROM [{store.schema}].[work_items]
            WHERE source_system LIKE 'test%'
        """)
        store.conn.commit()
    except Exception:
        pass


@pytest.fixture
def test_connector():
    """Fixture providing a test connector."""
    from ingest.connectors.test_connector import TestConnector
    
    connector = TestConnector()
    yield connector
    connector.close()


@pytest.fixture
def sample_work_items():
    """Fixture providing sample work items for testing."""
    from ingest.connectors.test_connector import create_test_work_items
    
    return create_test_work_items(count=5)
