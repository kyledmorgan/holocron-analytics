#!/usr/bin/env python3
"""
Schema Alignment Verification Script

Validates that the runtime database schema matches expected conventions
and identifies drift from documented standards.

Usage:
    python scripts/verify_schema_alignment.py [--verbose] [--connection-string "..."]
    
Exit codes:
    0 = All checks passed
    1 = Drift detected (non-compliant objects found)
    2 = Connection error
    3 = Configuration error
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc required. Install with: pip install pyodbc")
    sys.exit(3)


@dataclass
class ValidationIssue:
    """Represents a schema validation issue."""
    category: str
    severity: str  # 'error', 'warning'
    table_or_view: str
    column_or_object: str
    message: str
    recommendation: str


class SchemaValidator:
    """Validates database schema against documented conventions."""
    
    def __init__(self, connection: pyodbc.Connection, verbose: bool = False):
        self.conn = connection
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def log(self, msg: str) -> None:
        """Print verbose log messages."""
        if self.verbose:
            print(f"  [INFO] {msg}")
    
    def check_id_columns(self) -> None:
        """Check for deprecated ...Id column naming (should be ...Key, ...Guid, ...ExtKey)."""
        self.log("Checking for deprecated ...Id column names...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                s.name AS SchemaName,
                t.name AS TableName,
                c.name AS ColumnName
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE c.name LIKE '%Id'
              AND c.name NOT IN ('RowId')  -- Exclude known exceptions
              AND s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
              AND c.name NOT LIKE '%Guid%'
              AND c.name NOT LIKE '%Key%'
            ORDER BY s.name, t.name, c.name
        """)
        
        for row in cursor.fetchall():
            schema, table, column = row
            # Check if this is a legitimate case or needs renaming
            if column.endswith('Id') and not column.endswith('Guid'):
                self.issues.append(ValidationIssue(
                    category='naming_convention',
                    severity='warning',
                    table_or_view=f'{schema}.{table}',
                    column_or_object=column,
                    message=f"Column '{column}' uses deprecated ...Id pattern",
                    recommendation=f"Rename to ...Key, ...Guid, or ...ExtKey per naming conventions"
                ))
    
    def check_guid_defaults(self) -> None:
        """Check that public GUID columns use NEWID() not NEWSEQUENTIALID()."""
        self.log("Checking GUID default constraints...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(t.schema_id) AS SchemaName,
                t.name AS TableName,
                c.name AS ColumnName,
                dc.definition AS DefaultDefinition
            FROM sys.default_constraints dc
            INNER JOIN sys.columns c 
                ON dc.parent_object_id = c.object_id 
                AND dc.parent_column_id = c.column_id
            INNER JOIN sys.tables t ON dc.parent_object_id = t.object_id
            WHERE c.name LIKE '%Guid'
              AND dc.definition LIKE '%NEWSEQUENTIALID%'
        """)
        
        for row in cursor.fetchall():
            schema, table, column, definition = row
            self.issues.append(ValidationIssue(
                category='security',
                severity='error',
                table_or_view=f'{schema}.{table}',
                column_or_object=column,
                message=f"GUID column '{column}' uses NEWSEQUENTIALID() which reveals row creation order",
                recommendation="Change default to NEWID() for security"
            ))
    
    def check_datetime_types(self) -> None:
        """Check that timestamp columns use DATETIME2(3) not DATETIME."""
        self.log("Checking datetime column types...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(t.schema_id) AS SchemaName,
                t.name AS TableName,
                c.name AS ColumnName,
                ty.name AS TypeName
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            WHERE ty.name = 'datetime'
              AND SCHEMA_NAME(t.schema_id) IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
        """)
        
        for row in cursor.fetchall():
            schema, table, column, type_name = row
            self.issues.append(ValidationIssue(
                category='data_type',
                severity='warning',
                table_or_view=f'{schema}.{table}',
                column_or_object=column,
                message=f"Column '{column}' uses deprecated DATETIME type",
                recommendation="Change to DATETIME2(3) for consistency and precision"
            ))
    
    def check_timestamp_naming(self) -> None:
        """Check that timestamp columns end with Utc suffix."""
        self.log("Checking timestamp column naming...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(t.schema_id) AS SchemaName,
                t.name AS TableName,
                c.name AS ColumnName
            FROM sys.columns c
            INNER JOIN sys.tables t ON c.object_id = t.object_id
            INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            WHERE ty.name IN ('datetime', 'datetime2')
              AND SCHEMA_NAME(t.schema_id) IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
              AND c.name NOT LIKE '%Utc'
              AND c.name NOT LIKE '%Date'  -- Allow date-only columns
              AND c.name NOT IN ('ValidFrom', 'ValidTo')  -- Legacy patterns
        """)
        
        for row in cursor.fetchall():
            schema, table, column = row
            self.issues.append(ValidationIssue(
                category='naming_convention',
                severity='warning',
                table_or_view=f'{schema}.{table}',
                column_or_object=column,
                message=f"Timestamp column '{column}' missing Utc suffix",
                recommendation="Rename to end with Utc (e.g., CreatedUtc, UpdatedUtc)"
            ))
    
    def check_sem_views_location(self) -> None:
        """Check that semantic views are in sem schema, not dbo.sem_*."""
        self.log("Checking semantic view locations...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(v.schema_id) AS SchemaName,
                v.name AS ViewName
            FROM sys.views v
            WHERE SCHEMA_NAME(v.schema_id) = 'dbo'
              AND v.name LIKE 'sem_%'
        """)
        
        for row in cursor.fetchall():
            schema, view = row
            self.issues.append(ValidationIssue(
                category='schema_placement',
                severity='error',
                table_or_view=f'{schema}.{view}',
                column_or_object=view,
                message=f"View '{view}' is in dbo schema with sem_ prefix",
                recommendation="Move to sem schema with vw_ prefix (e.g., sem.vw_event)"
            ))
    
    def check_sem_views_prefix(self) -> None:
        """Check that views in sem schema use vw_ prefix."""
        self.log("Checking sem schema view prefixes...")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(v.schema_id) AS SchemaName,
                v.name AS ViewName
            FROM sys.views v
            WHERE SCHEMA_NAME(v.schema_id) = 'sem'
              AND v.name NOT LIKE 'vw_%'
              AND v.name NOT LIKE 'int_%'  -- Allow internal prefix
        """)
        
        for row in cursor.fetchall():
            schema, view = row
            self.issues.append(ValidationIssue(
                category='naming_convention',
                severity='warning',
                table_or_view=f'{schema}.{view}',
                column_or_object=view,
                message=f"View '{view}' in sem schema missing vw_ prefix",
                recommendation="Rename to use vw_ prefix (e.g., sem.vw_event)"
            ))
    
    def run_all_checks(self) -> None:
        """Run all validation checks."""
        print("Running schema alignment checks...")
        
        self.check_guid_defaults()
        self.check_id_columns()
        self.check_datetime_types()
        self.check_timestamp_naming()
        self.check_sem_views_location()
        self.check_sem_views_prefix()
        
        print(f"Completed {6} checks.")
    
    def report(self) -> int:
        """Print validation report and return exit code."""
        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']
        
        if not self.issues:
            print("\n✅ All schema alignment checks passed!")
            return 0
        
        print(f"\n{'='*70}")
        print(f"Schema Alignment Report")
        print(f"{'='*70}")
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        print(f"{'='*70}\n")
        
        if errors:
            print("ERRORS (must fix):\n")
            for issue in errors:
                print(f"  ❌ [{issue.category}] {issue.table_or_view}.{issue.column_or_object}")
                print(f"     {issue.message}")
                print(f"     → {issue.recommendation}\n")
        
        if warnings:
            print("WARNINGS (should fix):\n")
            for issue in warnings:
                print(f"  ⚠️  [{issue.category}] {issue.table_or_view}.{issue.column_or_object}")
                print(f"     {issue.message}")
                print(f"     → {issue.recommendation}\n")
        
        print(f"{'='*70}")
        
        if errors:
            print("❌ Schema alignment check FAILED - errors detected")
            return 1
        else:
            print("⚠️  Schema alignment check passed with warnings")
            return 0  # Warnings don't fail the check


def get_connection_string() -> str:
    """Get database connection string from environment or defaults."""
    # Check for full connection string
    conn_str = os.environ.get("VERIFY_SCHEMA_CONN_STR")
    if conn_str:
        return conn_str
    
    conn_str = os.environ.get("INGEST_SQLSERVER_CONN_STR")
    if conn_str:
        return conn_str
    
    # Build from discrete variables
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


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify database schema alignment with documented conventions"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--connection-string",
        type=str,
        help="Database connection string (overrides environment)"
    )
    args = parser.parse_args()
    
    # Get connection string
    conn_str = args.connection_string or get_connection_string()
    
    if args.verbose:
        # Mask password in output
        masked = conn_str
        if "PWD=" in masked:
            start = masked.find("PWD=") + 4
            end = masked.find(";", start) if ";" in masked[start:] else len(masked)
            masked = masked[:start] + "***" + masked[end:]
        print(f"Connection: {masked}")
    
    # Connect
    try:
        conn = pyodbc.connect(conn_str)
        print("Connected to database successfully.")
    except pyodbc.Error as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return 2
    
    try:
        validator = SchemaValidator(conn, verbose=args.verbose)
        validator.run_all_checks()
        return validator.report()
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
