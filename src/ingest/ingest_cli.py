#!/usr/bin/env python3
"""
CLI entry point for the Holocron Analytics ingestion framework.

Orchestrates the ingestion pipeline based on configuration.

Usage:
    python ingest_cli.py --config config/ingest.yaml
    python ingest_cli.py --config config/ingest.yaml --seed
    python ingest_cli.py --config config/ingest.yaml --max-items 100
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.config import IngestConfig
from ingest.core.models import WorkItem
from ingest.connectors import HttpConnector, MediaWikiConnector
from ingest.storage import FileLakeWriter, SqlServerIngestWriter
from ingest.state import SqliteStateStore
from ingest.discovery import MediaWikiDiscovery
from ingest.runner import IngestRunner


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_connectors(config: IngestConfig) -> dict:
    """Build connectors from configuration."""
    connectors = {}
    
    for source_config in config.get_sources():
        source_type = source_config.get("type")
        source_name = source_config.get("name")
        
        if source_type == "mediawiki":
            connector = MediaWikiConnector(
                name=source_name,
                api_url=source_config["api_url"],
                rate_limit_delay=source_config.get("rate_limit_delay", 1.0),
                timeout=source_config.get("timeout", 30),
                max_retries=source_config.get("max_retries", 3),
                user_agent=source_config.get("user_agent"),
            )
            connectors["mediawiki"] = connector
        
        elif source_type == "http":
            connector = HttpConnector(
                name=source_name,
                rate_limit_delay=source_config.get("rate_limit_delay", 0.0),
                timeout=source_config.get("timeout", 30),
                max_retries=source_config.get("max_retries", 3),
                user_agent=source_config.get("user_agent"),
            )
            connectors["http"] = connector
    
    return connectors


def build_storage_writers(config: IngestConfig) -> list:
    """Build storage writers from configuration."""
    writers = []
    storage_config = config.get_storage_config()
    
    # Data lake writer
    if storage_config.get("data_lake", {}).get("enabled", True):
        lake_config = storage_config["data_lake"]
        base_dir = Path(lake_config.get("base_dir", "local/data_lake"))
        
        writer = FileLakeWriter(
            base_dir=base_dir,
            create_dirs=True,
            pretty_print=lake_config.get("pretty_print", True),
        )
        writers.append(writer)
    
    # SQL Server writer
    if storage_config.get("sql_server", {}).get("enabled", False):
        sql_config = storage_config["sql_server"]
        
        # Get connection string from env or config
        conn_str = os.environ.get("INGEST_SQLSERVER_CONN_STR")
        if not conn_str:
            # Build from discrete values
            host = sql_config.get("host", "localhost")
            port = sql_config.get("port", "1433")
            database = sql_config.get("database", "HolocronAnalytics")
            user = sql_config.get("user", "sa")
            password = os.environ.get("INGEST_SQLSERVER_PASSWORD", sql_config.get("password"))
            driver = sql_config.get("driver", "ODBC Driver 18 for SQL Server")
            
            conn_str = (
                f"Driver={{{driver}}};"
                f"Server={host},{port};"
                f"Database={database};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=yes"
            )
        
        writer = SqlServerIngestWriter(
            connection_string=conn_str,
            schema=sql_config.get("schema", "ingest"),
            table=sql_config.get("table", "IngestRecords"),
        )
        writers.append(writer)
    
    return writers


def build_state_store(config: IngestConfig) -> SqliteStateStore:
    """Build state store from configuration."""
    state_config = config.get_state_config()
    db_path = Path(state_config.get("db_path", "local/state/ingest_state.db"))
    
    return SqliteStateStore(db_path=db_path)


def build_discovery_plugins(config: IngestConfig) -> list:
    """Build discovery plugins from configuration."""
    plugins = []
    
    for source_config in config.get_sources():
        source_type = source_config.get("type")
        source_name = source_config.get("name")
        discovery_config = source_config.get("discovery", {})
        
        if not discovery_config.get("enabled", True):
            continue
        
        if source_type == "mediawiki":
            plugin = MediaWikiDiscovery(
                api_url=source_config["api_url"],
                source_name=source_name,
                discover_links=discovery_config.get("discover_links", True),
                discover_categories=discovery_config.get("discover_categories", False),
                max_depth=discovery_config.get("max_depth"),
            )
            plugins.append(plugin)
    
    return plugins


def create_seed_work_items(config: IngestConfig) -> list:
    """Create initial work items from seed configuration."""
    work_items = []
    
    for seed_config in config.get_seeds():
        source_name = seed_config.get("source")
        resource_type = seed_config.get("resource_type", "page")
        titles = seed_config.get("titles", [])
        priority = seed_config.get("priority", 10)
        
        # Find the source configuration
        source_config = None
        for src in config.get_sources():
            if src.get("name") == source_name:
                source_config = src
                break
        
        if not source_config:
            logging.warning(f"Source not found for seed: {source_name}")
            continue
        
        source_type = source_config.get("type")
        
        # Create work items for each title
        for title in titles:
            if source_type == "mediawiki":
                from urllib.parse import urlencode
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "links",
                    "pllimit": 500,
                }
                request_uri = f"{source_config['api_url']}?{urlencode(params)}"
                
                work_item = WorkItem(
                    source_system="mediawiki",
                    source_name=source_name,
                    resource_type=resource_type,
                    resource_id=title,
                    request_uri=request_uri,
                    request_method="GET",
                    priority=priority,
                    metadata={"seed": True},
                )
                work_items.append(work_item)
    
    return work_items


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Holocron Analytics Ingestion Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration YAML file",
    )
    
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the queue with initial work items from config",
    )
    
    parser.add_argument(
        "--max-items",
        type=int,
        help="Maximum number of items to process",
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Number of items to process per batch",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show queue statistics and exit",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = IngestConfig(config_path=args.config)
    logger.info("Configuration loaded")
    
    # Build components
    logger.info("Building components...")
    connectors = build_connectors(config)
    storage_writers = build_storage_writers(config)
    state_store = build_state_store(config)
    discovery_plugins = build_discovery_plugins(config)
    
    logger.info(f"Connectors: {list(connectors.keys())}")
    logger.info(f"Storage writers: {[w.get_name() for w in storage_writers]}")
    logger.info(f"Discovery plugins: {[p.get_name() for p in discovery_plugins]}")
    
    # Create runner
    runner_config = config.get_runner_config()
    runner = IngestRunner(
        state_store=state_store,
        connectors=connectors,
        storage_writers=storage_writers,
        discovery_plugins=discovery_plugins,
        max_retries=runner_config.get("max_retries", 3),
        enable_discovery=runner_config.get("enable_discovery", True),
    )
    
    try:
        # Show stats mode
        if args.stats:
            stats = runner.get_stats()
            logger.info("Queue statistics:")
            logger.info(f"  Queue: {stats['queue']}")
            return 0
        
        # Seed queue
        if args.seed:
            logger.info("Seeding queue...")
            seed_items = create_seed_work_items(config)
            enqueued = runner.seed_queue(seed_items)
            logger.info(f"Seeded {enqueued} items")
            
            if not args.max_items and not args.batch_size:
                # Just seeding, not running
                return 0
        
        # Run ingestion
        batch_size = args.batch_size or runner_config.get("batch_size", 10)
        max_items = args.max_items or runner_config.get("max_items")
        
        logger.info("Starting ingestion run...")
        metrics = runner.run(
            batch_size=batch_size,
            max_items=max_items,
        )
        
        logger.info("Run complete!")
        logger.info(f"Final metrics: {metrics}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    finally:
        runner.close()


if __name__ == "__main__":
    sys.exit(main())
