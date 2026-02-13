"""
Unit tests for the relationship extraction interrogation.

Tests for:
- Interrogation definition creation
- Schema loading
- Output validation
"""

import pytest
import json
from pathlib import Path

from llm.interrogations.registry import get_registry, get_interrogation
from llm.interrogations.definitions.relationship_extraction import (
    create_relationship_extraction_v1,
    validate_relationship_extraction_output,
    SYSTEM_PROMPT,
    PROMPT_TEMPLATE,
)


class TestRelationshipExtractionDefinition:
    """Tests for relationship_extraction_v1 interrogation definition."""
    
    def test_definition_creation(self):
        """Test that definition is created with correct fields."""
        definition = create_relationship_extraction_v1()
        
        assert definition.key == "relationship_extraction_v1"
        assert definition.name == "Relationship Extraction"
        assert definition.version == "1.0.0"
        assert "relationship" in definition.description.lower()
    
    def test_definition_has_system_prompt(self):
        """Test that definition has a system prompt."""
        definition = create_relationship_extraction_v1()
        
        assert definition.system_prompt is not None
        assert "relationship" in definition.system_prompt.lower()
        assert "JSON" in definition.system_prompt
        assert "confidence" in definition.system_prompt.lower()
    
    def test_definition_has_prompt_template(self):
        """Test that definition has prompt template with placeholders."""
        definition = create_relationship_extraction_v1()
        
        assert definition.prompt_template is not None
        assert "{source_id}" in definition.prompt_template
        assert "{source_page_title}" in definition.prompt_template
        assert "{content}" in definition.prompt_template
    
    def test_definition_has_output_schema(self):
        """Test that definition has output schema."""
        definition = create_relationship_extraction_v1()
        
        schema = definition.output_schema
        assert schema is not None
        assert schema.get("type") == "object"
        assert "relationships" in schema.get("properties", {})
    
    def test_definition_has_validator(self):
        """Test that definition has a validator function."""
        definition = create_relationship_extraction_v1()
        
        assert definition.validator is not None
        assert callable(definition.validator)


class TestRelationshipExtractionRegistry:
    """Tests for relationship_extraction_v1 in the registry."""
    
    def test_registered_in_registry(self):
        """Test that relationship_extraction_v1 is registered."""
        registry = get_registry()
        
        definition = registry.get("relationship_extraction_v1")
        
        assert definition is not None
        assert definition.key == "relationship_extraction_v1"
    
    def test_get_interrogation_convenience(self):
        """Test get_interrogation convenience function."""
        definition = get_interrogation("relationship_extraction_v1")
        
        assert definition is not None
        assert definition.key == "relationship_extraction_v1"


class TestRelationshipExtractionOutputValidation:
    """Tests for relationship extraction output validation."""
    
    def test_valid_output_with_relationships(self):
        """Test validation passes for valid output with relationships."""
        valid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "start_date": "0 ABY",
                    "end_date": None,
                    "work_context": ["A New Hope"],
                    "confidence": 1.0,
                    "evidence_quote": "R2-D2 belonged to Luke Skywalker",
                    "bidirectional": False
                }
            ],
            "entities_referenced": [
                {"name": "R2-D2", "type": "Droid", "confidence": 1.0},
                {"name": "Luke Skywalker", "type": "PersonCharacter", "confidence": 1.0}
            ],
            "extraction_metadata": {
                "source_page_title": "R2-D2",
                "total_relationships_found": 1,
                "relationship_types_found": ["owned_by"],
                "extraction_notes": None
            }
        }
        
        errors = validate_relationship_extraction_output(valid_output)
        assert errors == []
    
    def test_valid_output_empty_relationships(self):
        """Test validation passes for output with no relationships."""
        valid_output = {
            "relationships": [],
            "entities_referenced": [],
            "extraction_metadata": {
                "source_page_title": "Test",
                "total_relationships_found": 0,
                "relationship_types_found": [],
                "extraction_notes": "No relationships found"
            }
        }
        
        errors = validate_relationship_extraction_output(valid_output)
        assert errors == []
    
    def test_valid_output_minimal(self):
        """Test validation passes for minimal valid output."""
        minimal_output = {
            "relationships": []
        }
        
        errors = validate_relationship_extraction_output(minimal_output)
        assert errors == []
    
    def test_valid_output_without_optional_fields(self):
        """Test validation passes for relationship without optional fields."""
        valid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "C-3PO",
                    "relation_type": "companion_of",
                    "confidence": 0.9
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(valid_output)
        assert errors == []
    
    def test_invalid_missing_relationships(self):
        """Test validation fails for missing relationships field."""
        invalid_output = {
            "entities_referenced": []
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("relationships" in e for e in errors)
    
    def test_invalid_relationships_not_array(self):
        """Test validation fails when relationships is not an array."""
        invalid_output = {
            "relationships": "not an array"
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("array" in e for e in errors)
    
    def test_invalid_relationship_missing_from_entity(self):
        """Test validation fails for relationship missing from_entity."""
        invalid_output = {
            "relationships": [
                {
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("from_entity" in e for e in errors)
    
    def test_invalid_relationship_missing_to_entity(self):
        """Test validation fails for relationship missing to_entity."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "relation_type": "owned_by",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("to_entity" in e for e in errors)
    
    def test_invalid_relationship_missing_relation_type(self):
        """Test validation fails for relationship missing relation_type."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("relation_type" in e for e in errors)
    
    def test_invalid_relationship_missing_confidence(self):
        """Test validation fails for relationship missing confidence."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by"
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("confidence" in e for e in errors)
    
    def test_invalid_confidence_out_of_range_low(self):
        """Test validation fails for confidence below 0."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": -0.5
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("0.0" in e or "1.0" in e for e in errors)
    
    def test_invalid_confidence_out_of_range_high(self):
        """Test validation fails for confidence above 1."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": 1.5
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("0.0" in e or "1.0" in e for e in errors)
    
    def test_invalid_from_entity_too_long(self):
        """Test validation fails for from_entity exceeding max length."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "X" * 501,  # 501 characters
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("500" in e or "length" in e.lower() for e in errors)
    
    def test_invalid_to_entity_too_long(self):
        """Test validation fails for to_entity exceeding max length."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "X" * 501,  # 501 characters
                    "relation_type": "owned_by",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("500" in e or "length" in e.lower() for e in errors)
    
    def test_invalid_relation_type_too_long(self):
        """Test validation fails for relation_type exceeding max length."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "X" * 101,  # 101 characters
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("100" in e or "length" in e.lower() for e in errors)
    
    def test_invalid_work_context_not_array(self):
        """Test validation fails when work_context is not an array."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": 1.0,
                    "work_context": "A New Hope"  # Should be array
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("work_context" in e and "array" in e for e in errors)
    
    def test_invalid_bidirectional_not_boolean(self):
        """Test validation fails when bidirectional is not boolean."""
        invalid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "C-3PO",
                    "relation_type": "companion_of",
                    "confidence": 1.0,
                    "bidirectional": "yes"  # Should be boolean
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("bidirectional" in e and "boolean" in e for e in errors)
    
    def test_invalid_entities_referenced_missing_name(self):
        """Test validation fails for entities_referenced missing name."""
        invalid_output = {
            "relationships": [],
            "entities_referenced": [
                {"type": "Droid", "confidence": 1.0}
            ]
        }
        
        errors = validate_relationship_extraction_output(invalid_output)
        assert len(errors) > 0
        assert any("name" in e for e in errors)
    
    def test_valid_multiple_relationships(self):
        """Test validation passes for multiple relationships."""
        valid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "served",
                    "confidence": 1.0
                },
                {
                    "from_entity": "C-3PO",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "served",
                    "confidence": 0.9
                },
                {
                    "from_entity": "R2-D2",
                    "to_entity": "C-3PO",
                    "relation_type": "companion_of",
                    "confidence": 1.0,
                    "bidirectional": True
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(valid_output)
        assert errors == []
    
    def test_valid_temporal_bounds(self):
        """Test validation passes for relationships with temporal bounds."""
        valid_output = {
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Padmé Amidala",
                    "relation_type": "owned_by",
                    "start_date": "32 BBY",
                    "end_date": "19 BBY",
                    "confidence": 1.0
                }
            ]
        }
        
        errors = validate_relationship_extraction_output(valid_output)
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
        assert "0.7" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_relationship_type_guidance(self):
        """Test that system prompt has relationship type examples."""
        assert "owned_by" in SYSTEM_PROMPT
        assert "served" in SYSTEM_PROMPT or "member_of" in SYSTEM_PROMPT
        assert "companion_of" in SYSTEM_PROMPT or "friend_of" in SYSTEM_PROMPT
    
    def test_system_prompt_has_temporal_guidance(self):
        """Test that system prompt has temporal bound guidance."""
        assert "start_date" in SYSTEM_PROMPT.lower()
        assert "end_date" in SYSTEM_PROMPT.lower()
        assert "temporal" in SYSTEM_PROMPT.lower() or "time" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_work_context_guidance(self):
        """Test that system prompt has work context guidance."""
        assert "work_context" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_examples(self):
        """Test that system prompt contains few-shot examples."""
        assert "Example 1" in SYSTEM_PROMPT or "example" in SYSTEM_PROMPT.lower()
        assert "R2-D2" in SYSTEM_PROMPT
    
    def test_prompt_template_placeholders(self):
        """Test that prompt template has required placeholders."""
        required_placeholders = [
            "{source_id}",
            "{source_page_title}",
            "{content}"
        ]
        for placeholder in required_placeholders:
            assert placeholder in PROMPT_TEMPLATE, f"Missing placeholder: {placeholder}"


class TestContractSchemaFile:
    """Tests for the relationship extraction contract schema file."""
    
    @pytest.fixture
    def schema_path(self):
        """Get path to the schema file."""
        return Path(__file__).parent.parent.parent.parent / "src" / "llm" / "contracts" / "relationship_extraction_v1_output.json"
    
    def test_schema_file_exists(self, schema_path):
        """Test that schema file exists."""
        assert schema_path.exists(), f"Schema file not found at {schema_path}"
    
    def test_schema_is_valid_json(self, schema_path):
        """Test that schema file contains valid JSON."""
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        assert isinstance(schema, dict)
    
    def test_schema_has_required_fields(self, schema_path):
        """Test that schema has required top-level fields."""
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        assert "$schema" in schema
        assert "title" in schema
        assert "type" in schema
        assert schema["type"] == "object"
        assert "required" in schema
        assert "relationships" in schema["required"]
    
    def test_schema_relationships_structure(self, schema_path):
        """Test that schema defines relationships array correctly."""
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        props = schema.get("properties", {})
        assert "relationships" in props
        
        rel_schema = props["relationships"]
        assert rel_schema.get("type") == "array"
        assert "items" in rel_schema
        
        item_schema = rel_schema["items"]
        assert "from_entity" in item_schema.get("properties", {})
        assert "to_entity" in item_schema.get("properties", {})
        assert "relation_type" in item_schema.get("properties", {})
        assert "confidence" in item_schema.get("properties", {})
    
    def test_schema_supports_temporal_bounds(self, schema_path):
        """Test that schema supports temporal bounds."""
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        rel_items = schema.get("properties", {}).get("relationships", {}).get("items", {})
        rel_props = rel_items.get("properties", {})
        
        assert "start_date" in rel_props
        assert "end_date" in rel_props
    
    def test_schema_supports_work_context(self, schema_path):
        """Test that schema supports work context."""
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        rel_items = schema.get("properties", {}).get("relationships", {}).get("items", {})
        rel_props = rel_items.get("properties", {})
        
        assert "work_context" in rel_props
        assert rel_props["work_context"].get("type") == "array"
