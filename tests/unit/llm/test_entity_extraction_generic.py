"""
Unit tests for generic entity extraction (Phase 3).

Tests:
- Interrogation definition creation
- Output validation
- Handler initialization
- Job type registration
"""

import json
import pytest

from src.llm.interrogations.definitions.entity_extraction_generic import (
    create_entity_extraction_generic_v1,
    validate_entity_extraction_generic_output,
    SYSTEM_PROMPT,
    PROMPT_TEMPLATE,
)
from src.llm.interrogations.registry import get_interrogation
from src.llm.jobs.registry import get_job_type


class TestInterrogationDefinition:
    """Tests for the entity_extraction_generic_v1 interrogation definition."""
    
    def test_creation(self):
        """Test that interrogation definition can be created."""
        definition = create_entity_extraction_generic_v1()
        
        assert definition.key == "entity_extraction_generic_v1"
        assert definition.name == "Generic Entity Extraction"
        assert definition.version == "1.0.0"
        assert "Phase 3" in definition.description
    
    def test_system_prompt_contains_entity_types(self):
        """Test that system prompt mentions key entity types."""
        assert "PersonCharacter" in SYSTEM_PROMPT
        assert "LocationPlace" in SYSTEM_PROMPT
        assert "Organization" in SYSTEM_PROMPT
        assert "VehicleCraft" in SYSTEM_PROMPT
        assert "Droid" in SYSTEM_PROMPT
        assert "Concept" in SYSTEM_PROMPT
    
    def test_system_prompt_confidence_guidance(self):
        """Test that system prompt has confidence scoring guidance."""
        assert "1.0" in SYSTEM_PROMPT  # explicitly named
        assert "0.7-0.9" in SYSTEM_PROMPT  # strongly implied
        assert "0.4-0.6" in SYSTEM_PROMPT  # weakly implied
    
    def test_prompt_template_has_placeholders(self):
        """Test that prompt template has required placeholders."""
        assert "{source_page_title}" in PROMPT_TEMPLATE
        assert "{source_id}" in PROMPT_TEMPLATE
        assert "{content}" in PROMPT_TEMPLATE
    
    def test_output_schema_is_valid(self):
        """Test that output schema is valid JSON schema."""
        definition = create_entity_extraction_generic_v1()
        schema = definition.output_schema
        
        assert schema.get("type") == "object"
        assert "entities" in schema.get("required", [])
        assert "entities" in schema.get("properties", {})
    
    def test_registry_integration(self):
        """Test that interrogation is registered in global registry."""
        definition = get_interrogation("entity_extraction_generic_v1")
        
        assert definition is not None
        assert definition.key == "entity_extraction_generic_v1"
    
    def test_validator_is_attached(self):
        """Test that validator function is attached to definition."""
        definition = create_entity_extraction_generic_v1()
        
        assert definition.validator is not None
        assert callable(definition.validator)


class TestOutputValidation:
    """Tests for the validate_entity_extraction_generic_output function."""
    
    def test_valid_minimal_output(self):
        """Test validation of minimal valid output."""
        output = {
            "entities": []
        }
        errors = validate_entity_extraction_generic_output(output)
        assert errors == []
    
    def test_valid_single_entity(self):
        """Test validation of output with one entity."""
        output = {
            "entities": [
                {
                    "name": "Luke Skywalker",
                    "type": "PersonCharacter",
                    "confidence": 1.0
                }
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert errors == []
    
    def test_valid_full_entity(self):
        """Test validation of entity with all optional fields."""
        output = {
            "entities": [
                {
                    "name": "Luke Skywalker",
                    "type": "PersonCharacter",
                    "confidence": 0.9,
                    "aliases": ["Skywalker", "Red Five"],
                    "attributes": {"homeworld": "Tatooine"},
                    "evidence_quote": "Luke was born on Tatooine",
                    "temporal_context": "0 BBY - 34 ABY",
                    "work_references": ["A New Hope", "The Empire Strikes Back"]
                }
            ],
            "relationships": [
                {
                    "from_entity": "Luke Skywalker",
                    "to_entity": "Rebel Alliance",
                    "relation_type": "member_of",
                    "start_date": "0 BBY",
                    "end_date": None,
                    "confidence": 0.95
                }
            ],
            "extraction_metadata": {
                "source_page_title": "Luke Skywalker",
                "total_entities_found": 1,
                "entity_types_found": ["PersonCharacter"],
                "primary_type_focus": None,
                "extraction_notes": "Main character extraction"
            }
        }
        errors = validate_entity_extraction_generic_output(output)
        assert errors == []
    
    def test_missing_entities_field(self):
        """Test validation fails when entities field missing."""
        output = {}
        errors = validate_entity_extraction_generic_output(output)
        assert "Missing required field: entities" in errors
    
    def test_entities_not_array(self):
        """Test validation fails when entities is not an array."""
        output = {"entities": "not an array"}
        errors = validate_entity_extraction_generic_output(output)
        assert "entities must be an array" in errors
    
    def test_entity_missing_name(self):
        """Test validation fails when entity missing name."""
        output = {
            "entities": [
                {"type": "Droid", "confidence": 0.8}
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("Missing required field: name" in e for e in errors)
    
    def test_entity_missing_type(self):
        """Test validation fails when entity missing type."""
        output = {
            "entities": [
                {"name": "R2-D2", "confidence": 1.0}
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("Missing required field: type" in e for e in errors)
    
    def test_entity_missing_confidence(self):
        """Test validation fails when entity missing confidence."""
        output = {
            "entities": [
                {"name": "R2-D2", "type": "Droid"}
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("Missing required field: confidence" in e for e in errors)
    
    def test_confidence_out_of_range_high(self):
        """Test validation fails when confidence > 1.0."""
        output = {
            "entities": [
                {"name": "R2-D2", "type": "Droid", "confidence": 1.5}
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("between 0.0 and 1.0" in e for e in errors)
    
    def test_confidence_out_of_range_low(self):
        """Test validation fails when confidence < 0.0."""
        output = {
            "entities": [
                {"name": "R2-D2", "type": "Droid", "confidence": -0.1}
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("between 0.0 and 1.0" in e for e in errors)
    
    def test_name_too_long(self):
        """Test validation fails when name exceeds max length."""
        max_name_length = 500
        output = {
            "entities": [
                {
                    "name": "A" * (max_name_length + 1),  # exceeds 500 char limit
                    "type": "Droid",
                    "confidence": 1.0
                }
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("exceeds maximum length" in e for e in errors)
    
    def test_type_too_long(self):
        """Test validation fails when type exceeds max length."""
        max_type_length = 100
        output = {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "T" * (max_type_length + 1),  # exceeds 100 char limit
                    "confidence": 1.0
                }
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("exceeds maximum length" in e for e in errors)
    
    def test_relationship_missing_fields(self):
        """Test validation fails for relationship missing required fields."""
        output = {
            "entities": [],
            "relationships": [
                {"from_entity": "Luke", "to_entity": "Leia"}
                # missing relation_type
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("Missing required field: relation_type" in e for e in errors)
    
    def test_relationship_confidence_validation(self):
        """Test relationship confidence is validated."""
        output = {
            "entities": [],
            "relationships": [
                {
                    "from_entity": "Luke",
                    "to_entity": "Leia",
                    "relation_type": "sibling_of",
                    "confidence": 2.0  # invalid
                }
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        assert any("confidence must be between 0.0 and 1.0" in e for e in errors)
    
    def test_multiple_entities_validated(self):
        """Test that all entities are validated."""
        output = {
            "entities": [
                {"name": "Valid", "type": "Droid", "confidence": 1.0},
                {"name": "Missing Confidence", "type": "Droid"},
            ]
        }
        errors = validate_entity_extraction_generic_output(output)
        # First entity valid, second missing confidence
        assert len(errors) == 1
        assert "entities[1]" in errors[0]


class TestJobTypeRegistration:
    """Tests for job type registration."""
    
    def test_job_type_registered(self):
        """Test that entity_extraction_generic is registered."""
        job_type = get_job_type("entity_extraction_generic")
        
        assert job_type is not None
        assert job_type.job_type == "entity_extraction_generic"
        assert job_type.display_name == "Generic Entity Extraction"
    
    def test_job_type_has_valid_interrogation(self):
        """Test that job type references valid interrogation."""
        job_type = get_job_type("entity_extraction_generic")
        interrogation = job_type.get_interrogation()
        
        assert interrogation is not None
        assert interrogation.key == "entity_extraction_generic_v1"
    
    def test_job_type_has_handler(self):
        """Test that job type has handler reference."""
        job_type = get_job_type("entity_extraction_generic")
        
        assert job_type.handler_ref is not None
        assert "entity_extraction_generic" in job_type.handler_ref
    
    def test_job_type_has_phase3_tag(self):
        """Test that job type has phase3 tag."""
        job_type = get_job_type("entity_extraction_generic")
        
        assert "phase3" in job_type.tags


class TestHandlerIntegration:
    """Tests for handler integration."""
    
    def test_handler_imports(self):
        """Test that handler can be imported."""
        from src.llm.handlers.entity_extraction_generic import (
            EntityExtractionGenericHandler,
            handle,
        )
        
        assert EntityExtractionGenericHandler is not None
        assert handle is not None
    
    def test_handler_creation(self):
        """Test that handler can be instantiated."""
        from src.llm.handlers.entity_extraction_generic import EntityExtractionGenericHandler
        
        handler = EntityExtractionGenericHandler()
        assert handler is not None
    
    def test_handler_interrogation_loaded(self):
        """Test that handler loads interrogation lazily."""
        from src.llm.handlers.entity_extraction_generic import EntityExtractionGenericHandler
        
        handler = EntityExtractionGenericHandler()
        interrogation = handler.interrogation
        
        assert interrogation is not None
        assert interrogation.key == "entity_extraction_generic_v1"
