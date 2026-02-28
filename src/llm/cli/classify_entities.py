"""
Entity Classification CLI - Classify entities with resume/checkpoint support.

This CLI runner identifies entities in DimEntity that need classification
(EntityType assignment) and enqueues LLM jobs for them. It supports:

- Resumable processing: skip already-classified entities
- Multiple run modes: fresh, resume, rerun
- Dry-run for previewing work
- Filtering by entity keys or status
- Observability with attempt/skip/success/fail counters

Usage:
    # Start fresh classification run
    python -m llm.cli.classify_entities --mode fresh --batch-size 200

    # Resume from last checkpoint
    python -m llm.cli.classify_entities --mode resume --batch-size 200

    # Resume but only retry failures
    python -m llm.cli.classify_entities --mode resume --only failed

    # Force re-run specific entities
    python -m llm.cli.classify_entities --mode rerun --entity-keys 123 456 789

    # Fill missing fields only (don't overwrite existing)
    python -m llm.cli.classify_entities --mode resume --fill-missing-only

    # Dry run (preview what would be processed)
    python -m llm.cli.classify_entities --mode resume --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Run-mode constants
# ---------------------------------------------------------------------------

MODE_FRESH = "fresh"
MODE_RESUME = "resume"
MODE_RERUN = "rerun"

ONLY_FAILED = "failed"
ONLY_PENDING = "pending"


# ---------------------------------------------------------------------------
# Classification predicate helpers
# ---------------------------------------------------------------------------

def is_entity_classified(row: Dict[str, Any], *, require_tags: bool = False,
                         require_normalization: bool = False) -> bool:
    """
    Determine whether an entity row is already classified.

    The default predicate:
        EntityType IS NOT NULL AND IsLatest = 1 AND IsActive = 1

    Optional stricter checks:
        --require-normalization → DisplayNameNormalized and SortName non-null
        --require-tags → AliasCsv non-null
    """
    if not row.get("EntityType"):
        return False
    if not row.get("IsLatest", True):
        return False
    if not row.get("IsActive", True):
        return False
    if require_normalization:
        if not row.get("DisplayNameNormalized") or not row.get("SortName"):
            return False
    if require_tags:
        # --require-tags checks AliasCsv (the alias/tag field on DimEntity)
        if not row.get("AliasCsv"):
            return False
    return True


# ---------------------------------------------------------------------------
# Run statistics
# ---------------------------------------------------------------------------

@dataclass
class RunStats:
    """Tracks classification run statistics."""
    attempted: int = 0
    skipped: int = 0
    succeeded: int = 0
    failed: int = 0
    already_classified: int = 0
    dry_run_would_process: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempted": self.attempted,
            "skipped": self.skipped,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "already_classified": self.already_classified,
            "dry_run_would_process": self.dry_run_would_process,
            "error_count": len(self.errors),
            "errors": self.errors[:20],
        }


# ---------------------------------------------------------------------------
# Classification service
# ---------------------------------------------------------------------------

@dataclass
class ClassifyConfig:
    """Configuration for entity classification runs."""
    mode: str = MODE_RESUME
    batch_size: int = 200
    dry_run: bool = False
    only: Optional[str] = None
    entity_keys: Optional[List[int]] = None
    fill_missing_only: bool = False
    require_tags: bool = False
    require_normalization: bool = False
    revalidate_existing: bool = False
    priority: int = 100
    interrogation_key: str = "entity_extraction_generic_v1"


class EntityClassificationService:
    """
    Service that identifies unclassified entities and enqueues LLM jobs.

    Resume behaviour (DB-first, hybrid approach):
    1. Query DimEntity for rows missing classification fields.
    2. Cross-reference llm.job queue to avoid duplicate enqueue.
    3. Use idempotent enqueue (dedupe_key) so re-runs are safe.

    The *done* predicate is:
        EntityType IS NOT NULL AND IsLatest = 1 AND IsActive = 1
    Optionally extended by --require-tags / --require-normalization.
    """

    def __init__(self, queue=None, config: Optional[ClassifyConfig] = None):
        self.queue = queue
        self.config = config or ClassifyConfig()

    # -- lazy queue loader --------------------------------------------------

    def _get_queue(self):
        if self.queue is None:
            from ..storage.sql_job_queue import SqlJobQueue, QueueConfig
            self.queue = SqlJobQueue(QueueConfig.from_env())
        return self.queue

    # -- candidate discovery ------------------------------------------------

    def get_candidates(self) -> List[Dict[str, Any]]:
        """
        Return DimEntity rows that need classification.

        Depending on mode/flags the query changes:
        - fresh  → all active latest entities
        - resume → entities not yet classified (EntityType IS NULL) or
                    entities whose LLM job is in a retryable state
        - rerun  → specific entity keys provided via CLI
        """
        cfg = self.config

        # Mode: rerun with explicit entity keys
        if cfg.mode == MODE_RERUN and cfg.entity_keys:
            return self._query_entities_by_keys(cfg.entity_keys)

        # Build WHERE clause fragments
        where_parts = ["e.IsLatest = 1", "e.IsActive = 1"]
        params: List[Any] = []

        if cfg.mode == MODE_FRESH:
            # Fresh: pick everything; the idempotent enqueue handles dupes
            pass
        elif cfg.mode == MODE_RESUME:
            if cfg.only == ONLY_FAILED:
                # Only pick entities whose *last* LLM job failed
                return self._query_failed_job_entities(cfg.batch_size)
            elif cfg.revalidate_existing:
                # Revalidate: include already-classified entities
                pass
            else:
                # Default resume: entities that are NOT yet classified
                if cfg.fill_missing_only:
                    # Also pick entities with partial classification
                    where_parts.append(
                        "(e.EntityType IS NULL"
                        " OR e.DisplayNameNormalized IS NULL"
                        " OR e.SortName IS NULL)"
                    )
                else:
                    where_parts.append("e.EntityType IS NULL")
        elif cfg.mode == MODE_RERUN:
            # rerun without explicit keys → treat like fresh
            pass

        where_clause = " AND ".join(where_parts)
        query = (
            f"SELECT TOP (?) "
            f"  e.EntityKey, e.EntityGuid, e.DisplayName, e.EntityType, "
            f"  e.DisplayNameNormalized, e.SortName, e.AliasCsv, "
            f"  e.IsLatest, e.IsActive, e.ExternalKey, e.SourcePageId "
            f"FROM dbo.DimEntity e "
            f"WHERE {where_clause} "
            f"ORDER BY e.EntityKey ASC"
        )
        params.insert(0, cfg.batch_size)

        return self._execute_query(query, params)

    def _query_entities_by_keys(self, keys: List[int]) -> List[Dict[str, Any]]:
        """Fetch specific entities by EntityKey."""
        if not keys:
            return []
        placeholders = ",".join("?" for _ in keys)
        query = (
            f"SELECT "
            f"  e.EntityKey, e.EntityGuid, e.DisplayName, e.EntityType, "
            f"  e.DisplayNameNormalized, e.SortName, e.AliasCsv, "
            f"  e.IsLatest, e.IsActive, e.ExternalKey, e.SourcePageId "
            f"FROM dbo.DimEntity e "
            f"WHERE e.EntityKey IN ({placeholders}) "
            f"  AND e.IsLatest = 1 AND e.IsActive = 1 "
            f"ORDER BY e.EntityKey ASC"
        )
        return self._execute_query(query, keys)

    def _query_failed_job_entities(self, limit: int) -> List[Dict[str, Any]]:
        """
        Find entities whose most recent classification job FAILED or DEADLETTER.
        """
        query = (
            "SELECT TOP (?) "
            "  e.EntityKey, e.EntityGuid, e.DisplayName, e.EntityType, "
            "  e.DisplayNameNormalized, e.SortName, e.AliasCsv, "
            "  e.IsLatest, e.IsActive, e.ExternalKey, e.SourcePageId "
            "FROM dbo.DimEntity e "
            "INNER JOIN llm.job j "
            "  ON j.dedupe_key = CONCAT('entity_classify:', CAST(e.EntityKey AS NVARCHAR)) "
            "  AND j.interrogation_key = ? "
            "  AND j.status IN ('FAILED', 'DEADLETTER') "
            "WHERE e.IsLatest = 1 AND e.IsActive = 1 "
            "ORDER BY e.EntityKey ASC"
        )
        return self._execute_query(query, [limit, self.config.interrogation_key])

    def _execute_query(self, query: str, params: list) -> List[Dict[str, Any]]:
        """Execute a query and return list of row dicts."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as exc:
            logger.error(f"Query failed: {exc}")
            return []

    # -- main processing loop -----------------------------------------------

    def run(self) -> RunStats:
        """
        Execute the classification run.

        1. Discover candidates from DimEntity.
        2. For each candidate, check the *done* predicate.
        3. Enqueue an LLM job via idempotent enqueue (safe for re-runs).
        4. Track statistics.
        """
        stats = RunStats()
        cfg = self.config

        candidates = self.get_candidates()
        logger.info(f"Found {len(candidates)} candidate entities (mode={cfg.mode})")

        if not candidates:
            logger.info("No candidates to process")
            return stats

        for row in candidates:
            entity_key = row.get("EntityKey")

            # Check "already done" predicate (skip if classified)
            if (cfg.mode != MODE_RERUN
                    and not cfg.revalidate_existing
                    and is_entity_classified(
                        row,
                        require_tags=cfg.require_tags,
                        require_normalization=cfg.require_normalization)):
                stats.already_classified += 1
                stats.skipped += 1
                continue

            stats.attempted += 1

            if cfg.dry_run:
                stats.dry_run_would_process += 1
                logger.info(
                    f"[DRY-RUN] Would enqueue classification for "
                    f"EntityKey={entity_key} ({row.get('DisplayName')})"
                )
                continue

            # Build dedupe key for idempotent enqueue
            dedupe_key = f"entity_classify:{entity_key}"

            job_input = {
                "entity_key": entity_key,
                "entity_guid": str(row.get("EntityGuid", "")),
                "display_name": row.get("DisplayName"),
                "source_page_id": str(row.get("SourcePageId", "")) if row.get("SourcePageId") else None,
                "external_key": row.get("ExternalKey"),
                "fill_missing_only": cfg.fill_missing_only,
                "classify_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                result = self._get_queue().enqueue_job_idempotent(
                    interrogation_key=cfg.interrogation_key,
                    dedupe_key=dedupe_key,
                    input_json=json.dumps(job_input),
                    priority=cfg.priority,
                )

                if result.get("is_duplicate"):
                    existing_status = result.get("existing_status")
                    if existing_status == "SUCCEEDED":
                        stats.skipped += 1
                        stats.already_classified += 1
                    elif existing_status in ("FAILED", "DEADLETTER"):
                        # In fresh mode or --only failed, a duplicate for a
                        # previously failed job means we re-enqueued it
                        # successfully (the stored proc returned the existing
                        # job_id).  Otherwise treat it as skipped.
                        if cfg.mode == MODE_FRESH or cfg.only == ONLY_FAILED:
                            stats.succeeded += 1
                        else:
                            stats.skipped += 1
                    else:
                        stats.skipped += 1
                    logger.debug(
                        f"Duplicate job for EntityKey={entity_key}: "
                        f"status={existing_status}"
                    )
                else:
                    stats.succeeded += 1
                    logger.info(
                        f"Enqueued classification job for EntityKey={entity_key} "
                        f"({row.get('DisplayName')})"
                    )

            except Exception as exc:
                stats.failed += 1
                error_msg = f"EntityKey={entity_key}: {exc}"
                stats.errors.append(error_msg)
                logger.warning(f"Failed to enqueue: {error_msg}")

        return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the classify-entities CLI."""
    parser = argparse.ArgumentParser(
        prog="classify-entities",
        description="Entity Classification Runner with resume/checkpoint support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start fresh classification run
  python -m llm.cli.classify_entities --mode fresh --batch-size 200

  # Resume from last checkpoint (skip already-classified)
  python -m llm.cli.classify_entities --mode resume --batch-size 200

  # Resume but only retry failed entities
  python -m llm.cli.classify_entities --mode resume --only failed

  # Force re-run specific entities
  python -m llm.cli.classify_entities --mode rerun --entity-keys 123 456 789

  # Fill missing fields only (don't overwrite existing)
  python -m llm.cli.classify_entities --mode resume --fill-missing-only

  # Dry run (preview what would be processed)
  python -m llm.cli.classify_entities --mode resume --dry-run

  # Require tags and normalization before considering "done"
  python -m llm.cli.classify_entities --mode resume --require-tags --require-normalization
        """,
    )

    parser.add_argument(
        "--mode",
        choices=[MODE_FRESH, MODE_RESUME, MODE_RERUN],
        default=MODE_RESUME,
        help=(
            "Run mode: 'fresh' processes all entities, 'resume' skips "
            "already-classified, 'rerun' processes specific entity keys "
            "(default: resume)"
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Maximum entities to process per run (default: 200)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be processed without enqueuing jobs",
    )
    parser.add_argument(
        "--only",
        choices=[ONLY_FAILED, ONLY_PENDING],
        default=None,
        help="Filter: 'failed' retries only failed jobs, 'pending' only pending",
    )
    parser.add_argument(
        "--entity-keys",
        type=int,
        nargs="+",
        default=None,
        help="Specific EntityKey values to process (used with --mode rerun)",
    )
    parser.add_argument(
        "--fill-missing-only",
        action="store_true",
        help="Only fill NULL fields; do not overwrite existing values",
    )
    parser.add_argument(
        "--require-tags",
        action="store_true",
        help="Require AliasCsv to be non-null before considering entity classified",
    )
    parser.add_argument(
        "--require-normalization",
        action="store_true",
        help="Require DisplayNameNormalized and SortName before considering classified",
    )
    parser.add_argument(
        "--revalidate-existing",
        action="store_true",
        help="Force re-classification even if entity is already classified",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=100,
        help="Job priority (higher = processed sooner, default: 100)",
    )
    parser.add_argument(
        "--interrogation-key",
        type=str,
        default="entity_extraction_generic_v1",
        help="Interrogation key for classification jobs (default: entity_extraction_generic_v1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Build config from args
    config = ClassifyConfig(
        mode=args.mode,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        only=args.only,
        entity_keys=args.entity_keys,
        fill_missing_only=args.fill_missing_only,
        require_tags=args.require_tags,
        require_normalization=args.require_normalization,
        revalidate_existing=args.revalidate_existing,
        priority=args.priority,
        interrogation_key=args.interrogation_key,
    )

    logger.info(f"Starting entity classification: mode={config.mode}, batch_size={config.batch_size}")

    service = EntityClassificationService(config=config)
    stats = service.run()

    # Print summary
    summary = stats.to_dict()
    print(json.dumps(summary, indent=2))

    if stats.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
