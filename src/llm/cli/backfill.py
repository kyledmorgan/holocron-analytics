"""
Backfill CLI - Bulk enqueue/re-enqueue operations with rate limits.

Phase 3: Implements bulk re-processing capabilities for:
- Entity extraction (by type, confidence threshold, date range)
- Relationship extraction (by date range, priority)
- Classification (by confidence threshold)

Safety rails include:
- Maximum jobs per run
- Queue depth thresholds
- Rate limiting
- Priority assignment for backfill vs live work
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


logger = logging.getLogger(__name__)


# Default safety configuration
DEFAULT_MAX_JOBS = 100
DEFAULT_MAX_QUEUE_DEPTH = 500
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_DELAY_SECONDS = 1.0
DEFAULT_BACKFILL_PRIORITY = 50  # Lower than live work (default 100)


class BackfillConfig:
    """Configuration for backfill operations."""
    
    def __init__(
        self,
        max_jobs: int = DEFAULT_MAX_JOBS,
        max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_delay_seconds: float = DEFAULT_BATCH_DELAY_SECONDS,
        backfill_priority: int = DEFAULT_BACKFILL_PRIORITY,
        dry_run: bool = False,
    ):
        self.max_jobs = max_jobs
        self.max_queue_depth = max_queue_depth
        self.batch_size = batch_size
        self.batch_delay_seconds = batch_delay_seconds
        self.backfill_priority = backfill_priority
        self.dry_run = dry_run
    
    @classmethod
    def from_env(cls) -> "BackfillConfig":
        """Create config from environment variables."""
        return cls(
            max_jobs=int(os.environ.get("BACKFILL_MAX_JOBS", str(DEFAULT_MAX_JOBS))),
            max_queue_depth=int(os.environ.get("BACKFILL_MAX_QUEUE_DEPTH", str(DEFAULT_MAX_QUEUE_DEPTH))),
            batch_size=int(os.environ.get("BACKFILL_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
            batch_delay_seconds=float(os.environ.get("BACKFILL_BATCH_DELAY_SECONDS", str(DEFAULT_BATCH_DELAY_SECONDS))),
            backfill_priority=int(os.environ.get("BACKFILL_PRIORITY", str(DEFAULT_BACKFILL_PRIORITY))),
        )


class BackfillService:
    """
    Service for bulk enqueue/re-enqueue operations.
    
    Supports selecting candidates by:
    - Entity type (for entity extraction)
    - Confidence threshold (re-process low confidence results)
    - Date range (time-window slices)
    - Status (failed jobs for retry)
    
    Example:
        >>> service = BackfillService(queue=sql_queue, config=config)
        >>> result = service.backfill_entities(
        ...     entity_type="PersonCharacter",
        ...     confidence_threshold=0.7,
        ...     max_jobs=50,
        ... )
    """
    
    def __init__(self, queue=None, config: Optional[BackfillConfig] = None):
        """
        Initialize the backfill service.
        
        Args:
            queue: SQL job queue instance
            config: Backfill configuration
        """
        self.queue = queue
        self.config = config or BackfillConfig.from_env()
    
    def _get_queue(self):
        """Lazy load queue if not provided."""
        if self.queue is None:
            from ..storage.sql_job_queue import SqlJobQueue, QueueConfig
            self.queue = SqlJobQueue(QueueConfig.from_env())
        return self.queue
    
    def get_queue_depth(self) -> int:
        """Get current queue depth (NEW + RUNNING jobs)."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM llm.job 
                WHERE status IN ('NEW', 'RUNNING')
            """)
            
            row = cursor.fetchone()
            return row[0] if row else 0
            
        except Exception as e:
            logger.warning(f"Failed to get queue depth: {e}")
            return 0
    
    def check_queue_safety(self) -> bool:
        """
        Check if queue is safe for backfill operations.
        
        Returns False if queue depth exceeds threshold.
        """
        depth = self.get_queue_depth()
        if depth >= self.config.max_queue_depth:
            logger.warning(
                f"Queue depth ({depth}) exceeds threshold ({self.config.max_queue_depth}). "
                f"Backfill operation blocked."
            )
            return False
        return True
    
    def backfill_entities(
        self,
        entity_type: Optional[str] = None,
        confidence_threshold: float = 0.7,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        source_system: str = "wookieepedia",
        priority: Optional[int] = None,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue entity extraction jobs for pages matching criteria.
        
        Args:
            entity_type: Filter by primary type (e.g., 'PersonCharacter')
            confidence_threshold: Re-process pages with confidence below this
            date_start: Start of date range (ISO format)
            date_end: End of date range (ISO format)
            source_system: Source system filter
            priority: Priority for backfill jobs (default: config.backfill_priority)
            max_jobs: Maximum jobs to enqueue (default: config.max_jobs)
        
        Returns:
            Dict with enqueued count, skipped count, and errors
        """
        max_jobs = max_jobs or self.config.max_jobs
        priority = priority or self.config.backfill_priority
        
        # Safety check
        if not self.check_queue_safety():
            return {
                "status": "blocked",
                "reason": "queue_depth_exceeded",
                "enqueued": 0,
                "skipped": 0,
                "errors": [],
            }
        
        logger.info(
            f"Starting entity backfill: type={entity_type}, "
            f"confidence<{confidence_threshold}, max_jobs={max_jobs}"
        )
        
        # Get candidate pages
        candidates = self._get_entity_backfill_candidates(
            entity_type=entity_type,
            confidence_threshold=confidence_threshold,
            date_start=date_start,
            date_end=date_end,
            source_system=source_system,
            limit=max_jobs,
        )
        
        # Enqueue jobs in batches
        return self._enqueue_jobs(
            candidates=candidates,
            job_type="entity_extraction_generic",
            priority=priority,
        )
    
    def backfill_relationships(
        self,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        source_system: str = "wookieepedia",
        priority: Optional[int] = None,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue relationship extraction jobs for pages in date range.
        
        Args:
            date_start: Start of date range (ISO format)
            date_end: End of date range (ISO format)
            source_system: Source system filter
            priority: Priority for backfill jobs
            max_jobs: Maximum jobs to enqueue
        
        Returns:
            Dict with enqueued count, skipped count, and errors
        """
        max_jobs = max_jobs or self.config.max_jobs
        priority = priority or self.config.backfill_priority
        
        # Safety check
        if not self.check_queue_safety():
            return {
                "status": "blocked",
                "reason": "queue_depth_exceeded",
                "enqueued": 0,
                "skipped": 0,
                "errors": [],
            }
        
        logger.info(
            f"Starting relationship backfill: date_range={date_start}..{date_end}, "
            f"max_jobs={max_jobs}"
        )
        
        # Get candidate pages
        candidates = self._get_relationship_backfill_candidates(
            date_start=date_start,
            date_end=date_end,
            source_system=source_system,
            limit=max_jobs,
        )
        
        # Enqueue jobs in batches
        return self._enqueue_jobs(
            candidates=candidates,
            job_type="relationship_extraction",
            priority=priority,
        )
    
    def backfill_classification(
        self,
        confidence_threshold: float = 0.7,
        source_system: str = "wookieepedia",
        priority: Optional[int] = None,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue classification jobs for pages with low confidence.
        
        Args:
            confidence_threshold: Re-process pages with confidence below this
            source_system: Source system filter
            priority: Priority for backfill jobs
            max_jobs: Maximum jobs to enqueue
        
        Returns:
            Dict with enqueued count, skipped count, and errors
        """
        max_jobs = max_jobs or self.config.max_jobs
        priority = priority or self.config.backfill_priority
        
        # Safety check
        if not self.check_queue_safety():
            return {
                "status": "blocked",
                "reason": "queue_depth_exceeded",
                "enqueued": 0,
                "skipped": 0,
                "errors": [],
            }
        
        logger.info(
            f"Starting classification backfill: confidence<{confidence_threshold}, "
            f"max_jobs={max_jobs}"
        )
        
        # Get candidate pages
        candidates = self._get_classification_backfill_candidates(
            confidence_threshold=confidence_threshold,
            source_system=source_system,
            limit=max_jobs,
        )
        
        # Enqueue jobs in batches
        return self._enqueue_jobs(
            candidates=candidates,
            job_type="page_classification",
            priority=priority,
        )
    
    def _get_entity_backfill_candidates(
        self,
        entity_type: Optional[str],
        confidence_threshold: float,
        date_start: Optional[str],
        date_end: Optional[str],
        source_system: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get candidate pages for entity extraction backfill."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT TOP (?)
                    sp.source_page_id,
                    sp.resource_id,
                    sp.source_system,
                    pc.primary_type,
                    pc.confidence_score
                FROM sem.SourcePage sp
                LEFT JOIN sem.PageClassification pc ON sp.source_page_id = pc.source_page_id
                    AND pc.is_current = 1
                WHERE sp.source_system = ?
                    AND sp.is_active = 1
                    AND (pc.confidence_score IS NULL OR pc.confidence_score < ?)
            """
            params = [limit, source_system, confidence_threshold]
            
            if entity_type:
                query += " AND pc.primary_type = ?"
                params.append(entity_type)
            
            if date_start:
                query += " AND sp.created_utc >= ?"
                params.append(date_start)
            
            if date_end:
                query += " AND sp.created_utc <= ?"
                params.append(date_end)
            
            query += " ORDER BY ISNULL(pc.confidence_score, 0) ASC"
            
            cursor.execute(query, params)
            
            candidates = []
            for row in cursor.fetchall():
                columns = [column[0] for column in cursor.description]
                candidates.append(dict(zip(columns, row)))
            
            logger.info(f"Found {len(candidates)} entity backfill candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to get entity backfill candidates: {e}")
            return []
    
    def _get_relationship_backfill_candidates(
        self,
        date_start: Optional[str],
        date_end: Optional[str],
        source_system: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get candidate pages for relationship extraction backfill."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Get pages that haven't had relationship extraction
            query = """
                SELECT TOP (?)
                    sp.source_page_id,
                    sp.resource_id,
                    sp.source_system,
                    pc.primary_type
                FROM sem.SourcePage sp
                LEFT JOIN sem.PageClassification pc ON sp.source_page_id = pc.source_page_id
                    AND pc.is_current = 1
                WHERE sp.source_system = ?
                    AND sp.is_active = 1
                    AND pc.primary_type NOT IN ('TechnicalSitePage', 'ReferenceMeta', 'Unknown')
            """
            params = [limit, source_system]
            
            if date_start:
                query += " AND sp.created_utc >= ?"
                params.append(date_start)
            
            if date_end:
                query += " AND sp.created_utc <= ?"
                params.append(date_end)
            
            query += " ORDER BY sp.created_utc DESC"
            
            cursor.execute(query, params)
            
            candidates = []
            for row in cursor.fetchall():
                columns = [column[0] for column in cursor.description]
                candidates.append(dict(zip(columns, row)))
            
            logger.info(f"Found {len(candidates)} relationship backfill candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to get relationship backfill candidates: {e}")
            return []
    
    def _get_classification_backfill_candidates(
        self,
        confidence_threshold: float,
        source_system: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get candidate pages for classification backfill."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT TOP (?)
                    sp.source_page_id,
                    sp.resource_id,
                    sp.source_system,
                    pc.primary_type,
                    pc.confidence_score
                FROM sem.SourcePage sp
                LEFT JOIN sem.PageClassification pc ON sp.source_page_id = pc.source_page_id
                    AND pc.is_current = 1
                WHERE sp.source_system = ?
                    AND sp.is_active = 1
                    AND (pc.confidence_score IS NULL OR pc.confidence_score < ?)
                ORDER BY ISNULL(pc.confidence_score, 0) ASC
            """
            
            cursor.execute(query, [limit, source_system, confidence_threshold])
            
            candidates = []
            for row in cursor.fetchall():
                columns = [column[0] for column in cursor.description]
                candidates.append(dict(zip(columns, row)))
            
            logger.info(f"Found {len(candidates)} classification backfill candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to get classification backfill candidates: {e}")
            return []
    
    def _enqueue_jobs(
        self,
        candidates: List[Dict[str, Any]],
        job_type: str,
        priority: int,
    ) -> Dict[str, Any]:
        """
        Enqueue jobs for candidates in batches with rate limiting.
        
        Returns results summary.
        """
        enqueued = 0
        skipped = 0
        errors = []
        
        if self.config.dry_run:
            logger.info(f"DRY-RUN: Would enqueue {len(candidates)} {job_type} jobs")
            return {
                "status": "dry_run",
                "enqueued": 0,
                "would_enqueue": len(candidates),
                "skipped": 0,
                "errors": [],
            }
        
        for i, candidate in enumerate(candidates):
            # Rate limiting - pause between batches
            if i > 0 and i % self.config.batch_size == 0:
                time.sleep(self.config.batch_delay_seconds)
                
                # Re-check queue safety periodically
                if not self.check_queue_safety():
                    logger.warning(f"Stopping backfill: queue depth exceeded after {enqueued} jobs")
                    break
            
            try:
                # Enqueue job
                job_input = {
                    "source_page_id": candidate.get("source_page_id"),
                    "source_id": candidate.get("resource_id"),
                    "source_system": candidate.get("source_system"),
                    "backfill": True,
                    "backfill_timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                # Map job type to interrogation key
                interrogation_key = self._get_interrogation_key(job_type)
                
                self._get_queue().enqueue_job(
                    interrogation_key=interrogation_key,
                    input_json=json.dumps(job_input),
                    priority=priority,
                )
                
                enqueued += 1
                
            except Exception as e:
                error_msg = f"Failed to enqueue job for {candidate.get('resource_id')}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                skipped += 1
        
        logger.info(
            f"Backfill complete: enqueued={enqueued}, skipped={skipped}, "
            f"errors={len(errors)}"
        )
        
        return {
            "status": "completed",
            "enqueued": enqueued,
            "skipped": skipped,
            "errors": errors[:10],  # Limit error output
        }
    
    def _get_interrogation_key(self, job_type: str) -> str:
        """Map job type to interrogation key."""
        mapping = {
            "entity_extraction_generic": "entity_extraction_generic_v1",
            "relationship_extraction": "relationship_extraction_v1",
            "page_classification": "page_classification_v1",
            "entity_extraction_droid": "entity_extraction_droid_v1",
        }
        return mapping.get(job_type, f"{job_type}_v1")


def main():
    """CLI entry point for backfill operations."""
    parser = argparse.ArgumentParser(
        description="LLM Backfill CLI - Bulk enqueue/re-enqueue operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-process pages with confidence < 0.7 (entity extraction)
  python -m src.llm.cli.backfill entities \\
    --entity-type=PersonCharacter \\
    --confidence-threshold=0.7 \\
    --max-jobs=100

  # Re-extract relationships for specific date range
  python -m src.llm.cli.backfill relationships \\
    --date-range=2024-01-01..2024-12-31 \\
    --priority=200

  # Re-classify low-confidence pages
  python -m src.llm.cli.backfill classification \\
    --confidence-threshold=0.6 \\
    --max-jobs=50
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Backfill command")
    
    # entities subcommand
    entities_parser = subparsers.add_parser(
        "entities",
        help="Backfill entity extraction jobs"
    )
    entities_parser.add_argument(
        "--entity-type",
        type=str,
        default=None,
        help="Filter by entity type (e.g., PersonCharacter, LocationPlace)"
    )
    entities_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Re-process pages with confidence below this (default: 0.7)"
    )
    entities_parser.add_argument(
        "--date-range",
        type=str,
        default=None,
        help="Date range filter (format: YYYY-MM-DD..YYYY-MM-DD)"
    )
    entities_parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS,
        help=f"Maximum jobs to enqueue (default: {DEFAULT_MAX_JOBS})"
    )
    entities_parser.add_argument(
        "--priority",
        type=int,
        default=DEFAULT_BACKFILL_PRIORITY,
        help=f"Priority for backfill jobs (default: {DEFAULT_BACKFILL_PRIORITY})"
    )
    entities_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be enqueued without actually enqueuing"
    )
    
    # relationships subcommand
    rel_parser = subparsers.add_parser(
        "relationships",
        help="Backfill relationship extraction jobs"
    )
    rel_parser.add_argument(
        "--date-range",
        type=str,
        default=None,
        help="Date range filter (format: YYYY-MM-DD..YYYY-MM-DD)"
    )
    rel_parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS,
        help=f"Maximum jobs to enqueue (default: {DEFAULT_MAX_JOBS})"
    )
    rel_parser.add_argument(
        "--priority",
        type=int,
        default=DEFAULT_BACKFILL_PRIORITY,
        help=f"Priority for backfill jobs (default: {DEFAULT_BACKFILL_PRIORITY})"
    )
    rel_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be enqueued without actually enqueuing"
    )
    
    # classification subcommand
    class_parser = subparsers.add_parser(
        "classification",
        help="Backfill classification jobs"
    )
    class_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Re-process pages with confidence below this (default: 0.7)"
    )
    class_parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS,
        help=f"Maximum jobs to enqueue (default: {DEFAULT_MAX_JOBS})"
    )
    class_parser.add_argument(
        "--priority",
        type=int,
        default=DEFAULT_BACKFILL_PRIORITY,
        help=f"Priority for backfill jobs (default: {DEFAULT_BACKFILL_PRIORITY})"
    )
    class_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be enqueued without actually enqueuing"
    )
    
    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Create service with dry-run config if specified
    config = BackfillConfig.from_env()
    if hasattr(args, "dry_run") and args.dry_run:
        config.dry_run = True
    
    service = BackfillService(config=config)
    
    # Parse date range if provided
    date_start = None
    date_end = None
    if hasattr(args, "date_range") and args.date_range:
        try:
            date_start, date_end = args.date_range.split("..")
        except ValueError:
            logger.error("Invalid date range format. Use: YYYY-MM-DD..YYYY-MM-DD")
            sys.exit(1)
    
    # Execute command
    if args.command == "entities":
        result = service.backfill_entities(
            entity_type=args.entity_type,
            confidence_threshold=args.confidence_threshold,
            date_start=date_start,
            date_end=date_end,
            priority=args.priority,
            max_jobs=args.max_jobs,
        )
    elif args.command == "relationships":
        result = service.backfill_relationships(
            date_start=date_start,
            date_end=date_end,
            priority=args.priority,
            max_jobs=args.max_jobs,
        )
    elif args.command == "classification":
        result = service.backfill_classification(
            confidence_threshold=args.confidence_threshold,
            priority=args.priority,
            max_jobs=args.max_jobs,
        )
    else:
        parser.print_help()
        sys.exit(1)
    
    # Output results
    print(json.dumps(result, indent=2))
    
    if result.get("status") == "blocked":
        sys.exit(2)
    elif result.get("errors"):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
