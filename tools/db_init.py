#!/usr/bin/env python3
"""
Database initialization tool for SQL Server.

Applies versioned migration scripts to initialize/update the database schema.
Migrations are idempotent and can be run multiple times safely.

Usage:
    python -m tools.db_init
    python -m tools.db_init --migrations-dir db/migrations
    python -m tools.db_init --dry-run

Environment variables:
    INGEST_SQLSERVER_HOST - SQL Server hostname (default: localhost)
    INGEST_SQLSERVER_PORT - SQL Server port (default: 1433)
    INGEST_SQLSERVER_DATABASE - Database name (default: Holocron)
    INGEST_SQLSERVER_USER - Username (default: sa)
    INGEST_SQLSERVER_PASSWORD - Password (required)
    INGEST_SQLSERVER_DRIVER - ODBC driver (default: ODBC Driver 18 for SQL Server)
    MSSQL_SA_PASSWORD - Alternative password variable (used if INGEST_SQLSERVER_PASSWORD not set)
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_connection_config() -> dict:
    """Get database connection configuration from environment variables."""
    return {
        "host": os.environ.get("INGEST_SQLSERVER_HOST", "localhost"),
        "port": int(os.environ.get("INGEST_SQLSERVER_PORT", "1433")),
        "database": os.environ.get("INGEST_SQLSERVER_DATABASE", 
                                   os.environ.get("MSSQL_DATABASE", "Holocron")),
        "username": os.environ.get("INGEST_SQLSERVER_USER", "sa"),
        "password": os.environ.get("INGEST_SQLSERVER_PASSWORD", 
                                   os.environ.get("MSSQL_SA_PASSWORD")),
        "driver": os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
    }


def build_connection_string(config: dict, use_master: bool = False) -> str:
    """Build ODBC connection string from config."""
    database = "master" if use_master else config["database"]
    return (
        f"Driver={{{config['driver']}}};"
        f"Server={config['host']},{config['port']};"
        f"Database={database};"
        f"UID={config['username']};"
        f"PWD={config['password']};"
        f"TrustServerCertificate=yes"
    )


def wait_for_sqlserver(config: dict, timeout: int = 60, interval: int = 2) -> bool:
    """
    Wait for SQL Server to be ready to accept connections.
    
    Args:
        config: Connection configuration
        timeout: Maximum time to wait in seconds
        interval: Time between retries in seconds
        
    Returns:
        True if connection succeeded, False if timeout
    """
    try:
        import pyodbc
    except ImportError:
        logger.error("pyodbc is required. Install with: pip install pyodbc")
        return False
    
    logger.info(f"Waiting for SQL Server at {config['host']}:{config['port']}...")
    
    conn_str = build_connection_string(config, use_master=True)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
            conn.close()
            logger.info("✓ SQL Server is ready")
            return True
        except pyodbc.Error as e:
            elapsed = int(time.time() - start_time)
            logger.debug(f"Connection attempt failed ({elapsed}s): {e}")
            time.sleep(interval)
    
    logger.error(f"✗ Timeout waiting for SQL Server ({timeout}s)")
    return False


def ensure_database_exists(config: dict) -> bool:
    """
    Ensure the target database exists, creating it if necessary.
    
    Args:
        config: Connection configuration
        
    Returns:
        True if database exists or was created
    """
    try:
        import pyodbc
    except ImportError:
        logger.error("pyodbc is required. Install with: pip install pyodbc")
        return False
    
    database = config["database"]
    logger.info(f"Ensuring database [{database}] exists...")
    
    conn_str = build_connection_string(config, use_master=True)
    
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT DB_ID(?)", (database,))
        result = cursor.fetchone()
        
        if result[0] is None:
            logger.info(f"Creating database [{database}]...")
            # Use dynamic SQL to avoid parameterization issues with CREATE DATABASE
            # Database name is from trusted config, not user input
            cursor.execute(f"CREATE DATABASE [{database}]")
            logger.info(f"✓ Database [{database}] created successfully")
        else:
            logger.info(f"✓ Database [{database}] already exists")
        
        conn.close()
        return True
        
    except pyodbc.Error as e:
        logger.error(f"✗ Failed to ensure database exists: {e}")
        return False


def get_migration_scripts(migrations_dir: Path) -> List[Path]:
    """
    Get sorted list of migration scripts from the migrations directory.
    
    Args:
        migrations_dir: Path to migrations directory
        
    Returns:
        List of migration script paths, sorted by name
    """
    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return []
    
    scripts = sorted(migrations_dir.glob("*.sql"))
    return scripts


def run_migration_script(conn, script_path: Path, dry_run: bool = False) -> bool:
    """
    Run a single migration script.
    
    Args:
        conn: pyodbc connection
        script_path: Path to the SQL script
        dry_run: If True, only print what would be done
        
    Returns:
        True if successful
    """
    logger.info(f"Running migration: {script_path.name}")
    
    try:
        sql_content = script_path.read_text(encoding="utf-8")
        
        if dry_run:
            logger.info(f"  [DRY RUN] Would execute {len(sql_content)} bytes of SQL")
            return True
        
        cursor = conn.cursor()
        
        # Split by GO statements (SQL Server batch separator)
        # Handle GO on its own line (case-insensitive)
        batches = []
        current_batch = []
        
        for line in sql_content.split('\n'):
            stripped = line.strip().upper()
            if stripped == 'GO':
                if current_batch:
                    batches.append('\n'.join(current_batch))
                    current_batch = []
            else:
                current_batch.append(line)
        
        # Don't forget the last batch if it doesn't end with GO
        if current_batch:
            batch_content = '\n'.join(current_batch).strip()
            if batch_content:
                batches.append(batch_content)
        
        # Execute each batch
        for i, batch in enumerate(batches, 1):
            if batch.strip():
                try:
                    cursor.execute(batch)
                    # Capture print messages
                    while cursor.nextset():
                        pass
                except Exception as e:
                    logger.error(f"  Error in batch {i}: {e}")
                    raise
        
        conn.commit()
        logger.info(f"  ✓ Migration completed: {script_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"  ✗ Migration failed: {script_path.name} - {e}")
        conn.rollback()
        return False


def run_migrations(
    config: dict,
    migrations_dir: Path,
    dry_run: bool = False,
    wait_timeout: int = 60,
) -> bool:
    """
    Run all migration scripts in order.
    
    Args:
        config: Database connection configuration
        migrations_dir: Path to migrations directory
        dry_run: If True, only print what would be done
        wait_timeout: Timeout for waiting for SQL Server
        
    Returns:
        True if all migrations succeeded
    """
    try:
        import pyodbc
    except ImportError:
        logger.error("pyodbc is required. Install with: pip install pyodbc")
        return False
    
    # Wait for SQL Server to be ready
    if not wait_for_sqlserver(config, timeout=wait_timeout):
        return False
    
    # Ensure database exists
    if not ensure_database_exists(config):
        return False
    
    # Get migration scripts
    scripts = get_migration_scripts(migrations_dir)
    
    if not scripts:
        logger.warning("No migration scripts found")
        return True
    
    logger.info(f"Found {len(scripts)} migration script(s)")
    
    # Connect to target database
    conn_str = build_connection_string(config)
    
    try:
        conn = pyodbc.connect(conn_str)
        
        # Run each migration
        for script in scripts:
            if not run_migration_script(conn, script, dry_run):
                conn.close()
                return False
        
        conn.close()
        logger.info("✓ All migrations completed successfully")
        return True
        
    except pyodbc.Error as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize SQL Server database with migration scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("db/migrations"),
        help="Path to migrations directory (default: db/migrations)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for waiting for SQL Server (default: 60)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print header
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║       SQL Server Database Initialization                    ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Get configuration
    config = get_connection_config()
    
    if not config["password"]:
        logger.error("No password configured!")
        logger.error("Set INGEST_SQLSERVER_PASSWORD or MSSQL_SA_PASSWORD environment variable")
        return 1
    
    # Print configuration (without password)
    logger.info("Configuration:")
    logger.info(f"  Host:       {config['host']}")
    logger.info(f"  Port:       {config['port']}")
    logger.info(f"  Database:   {config['database']}")
    logger.info(f"  User:       {config['username']}")
    logger.info(f"  Driver:     {config['driver']}")
    logger.info(f"  Migrations: {args.migrations_dir}")
    logger.info("")
    
    # Resolve migrations directory
    migrations_dir = args.migrations_dir
    if not migrations_dir.is_absolute():
        # Try relative to current directory first
        if not migrations_dir.exists():
            # Try relative to script location
            script_dir = Path(__file__).parent.parent
            migrations_dir = script_dir / args.migrations_dir
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        logger.error(f"Also tried: {args.migrations_dir}")
        return 1
    
    # Run migrations
    success = run_migrations(
        config=config,
        migrations_dir=migrations_dir,
        dry_run=args.dry_run,
        wait_timeout=args.wait_timeout,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
