"""
Seed file I/O and validation utilities.

Provides functions for discovering, reading, and validating seed JSON files.
"""

from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SeedTarget:
    """Target table configuration from seed file."""

    schema: str
    table: str
    natural_key: list[str] = field(default_factory=list)
    load_behavior: str = "truncate-insert"


@dataclass
class SeedOptions:
    """Loader options from seed file."""

    allow_identity_insert: bool = False
    ignore_unknown_fields: bool = False
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass
class SeedFile:
    """Parsed seed file with metadata and rows."""

    file_path: Path
    seed_version: str
    generated_utc: str
    target: SeedTarget
    options: SeedOptions
    rows: list[dict[str, Any]]

    @property
    def full_table_name(self) -> str:
        """Return schema.table name."""
        return f"{self.target.schema}.{self.target.table}"


class SeedValidationError(Exception):
    """
    Raised when seed file validation fails.

    This exception indicates that a seed file has structural issues
    such as missing required fields, invalid JSON, or schema mismatches.
    """


def load_seed_file(file_path: Path) -> SeedFile:
    """
    Load and validate a seed JSON file.

    Args:
        file_path: Path to the JSON seed file.

    Returns:
        Parsed SeedFile object.

    Raises:
        SeedValidationError: If the file is invalid.
    """
    if not file_path.exists():
        raise SeedValidationError(f"Seed file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SeedValidationError(f"Invalid JSON in {file_path}: {e}")

    # Validate required fields
    _validate_required_fields(data, file_path)

    # Parse target
    target_data = data["target"]
    target = SeedTarget(
        schema=target_data["schema"],
        table=target_data["table"],
        natural_key=target_data.get("naturalKey", []),
        load_behavior=target_data.get("loadBehavior", "truncate-insert"),
    )

    # Parse options
    options_data = data.get("options", {})
    options = SeedOptions(
        allow_identity_insert=options_data.get("allowIdentityInsert", False),
        ignore_unknown_fields=options_data.get("ignoreUnknownFields", False),
        defaults=options_data.get("defaults", {}),
    )

    # Validate rows
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        raise SeedValidationError(f"'rows' must be an array in {file_path}")

    return SeedFile(
        file_path=file_path,
        seed_version=data["seedVersion"],
        generated_utc=data["generatedUtc"],
        target=target,
        options=options,
        rows=rows,
    )


def _validate_required_fields(data: dict[str, Any], file_path: Path) -> None:
    """Validate that required fields are present in seed data."""
    required_top_level = ["seedVersion", "generatedUtc", "target", "rows"]
    for field in required_top_level:
        if field not in data:
            raise SeedValidationError(f"Missing required field '{field}' in {file_path}")

    target = data.get("target", {})
    required_target = ["schema", "table", "loadBehavior"]
    for field in required_target:
        if field not in target:
            raise SeedValidationError(
                f"Missing required target field '{field}' in {file_path}"
            )


def discover_seed_files(seeds_dir: Path) -> list[Path]:
    """
    Discover all seed JSON files in the data directory.

    Args:
        seeds_dir: Path to the seeds/data directory.

    Returns:
        List of paths to seed files, sorted by filename.
    """
    if not seeds_dir.exists():
        return []

    seed_files = sorted(seeds_dir.glob("*.json"))
    return seed_files


def generate_deterministic_guid(
    namespace: str, natural_key_values: list[str]
) -> str:
    """
    Generate a deterministic UUID v5 from namespace and natural key values.

    Args:
        namespace: Namespace string (typically schema.table).
        natural_key_values: List of natural key column values.

    Returns:
        UUID string in standard format.
    """
    # Use DNS namespace as base, then combine with our namespace string
    base_ns = uuid.uuid5(uuid.NAMESPACE_DNS, namespace)
    # Use JSON serialization for robust key string (handles special characters)
    key_string = json.dumps(
        [str(v) for v in natural_key_values], ensure_ascii=False, sort_keys=True
    )
    generated_uuid = uuid.uuid5(base_ns, key_string)
    return str(generated_uuid)


def compute_row_hash(
    row_data: dict[str, Any], exclude_columns: set[str] | None = None
) -> bytes:
    """
    Compute a SHA-256 hash of row data for change detection.

    Args:
        row_data: Dictionary of column values.
        exclude_columns: Set of column names to exclude from hash.

    Returns:
        32-byte SHA-256 hash.
    """
    if exclude_columns is None:
        exclude_columns = set()

    # Sort keys for deterministic ordering
    hash_parts = []
    for key in sorted(row_data.keys()):
        if key in exclude_columns:
            continue
        value = row_data[key]
        # Serialize value to string
        if value is None:
            str_val = "NULL"
        elif isinstance(value, dict):
            str_val = json.dumps(value, sort_keys=True, ensure_ascii=False)
        elif isinstance(value, bool):
            str_val = "1" if value else "0"
        else:
            str_val = str(value)
        hash_parts.append(f"{key}={str_val}")

    hash_input = "|".join(hash_parts)
    return hashlib.sha256(hash_input.encode("utf-8")).digest()


def serialize_json_columns(row: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize any dict values to JSON strings for database insertion.

    Args:
        row: Row data dictionary.

    Returns:
        New dictionary with dict values serialized to JSON strings.
    """
    result = {}
    for key, value in row.items():
        if isinstance(value, dict):
            result[key] = json.dumps(value, ensure_ascii=False)
        else:
            result[key] = value
    return result
