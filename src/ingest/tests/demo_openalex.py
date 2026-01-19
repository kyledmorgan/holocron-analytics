#!/usr/bin/env python3
"""
OpenAlex integration demonstration script.

This script shows how to use the OpenAlex connector and discovery
components to fetch and process academic works.
"""

import sys
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from ingest.connectors.openalex import OpenAlexConnector
from ingest.discovery.openalex_discovery import OpenAlexDiscovery
from ingest.discovery.entity_matcher import EntityMatcher
from ingest.core.models import WorkItem, IngestRecord
from ingest.core.connector import ConnectorRequest
from ingest.state import SqliteStateStore
from ingest.storage import FileLakeWriter
from ingest.runner import IngestRunner


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def demo_basic_fetch():
    """Demonstrate basic work fetching."""
    logger.info("=" * 60)
    logger.info("Demo 1: Basic OpenAlex Work Fetch")
    logger.info("=" * 60)
    
    # Create connector
    connector = OpenAlexConnector(rate_limit_delay=0.0)  # No delay for demo
    
    # Fetch a specific work
    work_id = "W2741809807"  # Example work
    request = ConnectorRequest(
        uri=f"https://api.openalex.org/works/{work_id}",
        method="GET",
    )
    
    logger.info(f"Fetching work: {work_id}")
    response = connector.fetch(request)
    
    if response.status_code == 200:
        payload = response.payload
        logger.info(f"✓ Successfully fetched work")
        logger.info(f"  Title: {payload.get('title', 'N/A')}")
        logger.info(f"  Year: {payload.get('publication_year', 'N/A')}")
        logger.info(f"  DOI: {payload.get('doi', 'N/A')}")
        logger.info(f"  Referenced works: {len(payload.get('referenced_works', []))}")
        logger.info(f"  Cited by: {payload.get('cited_by_count', 0)}")
    else:
        logger.error(f"✗ Failed to fetch work: {response.error_message}")
    
    return response


def demo_entity_matching():
    """Demonstrate entity matching."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Demo 2: Entity Matching")
    logger.info("=" * 60)
    
    # Create entity matcher
    matcher = EntityMatcher(
        known_entities=["Machine Learning", "Artificial Intelligence"],
        known_identifiers={
            "openalex_id": {"W2741809807"},
        },
        case_sensitive=False,
    )
    
    # Test various matching scenarios
    test_cases = [
        {
            "title": "Deep Learning for Natural Language Processing",
            "concepts": ["Machine Learning", "NLP"],
            "expected": True,
        },
        {
            "title": "A Study of Quantum Computing",
            "concepts": ["Physics", "Computing"],
            "expected": False,
        },
        {
            "identifiers": {"openalex_id": "W2741809807"},
            "expected": True,
        },
        {
            "title": "Biology Research",
            "concepts": ["Biology"],
            "expected": False,
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        result = matcher.matches_entity(**{k: v for k, v in test.items() if k != "expected"})
        expected = test["expected"]
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} Test {i}: {result} (expected {expected})")


def demo_discovery():
    """Demonstrate reference discovery."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Demo 3: Reference Discovery")
    logger.info("=" * 60)
    
    # Create components
    entity_matcher = EntityMatcher(
        known_entities=["Machine Learning", "Neural Networks", "Deep Learning"],
        case_sensitive=False,
    )
    
    discovery = OpenAlexDiscovery(
        entity_matcher=entity_matcher,
        max_depth=1,
        discover_references=True,
    )
    
    # Create a mock parent work item
    parent = WorkItem(
        source_system="openalex",
        source_name="openalex",
        resource_type="work",
        resource_id="W123456789",
        request_uri="https://api.openalex.org/works/W123456789",
        metadata={"depth": 0},
    )
    
    # Create a mock ingest record with references
    record = IngestRecord(
        ingest_id="test-123",
        source_system="openalex",
        source_name="openalex",
        resource_type="work",
        resource_id="W123456789",
        request_uri="https://api.openalex.org/works/W123456789",
        request_method="GET",
        status_code=200,
        payload={
            "id": "https://openalex.org/W123456789",
            "title": "Example ML Paper",
            "referenced_works": [
                "https://openalex.org/W111111111",
                "https://openalex.org/W222222222",
                "https://openalex.org/W333333333",
            ],
        },
        fetched_at_utc=datetime.now(timezone.utc),
    )
    
    # Discover new work items
    discovered = discovery.discover(record, parent)
    
    logger.info(f"Discovered {len(discovered)} referenced works")
    for item in discovered:
        logger.info(f"  - {item.resource_id} (depth={item.metadata['depth']})")


def demo_full_pipeline():
    """Demonstrate full ingestion pipeline with OpenAlex."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Demo 4: Full Ingestion Pipeline (Dry Run)")
    logger.info("=" * 60)
    
    # Use temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Setup components
        state_store = SqliteStateStore(db_path=tmp_path / "state.db")
        connector = OpenAlexConnector(rate_limit_delay=0.0)
        file_writer = FileLakeWriter(base_dir=tmp_path / "data_lake")
        
        entity_matcher = EntityMatcher(
            known_entities=["Machine Learning"],
            case_sensitive=False,
        )
        
        discovery_plugin = OpenAlexDiscovery(
            entity_matcher=entity_matcher,
            max_depth=0,  # No discovery for demo
        )
        
        # Create runner
        runner = IngestRunner(
            state_store=state_store,
            connectors={"openalex": connector},
            storage_writers=[file_writer],
            discovery_plugins=[discovery_plugin],
            enable_discovery=False,  # Disabled for demo
        )
        
        # Seed with a work
        work_item = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W2741809807",
            request_uri="https://api.openalex.org/works/W2741809807",
            priority=10,
            metadata={"depth": 0},
        )
        
        logger.info("Seeding queue with 1 work...")
        runner.seed_queue([work_item])
        
        logger.info("Running ingestion (1 item)...")
        metrics = runner.run(batch_size=1, max_items=1)
        
        logger.info("Ingestion complete!")
        logger.info(f"  Items processed: {metrics['items_processed']}")
        logger.info(f"  Items succeeded: {metrics['items_succeeded']}")
        logger.info(f"  Items failed: {metrics['items_failed']}")
        
        # Check data lake
        data_lake_files = list((tmp_path / "data_lake").rglob("*.json"))
        logger.info(f"  Data lake files: {len(data_lake_files)}")
        
        if data_lake_files:
            logger.info(f"  Example file: {data_lake_files[0].relative_to(tmp_path)}")
            with open(data_lake_files[0]) as f:
                content = json.load(f)
                logger.info(f"  Stored work: {content['resource_id']}")
        
        runner.close()


def main():
    """Run all demonstrations."""
    logger.info("OpenAlex Integration Demonstration")
    logger.info("")
    
    try:
        # Run demos
        demo_basic_fetch()
        demo_entity_matching()
        demo_discovery()
        demo_full_pipeline()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ All demonstrations completed successfully!")
        logger.info("=" * 60)
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nDemonstration interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"✗ Demonstration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
