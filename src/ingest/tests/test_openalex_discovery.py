#!/usr/bin/env python3
"""
Unit tests for OpenAlexDiscovery.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.discovery.openalex_discovery import OpenAlexDiscovery
from ingest.discovery.entity_matcher import EntityMatcher
from ingest.core.models import WorkItem, IngestRecord


class TestOpenAlexDiscovery(unittest.TestCase):
    """Test cases for OpenAlexDiscovery."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create entity matcher with known entities
        self.entity_matcher = EntityMatcher(
            known_entities=["Star Wars", "Machine Learning"],
            known_identifiers={
                "doi": {"10.1234/known"},
                "openalex_id": {"W111111111"},
            },
            case_sensitive=False,
        )
        
        self.discovery = OpenAlexDiscovery(
            entity_matcher=self.entity_matcher,
            max_depth=1,
            discover_references=True,
            discover_related=False,
        )
    
    def test_initialization(self):
        """Test discovery initialization."""
        self.assertEqual(self.discovery.max_depth, 1)
        self.assertTrue(self.discovery.discover_references)
        self.assertFalse(self.discovery.discover_related)
        self.assertEqual(self.discovery.get_name(), "openalex")
    
    def test_discover_references_from_single_work(self):
        """Test discovering references from a single work response."""
        # Create parent work item (seed, depth 0)
        parent = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            metadata={"depth": 0},
        )
        
        # Create ingest record with referenced works
        # NOTE: Work must match a known entity to have references discovered
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
                "title": "Star Wars: A Study",  # Matches known entity "Star Wars"
                "referenced_works": [
                    "https://openalex.org/W111111111",
                    "https://openalex.org/W222222222",
                    "https://openalex.org/W333333333",
                ],
            },
            fetched_at_utc=datetime.now(timezone.utc),
        )
        
        # Discover new work items
        discovered = self.discovery.discover(record, parent)
        
        # Should discover 3 referenced works
        self.assertEqual(len(discovered), 3)
        
        # Verify first discovered item
        item = discovered[0]
        self.assertEqual(item.source_system, "openalex")
        self.assertEqual(item.resource_type, "work")
        self.assertEqual(item.resource_id, "W111111111")
        self.assertEqual(item.metadata["depth"], 1)
        self.assertEqual(item.metadata["discovered_via"], "references")
        self.assertEqual(item.discovered_from, parent.work_item_id)
    
    def test_discover_filters_non_matching_entities(self):
        """Test that works not matching entities don't have references discovered."""
        parent = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            metadata={"depth": 0},
        )
        
        # Work that doesn't match any known entity
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
                "title": "Unrelated Biology Paper",  # Doesn't match known entities
                "referenced_works": [
                    "https://openalex.org/W111111111",
                    "https://openalex.org/W222222222",
                ],
            },
            fetched_at_utc=datetime.now(timezone.utc),
        )
        
        discovered = self.discovery.discover(record, parent)
        
        # Should discover no works because parent doesn't match entities
        self.assertEqual(len(discovered), 0)
    
    def test_discover_no_references(self):
        """Test discovery when no references are present."""
        parent = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            metadata={"depth": 0},
        )
        
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
                "title": "Star Wars Analysis",  # Matches known entity
                "referenced_works": [],
            },
            fetched_at_utc=datetime.now(timezone.utc),
        )
        
        discovered = self.discovery.discover(record, parent)
        self.assertEqual(len(discovered), 0)
    
    def test_max_depth_enforcement(self):
        """Test that max depth is enforced."""
        # Create parent at max depth
        parent = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            metadata={"depth": 1},  # At max depth
        )
        
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
                "referenced_works": ["https://openalex.org/W999999999"],
            },
            fetched_at_utc=datetime.now(timezone.utc),
        )
        
        discovered = self.discovery.discover(record, parent)
        
        # Should not discover anything due to max depth
        self.assertEqual(len(discovered), 0)
    
    def test_discover_from_search_results(self):
        """Test discovery from search/list results."""
        parent = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="search",
            resource_id="search_query",
            request_uri="https://api.openalex.org/works?search=test",
            metadata={"depth": 0},
        )
        
        # OpenAlex search results format
        record = IngestRecord(
            ingest_id="test-123",
            source_system="openalex",
            source_name="openalex",
            resource_type="search",
            resource_id="search_query",
            request_uri="https://api.openalex.org/works?search=test",
            request_method="GET",
            status_code=200,
            payload={
                "results": [
                    {
                        "id": "https://openalex.org/W111111111",
                        "title": "Machine Learning Study",  # Matches known entity
                        "referenced_works": [
                            "https://openalex.org/W222222222",
                        ],
                    },
                    {
                        "id": "https://openalex.org/W333333333",
                        "title": "Star Wars Analysis",  # Matches known entity
                        "referenced_works": [
                            "https://openalex.org/W444444444",
                        ],
                    },
                ],
            },
            fetched_at_utc=datetime.now(timezone.utc),
        )
        
        discovered = self.discovery.discover(record, parent)
        
        # Should discover 2 referenced works (1 from each result)
        self.assertEqual(len(discovered), 2)
    
    def test_get_depth_from_metadata(self):
        """Test depth calculation from metadata."""
        work_item = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            metadata={"depth": 2},
        )
        
        depth = self.discovery._get_depth(work_item)
        self.assertEqual(depth, 2)
    
    def test_get_depth_from_discovered_from(self):
        """Test depth calculation when discovered_from is set."""
        work_item = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
            discovered_from="parent-id",
        )
        
        depth = self.discovery._get_depth(work_item)
        self.assertEqual(depth, 1)
    
    def test_get_depth_seed(self):
        """Test depth calculation for seed items."""
        work_item = WorkItem(
            source_system="openalex",
            source_name="openalex",
            resource_type="work",
            resource_id="W123456789",
            request_uri="https://api.openalex.org/works/W123456789",
        )
        
        depth = self.discovery._get_depth(work_item)
        self.assertEqual(depth, 0)
    
    def test_matches_known_entity_by_title(self):
        """Test entity matching by title."""
        work_data = {
            "title": "Star Wars: A New Hope",
            "id": "https://openalex.org/W999999999",
        }
        
        result = self.discovery._matches_known_entity(work_data)
        self.assertTrue(result)
    
    def test_matches_known_entity_by_doi(self):
        """Test entity matching by DOI."""
        work_data = {
            "title": "Random Paper",
            "doi": "https://doi.org/10.1234/known",
            "id": "https://openalex.org/W999999999",
        }
        
        result = self.discovery._matches_known_entity(work_data)
        self.assertTrue(result)
    
    def test_matches_known_entity_by_concepts(self):
        """Test entity matching by concepts."""
        work_data = {
            "title": "Random Paper",
            "id": "https://openalex.org/W999999999",
            "concepts": [
                {"display_name": "Machine Learning"},
                {"display_name": "Neural Networks"},
            ],
        }
        
        result = self.discovery._matches_known_entity(work_data)
        self.assertTrue(result)
    
    def test_no_match_known_entity(self):
        """Test when work doesn't match any known entity."""
        work_data = {
            "title": "Unrelated Paper",
            "id": "https://openalex.org/W999999999",
            "concepts": [
                {"display_name": "Biology"},
            ],
        }
        
        result = self.discovery._matches_known_entity(work_data)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
