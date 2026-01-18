"""
Database introspection utilities for seed loading.

Provides functions to query table metadata from SQL Server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pyodbc


@dataclass
class ColumnInfo:
    """Information about a database column."""

    name: str
    data_type: str
    max_length: int | None
    is_nullable: bool
    is_identity: bool
    column_ordinal: int


@dataclass
class TableSchema:
    """Schema information for a database table."""

    schema_name: str
    table_name: str
    columns: dict[str, ColumnInfo] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Return schema.table name."""
        return f"{self.schema_name}.{self.table_name}"

    @property
    def identity_column(self) -> str | None:
        """Return the name of the identity column, if any."""
        for col in self.columns.values():
            if col.is_identity:
                return col.name
        return None

    @property
    def guid_column(self) -> str | None:
        """Return the name of the GUID column (second ordinal by convention)."""
        # Find column at ordinal position 2 that is uniqueidentifier
        for col in self.columns.values():
            if col.column_ordinal == 2 and col.data_type == "uniqueidentifier":
                return col.name
        # Fallback: look for any column ending in 'Guid'
        for col in self.columns.values():
            if col.name.endswith("Guid") and col.data_type == "uniqueidentifier":
                return col.name
        return None

    def get_insertable_columns(
        self, include_identity: bool = False
    ) -> list[str]:
        """Get list of column names suitable for INSERT."""
        result = []
        for col in sorted(self.columns.values(), key=lambda c: c.column_ordinal):
            if col.is_identity and not include_identity:
                continue
            result.append(col.name)
        return result


def get_table_columns(
    conn: pyodbc.Connection, schema_name: str, table_name: str
) -> TableSchema:
    """
    Query INFORMATION_SCHEMA to get column metadata for a table.

    Args:
        conn: Active database connection.
        schema_name: Schema name (e.g., 'dbo').
        table_name: Table name (e.g., 'DimFranchise').

    Returns:
        TableSchema object with column information.
    """
    query = """
    SELECT
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.CHARACTER_MAXIMUM_LENGTH,
        CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS IsNullable,
        COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'IsIdentity') AS IsIdentity,
        c.ORDINAL_POSITION
    FROM INFORMATION_SCHEMA.COLUMNS c
    WHERE c.TABLE_SCHEMA = ?
      AND c.TABLE_NAME = ?
    ORDER BY c.ORDINAL_POSITION
    """

    cursor = conn.cursor()
    cursor.execute(query, (schema_name, table_name))

    table_schema = TableSchema(schema_name=schema_name, table_name=table_name)

    for row in cursor.fetchall():
        col_info = ColumnInfo(
            name=row.COLUMN_NAME,
            data_type=row.DATA_TYPE,
            max_length=row.CHARACTER_MAXIMUM_LENGTH,
            is_nullable=bool(row.IsNullable),
            is_identity=bool(row.IsIdentity),
            column_ordinal=row.ORDINAL_POSITION,
        )
        table_schema.columns[col_info.name] = col_info

    cursor.close()
    return table_schema


def validate_seed_columns(
    seed_columns: set[str],
    table_schema: TableSchema,
    ignore_unknown: bool = False,
) -> list[str]:
    """
    Validate that seed columns exist in the target table.

    Args:
        seed_columns: Set of column names from seed data.
        table_schema: Schema information for target table.
        ignore_unknown: If True, skip unknown columns instead of raising.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []
    table_columns = set(table_schema.columns.keys())

    unknown_columns = seed_columns - table_columns
    if unknown_columns and not ignore_unknown:
        errors.append(
            f"Unknown columns in seed data for {table_schema.full_name}: "
            f"{', '.join(sorted(unknown_columns))}"
        )

    return errors


def check_table_exists(
    conn: pyodbc.Connection, schema_name: str, table_name: str
) -> bool:
    """
    Check if a table exists in the database.

    Args:
        conn: Active database connection.
        schema_name: Schema name.
        table_name: Table name.

    Returns:
        True if table exists, False otherwise.
    """
    query = """
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    """
    cursor = conn.cursor()
    cursor.execute(query, (schema_name, table_name))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0
