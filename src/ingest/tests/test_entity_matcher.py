#!/usr/bin/env python3
"""
Unit tests for EntityMatcher.
"""

import sys
import unittest
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.discovery.entity_matcher import EntityMatcher


class TestEntityMatcher(unittest.TestCase):
    """Test cases for EntityMatcher."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.matcher = EntityMatcher(
            known_entities=["Star Wars", "Star Trek", "Machine Learning"],
            known_identifiers={
                "doi": {"10.1234/example", "10.5678/another"},
                "openalex_id": {"W123456789", "W987654321"},
            },
            case_sensitive=False,
        )
    
    def test_initialization(self):
        """Test matcher initialization."""
        self.assertEqual(len(self.matcher.known_entities), 3)
        self.assertEqual(len(self.matcher.known_identifiers["doi"]), 2)
    
    def test_match_by_title_exact(self):
        """Test exact title match."""
        result = self.matcher.matches_entity(title="Star Wars")
        self.assertTrue(result)
    
    def test_match_by_title_substring(self):
        """Test substring match in title."""
        result = self.matcher.matches_entity(title="The Star Wars Saga")
        self.assertTrue(result)
    
    def test_match_by_title_case_insensitive(self):
        """Test case-insensitive title match."""
        result = self.matcher.matches_entity(title="star wars")
        self.assertTrue(result)
    
    def test_no_match_by_title(self):
        """Test no match when title doesn't match."""
        result = self.matcher.matches_entity(title="Random Paper")
        self.assertFalse(result)
    
    def test_match_by_doi(self):
        """Test match by DOI identifier."""
        result = self.matcher.matches_entity(
            identifiers={"doi": "10.1234/example"}
        )
        self.assertTrue(result)
    
    def test_match_by_openalex_id(self):
        """Test match by OpenAlex ID."""
        result = self.matcher.matches_entity(
            identifiers={"openalex_id": "W123456789"}
        )
        self.assertTrue(result)
    
    def test_no_match_by_identifier(self):
        """Test no match when identifier doesn't match."""
        result = self.matcher.matches_entity(
            identifiers={"doi": "10.9999/unknown"}
        )
        self.assertFalse(result)
    
    def test_match_by_concepts(self):
        """Test match by concepts."""
        result = self.matcher.matches_entity(
            concepts=["Machine Learning", "Deep Learning"]
        )
        self.assertTrue(result)
    
    def test_no_match_by_concepts(self):
        """Test no match when concepts don't match."""
        result = self.matcher.matches_entity(
            concepts=["Biology", "Chemistry"]
        )
        self.assertFalse(result)
    
    def test_match_multiple_criteria(self):
        """Test match with multiple criteria."""
        result = self.matcher.matches_entity(
            title="A Study on Star Trek",
            identifiers={"doi": "10.9999/unknown"},
            concepts=["Space Exploration"],
        )
        self.assertTrue(result)  # Should match on title
    
    def test_add_entity_runtime(self):
        """Test adding entity at runtime."""
        self.matcher.add_entity("Lord of the Rings")
        result = self.matcher.matches_entity(title="Lord of the Rings")
        self.assertTrue(result)
    
    def test_add_identifier_runtime(self):
        """Test adding identifier at runtime."""
        self.matcher.add_identifier("doi", "10.1111/new")
        result = self.matcher.matches_entity(
            identifiers={"doi": "10.1111/new"}
        )
        self.assertTrue(result)
    
    def test_case_sensitive_matching(self):
        """Test case-sensitive matching."""
        matcher = EntityMatcher(
            known_entities=["Star Wars"],
            case_sensitive=True,
        )
        
        # Should match exact case
        self.assertTrue(matcher.matches_entity(title="Star Wars"))
        
        # Should not match different case
        self.assertFalse(matcher.matches_entity(title="star wars"))
    
    def test_from_config(self):
        """Test creating matcher from config."""
        config = {
            "entities": ["Star Wars", "Star Trek"],
            "identifiers": {
                "doi": ["10.1234/example"],
                "openalex_id": ["W123456789"],
            },
            "case_sensitive": False,
        }
        
        matcher = EntityMatcher.from_config(config)
        
        self.assertEqual(len(matcher.known_entities), 2)
        self.assertTrue(matcher.matches_entity(title="Star Wars"))
        self.assertTrue(matcher.matches_entity(
            identifiers={"doi": "10.1234/example"}
        ))


if __name__ == "__main__":
    unittest.main()
