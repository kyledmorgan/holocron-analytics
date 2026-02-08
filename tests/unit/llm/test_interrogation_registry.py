"""
Unit tests for the interrogation registry.

Tests for:
- Registry registration and lookup
- Built-in interrogation definitions
- Schema loading and validation
"""

import pytest

from llm.interrogations.registry import (
    InterrogationRegistry,
    InterrogationDefinition,
    get_registry,
    get_interrogation,
)


class TestInterrogationDefinition:
    """Tests for InterrogationDefinition dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        definition = InterrogationDefinition(
            key="test_v1",
            name="Test Interrogation",
            version="1.0.0",
            description="A test interrogation",
            prompt_template="Extract {entity_type} from {evidence_content}",
            output_schema={"type": "object"},
        )
        
        assert definition.key == "test_v1"
        assert definition.version == "1.0.0"
        assert definition.system_prompt is None
        assert definition.recommended_temperature == 0.0
    
    def test_get_schema_for_ollama(self):
        """Test schema retrieval for Ollama."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        definition = InterrogationDefinition(
            key="test",
            name="Test",
            version="1.0",
            description="Test",
            prompt_template="test",
            output_schema=schema,
        )
        
        ollama_schema = definition.get_schema_for_ollama()
        assert ollama_schema == schema
    
    def test_validate_output_no_validator(self):
        """Test validation with no validator returns empty list."""
        definition = InterrogationDefinition(
            key="test",
            name="Test",
            version="1.0",
            description="Test",
            prompt_template="test",
            output_schema={},
        )
        
        errors = definition.validate_output({"any": "data"})
        assert errors == []
    
    def test_validate_output_with_validator(self):
        """Test validation with custom validator."""
        def validator(data):
            errors = []
            if "required_field" not in data:
                errors.append("Missing required_field")
            return errors
        
        definition = InterrogationDefinition(
            key="test",
            name="Test",
            version="1.0",
            description="Test",
            prompt_template="test",
            output_schema={},
            validator=validator,
        )
        
        # Valid data
        errors = definition.validate_output({"required_field": "value"})
        assert errors == []
        
        # Invalid data
        errors = definition.validate_output({"other": "value"})
        assert len(errors) == 1
        assert "required_field" in errors[0]


class TestInterrogationRegistry:
    """Tests for InterrogationRegistry."""
    
    def test_empty_registry(self):
        """Test empty registry."""
        registry = InterrogationRegistry()
        # Force load to happen by calling list_keys
        keys = registry.list_keys()
        # Should have built-in interrogations
        assert isinstance(keys, list)
    
    def test_register_and_get(self):
        """Test registering and retrieving a definition."""
        registry = InterrogationRegistry()
        
        definition = InterrogationDefinition(
            key="custom_v1",
            name="Custom",
            version="1.0",
            description="Custom interrogation",
            prompt_template="test",
            output_schema={},
        )
        
        registry.register(definition)
        
        retrieved = registry.get("custom_v1")
        assert retrieved is not None
        assert retrieved.key == "custom_v1"
    
    def test_get_not_found(self):
        """Test getting non-existent definition."""
        registry = InterrogationRegistry()
        
        result = registry.get("nonexistent_key")
        assert result is None
    
    def test_list_keys(self):
        """Test listing all keys."""
        registry = InterrogationRegistry()
        
        # Register a custom one
        definition = InterrogationDefinition(
            key="list_test_v1",
            name="List Test",
            version="1.0",
            description="Test",
            prompt_template="test",
            output_schema={},
        )
        registry.register(definition)
        
        keys = registry.list_keys()
        assert "list_test_v1" in keys


class TestBuiltinInterrogations:
    """Tests for built-in interrogation definitions."""
    
    def test_sw_entity_facts_v1_exists(self):
        """Test that sw_entity_facts_v1 is registered."""
        registry = get_registry()
        
        definition = registry.get("sw_entity_facts_v1")
        
        assert definition is not None
        assert definition.key == "sw_entity_facts_v1"
        assert definition.name == "Star Wars Entity Facts"
        assert definition.version == "1.0.0"
    
    def test_sw_entity_facts_v1_has_prompt_template(self):
        """Test that sw_entity_facts_v1 has a prompt template."""
        definition = get_interrogation("sw_entity_facts_v1")
        
        assert definition is not None
        assert "{entity_type}" in definition.prompt_template
        assert "{entity_id}" in definition.prompt_template
        assert "{evidence_content}" in definition.prompt_template
    
    def test_sw_entity_facts_v1_has_schema(self):
        """Test that sw_entity_facts_v1 has an output schema."""
        definition = get_interrogation("sw_entity_facts_v1")
        
        assert definition is not None
        schema = definition.output_schema
        
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "entity_type" in schema["properties"]
        assert "entity_id" in schema["properties"]
        assert "facts" in schema["properties"]
    
    def test_sw_entity_facts_v1_has_system_prompt(self):
        """Test that sw_entity_facts_v1 has a system prompt."""
        definition = get_interrogation("sw_entity_facts_v1")
        
        assert definition is not None
        assert definition.system_prompt is not None
        assert "Star Wars" in definition.system_prompt
    
    def test_sw_entity_facts_v1_has_validator(self):
        """Test that sw_entity_facts_v1 has a validator."""
        definition = get_interrogation("sw_entity_facts_v1")
        
        assert definition is not None
        assert definition.validator is not None
        
        # Test validator with valid data
        valid_data = {
            "entity_type": "character",
            "entity_id": "luke",
            "facts": []
        }
        errors = definition.validate_output(valid_data)
        assert errors == []
        
        # Test validator with invalid data
        invalid_data = {
            "entity_id": "luke",
            "facts": []
        }
        errors = definition.validate_output(invalid_data)
        assert len(errors) > 0
    
    def test_page_classification_v1_exists(self):
        """Test that page_classification_v1 is registered."""
        registry = get_registry()
        
        definition = registry.get("page_classification_v1")
        
        assert definition is not None
        assert definition.key == "page_classification_v1"
        assert definition.name == "Page Classification"
        assert definition.version == "1.1.0"
    
    def test_page_classification_v1_has_type_key_block(self):
        """Test that page_classification_v1 includes TYPE KEY controlled vocabulary."""
        definition = get_interrogation("page_classification_v1")
        
        assert definition is not None
        assert definition.system_prompt is not None
        
        # Verify TYPE KEY block is present
        assert "TYPE KEY (Controlled Vocabulary)" in definition.system_prompt
        
        # Verify all primary types are defined with descriptions
        required_types = [
            "PersonCharacter:",
            "Droid:",
            "Species:",
            "LocationPlace:",
            "VehicleCraft:",
            "ObjectItem:",
            "WorkMedia:",
            "EventConflict:",
            "Organization:",
            "Concept:",
            "TimePeriod:",
            "ReferenceMeta:",
            "TechnicalSitePage:",
            "Unknown:",
        ]
        for type_name in required_types:
            assert type_name in definition.system_prompt, f"Missing type definition: {type_name}"
        
        # Verify DECISION RULES are present
        assert "DECISION RULES" in definition.system_prompt
        
        # Verify key decision rules for new types are present
        assert "droid" in definition.system_prompt.lower() and "model" in definition.system_prompt.lower()
        assert "ReferenceMeta" in definition.system_prompt or "disambiguation" in definition.system_prompt
    
    def test_page_classification_v1_schema_has_correct_types(self):
        """Test that page_classification_v1 schema has updated type enum."""
        definition = get_interrogation("page_classification_v1")
        
        assert definition is not None
        
        types = definition.output_schema["properties"]["primary_type"]["enum"]
        
        # Verify new types are present
        assert "Droid" in types
        assert "VehicleCraft" in types
        assert "ObjectItem" in types
        assert "ReferenceMeta" in types
        assert "ObjectArtifact" in types
        assert "Unknown" in types
        
        # Verify renamed/removed types
        assert "MetaReference" not in types
        assert "Other" not in types
        assert "Technology" not in types
        assert "Vehicle" not in types
        assert "Weapon" not in types
    
    def test_page_classification_v1_validator(self):
        """Test that page_classification_v1 validator works with new types."""
        definition = get_interrogation("page_classification_v1")
        
        assert definition is not None
        assert definition.validator is not None
        
        # Test valid data with new types
        test_cases = [
            ("Droid", "Named droid individual"),
            ("VehicleCraft", "Named starship with specifications"),
            ("ObjectItem", "Lightsaber weapon"),
            ("ReferenceMeta", "List of Star Wars films"),
            ("ObjectArtifact", "Named vessel"),
        ]
        
        for primary_type, rationale in test_cases:
            valid_data = {
                "primary_type": primary_type,
                "confidence_score": 0.9,
                "needs_review": False,
                "rationale": rationale
            }
            errors = definition.validate_output(valid_data)
            assert errors == [], f"Validation failed for {primary_type}: {errors}"
        
        # Test valid data with Unknown (replacement for Other)
        valid_data_unknown = {
            "primary_type": "Unknown",
            "confidence_score": 0.5,
            "needs_review": True,
            "rationale": "Unclear classification"
        }
        errors = definition.validate_output(valid_data_unknown)
        assert errors == []
        
        # Test invalid data with old type (should fail)
        invalid_data = {
            "primary_type": "Other",  # Old type, no longer valid
            "confidence_score": 0.5,
            "needs_review": True,
            "rationale": "test"
        }
        errors = definition.validate_output(invalid_data)
        assert len(errors) > 0
        assert "Invalid primary_type" in errors[0]


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_registry_singleton(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2
    
    def test_get_interrogation_convenience(self):
        """Test get_interrogation convenience function."""
        definition = get_interrogation("sw_entity_facts_v1")
        
        assert definition is not None
        assert definition.key == "sw_entity_facts_v1"
    
    def test_get_interrogation_not_found(self):
        """Test get_interrogation with non-existent key."""
        definition = get_interrogation("does_not_exist")
        
        assert definition is None
