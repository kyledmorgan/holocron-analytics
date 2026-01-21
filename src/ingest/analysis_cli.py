#!/usr/bin/env python3
"""
CLI for inbound link analysis and content seeding.

Usage:
    # Analyze inbound links and generate rank file
    python analysis_cli.py --analyze --source wookieepedia
    
    # Seed content work items based on rank (top 100 pages)
    python analysis_cli.py --seed-content --source wookieepedia --limit 100
    
    # Both: analyze first, then seed
    python analysis_cli.py --analyze --seed-content --source wookieepedia --limit 50
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.analysis import InboundLinkAnalyzer, seed_content_queue
from ingest.state import SqliteStateStore


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Inbound Link Analysis and Content Seeding CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run inbound link analysis and generate rank file",
    )
    
    parser.add_argument(
        "--seed-content",
        action="store_true",
        help="Seed content work items based on inbound link rank",
    )
    
    parser.add_argument(
        "--source",
        type=str,
        default="wookieepedia",
        help="MediaWiki source name (default: wookieepedia)",
    )
    
    parser.add_argument(
        "--api-url",
        type=str,
        default="https://starwars.fandom.com/api.php",
        help="MediaWiki API URL (default: Wookieepedia)",
    )
    
    parser.add_argument(
        "--data-lake",
        type=Path,
        default=Path("local/data_lake"),
        help="Path to data lake directory",
    )
    
    parser.add_argument(
        "--state-db",
        type=Path,
        default=Path("local/state/ingest_state.db"),
        help="Path to SQLite state database",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of pages to seed content for",
    )
    
    parser.add_argument(
        "--priority",
        type=int,
        default=1,
        help="Priority for content work items (default: 1)",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    if not args.analyze and not args.seed_content:
        logger.error("Must specify --analyze and/or --seed-content")
        return 1
    
    # Run analysis if requested
    if args.analyze:
        logger.info(f"Running inbound link analysis for source: {args.source}")
        
        analyzer = InboundLinkAnalyzer(
            source_name=args.source,
            data_lake_base=args.data_lake,
        )
        
        try:
            output_path = analyzer.analyze_and_save()
            stats = analyzer.get_stats()
            
            logger.info(f"Analysis complete!")
            logger.info(f"  Files processed: {stats['files_processed']}")
            logger.info(f"  Links counted: {stats['links_counted']}")
            logger.info(f"  Known pages: {stats['known_pages']}")
            logger.info(f"  Unique linked titles: {stats['unique_linked_titles']}")
            logger.info(f"  Output: {output_path}")
            
        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            return 1
    
    # Seed content work items if requested
    if args.seed_content:
        logger.info(f"Seeding content work items for source: {args.source}")
        
        state_store = None
        try:
            state_store = SqliteStateStore(db_path=args.state_db)
            
            enqueued = seed_content_queue(
                state_store=state_store,
                source_name=args.source,
                api_url=args.api_url,
                data_lake_base=args.data_lake,
                limit=args.limit,
                priority=args.priority,
            )
            
            stats = state_store.get_stats()
            
            logger.info(f"Content seeding complete!")
            logger.info(f"  New items enqueued: {enqueued}")
            logger.info(f"  Queue status: {stats}")
            
        except FileNotFoundError as e:
            logger.error(f"Cannot seed content: {e}")
            logger.error("Run --analyze first to generate the inbound link rank file.")
            return 1
        except Exception as e:
            logger.exception(f"Content seeding failed: {e}")
            return 1
        finally:
            if state_store is not None:
                state_store.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
