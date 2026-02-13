"""
Priority CLI - Queue priority management and escalation.

Phase 3: Implements priority escalation controls:
- Manual priority bumping for specific jobs/types
- Auto-escalation for stale jobs (anti-starvation)
- Priority band management
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


logger = logging.getLogger(__name__)


# Default escalation configuration
DEFAULT_AGE_THRESHOLD_MINUTES = 60
DEFAULT_PRIORITY_BOOST = 50
DEFAULT_MAX_PRIORITY = 300
DEFAULT_MAX_JOBS_PER_RUN = 100


class PriorityConfig:
    """Configuration for priority operations."""
    
    def __init__(
        self,
        age_threshold_minutes: int = DEFAULT_AGE_THRESHOLD_MINUTES,
        priority_boost: int = DEFAULT_PRIORITY_BOOST,
        max_priority: int = DEFAULT_MAX_PRIORITY,
        max_jobs_per_run: int = DEFAULT_MAX_JOBS_PER_RUN,
        dry_run: bool = False,
    ):
        self.age_threshold_minutes = age_threshold_minutes
        self.priority_boost = priority_boost
        self.max_priority = max_priority
        self.max_jobs_per_run = max_jobs_per_run
        self.dry_run = dry_run
    
    @classmethod
    def from_env(cls) -> "PriorityConfig":
        """Create config from environment variables."""
        return cls(
            age_threshold_minutes=int(os.environ.get("ESCALATION_AGE_THRESHOLD", str(DEFAULT_AGE_THRESHOLD_MINUTES))),
            priority_boost=int(os.environ.get("ESCALATION_PRIORITY_BOOST", str(DEFAULT_PRIORITY_BOOST))),
            max_priority=int(os.environ.get("ESCALATION_MAX_PRIORITY", str(DEFAULT_MAX_PRIORITY))),
            max_jobs_per_run=int(os.environ.get("ESCALATION_MAX_JOBS", str(DEFAULT_MAX_JOBS_PER_RUN))),
        )


class PriorityService:
    """
    Service for queue priority management.
    
    Supports:
    - Manual priority bumping
    - Auto-escalation based on age
    - Priority reset
    - Queue health queries
    
    Example:
        >>> service = PriorityService(queue=sql_queue)
        >>> result = service.escalate_aged_jobs(age_threshold_minutes=60)
    """
    
    def __init__(self, queue=None, config: Optional[PriorityConfig] = None):
        """
        Initialize the priority service.
        
        Args:
            queue: SQL job queue instance
            config: Priority configuration
        """
        self.queue = queue
        self.config = config or PriorityConfig.from_env()
    
    def _get_queue(self):
        """Lazy load queue if not provided."""
        if self.queue is None:
            from ..storage.sql_job_queue import SqlJobQueue, QueueConfig
            self.queue = SqlJobQueue(QueueConfig.from_env())
        return self.queue
    
    def escalate_aged_jobs(
        self,
        age_threshold_minutes: Optional[int] = None,
        priority_boost: Optional[int] = None,
        max_priority: Optional[int] = None,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Escalate priority of jobs exceeding age threshold.
        
        Args:
            age_threshold_minutes: Jobs older than this get escalated
            priority_boost: Amount to increase priority by
            max_priority: Maximum priority cap
            max_jobs: Maximum jobs to escalate per run
        
        Returns:
            Dict with escalation results
        """
        age_threshold = age_threshold_minutes or self.config.age_threshold_minutes
        boost = priority_boost or self.config.priority_boost
        max_pri = max_priority or self.config.max_priority
        max_jobs = max_jobs or self.config.max_jobs_per_run
        
        logger.info(
            f"Escalating aged jobs: age>{age_threshold}min, boost={boost}, "
            f"max_priority={max_pri}"
        )
        
        if self.config.dry_run:
            # Count affected jobs without modifying
            count = self._count_aged_jobs(age_threshold, max_pri)
            return {
                "status": "dry_run",
                "would_escalate": count,
                "age_threshold_minutes": age_threshold,
                "priority_boost": boost,
            }
        
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Use stored procedure if available
            cursor.execute(
                "EXEC llm.usp_escalate_aged_jobs @age_threshold_minutes = ?, "
                "@priority_boost = ?, @max_priority = ?, @max_jobs_per_run = ?",
                (age_threshold, boost, max_pri, max_jobs)
            )
            
            row = cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                result = dict(zip(columns, row))
                result["status"] = "completed"
                return result
            
            return {
                "status": "completed",
                "jobs_escalated": 0,
            }
            
        except Exception as e:
            # Fallback to direct SQL if stored procedure not found
            logger.warning(f"Stored procedure not available, using direct SQL: {e}")
            return self._escalate_aged_jobs_direct(age_threshold, boost, max_pri, max_jobs)
    
    def _count_aged_jobs(self, age_threshold: int, max_priority: int) -> int:
        """Count jobs eligible for escalation."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*)
                FROM llm.job
                WHERE status = 'NEW'
                  AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > ?
                  AND priority < ?
            """, (age_threshold, max_priority))
            
            row = cursor.fetchone()
            return row[0] if row else 0
            
        except Exception as e:
            logger.error(f"Failed to count aged jobs: {e}")
            return 0
    
    def _escalate_aged_jobs_direct(
        self,
        age_threshold: int,
        boost: int,
        max_priority: int,
        max_jobs: int,
    ) -> Dict[str, Any]:
        """Direct SQL implementation of escalation."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Use parameterized query for all values including max_jobs
            # SQL Server requires TOP in specific syntax, using dynamic SQL safely
            query = """
                UPDATE TOP (?) llm.job
                SET 
                    priority = CASE 
                        WHEN priority + ? > ? THEN ?
                        ELSE priority + ?
                    END,
                    updated_at = GETUTCDATE()
                WHERE status = 'NEW'
                  AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > ?
                  AND priority < ?
            """
            cursor.execute(query, (max_jobs, boost, max_priority, max_priority, boost, age_threshold, max_priority))
            
            affected = cursor.rowcount
            
            return {
                "status": "completed",
                "jobs_escalated": affected,
                "age_threshold_minutes": age_threshold,
                "priority_boost": boost,
            }
            
        except Exception as e:
            logger.error(f"Failed to escalate jobs: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def bump_priority(
        self,
        job_type: Optional[str] = None,
        job_ids: Optional[List[str]] = None,
        source_pattern: Optional[str] = None,
        priority_boost: Optional[int] = None,
        set_priority: Optional[int] = None,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Bump priority for specific jobs.
        
        Args:
            job_type: Filter by interrogation key
            job_ids: Specific job IDs to bump
            source_pattern: Filter by source pattern (LIKE match)
            priority_boost: Amount to increase priority by
            set_priority: Set priority to exact value (overrides boost)
            max_jobs: Maximum jobs to affect
        
        Returns:
            Dict with bump results
        """
        boost = priority_boost or self.config.priority_boost
        max_jobs = max_jobs or self.config.max_jobs_per_run
        
        if self.config.dry_run:
            count = self._count_bump_candidates(job_type, job_ids, source_pattern)
            return {
                "status": "dry_run",
                "would_affect": count,
            }
        
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic query
            query_parts = [f"UPDATE TOP ({max_jobs}) llm.job SET "]
            
            if set_priority is not None:
                query_parts.append("priority = ?, ")
                params = [set_priority]
            else:
                query_parts.append("priority = priority + ?, ")
                params = [boost]
            
            query_parts.append("updated_at = GETUTCDATE() WHERE status IN ('NEW', 'RUNNING')")
            
            if job_ids:
                placeholders = ",".join(["?" for _ in job_ids])
                query_parts.append(f" AND job_id IN ({placeholders})")
                params.extend(job_ids)
            
            if job_type:
                query_parts.append(" AND interrogation_key = ?")
                params.append(job_type)
            
            if source_pattern:
                query_parts.append(" AND input_json LIKE ?")
                params.append(f"%{source_pattern}%")
            
            query = "".join(query_parts)
            cursor.execute(query, params)
            
            affected = cursor.rowcount
            
            return {
                "status": "completed",
                "jobs_affected": affected,
            }
            
        except Exception as e:
            logger.error(f"Failed to bump priority: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def _count_bump_candidates(
        self,
        job_type: Optional[str],
        job_ids: Optional[List[str]],
        source_pattern: Optional[str],
    ) -> int:
        """Count jobs eligible for priority bump."""
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            query_parts = ["SELECT COUNT(*) FROM llm.job WHERE status IN ('NEW', 'RUNNING')"]
            params = []
            
            if job_ids:
                placeholders = ",".join(["?" for _ in job_ids])
                query_parts.append(f" AND job_id IN ({placeholders})")
                params.extend(job_ids)
            
            if job_type:
                query_parts.append(" AND interrogation_key = ?")
                params.append(job_type)
            
            if source_pattern:
                query_parts.append(" AND input_json LIKE ?")
                params.append(f"%{source_pattern}%")
            
            query = "".join(query_parts)
            cursor.execute(query, params)
            
            row = cursor.fetchone()
            return row[0] if row else 0
            
        except Exception as e:
            logger.error(f"Failed to count bump candidates: {e}")
            return 0
    
    def get_queue_health(self) -> Dict[str, Any]:
        """
        Get comprehensive queue health summary.
        
        Returns:
            Dict with queue metrics
        """
        try:
            conn = self._get_queue()._get_connection()
            cursor = conn.cursor()
            
            # Overall metrics
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM llm.job WHERE status = 'NEW') AS pending_jobs,
                    (SELECT COUNT(*) FROM llm.job WHERE status = 'RUNNING') AS running_jobs,
                    (SELECT COUNT(*) FROM llm.job WHERE status = 'SUCCEEDED' 
                     AND created_at > DATEADD(HOUR, -24, GETUTCDATE())) AS succeeded_24h,
                    (SELECT COUNT(*) FROM llm.job WHERE status = 'FAILED' 
                     AND created_at > DATEADD(HOUR, -24, GETUTCDATE())) AS failed_24h,
                    (SELECT COUNT(*) FROM llm.job WHERE status = 'DEADLETTER') AS deadletter_total,
                    (SELECT AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) 
                     FROM llm.job WHERE status = 'NEW') AS avg_pending_age_minutes,
                    (SELECT MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) 
                     FROM llm.job WHERE status = 'NEW') AS max_pending_age_minutes,
                    (SELECT COUNT(*) FROM llm.job 
                     WHERE status = 'NEW' AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 60) AS stale_job_count
            """)
            
            row = cursor.fetchone()
            columns = [column[0] for column in cursor.description]
            metrics = dict(zip(columns, row))
            
            # Health by status
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) AS job_count,
                    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes
                FROM llm.job
                GROUP BY status
            """)
            
            by_status = []
            for row in cursor.fetchall():
                cols = [c[0] for c in cursor.description]
                by_status.append(dict(zip(cols, row)))
            
            return {
                "status": "ok",
                "metrics": metrics,
                "by_status": by_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue health: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


def main():
    """CLI entry point for priority operations."""
    parser = argparse.ArgumentParser(
        description="LLM Priority CLI - Queue priority management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-escalate jobs older than 60 minutes
  python -m src.llm.cli.priority escalate --age-threshold=60

  # Bump priority for specific job type
  python -m src.llm.cli.priority bump --job-type=page_classification_v1 --boost=100

  # Set exact priority for jobs
  python -m src.llm.cli.priority bump --job-type=entity_extraction_generic_v1 --set-priority=250

  # Get queue health summary
  python -m src.llm.cli.priority health
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Priority command")
    
    # escalate subcommand
    escalate_parser = subparsers.add_parser(
        "escalate",
        help="Auto-escalate aged jobs"
    )
    escalate_parser.add_argument(
        "--age-threshold",
        type=int,
        default=DEFAULT_AGE_THRESHOLD_MINUTES,
        help=f"Jobs older than this (minutes) get escalated (default: {DEFAULT_AGE_THRESHOLD_MINUTES})"
    )
    escalate_parser.add_argument(
        "--boost",
        type=int,
        default=DEFAULT_PRIORITY_BOOST,
        help=f"Priority boost amount (default: {DEFAULT_PRIORITY_BOOST})"
    )
    escalate_parser.add_argument(
        "--max-priority",
        type=int,
        default=DEFAULT_MAX_PRIORITY,
        help=f"Maximum priority cap (default: {DEFAULT_MAX_PRIORITY})"
    )
    escalate_parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS_PER_RUN,
        help=f"Maximum jobs to escalate (default: {DEFAULT_MAX_JOBS_PER_RUN})"
    )
    escalate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be escalated without changes"
    )
    
    # bump subcommand
    bump_parser = subparsers.add_parser(
        "bump",
        help="Bump priority for specific jobs"
    )
    bump_parser.add_argument(
        "--job-type",
        type=str,
        default=None,
        help="Filter by interrogation key"
    )
    bump_parser.add_argument(
        "--job-ids",
        type=str,
        default=None,
        help="Comma-separated job IDs"
    )
    bump_parser.add_argument(
        "--source-pattern",
        type=str,
        default=None,
        help="Filter by source pattern (substring match)"
    )
    bump_parser.add_argument(
        "--boost",
        type=int,
        default=DEFAULT_PRIORITY_BOOST,
        help=f"Priority boost amount (default: {DEFAULT_PRIORITY_BOOST})"
    )
    bump_parser.add_argument(
        "--set-priority",
        type=int,
        default=None,
        help="Set exact priority value (overrides --boost)"
    )
    bump_parser.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_MAX_JOBS_PER_RUN,
        help=f"Maximum jobs to affect (default: {DEFAULT_MAX_JOBS_PER_RUN})"
    )
    bump_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be bumped without changes"
    )
    
    # health subcommand
    health_parser = subparsers.add_parser(
        "health",
        help="Get queue health summary"
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
    
    # Create service
    config = PriorityConfig.from_env()
    if hasattr(args, "dry_run") and args.dry_run:
        config.dry_run = True
    
    service = PriorityService(config=config)
    
    # Execute command
    if args.command == "escalate":
        result = service.escalate_aged_jobs(
            age_threshold_minutes=args.age_threshold,
            priority_boost=args.boost,
            max_priority=args.max_priority,
            max_jobs=args.max_jobs,
        )
    elif args.command == "bump":
        job_ids = args.job_ids.split(",") if args.job_ids else None
        result = service.bump_priority(
            job_type=args.job_type,
            job_ids=job_ids,
            source_pattern=args.source_pattern,
            priority_boost=args.boost,
            set_priority=args.set_priority,
            max_jobs=args.max_jobs,
        )
    elif args.command == "health":
        result = service.get_queue_health()
    else:
        parser.print_help()
        sys.exit(1)
    
    # Output results
    print(json.dumps(result, indent=2, default=str))
    
    if result.get("status") == "error":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
