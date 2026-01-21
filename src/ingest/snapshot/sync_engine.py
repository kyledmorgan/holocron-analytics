"""
Sync engine for bidirectional delta reconciliation.

Provides JSON → SQL import, SQL → JSON export, and full bidirectional sync
with conflict resolution and dry-run reporting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import ExchangeRecord
from .manifest import SnapshotManifest
from .file_snapshot import SnapshotReader, SnapshotWriter
from .sql_mirror import SqlMirror
from .canonical import compute_content_hash

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """Direction for sync operations."""
    BIDIRECTIONAL = "bidirectional"
    JSON_TO_SQL = "json_to_sql"
    SQL_TO_JSON = "sql_to_json"


class ConflictStrategy(str, Enum):
    """Strategy for resolving conflicts."""
    PREFER_NEWEST = "prefer_newest"
    PREFER_SQL = "prefer_sql"
    PREFER_JSON = "prefer_json"
    FAIL = "fail"


@dataclass
class ConflictInfo:
    """Information about a sync conflict."""
    natural_key: str
    source_system: str
    entity_type: str
    json_hash: str
    sql_hash: str
    json_observed_at: Optional[datetime]
    sql_observed_at: Optional[datetime]
    resolution: str  # 'json_wins', 'sql_wins', 'failed'


@dataclass
class SyncReport:
    """Report of a sync operation."""
    direction: str
    dry_run: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # JSON to SQL counts
    json_to_sql_inserted: int = 0
    json_to_sql_updated: int = 0
    json_to_sql_skipped: int = 0
    
    # SQL to JSON counts
    sql_to_json_inserted: int = 0
    sql_to_json_skipped: int = 0
    
    # Conflicts
    conflicts: List[ConflictInfo] = field(default_factory=list)
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    # Summary hashes
    json_record_count: int = 0
    sql_record_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "direction": self.direction,
            "dry_run": self.dry_run,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "json_to_sql": {
                "inserted": self.json_to_sql_inserted,
                "updated": self.json_to_sql_updated,
                "skipped": self.json_to_sql_skipped,
            },
            "sql_to_json": {
                "inserted": self.sql_to_json_inserted,
                "skipped": self.sql_to_json_skipped,
            },
            "conflicts": [
                {
                    "natural_key": c.natural_key,
                    "source_system": c.source_system,
                    "entity_type": c.entity_type,
                    "json_hash": c.json_hash[:16] + "...",
                    "sql_hash": c.sql_hash[:16] + "...",
                    "resolution": c.resolution,
                }
                for c in self.conflicts
            ],
            "errors": self.errors,
            "json_record_count": self.json_record_count,
            "sql_record_count": self.sql_record_count,
        }

    def summary(self) -> str:
        """Get a human-readable summary."""
        lines = [
            f"Sync Report ({self.direction})",
            f"  Dry run: {self.dry_run}",
            f"  Duration: {(self.completed_at - self.started_at).total_seconds():.1f}s" if self.completed_at else "",
            "",
            "  JSON → SQL:",
            f"    Inserted: {self.json_to_sql_inserted}",
            f"    Updated: {self.json_to_sql_updated}",
            f"    Skipped: {self.json_to_sql_skipped}",
            "",
            "  SQL → JSON:",
            f"    Inserted: {self.sql_to_json_inserted}",
            f"    Skipped: {self.sql_to_json_skipped}",
            "",
            f"  Conflicts: {len(self.conflicts)}",
            f"  Errors: {len(self.errors)}",
            "",
            f"  JSON records: {self.json_record_count}",
            f"  SQL records: {self.sql_record_count}",
        ]
        return "\n".join(lines)


class SyncEngine:
    """
    Bidirectional sync engine for JSON ⇄ SQL reconciliation.
    
    Supports:
    - JSON → SQL import (replay)
    - SQL → JSON export
    - Full bidirectional reconciliation
    - Dry-run mode
    - Conflict resolution strategies
    """

    def __init__(
        self,
        snapshot_dir: Path,
        sql_mirror: SqlMirror,
        manifest: Optional[SnapshotManifest] = None,
    ):
        """
        Initialize the sync engine.
        
        Args:
            snapshot_dir: Path to the snapshot dataset directory
            sql_mirror: SQL mirror instance
            manifest: Optional manifest (loaded from snapshot_dir if not provided)
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.sql_mirror = sql_mirror
        
        # Load manifest if not provided
        if manifest:
            self.manifest = manifest
        else:
            self.manifest = SnapshotManifest.load(self.snapshot_dir / "manifest.json")

    def import_json_to_sql(
        self,
        dry_run: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
    ) -> SyncReport:
        """
        Import records from JSON snapshot to SQL.
        
        Args:
            dry_run: If True, report what would be done without making changes
            conflict_strategy: How to resolve conflicts (default from manifest)
            
        Returns:
            SyncReport with results
        """
        strategy = conflict_strategy or ConflictStrategy(
            self.manifest.sync_policy.conflict_strategy
        )
        
        report = SyncReport(
            direction=SyncDirection.JSON_TO_SQL.value,
            dry_run=dry_run,
            started_at=datetime.now(timezone.utc),
        )
        
        try:
            # Load snapshot
            reader = SnapshotReader(self.snapshot_dir)
            
            # Get existing SQL hashes
            sql_hashes = self.sql_mirror.get_all_hashes(
                source_system=self.manifest.source_system,
                entity_type=self.manifest.entity_type,
            )
            
            # Track natural keys for conflict detection
            natural_key_to_hash: Dict[str, str] = {}
            
            for record in reader.read_all():
                report.json_record_count += 1
                
                # Check if hash already exists (skip)
                if record.content_sha256 in sql_hashes:
                    report.json_to_sql_skipped += 1
                    continue
                
                # Check for natural key conflict
                if record.natural_key:
                    existing = self.sql_mirror.get_records_by_natural_key(
                        record.source_system,
                        record.entity_type,
                        record.natural_key,
                    )
                    
                    if existing:
                        # Conflict detected
                        conflict = self._resolve_conflict(
                            json_record=record,
                            sql_record=existing[0],
                            strategy=strategy,
                            prefer_json=True,
                        )
                        report.conflicts.append(conflict)
                        
                        if conflict.resolution == "failed":
                            report.errors.append(
                                f"Conflict for {record.natural_key}: strategy is 'fail'"
                            )
                            continue
                        elif conflict.resolution == "sql_wins":
                            report.json_to_sql_skipped += 1
                            continue
                        # json_wins: proceed to update
                
                # Insert or update
                if not dry_run:
                    try:
                        success, action = self.sql_mirror.upsert(record)
                        if action == "inserted":
                            report.json_to_sql_inserted += 1
                        elif action == "updated":
                            report.json_to_sql_updated += 1
                        else:
                            report.json_to_sql_skipped += 1
                    except Exception as e:
                        report.errors.append(f"Insert error: {e}")
                else:
                    # Dry run: estimate action
                    if record.natural_key and existing:
                        report.json_to_sql_updated += 1
                    else:
                        report.json_to_sql_inserted += 1
            
            report.sql_record_count = self.sql_mirror.count(
                source_system=self.manifest.source_system,
                entity_type=self.manifest.entity_type,
            )
            
        except Exception as e:
            report.errors.append(f"Import error: {e}")
            logger.exception("Error during JSON to SQL import")
        
        report.completed_at = datetime.now(timezone.utc)
        return report

    def export_sql_to_json(
        self,
        dry_run: bool = False,
    ) -> SyncReport:
        """
        Export records from SQL to JSON snapshot.
        
        Args:
            dry_run: If True, report what would be done without making changes
            
        Returns:
            SyncReport with results
        """
        report = SyncReport(
            direction=SyncDirection.SQL_TO_JSON.value,
            dry_run=dry_run,
            started_at=datetime.now(timezone.utc),
        )
        
        try:
            # Get existing JSON hashes
            try:
                reader = SnapshotReader(self.snapshot_dir)
                json_hashes = reader.get_hashes()
                report.json_record_count = len(json_hashes)
            except FileNotFoundError:
                # Snapshot doesn't exist yet
                json_hashes = set()
            
            # Get SQL records
            sql_records = self.sql_mirror.get_records_by_scope(
                source_system=self.manifest.source_system,
                entity_type=self.manifest.entity_type,
            )
            report.sql_record_count = len(sql_records)
            
            # Find records to export
            records_to_export = []
            for record in sql_records:
                if record.content_sha256 not in json_hashes:
                    records_to_export.append(record)
                    report.sql_to_json_inserted += 1
                else:
                    report.sql_to_json_skipped += 1
            
            # Write to snapshot
            if not dry_run and records_to_export:
                writer = SnapshotWriter(
                    base_dir=self.snapshot_dir.parent,
                    manifest=self.manifest,
                )
                
                for record in records_to_export:
                    writer.write(record)
                
                writer.close()
                report.json_record_count += len(records_to_export)
            
        except Exception as e:
            report.errors.append(f"Export error: {e}")
            logger.exception("Error during SQL to JSON export")
        
        report.completed_at = datetime.now(timezone.utc)
        return report

    def sync(
        self,
        direction: Optional[SyncDirection] = None,
        dry_run: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
    ) -> SyncReport:
        """
        Perform sync in specified direction.
        
        Args:
            direction: Sync direction (default from manifest)
            dry_run: If True, report what would be done without making changes
            conflict_strategy: How to resolve conflicts
            
        Returns:
            Combined SyncReport
        """
        dir_value = direction or SyncDirection(
            self.manifest.sync_policy.direction_default
        )
        
        report = SyncReport(
            direction=dir_value.value,
            dry_run=dry_run,
            started_at=datetime.now(timezone.utc),
        )
        
        try:
            if dir_value == SyncDirection.JSON_TO_SQL:
                sub_report = self.import_json_to_sql(dry_run, conflict_strategy)
                self._merge_report(report, sub_report)
                
            elif dir_value == SyncDirection.SQL_TO_JSON:
                sub_report = self.export_sql_to_json(dry_run)
                self._merge_report(report, sub_report)
                
            elif dir_value == SyncDirection.BIDIRECTIONAL:
                # Import JSON to SQL first
                import_report = self.import_json_to_sql(dry_run, conflict_strategy)
                self._merge_report(report, import_report)
                
                # Then export SQL to JSON
                export_report = self.export_sql_to_json(dry_run)
                self._merge_report(report, export_report)
            
        except Exception as e:
            report.errors.append(f"Sync error: {e}")
            logger.exception("Error during sync")
        
        report.completed_at = datetime.now(timezone.utc)
        return report

    def _resolve_conflict(
        self,
        json_record: ExchangeRecord,
        sql_record: ExchangeRecord,
        strategy: ConflictStrategy,
        prefer_json: bool,
    ) -> ConflictInfo:
        """Resolve a conflict between JSON and SQL records."""
        conflict = ConflictInfo(
            natural_key=json_record.natural_key or "",
            source_system=json_record.source_system,
            entity_type=json_record.entity_type,
            json_hash=json_record.content_sha256,
            sql_hash=sql_record.content_sha256,
            json_observed_at=json_record.observed_at_utc,
            sql_observed_at=sql_record.observed_at_utc,
            resolution="",
        )
        
        if strategy == ConflictStrategy.FAIL:
            conflict.resolution = "failed"
        elif strategy == ConflictStrategy.PREFER_JSON:
            conflict.resolution = "json_wins"
        elif strategy == ConflictStrategy.PREFER_SQL:
            conflict.resolution = "sql_wins"
        elif strategy == ConflictStrategy.PREFER_NEWEST:
            # Compare timestamps
            json_time = json_record.observed_at_utc
            sql_time = sql_record.observed_at_utc
            
            if json_time and sql_time:
                if json_time >= sql_time:
                    conflict.resolution = "json_wins"
                else:
                    conflict.resolution = "sql_wins"
            elif json_time:
                conflict.resolution = "json_wins"
            elif sql_time:
                conflict.resolution = "sql_wins"
            else:
                # Both null: prefer the source being written
                conflict.resolution = "json_wins" if prefer_json else "sql_wins"
        
        return conflict

    def _merge_report(self, target: SyncReport, source: SyncReport) -> None:
        """Merge source report counts into target."""
        target.json_to_sql_inserted += source.json_to_sql_inserted
        target.json_to_sql_updated += source.json_to_sql_updated
        target.json_to_sql_skipped += source.json_to_sql_skipped
        target.sql_to_json_inserted += source.sql_to_json_inserted
        target.sql_to_json_skipped += source.sql_to_json_skipped
        target.conflicts.extend(source.conflicts)
        target.errors.extend(source.errors)
        target.json_record_count = max(target.json_record_count, source.json_record_count)
        target.sql_record_count = max(target.sql_record_count, source.sql_record_count)
