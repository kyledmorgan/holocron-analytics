"""
Unit tests for the entity extraction droid interrogation.

Tests for:
- Interrogation definition creation
- Schema loading
- Output validation
"""

import pytest
import json
from pathlib import Path

from llm.interrogations.registry import get_registry, get_interrogation
from llm.interrogations.definitions.entity_extraction_droid import (
    create_entity_extraction_droid_v1,
    validate_entity_extraction_output,
    SYSTEM_PROMPT,
    PROMPT_TEMPLATE,
)


class TestEntityExtractionDroidDefinition:
    """Tests for entity_extraction_droid_v1 interrogation definition."""
    
    def test_definition_creation(self):
        """Test that definition is created with correct fields."""
        definition = create_entity_extraction_droid_v1()
        
        assert definition.key == "entity_extraction_droid_v1"
        assert definition.name == "Droid Entity Extraction"
        assert definition.version == "1.0.0"
        assert "droid" in definition.description.lower()
    
    def test_definition_has_system_prompt(self):
        """Test that definition has a system prompt."""
        definition = create_entity_extraction_droid_v1()
        
        assert definition.system_prompt is not None
        assert "Droid" in definition.system_prompt
        assert "JSON" in definition.system_prompt
        assert "confidence" in definition.system_prompt.lower()
    
    def test_definition_has_prompt_template(self):
        """Test that definition has prompt template with placeholders."""
        definition = create_entity_extraction_droid_v1()
        
        assert definition.prompt_template is not None
        assert "{source_id}" in definition.prompt_template
        assert "{source_page_title}" in definition.prompt_template
        assert "{content}" in definition.prompt_template
    
    def test_definition_has_output_schema(self):
        """Test that definition has output schema."""
        definition = create_entity_extraction_droid_v1()
        
        schema = definition.output_schema
        assert schema is not None
        assert schema.get("type") == "object"
        assert "entities" in schema.get("properties", {})
    
    def test_definition_has_validator(self):
        """Test that definition has a validator function."""
        definition = create_entity_extraction_droid_v1()
        
        assert definition.validator is not None
        assert callable(definition.validator)


class TestEntityExtractionDroidRegistry:
    """Tests for entity_extraction_droid_v1 in the registry."""
    
    def test_registered_in_registry(self):
        """Test that entity_extraction_droid_v1 is registered."""
        registry = get_registry()
        
        definition = registry.get("entity_extraction_droid_v1")
        
        assert definition is not None
        assert definition.key == "entity_extraction_droid_v1"
    
    def test_get_interrogation_convenience(self):
        """Test get_interrogation convenience function."""
        definition = get_interrogation("entity_extraction_droid_v1")
        
        assert definition is not None
        assert definition.key == "entity_extraction_droid_v1"


class TestEntityExtractionOutputValidation:
    """Tests for entity extraction output validation."""
    
    def test_valid_output_with_entities(self):
        """Test validation passes for valid output with entities."""
        valid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid",
                    "confidence": 1.0,
                    "aliases": ["Artoo"],
                    "attributes": {"model": "R2-series"},
                    "evidence_quote": "R2-D2, an astromech droid"
                }
            ],
            "relationships": [],
            "extraction_metadata": {
                "source_page_title": "R2-D2",
                "total_entities_found": 1,
                "primary_type_focus": "Droid",
                "extraction_notes": None
            }
        }
        
        errors = validate_entity_extraction_output(valid_output)
        assert errors == []
    
    def test_valid_output_empty_entities(self):
        """Test validation passes for output with no entities."""
        valid_output = {
            "entities": [],
            "relationships": [],
            "extraction_metadata": {
                "source_page_title": "Test",
                "total_entities_found": 0,
                "primary_type_focus": "Droid",
                "extraction_notes": "No droids found"
            }
        }
        
        errors = validate_entity_extraction_output(valid_output)
        assert errors == []
    
    def test_valid_output_minimal(self):
        """Test validation passes for minimal valid output."""
        minimal_output = {
            "entities": []
        }
        
        errors = validate_entity_extraction_output(minimal_output)
        assert errors == []
    
    def test_invalid_missing_entities(self):
        """Test validation fails for missing entities field."""
        invalid_output = {
            "relationships": []
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("entities" in e for e in errors)
    
    def test_invalid_entities_not_array(self):
        """Test validation fails when entities is not an array."""
        invalid_output = {
            "entities": "not an array"
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("array" in e for e in errors)
    
    def test_invalid_entity_missing_name(self):
        """Test validation fails for entity missing name."""
        invalid_output = {
            "entities": [
                {
                    "type": "Droid",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("name" in e for e in errors)
    
    def test_invalid_entity_missing_type(self):
        """Test validation fails for entity missing type."""
        invalid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("type" in e for e in errors)
    
    def test_invalid_entity_missing_confidence(self):
        """Test validation fails for entity missing confidence."""
        invalid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid"
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("confidence" in e for e in errors)
    
    def test_invalid_confidence_out_of_range_low(self):
        """Test validation fails for confidence below 0."""
        invalid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid",
                    "confidence": -0.5
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("0.0" in e or "1.0" in e for e in errors)
    
    def test_invalid_confidence_out_of_range_high(self):
        """Test validation fails for confidence above 1."""
        invalid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid",
                    "confidence": 1.5
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("0.0" in e or "1.0" in e for e in errors)
    
    def test_invalid_name_too_long(self):
        """Test validation fails for name exceeding max length."""
        invalid_output = {
            "entities": [
                {
                    "name": "X" * 501,  # 501 characters
                    "type": "Droid",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("500" in e or "length" in e.lower() for e in errors)
    
    def test_invalid_relationship_missing_fields(self):
        """Test validation fails for relationship missing required fields."""
        invalid_output = {
            "entities": [],
            "relationships": [
                {
                    "from_entity": "R2-D2"
                    # missing to_entity, relation_type
                }
            ]
        }
        
        errors = validate_entity_extraction_output(invalid_output)
        assert len(errors) > 0
    
    def test_valid_relationship(self):
        """Test validation passes for valid relationship."""
        valid_output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid",
                    "confidence": 1.0
                }
            ],
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "served",
                    "start_date": None,
                    "end_date": None,
                    "confidence": 0.9
                }
            ]
        }
        
        errors = validate_entity_extraction_output(valid_output)
        assert errors == []


class TestPromptTemplateContent:
    """Tests for prompt template content and structure."""
    
    def test_system_prompt_has_rules(self):
        """Test that system prompt contains extraction rules."""
        assert "RULES:" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT
        assert "hallucinate" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_confidence_guidance(self):
        """Test that system prompt has confidence scoring guidance."""
        assert "1.0" in SYSTEM_PROMPT
        assert "0.7" in SYSTEM_PROMPT or "0.8" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_examples(self):
        """Test that system prompt contains few-shot examples."""
        assert "Example 1" in SYSTEM_PROMPT or "example" in SYSTEM_PROMPT.lower()
        assert "R2-D2" in SYSTEM_PROMPT
    
    def test_system_prompt_has_attribute_guidance(self):
        """Test that system prompt has droid attribute guidance."""
        assert "model" in SYSTEM_PROMPT.lower()
        assert "manufacturer" in SYSTEM_PROMPT.lower()
        assert "droid_class" in SYSTEM_PROMPT.lower() or "class" in SYSTEM_PROMPT.lower()
    
    def test_prompt_template_placeholders(self):
        """Test that prompt template has required placeholders."""
        required_placeholders = [
            "{source_id}",
            "{source_page_title}",
            "{content}"
        ]
        for placeholder in required_placeholders:
            assert placeholder in PROMPT_TEMPLATE, f"Missing placeholder: {placeholder}"


class TestGoldenSetFixture:
    """Tests for the golden set fixture file."""
    
    @pytest.fixture
    def golden_set(self):
        """Load the golden set fixture."""
        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "droid_extraction_golden_set.json"
        with open(fixture_path, "r") as f:
            return json.load(f)
    
    def test_golden_set_has_test_cases(self, golden_set):
        """Test that golden set has test cases."""
        assert "test_cases" in golden_set
        assert len(golden_set["test_cases"]) >= 5
    
    def test_golden_set_test_case_structure(self, golden_set):
        """Test that each test case has required fields."""
        required_fields = ["id", "name", "intent", "source_page_title", "source_id", "content"]
        
        for case in golden_set["test_cases"]:
            for field in required_fields:
                assert field in case, f"Test case {case.get('id', 'unknown')} missing field: {field}"
    
    def test_golden_set_has_clean_droid_case(self, golden_set):
        """Test that golden set includes clean named droid case."""
        clean_cases = [c for c in golden_set["test_cases"] if "clean" in c["name"].lower()]
        assert len(clean_cases) > 0
    
    def test_golden_set_has_no_droid_case(self, golden_set):
        """Test that golden set includes case with no droids."""
        no_droid_cases = [c for c in golden_set["test_cases"] if c.get("expected_entities", 1) == 0]
        assert len(no_droid_cases) > 0
    
    def test_golden_set_has_vague_reference_case(self, golden_set):
        """Test that golden set includes vague/low confidence case."""
        vague_cases = [c for c in golden_set["test_cases"] if "vague" in c["name"].lower()]
        assert len(vague_cases) > 0
    
    def test_golden_set_has_multiple_entities_case(self, golden_set):
        """Test that golden set includes multiple entities case."""
        multi_cases = [c for c in golden_set["test_cases"] if c.get("expected_entities", 0) > 1]
        assert len(multi_cases) > 0
