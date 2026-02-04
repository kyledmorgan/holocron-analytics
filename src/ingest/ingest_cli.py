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
from ingest.connectors import HttpConnector, MediaWikiConnector, OpenAlexConnector
from ingest.storage import FileLakeWriter, SqlServerIngestWriter
from ingest.state import create_state_store
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
    logger = logging.getLogger(__name__)
    connectors = {}
    
    for source_config in config.get_sources():
        source_type = source_config.get("type")
        source_name = source_config.get("name")
        
        if not source_type:
            logger.warning(f"Skipping source '{source_name}': missing 'type' field")
            continue
        
        if not source_name:
            logger.warning(f"Skipping source with type '{source_type}': missing 'name' field")
            continue
        
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
            logger.info(f"Built connector: {source_name} ({source_type})")
        
        elif source_type == "http":
            connector = HttpConnector(
                name=source_name,
                rate_limit_delay=source_config.get("rate_limit_delay", 0.0),
                timeout=source_config.get("timeout", 30),
                max_retries=source_config.get("max_retries", 3),
                user_agent=source_config.get("user_agent"),
            )
            connectors["http"] = connector
            logger.info(f"Built connector: {source_name} ({source_type})")
        
        elif source_type == "openalex":
            connector = OpenAlexConnector(
                email=source_config.get("email"),
                rate_limit_delay=source_config.get("rate_limit_delay", 0.1),
                timeout=source_config.get("timeout", 30),
                max_retries=source_config.get("max_retries", 3),
            )
            connectors["openalex"] = connector
            logger.info(f"Built connector: {source_name} ({source_type})")
        
        else:
            logger.warning(
                f"Skipping source '{source_name}': unknown type '{source_type}'. "
                f"Supported types: mediawiki, http, openalex"
            )
    
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


def build_state_store(config: IngestConfig):
    """Build state store from configuration."""
    import os
    
    state_config = config.get_state_config()
    
    # Determine backend from config or environment
    backend = os.environ.get("DB_BACKEND", state_config.get("type", "sqlserver"))
    
    if backend != "sqlserver":
        raise ValueError(
            f"SQLite backend has been removed. Only 'sqlserver' backend is supported. "
            f"Set DB_BACKEND=sqlserver and configure SQL Server connection parameters."
        )
    
    # SQL Server configuration
    sql_config = state_config.get("sqlserver", {})
    
    return create_state_store(
        backend="sqlserver",
        connection_string=os.environ.get("INGEST_SQLSERVER_STATE_CONN_STR"),
        host=sql_config.get("host", os.environ.get("INGEST_SQLSERVER_HOST", "localhost")),
        port=int(sql_config.get("port", os.environ.get("INGEST_SQLSERVER_PORT", "1433"))),
        database=sql_config.get("database", os.environ.get("INGEST_SQLSERVER_DATABASE", "Holocron")),
        username=sql_config.get("user", os.environ.get("INGEST_SQLSERVER_USER", "sa")),
        password=os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD"),
        driver=sql_config.get("driver", os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")),
        schema=sql_config.get("schema", "ingest"),
    )


def build_discovery_plugins(config: IngestConfig) -> list:
    """Build discovery plugins from configuration."""
    logger = logging.getLogger(__name__)
    plugins = []
    
    for source_config in config.get_sources():
        source_type = source_config.get("type")
        source_name = source_config.get("name")
        discovery_config = source_config.get("discovery", {})
        
        if not discovery_config.get("enabled", True):
            logger.debug(f"Discovery disabled for source '{source_name}'")
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
            logger.info(f"Built discovery plugin: {source_name} (mediawiki)")
        
        elif source_type == "openalex":
            # Build entity matcher for controlled expansion
            entity_config = source_config.get("entity_matching", {})
            entities = entity_config.get("entities", [])
            identifiers = entity_config.get("identifiers", {})
            case_sensitive = entity_config.get("case_sensitive", False)
            
            entity_matcher = EntityMatcher(
                known_entities=entities,
                known_identifiers=identifiers,
                case_sensitive=case_sensitive,
            )
            
            plugin = OpenAlexDiscovery(
                entity_matcher=entity_matcher,
                max_depth=discovery_config.get("max_depth", 1),
                discover_references=discovery_config.get("discover_references", True),
                discover_related=discovery_config.get("discover_related", False),
            )
            plugins.append(plugin)
            logger.info(
                f"Built discovery plugin: {source_name} (openalex) "
                f"with {len(entities)} entity filters, max_depth={discovery_config.get('max_depth', 1)}"
            )
    
    return plugins


def create_seed_work_items(config: IngestConfig) -> list:
    """Create initial work items from seed configuration."""
    logger = logging.getLogger(__name__)
    work_items = []
    
    for seed_config in config.get_seeds():
        source_name = seed_config.get("source")
        resource_type = seed_config.get("resource_type", "page")
        priority = seed_config.get("priority", 10)
        
        if not source_name:
            logger.warning("Skipping seed: missing 'source' field")
            continue
        
        # Find the source configuration
        source_config = None
        for src in config.get_sources():
            if src.get("name") == source_name:
                source_config = src
                break
        
        if not source_config:
            logger.warning(f"Skipping seed: source '{source_name}' not found in sources config")
            continue
        
        source_type = source_config.get("type")
        
        # Handle MediaWiki seeds
        if source_type == "mediawiki":
            titles = seed_config.get("titles", [])
            if not titles:
                logger.warning(f"Skipping MediaWiki seed for '{source_name}': no 'titles' provided")
                continue
            
            for title in titles:
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
                logger.debug(f"Created MediaWiki seed: {title}")
        
        # Handle OpenAlex seeds
        elif source_type == "openalex":
            if resource_type == "search":
                # Search seed - create a work item for the search query
                search_query = seed_config.get("search_query")
                if not search_query:
                    logger.warning(f"Skipping OpenAlex search seed for '{source_name}': no 'search_query' provided")
                    continue
                
                from urllib.parse import urlencode, quote
                filters = seed_config.get("filters", [])
                per_page = seed_config.get("per_page", 25)
                
                # Build OpenAlex search URL
                filter_str = ",".join(filters) if filters else ""
                params = {
                    "search": search_query,
                    "per-page": per_page,
                }
                if filter_str:
                    params["filter"] = filter_str
                
                base_url = "https://api.openalex.org/works"
                request_uri = f"{base_url}?{urlencode(params)}"
                
                work_item = WorkItem(
                    source_system="openalex",
                    source_name=source_name,
                    resource_type="search",
                    resource_id=f"search:{search_query}",
                    request_uri=request_uri,
                    request_method="GET",
                    priority=priority,
                    metadata={
                        "seed": True,
                        "search_query": search_query,
                        "filters": filters,
                    },
                )
                work_items.append(work_item)
                logger.info(f"Created OpenAlex search seed: '{search_query}' with {len(filters)} filters")
            
            elif resource_type == "work":
                # Work ID seed - create work items for specific work IDs
                work_ids = seed_config.get("work_ids", [])
                dois = seed_config.get("dois", [])
                
                if not work_ids and not dois:
                    logger.warning(f"Skipping OpenAlex work seed for '{source_name}': no 'work_ids' or 'dois' provided")
                    continue
                
                # Handle work IDs
                for work_id in work_ids:
                    # Ensure ID has proper format (W1234567890)
                    if not work_id.startswith("W"):
                        work_id = f"W{work_id}"
                    
                    request_uri = f"https://api.openalex.org/works/{work_id}"
                    
                    work_item = WorkItem(
                        source_system="openalex",
                        source_name=source_name,
                        resource_type="work",
                        resource_id=work_id,
                        request_uri=request_uri,
                        request_method="GET",
                        priority=priority,
                        metadata={"seed": True},
                    )
                    work_items.append(work_item)
                    logger.debug(f"Created OpenAlex work seed: {work_id}")
                
                # Handle DOIs
                for doi in dois:
                    # DOIs are looked up via the works endpoint with filter
                    from urllib.parse import quote
                    encoded_doi = quote(doi, safe="")
                    request_uri = f"https://api.openalex.org/works/doi:{encoded_doi}"
                    
                    work_item = WorkItem(
                        source_system="openalex",
                        source_name=source_name,
                        resource_type="work",
                        resource_id=f"doi:{doi}",
                        request_uri=request_uri,
                        request_method="GET",
                        priority=priority,
                        metadata={"seed": True, "doi": doi},
                    )
                    work_items.append(work_item)
                    logger.debug(f"Created OpenAlex DOI seed: {doi}")
            
            else:
                logger.warning(
                    f"Skipping OpenAlex seed for '{source_name}': unknown resource_type '{resource_type}'. "
                    f"Supported types: search, work"
                )
        
        else:
            logger.warning(
                f"Skipping seed for '{source_name}': source type '{source_type}' seed creation not implemented. "
                f"Supported types: mediawiki, openalex"
            )
    
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
