"""
Unit tests for Phase 1 contracts.

Tests for:
- Contract dataclass creation and serialization
- Input/output validation
- JSON schema compliance
"""

import json
import pytest
from datetime import datetime, timezone

from llm.contracts.phase1_contracts import (
    EvidenceSnippet,
    EvidenceBundleV1,
    JobInputEnvelope,
    ExtractedFact,
    EntityFactsOutput,
    Job,
    JobStatus,
    validate_entity_facts_output,
)


class TestEvidenceSnippet:
    """Tests for EvidenceSnippet dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        snippet = EvidenceSnippet(
            evidence_id="e1",
            source_uri="https://example.com/doc",
            text="Luke Skywalker is a Jedi."
        )
        
        assert snippet.evidence_id == "e1"
        assert snippet.source_uri == "https://example.com/doc"
        assert snippet.text == "Luke Skywalker is a Jedi."
        assert snippet.offsets is None
        assert snippet.metadata is None
    
    def test_to_dict(self):
        """Test serialization to dict."""
        snippet = EvidenceSnippet(
            evidence_id="e1",
            source_uri="source",
            text="text content",
            offsets={"start": 0, "end": 100},
            metadata={"page": 1}
        )
        
        d = snippet.to_dict()
        assert d["evidence_id"] == "e1"
        assert d["offsets"] == {"start": 0, "end": 100}
        assert d["metadata"] == {"page": 1}
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "evidence_id": "e2",
            "source_uri": "file://doc.txt",
            "text": "Some text",
            "offsets": {"start": 10, "end": 50}
        }
        
        snippet = EvidenceSnippet.from_dict(data)
        assert snippet.evidence_id == "e2"
        assert snippet.offsets == {"start": 10, "end": 50}


class TestEvidenceBundleV1:
    """Tests for EvidenceBundleV1 dataclass."""
    
    def test_empty_bundle(self):
        """Test creation of empty bundle."""
        bundle = EvidenceBundleV1()
        
        assert len(bundle.snippets) == 0
        assert bundle.bundle_id is not None
        assert bundle.created_utc is not None
    
    def test_bundle_with_snippets(self):
        """Test bundle with multiple snippets."""
        snippets = [
            EvidenceSnippet("e1", "source1", "text1"),
            EvidenceSnippet("e2", "source2", "text2"),
        ]
        bundle = EvidenceBundleV1(snippets=snippets)
        
        assert len(bundle.snippets) == 2
    
    def test_to_dict(self):
        """Test serialization."""
        snippet = EvidenceSnippet("e1", "source", "text")
        bundle = EvidenceBundleV1(snippets=[snippet], bundle_id="test-bundle")
        
        d = bundle.to_dict()
        assert d["bundle_id"] == "test-bundle"
        assert len(d["snippets"]) == 1
        assert "created_utc" in d


class TestJobInputEnvelope:
    """Tests for JobInputEnvelope dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        envelope = JobInputEnvelope(
            entity_type="character",
            entity_id="luke_skywalker",
            source_refs=["ref1", "ref2"]
        )
        
        assert envelope.entity_type == "character"
        assert envelope.entity_id == "luke_skywalker"
        assert len(envelope.source_refs) == 2
    
    def test_to_json(self):
        """Test JSON serialization."""
        envelope = JobInputEnvelope(
            entity_type="planet",
            entity_id="tatooine"
        )
        
        json_str = envelope.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["entity_type"] == "planet"
        assert parsed["entity_id"] == "tatooine"
        assert parsed["source_refs"] == []
    
    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = '{"entity_type": "starship", "entity_id": "falcon", "source_refs": ["a"]}'
        
        envelope = JobInputEnvelope.from_json(json_str)
        
        assert envelope.entity_type == "starship"
        assert envelope.entity_id == "falcon"
        assert envelope.source_refs == ["a"]


class TestExtractedFact:
    """Tests for ExtractedFact dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        fact = ExtractedFact(
            fact_key="species",
            value="Human",
            confidence=1.0,
            evidence_ids=["e1"]
        )
        
        assert fact.fact_key == "species"
        assert fact.value == "Human"
        assert fact.confidence == 1.0
        assert fact.unit is None
    
    def test_with_unit(self):
        """Test fact with unit."""
        fact = ExtractedFact(
            fact_key="birth_year",
            value=19,
            confidence=0.9,
            evidence_ids=["e1"],
            unit="BBY"
        )
        
        d = fact.to_dict()
        assert d["unit"] == "BBY"
    
    def test_null_value(self):
        """Test fact with null value (not found)."""
        fact = ExtractedFact(
            fact_key="death_year",
            value=None,
            confidence=0.0,
            evidence_ids=[],
            notes="Not found in evidence"
        )
        
        assert fact.value is None
        assert fact.confidence == 0.0


class TestEntityFactsOutput:
    """Tests for EntityFactsOutput dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        facts = [
            ExtractedFact("name", "Luke Skywalker", 1.0, ["e1"]),
            ExtractedFact("species", "Human", 0.9, ["e1"]),
        ]
        
        output = EntityFactsOutput(
            entity_type="character",
            entity_id="luke_skywalker",
            entity_name="Luke Skywalker",
            facts=facts
        )
        
        assert output.entity_type == "character"
        assert len(output.facts) == 2
    
    def test_to_json(self):
        """Test JSON serialization."""
        output = EntityFactsOutput(
            entity_type="character",
            entity_id="test",
            entity_name="Test",
            facts=[]
        )
        
        json_str = output.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["entity_type"] == "character"
        assert parsed["facts"] == []


class TestValidateEntityFactsOutput:
    """Tests for validate_entity_facts_output function."""
    
    def test_valid_output(self):
        """Test validation of valid output."""
        data = {
            "entity_type": "character",
            "entity_id": "luke",
            "entity_name": "Luke Skywalker",
            "facts": [
                {
                    "fact_key": "species",
                    "value": "Human",
                    "confidence": 1.0,
                    "evidence_ids": ["e1"]
                }
            ]
        }
        
        errors = validate_entity_facts_output(data)
        assert errors == []
    
    def test_missing_entity_type(self):
        """Test missing required field."""
        data = {
            "entity_id": "luke",
            "facts": []
        }
        
        errors = validate_entity_facts_output(data)
        assert any("entity_type" in e for e in errors)
    
    def test_missing_entity_id(self):
        """Test missing entity_id."""
        data = {
            "entity_type": "character",
            "facts": []
        }
        
        errors = validate_entity_facts_output(data)
        assert any("entity_id" in e for e in errors)
    
    def test_missing_facts(self):
        """Test missing facts array."""
        data = {
            "entity_type": "character",
            "entity_id": "luke"
        }
        
        errors = validate_entity_facts_output(data)
        assert any("facts" in e for e in errors)
    
    def test_facts_not_array(self):
        """Test facts not being an array."""
        data = {
            "entity_type": "character",
            "entity_id": "luke",
            "facts": "not an array"
        }
        
        errors = validate_entity_facts_output(data)
        assert any("array" in e for e in errors)
    
    def test_invalid_confidence(self):
        """Test confidence out of range."""
        data = {
            "entity_type": "character",
            "entity_id": "luke",
            "facts": [
                {
                    "fact_key": "test",
                    "value": "value",
                    "confidence": 1.5,  # Out of range
                    "evidence_ids": []
                }
            ]
        }
        
        errors = validate_entity_facts_output(data)
        assert any("confidence" in e for e in errors)
    
    def test_empty_facts_valid(self):
        """Test that empty facts array is valid."""
        data = {
            "entity_type": "character",
            "entity_id": "luke",
            "facts": []
        }
        
        errors = validate_entity_facts_output(data)
        assert errors == []


class TestJob:
    """Tests for Job dataclass."""
    
    def test_from_row(self):
        """Test creating Job from database row."""
        row = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "created_utc": datetime.now(timezone.utc),
            "status": "NEW",
            "priority": 100,
            "interrogation_key": "sw_entity_facts_v1",
            "input_json": '{"entity_type": "character", "entity_id": "luke"}',
            "evidence_ref_json": None,
            "model_hint": "llama3.2",
            "max_attempts": 3,
            "attempt_count": 0,
            "available_utc": datetime.now(timezone.utc),
            "locked_by": None,
            "locked_utc": None,
            "last_error": None
        }
        
        job = Job.from_row(row)
        
        assert job.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert job.status == JobStatus.NEW
        assert job.interrogation_key == "sw_entity_facts_v1"
    
    def test_get_input(self):
        """Test parsing input_json."""
        job = Job(
            job_id="test",
            interrogation_key="test",
            input_json='{"entity_type": "planet", "entity_id": "tatooine", "source_refs": []}'
        )
        
        envelope = job.get_input()
        
        assert envelope.entity_type == "planet"
        assert envelope.entity_id == "tatooine"
    
    def test_get_evidence_refs_null(self):
        """Test getting null evidence refs."""
        job = Job(
            job_id="test",
            interrogation_key="test",
            input_json='{}',
            evidence_ref_json=None
        )
        
        refs = job.get_evidence_refs()
        assert refs is None
    
    def test_get_evidence_refs(self):
        """Test getting evidence refs."""
        job = Job(
            job_id="test",
            interrogation_key="test",
            input_json='{}',
            evidence_ref_json='["file1.txt", "file2.txt"]'
        )
        
        refs = job.get_evidence_refs()
        assert refs == ["file1.txt", "file2.txt"]
