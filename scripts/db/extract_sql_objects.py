#!/usr/bin/env python3
"""
SQL Object Extraction & Reconciliation Script

Connects to the Docker SQL Server instance and extracts object definitions
into the canonical repo folder structure:

  - src/db/dml/stored_procedures/  → stored procedures
  - src/db/dml/functions/          → scalar + table-valued functions
  - src/db/dml/triggers/           → triggers
  - src/db/views/                  → views (organized by schema subfolder)

Optionally emits a reconciliation report comparing SQL Server objects
to existing repo files.

Usage:
    python scripts/db/extract_sql_objects.py [OPTIONS]

Options:
    --extract           Extract object definitions from SQL Server to repo
    --reconcile         Print reconciliation report (no file writes)
    --verbose, -v       Enable verbose output
    --dry-run           Show what would be written without writing
    --connection-string Override the database connection string
    --schemas           Comma-separated list of schemas to include
                        (default: dbo,sem,llm,ingest,vector)

Exit codes:
    0 = Success (or reconciliation found no issues)
    1 = Reconciliation found mismatches
    2 = Connection error
    3 = Configuration error
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc required. Install with: pip install pyodbc")
    sys.exit(3)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DML_ROOT = REPO_ROOT / "src" / "db" / "dml"
VIEWS_ROOT = REPO_ROOT / "src" / "db" / "views"
DDL_ROOT = REPO_ROOT / "src" / "db" / "ddl"

# Map SQL Server object type codes to repo sub-paths under DML_ROOT
OBJECT_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "P":   ("stored_procedures", "Stored Procedure"),
    "FN":  ("functions", "Scalar Function"),
    "IF":  ("functions", "Inline Table-Valued Function"),
    "TF":  ("functions", "Table-Valued Function"),
    "TR":  ("triggers", "Trigger"),
}

DEFAULT_SCHEMAS = {"dbo", "sem", "llm", "ingest", "vector"}

# Regex to strip environment-specific USE [database] or full qualifiers
RE_USE_DB = re.compile(r"^\s*USE\s+\[?\w+\]?\s*;?\s*$", re.MULTILINE | re.IGNORECASE)
RE_DB_QUALIFIER = re.compile(r"\[Holocron\]\.", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SqlObject:
    """Represents a programmable object extracted from SQL Server."""
    schema_name: str
    object_name: str
    object_type: str          # SQL Server type code (P, FN, IF, TF, TR, V)
    type_desc: str            # Human-readable description
    definition: Optional[str] # Source text from sys.sql_modules


@dataclass
class ReconciliationResult:
    """Summary of reconciliation between SQL Server and repo."""
    in_sql_not_repo: List[str] = field(default_factory=list)
    in_repo_not_sql: List[str] = field(default_factory=list)
    matched: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Connection helper  (mirrors verify_schema_alignment.py)
# ---------------------------------------------------------------------------

def get_connection_string() -> str:
    """Build a connection string from environment variables."""
    conn_str = os.environ.get("VERIFY_SCHEMA_CONN_STR")
    if conn_str:
        return conn_str

    conn_str = os.environ.get("INGEST_SQLSERVER_CONN_STR")
    if conn_str:
        return conn_str

    host = os.environ.get("DB_HOST", os.environ.get("INGEST_SQLSERVER_HOST", "localhost"))
    port = os.environ.get("DB_PORT", os.environ.get("INGEST_SQLSERVER_PORT", "1433"))
    database = os.environ.get("DB_NAME", os.environ.get("MSSQL_DATABASE", "Holocron"))
    username = os.environ.get("DB_USER", os.environ.get("INGEST_SQLSERVER_USER", "sa"))
    password = os.environ.get("DB_PASSWORD", os.environ.get("MSSQL_SA_PASSWORD", ""))
    driver = os.environ.get("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    return (
        f"Driver={{{driver}}};"
        f"Server={host},{port};"
        f"Database={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes"
    )


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------

def fetch_objects(conn: pyodbc.Connection, schemas: Set[str]) -> List[SqlObject]:
    """
    Query sys.objects + sys.sql_modules for all programmable objects and views
    in the requested schemas.
    """
    schema_list = ", ".join(f"'{s}'" for s in schemas)

    query = f"""
        SELECT
            s.name          AS schema_name,
            o.name          AS object_name,
            RTRIM(o.type)   AS object_type,   -- sys.objects.type is CHAR(2), padded with space
            o.type_desc     AS type_desc,
            m.definition    AS definition
        FROM sys.objects o
        INNER JOIN sys.schemas s   ON o.schema_id = s.schema_id
        LEFT  JOIN sys.sql_modules m ON o.object_id = m.object_id
        WHERE s.name IN ({schema_list})
          AND o.type IN ('P','FN','IF','TF','TR','V')
          AND o.is_ms_shipped = 0
        ORDER BY s.name, o.type, o.name
    """

    cursor = conn.cursor()
    cursor.execute(query)

    objects: List[SqlObject] = []
    for row in cursor.fetchall():
        objects.append(SqlObject(
            schema_name=row.schema_name,
            object_name=row.object_name,
            object_type=row.object_type,
            type_desc=row.type_desc,
            definition=row.definition,
        ))
    return objects


def normalize_definition(definition: Optional[str]) -> str:
    """
    Normalize a SQL definition for stable, diff-friendly output.

    - Strip USE [database] statements
    - Remove database-qualified references like [Holocron].
    - Normalize line endings to LF
    - Strip trailing whitespace per line
    - Ensure file ends with a single newline
    """
    if not definition:
        return "-- (definition not available via sys.sql_modules)\n"

    text = definition

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove USE [db] lines
    text = RE_USE_DB.sub("", text)

    # Remove database qualifiers
    text = RE_DB_QUALIFIER.sub("", text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]

    # Trim leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines) + "\n"


def target_path(obj: SqlObject) -> Path:
    """
    Determine the canonical file path for a given SQL object.

    Views  → src/db/views/{schema}/{schema}.{name}.sql
    Others → src/db/dml/{type_folder}/{schema}.{name}.sql
    """
    filename = f"{obj.schema_name}.{obj.object_name}.sql"

    if obj.object_type == "V":
        return VIEWS_ROOT / obj.schema_name / filename

    type_info = OBJECT_TYPE_MAP.get(obj.object_type)
    if not type_info:
        # Fallback
        return DML_ROOT / "other" / filename
    subfolder, _ = type_info
    return DML_ROOT / subfolder / filename


# ---------------------------------------------------------------------------
# Repo scanning
# ---------------------------------------------------------------------------

def scan_repo_objects(schemas: Set[str]) -> Dict[str, Path]:
    """
    Walk the repo's DML and views directories and return a map of
    'schema.object_name' → file path for every .sql file found.

    Handles two naming patterns:
      - Schema-prefixed: dbo.usp_claim_next_job.sql → 'dbo.usp_claim_next_job'
      - Legacy (no prefix): vw_event.sql in sem/ → inferred from CREATE statement
    """
    found: Dict[str, Path] = {}

    for root_dir in (DML_ROOT, VIEWS_ROOT):
        if not root_dir.exists():
            continue
        for sql_file in root_dir.rglob("*.sql"):
            stem = sql_file.stem  # e.g. "dbo.usp_claim_next_job" or "vw_event"
            if "." in stem:
                # Schema-prefixed filename
                found[stem.lower()] = sql_file
            else:
                # Legacy filename — infer schema from CREATE statement
                schema = _infer_schema_from_file(sql_file)
                if schema:
                    key = f"{schema}.{stem}".lower()
                    found[key] = sql_file

    return found


def _infer_schema_from_file(sql_file: Path) -> Optional[str]:
    """
    Read the first lines of a .sql file to find the schema from a CREATE statement.
    Looks for patterns like: CREATE OR ALTER VIEW dbo.view_name
    """
    try:
        text = sql_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    match = re.search(
        r"CREATE\s+(?:OR\s+ALTER\s+)?(?:VIEW|PROCEDURE|FUNCTION|TRIGGER)\s+"
        r"(?:\[?(\w+)\]?\.)?\[?(\w+)\]?",
        text,
        re.IGNORECASE,
    )
    if match:
        return (match.group(1) or "dbo").lower()
    return None


# ---------------------------------------------------------------------------
# Write / reconcile
# ---------------------------------------------------------------------------

def write_object(obj: SqlObject, dry_run: bool, verbose: bool) -> bool:
    """Write a single object definition to its canonical file. Returns True if written."""
    path = target_path(obj)
    content = normalize_definition(obj.definition)

    if dry_run:
        print(f"  [DRY-RUN] Would write: {path.relative_to(REPO_ROOT)}")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")

    if verbose:
        print(f"  [WROTE] {path.relative_to(REPO_ROOT)}")
    return True


def reconcile(
    sql_objects: List[SqlObject],
    repo_files: Dict[str, Path],
    verbose: bool,
) -> ReconciliationResult:
    """Compare SQL Server objects against repo files."""
    result = ReconciliationResult()

    sql_keys: Set[str] = set()
    for obj in sql_objects:
        key = f"{obj.schema_name}.{obj.object_name}".lower()
        sql_keys.add(key)

        if key in repo_files:
            result.matched.append(key)
        else:
            result.in_sql_not_repo.append(key)

    for key in repo_files:
        if key not in sql_keys:
            result.in_repo_not_sql.append(key)

    return result


def print_reconciliation_report(result: ReconciliationResult) -> int:
    """Print a human-readable reconciliation report. Returns exit code."""
    print("\n" + "=" * 70)
    print("SQL Server ↔ Repo Reconciliation Report")
    print("=" * 70)

    print(f"\n  Matched objects:          {len(result.matched)}")
    print(f"  In SQL, missing in repo:  {len(result.in_sql_not_repo)}")
    print(f"  In repo, missing in SQL:  {len(result.in_repo_not_sql)}")

    if result.in_sql_not_repo:
        print("\n  Objects in SQL Server but NOT in repo (baseline gaps):")
        for name in sorted(result.in_sql_not_repo):
            print(f"    + {name}")

    if result.in_repo_not_sql:
        print("\n  Files in repo but NOT in SQL Server (stale or pending migration):")
        for name in sorted(result.in_repo_not_sql):
            print(f"    - {name}")

    if not result.in_sql_not_repo and not result.in_repo_not_sql:
        print("\n  ✅ SQL Server and repo are fully synchronized.")
        return 0
    else:
        print("\n  ⚠️  Mismatches detected. Review the items above.")
        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract SQL object definitions from Docker SQL Server into repo canonical files."
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract definitions from SQL Server and write to repo",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Print reconciliation report (no file writes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--connection-string",
        type=str,
        default=None,
        help="Database connection string (overrides environment)",
    )
    parser.add_argument(
        "--schemas",
        type=str,
        default=None,
        help="Comma-separated list of schemas to include (default: dbo,sem,llm,ingest,vector)",
    )
    args = parser.parse_args()

    if not args.extract and not args.reconcile:
        parser.print_help()
        print("\nError: Specify --extract and/or --reconcile.")
        return 3

    # Resolve schemas
    schemas = DEFAULT_SCHEMAS
    if args.schemas:
        schemas = {s.strip() for s in args.schemas.split(",")}

    # Connect
    conn_str = args.connection_string or get_connection_string()
    if args.verbose:
        masked = conn_str
        if "PWD=" in masked:
            start = masked.find("PWD=") + 4
            end = masked.find(";", start) if ";" in masked[start:] else len(masked)
            masked = masked[:start] + "***" + masked[end:]
        print(f"Connection: {masked}")

    try:
        conn = pyodbc.connect(conn_str)
        print("Connected to SQL Server.")
    except pyodbc.Error as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return 2

    try:
        # Fetch objects from SQL Server
        sql_objects = fetch_objects(conn, schemas)
        print(f"Found {len(sql_objects)} objects in SQL Server.")

        if args.extract:
            written = 0
            for obj in sql_objects:
                if write_object(obj, dry_run=args.dry_run, verbose=args.verbose):
                    written += 1
            action = "Would write" if args.dry_run else "Wrote"
            print(f"\n{action} {written} object definition(s).")

        if args.reconcile:
            repo_files = scan_repo_objects(schemas)
            result = reconcile(sql_objects, repo_files, verbose=args.verbose)
            return print_reconciliation_report(result)

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
