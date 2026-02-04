#!/usr/bin/env python3
"""
Seed Loader CLI for Holocron Analytics.

Loads JSON seed data into SQL Server dimensional model tables.

Usage:
    python seed_loader.py --all
    python seed_loader.py --tables DimFranchise,DimWork
    python seed_loader.py --all --dry-run
    python seed_loader.py --all --verbose
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pyodbc
except ImportError:
    print("Error: pyodbc is required. Install with: pip install pyodbc")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv is optional
    pass

from ingest.seeds import (
    SeedFile,
    SeedLoader,
    discover_seed_files,
    load_seed_file,
)
from ingest.seeds.seed_io import SeedValidationError
from ingest.seeds.db_loader import SeedLoaderError


# Default paths
SEEDS_DATA_DIR = Path(__file__).parent.parent / "db" / "seeds" / "data"
SEEDS_LOGS_DIR = Path(__file__).parent.parent / "db" / "seeds" / "logs"


def setup_logging(verbose: bool = False, log_dir: Path | None = None) -> None:
    """Configure logging to console and optionally to file."""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler (if log_dir provided)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"seed_loader_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        logging.info(f"Logging to file: {log_file}")


def get_connection_string() -> str:
    """
    Build ODBC connection string from environment variables.

    Supports either a full connection string or discrete variables.
    """
    # Option 1: Full connection string
    conn_str = os.environ.get("SEED_SQLSERVER_CONN_STR")
    if conn_str:
        return conn_str

    # Option 2: Discrete variables
    host = os.environ.get("SEED_SQLSERVER_HOST")
    database = os.environ.get("SEED_SQLSERVER_DATABASE")
    user = os.environ.get("SEED_SQLSERVER_USER")
    password = os.environ.get("SEED_SQLSERVER_PASSWORD")
    port = os.environ.get("SEED_SQLSERVER_PORT", "1434")
    driver = os.environ.get(
        "SEED_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"
    )

    if not all([host, database, user, password]):
        raise ValueError(
            "Database connection not configured. Set SEED_SQLSERVER_CONN_STR or "
            "individual SEED_SQLSERVER_HOST, SEED_SQLSERVER_DATABASE, "
            "SEED_SQLSERVER_USER, SEED_SQLSERVER_PASSWORD environment variables."
        )

    return (
        f"Driver={{{driver}}};"
        f"Server={host},{port};"
        f"Database={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes"
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Load JSON seed data into SQL Server tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Load all seed files
    python seed_loader.py --all

    # Load specific tables only
    python seed_loader.py --tables DimFranchise,DimWork,DimScene

    # Validate without writing (dry run)
    python seed_loader.py --all --dry-run

    # Verbose output with debug logging
    python seed_loader.py --all --verbose
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all seed files found in the data directory",
    )

    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of table names to load (e.g., DimFranchise,DimWork)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate seed files without writing to database",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    parser.add_argument(
        "--seeds-dir",
        type=Path,
        default=SEEDS_DATA_DIR,
        help=f"Path to seeds data directory (default: {SEEDS_DATA_DIR})",
    )

    parser.add_argument(
        "--no-file-log",
        action="store_true",
        help="Disable logging to file",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Validate arguments
    if not args.all and not args.tables:
        print("Error: Must specify --all or --tables")
        return 1

    # Setup logging
    log_dir = None if args.no_file_log else SEEDS_LOGS_DIR
    setup_logging(verbose=args.verbose, log_dir=log_dir)

    logger = logging.getLogger(__name__)

    # Discover seed files
    logger.info(f"Discovering seed files in: {args.seeds_dir}")
    seed_file_paths = discover_seed_files(args.seeds_dir)

    if not seed_file_paths:
        logger.error(f"No seed files found in {args.seeds_dir}")
        return 1

    logger.info(f"Found {len(seed_file_paths)} seed files")

    # Parse table filter
    table_filter: set[str] | None = None
    if args.tables:
        table_filter = set(t.strip() for t in args.tables.split(","))
        logger.info(f"Filtering to tables: {', '.join(sorted(table_filter))}")

    # Load and parse seed files
    seed_files: list[SeedFile] = []
    for path in seed_file_paths:
        try:
            sf = load_seed_file(path)
            seed_files.append(sf)
            logger.debug(f"Parsed: {path.name} -> {sf.full_table_name}")
        except SeedValidationError as e:
            logger.error(f"Failed to parse {path}: {e}")
            return 1

    # Connect to database
    if args.dry_run:
        logger.info("[DRY RUN] Skipping database connection")
        # Still need to validate - create a mock validation pass
        logger.info("Performing offline validation...")
        for sf in seed_files:
            if table_filter and sf.target.table not in table_filter:
                continue
            columns = sorted(sf.rows[0].keys()) if sf.rows else []
            logger.info(
                f"  {sf.target.table}: {len(sf.rows)} rows, "
                f"columns: {', '.join(columns)}"
            )
        logger.info("[DRY RUN] Validation complete (no database connection)")
        return 0

    try:
        conn_str = get_connection_string()
        logger.info("Connecting to SQL Server...")
        conn = pyodbc.connect(conn_str, autocommit=False)
        logger.info("Connected successfully")
    except ValueError as e:
        logger.error(str(e))
        return 1
    except pyodbc.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1

    try:
        # Create loader
        loader = SeedLoader(
            conn=conn,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        # Load all seeds
        results = loader.load_all(seed_files, table_filter=table_filter)

        # Commit transaction
        conn.commit()
        logger.info("Transaction committed")

        # Summary
        total_rows = sum(r for r in results.values() if r > 0)
        logger.info(f"Seed loading complete. Total rows inserted: {total_rows}")

        for table, count in results.items():
            status = f"{count} rows" if count >= 0 else "FAILED"
            logger.info(f"  {table}: {status}")

        return 0 if all(r >= 0 for r in results.values()) else 1

    except SeedLoaderError as e:
        logger.error(f"Seed loading failed: {e}")
        conn.rollback()
        logger.info("Transaction rolled back")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        conn.rollback()
        return 1
    finally:
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    sys.exit(main())
