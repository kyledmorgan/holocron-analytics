"""
Database loading utilities for seed data.

Provides the main SeedLoader class for truncating and inserting seed data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pyodbc

from .seed_io import (
    SeedFile,
    compute_row_hash,
    generate_deterministic_guid,
    serialize_json_columns,
)
from .db_introspection import (
    TableSchema,
    get_table_columns,
    validate_seed_columns,
    check_table_exists,
)

logger = logging.getLogger(__name__)


# Static load order for FK dependency resolution
# Tables earlier in the list have no dependencies on later tables
LOAD_ORDER = [
    # Level 0: No FK dependencies
    "DimFranchise",
    "DimIssueType",
    # Level 1: Depend on DimFranchise only
    "DimContinuityFrame",
    "DimEra",
    "DimWork",
    "DimEventType",
    "DimEntity",
    "DimTechAsset",
    # Level 2: Depend on Level 0-1
    "DimScene",
    "DimSpecies",
    "DimLocation",
    "DimDroidModel",
    # Level 3: Depend on Level 0-2
    "DimCharacter",
    "DimTechInstance",
    # Level 4: Depend on Level 0-3
    "DimDroidInstance",
    # Level 5: Facts (depend on multiple dims)
    "FactEvent",
    "ContinuityIssue",
    "FactClaim",
    # Level 6: Bridges (depend on facts)
    "BridgeEventParticipant",
    "BridgeEventAsset",
    "BridgeContinuityIssueClaim",
]


class SeedLoaderError(Exception):
    """Raised when seed loading fails."""

    pass


class SeedLoader:
    """
    Loads seed data into SQL Server tables.

    Handles truncation, validation, and insertion of seed rows.
    """

    def __init__(
        self,
        conn: pyodbc.Connection,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the seed loader.

        Args:
            conn: Active pyodbc connection to SQL Server.
            dry_run: If True, validate only without writing.
            verbose: If True, enable verbose logging.
        """
        self.conn = conn
        self.dry_run = dry_run
        self.verbose = verbose
        self._table_schemas: dict[str, TableSchema] = {}

    def get_table_schema(self, schema_name: str, table_name: str) -> TableSchema:
        """Get cached table schema or fetch from database."""
        key = f"{schema_name}.{table_name}"
        if key not in self._table_schemas:
            self._table_schemas[key] = get_table_columns(
                self.conn, schema_name, table_name
            )
        return self._table_schemas[key]

    def validate_seed_file(self, seed_file: SeedFile) -> list[str]:
        """
        Validate a seed file against the target table schema.

        Args:
            seed_file: Parsed seed file.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Check table exists
        if not check_table_exists(
            self.conn, seed_file.target.schema, seed_file.target.table
        ):
            errors.append(
                f"Table not found: {seed_file.full_table_name}"
            )
            return errors

        # Get table schema
        table_schema = self.get_table_schema(
            seed_file.target.schema, seed_file.target.table
        )

        # Collect all unique columns from rows
        all_row_columns: set[str] = set()
        for row in seed_file.rows:
            all_row_columns.update(row.keys())

        # Validate columns
        col_errors = validate_seed_columns(
            all_row_columns,
            table_schema,
            ignore_unknown=seed_file.options.ignore_unknown_fields,
        )
        errors.extend(col_errors)

        # Validate GUID column presence
        guid_col = table_schema.guid_column
        if guid_col:
            for i, row in enumerate(seed_file.rows):
                if guid_col not in row:
                    # Check if we can generate it
                    if seed_file.target.natural_key:
                        # We'll generate it - that's OK
                        pass
                    else:
                        errors.append(
                            f"Row {i+1} missing GUID column '{guid_col}' and no "
                            f"naturalKey defined for auto-generation"
                        )

        # Validate unique GUIDs in seed
        if guid_col:
            guids = [row.get(guid_col) for row in seed_file.rows if guid_col in row]
            if len(guids) != len(set(guids)):
                errors.append(f"Duplicate GUIDs found in seed file for {guid_col}")

        return errors

    def truncate_table(self, schema_name: str, table_name: str) -> None:
        """
        Truncate a table, handling FK constraints.

        Args:
            schema_name: Schema name.
            table_name: Table name.
        """
        full_name = f"{schema_name}.{table_name}"
        cursor = self.conn.cursor()

        try:
            # Try TRUNCATE first
            logger.debug(f"Attempting TRUNCATE on {full_name}")
            cursor.execute(f"TRUNCATE TABLE {full_name}")
            logger.info(f"TRUNCATED {full_name}")
        except pyodbc.Error as e:
            # TRUNCATE failed (likely FK constraint) - use DELETE with constraint disable
            logger.debug(f"TRUNCATE failed on {full_name}, trying DELETE: {e}")

            try:
                # Disable constraints
                cursor.execute(f"ALTER TABLE {full_name} NOCHECK CONSTRAINT ALL")

                # Delete all rows
                cursor.execute(f"DELETE FROM {full_name}")

                # Re-enable constraints
                cursor.execute(
                    f"ALTER TABLE {full_name} WITH CHECK CHECK CONSTRAINT ALL"
                )

                logger.info(f"DELETED all rows from {full_name} (constraints toggled)")
            except pyodbc.Error as delete_error:
                logger.error(f"Failed to clear {full_name}: {delete_error}")
                raise SeedLoaderError(
                    f"Could not truncate or delete from {full_name}: {delete_error}"
                )

        cursor.close()

    def insert_rows(
        self, seed_file: SeedFile, table_schema: TableSchema
    ) -> int:
        """
        Insert seed rows into the target table.

        Args:
            seed_file: Parsed seed file with rows.
            table_schema: Schema information for target table.

        Returns:
            Number of rows inserted.
        """
        if not seed_file.rows:
            return 0

        cursor = self.conn.cursor()
        rows_inserted = 0

        # Determine columns to insert
        include_identity = seed_file.options.allow_identity_insert
        guid_col = table_schema.guid_column
        identity_col = table_schema.identity_column

        # Columns that will be auto-filled by loader
        auto_columns = {"RowHash", "ValidFromUtc", "CreatedUtc", "UpdatedUtc"}

        # Columns from seed defaults
        default_columns = set(seed_file.options.defaults.keys())

        try:
            if include_identity and identity_col:
                cursor.execute(
                    f"SET IDENTITY_INSERT {table_schema.full_name} ON"
                )

            for row in seed_file.rows:
                prepared_row = self._prepare_row(
                    row,
                    seed_file,
                    table_schema,
                    guid_col,
                    identity_col,
                    auto_columns,
                    default_columns,
                )

                # Filter to only valid table columns
                valid_columns = [
                    col for col in prepared_row.keys()
                    if col in table_schema.columns
                    and (include_identity or col != identity_col)
                ]

                # Build INSERT statement
                columns_str = ", ".join(valid_columns)
                placeholders = ", ".join("?" for _ in valid_columns)
                values = [prepared_row[col] for col in valid_columns]

                sql = f"INSERT INTO {table_schema.full_name} ({columns_str}) VALUES ({placeholders})"

                if self.verbose:
                    logger.debug(f"Executing: {sql}")
                    logger.debug(f"Values: {values}")

                cursor.execute(sql, values)
                rows_inserted += 1

            if include_identity and identity_col:
                cursor.execute(
                    f"SET IDENTITY_INSERT {table_schema.full_name} OFF"
                )

        except pyodbc.Error as e:
            logger.error(f"Insert failed: {e}")
            raise SeedLoaderError(f"Failed to insert into {table_schema.full_name}: {e}")
        finally:
            cursor.close()

        return rows_inserted

    def _prepare_row(
        self,
        row: dict[str, Any],
        seed_file: SeedFile,
        table_schema: TableSchema,
        guid_col: str | None,
        identity_col: str | None,
        auto_columns: set[str],
        default_columns: set[str],
    ) -> dict[str, Any]:
        """Prepare a row for insertion with defaults and computed values."""
        prepared = dict(row)

        # Serialize JSON columns
        prepared = serialize_json_columns(prepared)

        # Apply defaults for missing columns
        for col, default_val in seed_file.options.defaults.items():
            if col not in prepared and col in table_schema.columns:
                prepared[col] = default_val

        # Generate GUID if missing and natural key is defined
        if guid_col and guid_col not in prepared:
            if seed_file.target.natural_key:
                key_values = [
                    str(prepared.get(k, "")) for k in seed_file.target.natural_key
                ]
                namespace = f"{seed_file.target.schema}.{seed_file.target.table}"
                prepared[guid_col] = generate_deterministic_guid(namespace, key_values)
            else:
                raise SeedLoaderError(
                    f"Missing GUID column '{guid_col}' and no naturalKey defined"
                )

        # Set timestamp defaults
        now_utc = datetime.now(timezone.utc)
        if "ValidFromUtc" in table_schema.columns and "ValidFromUtc" not in prepared:
            prepared["ValidFromUtc"] = now_utc
        if "CreatedUtc" in table_schema.columns and "CreatedUtc" not in prepared:
            prepared["CreatedUtc"] = now_utc

        # Compute RowHash
        if "RowHash" in table_schema.columns:
            # Exclude columns that are:
            # - identity PK (auto-generated)
            # - UpdatedUtc (changes on every update)
            # - RowHash itself
            # - ValidFromUtc, CreatedUtc (set by loader at load time, not business data)
            # This ensures the hash represents the actual seed content for change detection
            exclude = {identity_col, "UpdatedUtc", "RowHash", "ValidFromUtc", "CreatedUtc"}
            exclude.discard(None)
            prepared["RowHash"] = compute_row_hash(prepared, exclude)

        return prepared

    def load_seed_file(self, seed_file: SeedFile) -> int:
        """
        Load a single seed file into its target table.

        Args:
            seed_file: Parsed seed file.

        Returns:
            Number of rows inserted.
        """
        logger.info(f"Loading seed file: {seed_file.file_path.name}")

        # Validate
        errors = self.validate_seed_file(seed_file)
        if errors:
            for err in errors:
                logger.error(f"Validation error: {err}")
            raise SeedLoaderError(
                f"Validation failed for {seed_file.file_path}: {errors}"
            )

        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would load {len(seed_file.rows)} rows into "
                f"{seed_file.full_table_name}"
            )
            return 0

        # Get table schema
        table_schema = self.get_table_schema(
            seed_file.target.schema, seed_file.target.table
        )

        # Truncate
        self.truncate_table(seed_file.target.schema, seed_file.target.table)

        # Insert
        rows_inserted = self.insert_rows(seed_file, table_schema)

        logger.info(
            f"Loaded {rows_inserted} rows into {seed_file.full_table_name}"
        )

        return rows_inserted

    def load_all(
        self,
        seed_files: list[SeedFile],
        table_filter: set[str] | None = None,
    ) -> dict[str, int]:
        """
        Load all seed files in dependency order.

        Args:
            seed_files: List of parsed seed files.
            table_filter: If provided, only load these tables.

        Returns:
            Dictionary mapping table names to rows inserted.
        """
        # Create lookup by table name
        seed_by_table = {sf.target.table: sf for sf in seed_files}

        # Determine load order
        tables_to_load = []
        for table in LOAD_ORDER:
            if table in seed_by_table:
                if table_filter is None or table in table_filter:
                    tables_to_load.append(table)

        # Check for tables not in load order
        for sf in seed_files:
            if sf.target.table not in LOAD_ORDER:
                logger.warning(
                    f"Table {sf.target.table} not in LOAD_ORDER, appending to end"
                )
                if table_filter is None or sf.target.table in table_filter:
                    tables_to_load.append(sf.target.table)

        if self.dry_run:
            logger.info("[DRY RUN] Validating all seed files...")

        # If truncating, do it in reverse order first
        if not self.dry_run:
            logger.info("Truncating tables in reverse dependency order...")
            for table in reversed(tables_to_load):
                if table in seed_by_table:
                    sf = seed_by_table[table]
                    self.truncate_table(sf.target.schema, sf.target.table)

        # Now insert in forward order
        results: dict[str, int] = {}
        for table in tables_to_load:
            sf = seed_by_table[table]

            if self.dry_run:
                errors = self.validate_seed_file(sf)
                if errors:
                    for err in errors:
                        logger.error(f"Validation error: {err}")
                    results[table] = -1
                else:
                    logger.info(
                        f"[DRY RUN] {table}: {len(sf.rows)} rows would be inserted"
                    )
                    results[table] = len(sf.rows)
            else:
                table_schema = self.get_table_schema(sf.target.schema, sf.target.table)
                rows = self.insert_rows(sf, table_schema)
                results[table] = rows

        return results
