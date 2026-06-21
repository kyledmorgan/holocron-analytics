"""
Unit tests for the job type registry.

Tests for:
- JobTypeDefinition creation and methods
- JobTypeRegistry registration and lookup
- Built-in job type definitions
"""

import pytest

from llm.jobs.registry import (
    JobTypeDefinition,
    JobTypeRegistry,
    get_job_type_registry,
    get_job_type,
    register_job_type,
)


class TestJobTypeDefinition:
    """Tests for JobTypeDefinition dataclass."""
    
    def test_creation(self):
        """Test basic creation."""
        definition = JobTypeDefinition(
            job_type="test_job",
            display_name="Test Job",
            interrogation_key="test_v1",
            handler_ref="src.llm.handlers.test.handle",
        )
        
        assert definition.job_type == "test_job"
        assert definition.display_name == "Test Job"
        assert definition.interrogation_key == "test_v1"
        assert definition.handler_ref == "src.llm.handlers.test.handle"
        # Check defaults
        assert definition.max_attempts == 3
        assert definition.default_priority == 100
        assert definition.timeout_seconds == 300
        assert definition.version is None
        assert definition.description is None
        assert definition.tags == []
    
    def test_creation_with_all_fields(self):
        """Test creation with all optional fields."""
        definition = JobTypeDefinition(
            job_type="full_job",
            display_name="Full Job",
            interrogation_key="full_v1",
            handler_ref="src.llm.handlers.full.handle",
            max_attempts=5,
            default_priority=200,
            timeout_seconds=600,
            version="2.0.0",
            description="A fully configured job type",
            tags=["test", "full"],
        )
        
        assert definition.max_attempts == 5
        assert definition.default_priority == 200
        assert definition.timeout_seconds == 600
        assert definition.version == "2.0.0"
        assert definition.description == "A fully configured job type"
        assert definition.tags == ["test", "full"]
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        definition = JobTypeDefinition(
            job_type="test_job",
            display_name="Test Job",
            interrogation_key="test_v1",
            handler_ref="src.llm.handlers.test.handle",
            version="1.0.0",
            tags=["test"],
        )
        
        result = definition.to_dict()
        
        assert result["job_type"] == "test_job"
        assert result["display_name"] == "Test Job"
        assert result["interrogation_key"] == "test_v1"
        assert result["handler_ref"] == "src.llm.handlers.test.handle"
        assert result["version"] == "1.0.0"
        assert result["tags"] == ["test"]
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "job_type": "test_job",
            "display_name": "Test Job",
            "interrogation_key": "test_v1",
            "handler_ref": "src.llm.handlers.test.handle",
            "max_attempts": 5,
            "tags": ["test"],
        }
        
        definition = JobTypeDefinition.from_dict(data)
        
        assert definition.job_type == "test_job"
        assert definition.max_attempts == 5
        assert definition.tags == ["test"]
    
    def test_get_interrogation_existing(self):
        """Test getting interrogation for known key."""
        definition = JobTypeDefinition(
            job_type="page_class",
            display_name="Page Classification",
            interrogation_key="page_classification_v1",
            handler_ref="src.llm.handlers.page_classification.handle",
        )
        
        interrogation = definition.get_interrogation()
        
        assert interrogation is not None
        assert interrogation.key == "page_classification_v1"
    
    def test_get_interrogation_missing(self):
        """Test getting interrogation for unknown key."""
        definition = JobTypeDefinition(
            job_type="unknown",
            display_name="Unknown",
            interrogation_key="nonexistent_v1",
            handler_ref="src.llm.handlers.unknown.handle",
        )
        
        interrogation = definition.get_interrogation()
        
        assert interrogation is None


class TestJobTypeRegistry:
    """Tests for JobTypeRegistry."""
    
    def test_empty_registry_loads_builtins(self):
        """Test that empty registry loads built-in definitions."""
        registry = JobTypeRegistry()
        
        types = registry.list_types()
        
        assert isinstance(types, list)
        assert len(types) >= 2  # page_classification and sw_entity_facts
    
    def test_register_and_get(self):
        """Test registering and retrieving a definition."""
        registry = JobTypeRegistry()
        
        definition = JobTypeDefinition(
            job_type="custom_v1",
            display_name="Custom",
            interrogation_key="custom_v1",
            handler_ref="src.llm.handlers.custom.handle",
        )
        
        registry.register(definition)
        
        retrieved = registry.get("custom_v1")
        assert retrieved is not None
        assert retrieved.job_type == "custom_v1"
    
    def test_get_not_found(self):
        """Test getting non-existent definition."""
        registry = JobTypeRegistry()
        
        result = registry.get("nonexistent_type")
        assert result is None
    
    def test_list_types(self):
        """Test listing all job types."""
        registry = JobTypeRegistry()
        
        # Register a custom one
        definition = JobTypeDefinition(
            job_type="list_test_v1",
            display_name="List Test",
            interrogation_key="list_test_v1",
            handler_ref="test.handle",
        )
        registry.register(definition)
        
        types = registry.list_types()
        assert "list_test_v1" in types
    
    def test_list_definitions(self):
        """Test listing all definitions."""
        registry = JobTypeRegistry()
        
        definitions = registry.list_definitions()
        
        assert isinstance(definitions, list)
        assert all(isinstance(d, JobTypeDefinition) for d in definitions)


class TestBuiltinJobTypes:
    """Tests for built-in job type definitions."""
    
    def test_page_classification_exists(self):
        """Test that page_classification is registered."""
        registry = get_job_type_registry()
        
        definition = registry.get("page_classification")
        
        assert definition is not None
        assert definition.job_type == "page_classification"
        assert definition.display_name == "Page Classification"
        assert definition.interrogation_key == "page_classification_v1"
    
    def test_page_classification_has_valid_interrogation(self):
        """Test that page_classification points to valid interrogation."""
        definition = get_job_type("page_classification")
        
        assert definition is not None
        interrogation = definition.get_interrogation()
        
        assert interrogation is not None
        assert interrogation.key == "page_classification_v1"
    
    def test_sw_entity_facts_exists(self):
        """Test that sw_entity_facts is registered."""
        registry = get_job_type_registry()
        
        definition = registry.get("sw_entity_facts")
        
        assert definition is not None
        assert definition.job_type == "sw_entity_facts"
        assert definition.interrogation_key == "sw_entity_facts_v1"
    
    def test_sw_entity_facts_has_valid_interrogation(self):
        """Test that sw_entity_facts points to valid interrogation."""
        definition = get_job_type("sw_entity_facts")
        
        assert definition is not None
        interrogation = definition.get_interrogation()
        
        assert interrogation is not None
        assert interrogation.key == "sw_entity_facts_v1"


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_job_type_registry_singleton(self):
        """Test that get_job_type_registry returns same instance."""
        # Note: Due to global state, we can't perfectly test singleton
        # but we can verify it returns a registry
        registry = get_job_type_registry()
        
        assert isinstance(registry, JobTypeRegistry)
    
    def test_get_job_type_convenience(self):
        """Test get_job_type convenience function."""
        definition = get_job_type("page_classification")
        
        assert definition is not None
        assert definition.job_type == "page_classification"
    
    def test_get_job_type_not_found(self):
        """Test get_job_type with non-existent type."""
        definition = get_job_type("does_not_exist")
        
        assert definition is None
    
    def test_register_job_type(self):
        """Test register_job_type convenience function."""
        definition = JobTypeDefinition(
            job_type="convenience_test",
            display_name="Convenience Test",
            interrogation_key="test_v1",
            handler_ref="test.handle",
        )
        
        register_job_type(definition)
        
        retrieved = get_job_type("convenience_test")
        assert retrieved is not None
        assert retrieved.job_type == "convenience_test"
