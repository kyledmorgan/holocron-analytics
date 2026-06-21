#!/usr/bin/env python
"""
Helper script to enqueue LLM derive jobs.

This script provides a simple way to enqueue jobs for the Phase 1 runner
without needing to write SQL directly.

Usage:
    # Enqueue a job with inline evidence
    python scripts/llm_enqueue_job.py \
        --entity-type character \
        --entity-id luke_skywalker \
        --evidence "Luke Skywalker was a human male Jedi born on Tatooine in 19 BBY."

    # Enqueue a job with evidence from file
    python scripts/llm_enqueue_job.py \
        --entity-type planet \
        --entity-id tatooine \
        --evidence-file evidence.txt

    # Enqueue with custom priority and model
    python scripts/llm_enqueue_job.py \
        --entity-type character \
        --entity-id vader \
        --evidence "Darth Vader was a Sith Lord." \
        --priority 200 \
        --model llama3.1

Environment Variables:
    LLM_SQLSERVER_HOST, LLM_SQLSERVER_PASSWORD, etc.
    (Falls back to INGEST_SQLSERVER_* or MSSQL_* vars)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm.storage.sql_job_queue import SqlJobQueue, QueueConfig


def _load_dotenv_if_present() -> None:
    """
    Load key/value pairs from .env into process env if not already set.

    Keeps explicit shell environment values as the source of truth.
    """
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and os.environ.get(key) is None:
            os.environ[key] = value


def main():
    parser = argparse.ArgumentParser(
        description="Enqueue an LLM derive job",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--entity-type",
        required=True,
        help="Type of entity (e.g., character, planet, starship)"
    )
    parser.add_argument(
        "--entity-id",
        required=True,
        help="Entity identifier (e.g., luke_skywalker)"
    )
    parser.add_argument(
        "--evidence",
        action="append",
        help="Evidence text (can be specified multiple times)"
    )
    parser.add_argument(
        "--evidence-file",
        action="append",
        help="Path to file containing evidence (can be specified multiple times)"
    )
    parser.add_argument(
        "--interrogation",
        default="sw_entity_facts_v1",
        help="Interrogation key (default: sw_entity_facts_v1)"
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=100,
        help="Job priority (higher = processed sooner, default: 100)"
    )
    parser.add_argument(
        "--model",
        help="Model hint (e.g., llama3.2, llama3.1)"
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum retry attempts (default: 3)"
    )
    
    args = parser.parse_args()

    # Make local CLI runs work without manually exporting env vars first.
    _load_dotenv_if_present()
    
    # Build evidence list
    evidence_items = []
    evidence_index = 1
    
    # Add evidence from command line
    if args.evidence:
        for text in args.evidence:
            evidence_items.append({
                "evidence_id": f"e{evidence_index}",
                "source_uri": "cli_input",
                "text": text
            })
            evidence_index += 1
    
    # Add evidence from files
    if args.evidence_file:
        for filepath in args.evidence_file:
            path = Path(filepath)
            if not path.exists():
                print(f"Error: Evidence file not found: {filepath}", file=sys.stderr)
                sys.exit(1)
            
            text = path.read_text(encoding="utf-8")
            evidence_items.append({
                "evidence_id": f"e{evidence_index}",
                "source_uri": str(path.absolute()),
                "text": text
            })
            evidence_index += 1
    
    if not evidence_items:
        print("Error: No evidence provided. Use --evidence or --evidence-file", file=sys.stderr)
        sys.exit(1)
    
    # Build input envelope
    input_data = {
        "entity_type": args.entity_type,
        "entity_id": args.entity_id,
        "source_refs": [],
        "extra_params": {
            "evidence": evidence_items
        }
    }
    
    # Connect to queue
    try:
        config = QueueConfig.from_env()
        queue = SqlJobQueue(config)
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        print("\nMake sure SQL Server is running and environment variables are set:", file=sys.stderr)
        print("  LLM_SQLSERVER_PASSWORD or MSSQL_SA_PASSWORD", file=sys.stderr)
        sys.exit(1)
    
    # Enqueue job
    try:
        job_id = queue.enqueue_job(
            interrogation_key=args.interrogation,
            input_json=json.dumps(input_data),
            priority=args.priority,
            model_hint=args.model,
            max_attempts=args.max_attempts,
        )
        
        print(f"Job enqueued successfully!")
        print(f"  Job ID: {job_id}")
        print(f"  Interrogation: {args.interrogation}")
        print(f"  Entity: {args.entity_type}/{args.entity_id}")
        print(f"  Evidence items: {len(evidence_items)}")
        print(f"  Priority: {args.priority}")
        if args.model:
            print(f"  Model hint: {args.model}")
        
    except Exception as e:
        print(f"Error enqueuing job: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        queue.close()


if __name__ == "__main__":
    main()
