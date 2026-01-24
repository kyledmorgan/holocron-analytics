#!/usr/bin/env python
"""
Helper script to inspect LLM derive jobs and runs.

Usage:
    # List recent jobs
    python scripts/llm_inspect_jobs.py --list

    # Show details for a specific job
    python scripts/llm_inspect_jobs.py --job-id abc123

    # Show queue statistics
    python scripts/llm_inspect_jobs.py --stats

Environment Variables:
    LLM_SQLSERVER_HOST, LLM_SQLSERVER_PASSWORD, etc.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.storage.sql_job_queue import SqlJobQueue, QueueConfig


def list_jobs(queue, limit=20):
    """List recent jobs."""
    conn = queue._get_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT TOP {limit}
            j.job_id,
            j.status,
            j.interrogation_key,
            j.priority,
            j.attempt_count,
            j.max_attempts,
            j.created_utc,
            j.available_utc,
            j.locked_by,
            CASE 
                WHEN LEN(j.last_error) > 80 THEN LEFT(j.last_error, 80) + '...'
                ELSE j.last_error
            END as last_error
        FROM [{queue.config.schema}].[job] j
        ORDER BY j.created_utc DESC
    """)
    
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    
    if not rows:
        print("No jobs found.")
        return
    
    print(f"{'Job ID':<40} {'Status':<12} {'Key':<25} {'Pri':<4} {'Att':<5} {'Error':<40}")
    print("-" * 130)
    
    for row in rows:
        job = dict(zip(columns, row))
        job_id_short = str(job['job_id'])[:36]
        error = job.get('last_error') or ''
        print(f"{job_id_short:<40} {job['status']:<12} {job['interrogation_key']:<25} "
              f"{job['priority']:<4} {job['attempt_count']}/{job['max_attempts']:<3} {error:<40}")


def show_job(queue, job_id):
    """Show details for a specific job."""
    conn = queue._get_connection()
    cursor = conn.cursor()
    
    # Get job details
    cursor.execute(f"""
        SELECT *
        FROM [{queue.config.schema}].[job]
        WHERE job_id = ?
    """, (job_id,))
    
    row = cursor.fetchone()
    if not row:
        print(f"Job not found: {job_id}")
        return
    
    columns = [col[0] for col in cursor.description]
    job = dict(zip(columns, row))
    
    print("=" * 60)
    print("JOB DETAILS")
    print("=" * 60)
    print(f"Job ID:         {job['job_id']}")
    print(f"Status:         {job['status']}")
    print(f"Interrogation:  {job['interrogation_key']}")
    print(f"Priority:       {job['priority']}")
    print(f"Attempts:       {job['attempt_count']} / {job['max_attempts']}")
    print(f"Created:        {job['created_utc']}")
    print(f"Available:      {job['available_utc']}")
    print(f"Locked By:      {job.get('locked_by') or 'None'}")
    print(f"Model Hint:     {job.get('model_hint') or 'None'}")
    
    if job.get('last_error'):
        print(f"\nLast Error:\n{job['last_error']}")
    
    # Get runs for this job
    cursor.execute(f"""
        SELECT *
        FROM [{queue.config.schema}].[run]
        WHERE job_id = ?
        ORDER BY started_utc DESC
    """, (job_id,))
    
    runs = cursor.fetchall()
    run_columns = [col[0] for col in cursor.description]
    
    if runs:
        print("\n" + "=" * 60)
        print("RUNS")
        print("=" * 60)
        
        for run_row in runs:
            run = dict(zip(run_columns, run_row))
            print(f"\nRun ID:     {run['run_id']}")
            print(f"Status:     {run['status']}")
            print(f"Model:      {run['model_name']}")
            print(f"Started:    {run['started_utc']}")
            print(f"Completed:  {run.get('completed_utc') or 'In Progress'}")
            
            if run.get('metrics_json'):
                print(f"Metrics:    {run['metrics_json']}")
            
            if run.get('error'):
                print(f"Error:      {run['error'][:200]}")
            
            # Get artifacts for this run
            cursor.execute(f"""
                SELECT artifact_type, lake_uri, byte_count
                FROM [{queue.config.schema}].[artifact]
                WHERE run_id = ?
                ORDER BY created_utc
            """, (run['run_id'],))
            
            artifacts = cursor.fetchall()
            if artifacts:
                print("Artifacts:")
                for art in artifacts:
                    print(f"  - {art[0]}: {art[1]} ({art[2]} bytes)")


def show_stats(queue):
    """Show queue statistics."""
    stats = queue.get_queue_stats()
    
    print("=" * 40)
    print("QUEUE STATISTICS")
    print("=" * 40)
    
    total = sum(stats.values())
    for status, count in sorted(stats.items()):
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {status:<15} {count:>6} ({pct:5.1f}%)")
    
    print("-" * 40)
    print(f"  {'TOTAL':<15} {total:>6}")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect LLM derive jobs and runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list",
        action="store_true",
        help="List recent jobs"
    )
    group.add_argument(
        "--job-id",
        help="Show details for a specific job"
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Show queue statistics"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of jobs to list (default: 20)"
    )
    
    args = parser.parse_args()
    
    # Connect to queue
    try:
        config = QueueConfig.from_env()
        queue = SqlJobQueue(config)
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.list:
            list_jobs(queue, args.limit)
        elif args.job_id:
            show_job(queue, args.job_id)
        elif args.stats:
            show_stats(queue)
    finally:
        queue.close()


if __name__ == "__main__":
    main()
