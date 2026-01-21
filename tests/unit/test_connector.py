"""
Unit tests for the test connector.

These tests verify the test connector functionality without external dependencies.
"""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ingest.connectors.test_connector import (
    TestConnector,
    create_test_work_items,
    SYNTHETIC_RESOURCES,
)
from ingest.core.connector import ConnectorRequest


class TestTestConnector:
    """Tests for TestConnector."""
    
    def test_connector_initialization(self):
        """Test connector initializes with default resources."""
        connector = TestConnector()
        
        assert connector.get_name() == "test"
        assert len(connector.resources) == len(SYNTHETIC_RESOURCES)
    
    def test_connector_fetch_success(self):
        """Test successful fetch returns expected data."""
        connector = TestConnector()
        
        request = ConnectorRequest(
            uri="https://test.example.com/resources/test_resource_001",
            method="GET",
        )
        
        response = connector.fetch(request)
        
        assert response.status_code == 200
        assert "resource" in response.payload
        assert response.payload["resource"]["id"] == "test_resource_001"
    
    def test_connector_fetch_not_found(self):
        """Test fetch for non-existent resource returns 404."""
        connector = TestConnector()
        
        request = ConnectorRequest(
            uri="https://test.example.com/resources/nonexistent",
            method="GET",
        )
        
        response = connector.fetch(request)
        
        assert response.status_code == 404
        assert "error" in response.payload
    
    def test_connector_simulated_error(self):
        """Test simulated errors for specific resource IDs."""
        connector = TestConnector(error_resource_ids=["test_resource_001"])
        
        request = ConnectorRequest(
            uri="https://test.example.com/resources/test_resource_001",
            method="GET",
        )
        
        response = connector.fetch(request)
        
        assert response.status_code == 500
        assert response.error_message is not None
    
    def test_connector_request_history(self):
        """Test request history is tracked."""
        connector = TestConnector()
        
        request1 = ConnectorRequest(uri="/resources/test_resource_001", method="GET")
        request2 = ConnectorRequest(uri="/resources/test_resource_002", method="GET")
        
        connector.fetch(request1)
        connector.fetch(request2)
        
        assert len(connector.request_history) == 2
    
    def test_connector_reset(self):
        """Test reset clears request history."""
        connector = TestConnector()
        
        request = ConnectorRequest(uri="/resources/test_resource_001", method="GET")
        connector.fetch(request)
        
        assert len(connector.request_history) == 1
        
        connector.reset()
        
        assert len(connector.request_history) == 0
    
    def test_connector_custom_resources(self):
        """Test connector with custom resources."""
        custom_resources = [
            {"id": "custom_001", "title": "Custom Resource", "type": "custom"},
        ]
        
        connector = TestConnector(custom_resources=custom_resources)
        
        assert len(connector.resources) == 1
        
        request = ConnectorRequest(uri="/resources/custom_001", method="GET")
        response = connector.fetch(request)
        
        assert response.status_code == 200
        assert response.payload["resource"]["id"] == "custom_001"
    
    def test_get_seed_work_items(self):
        """Test generating seed work items."""
        connector = TestConnector()
        
        work_items = connector.get_seed_work_items(
            source_name="test_source",
            priority=50,
        )
        
        assert len(work_items) == len(SYNTHETIC_RESOURCES)
        
        for item in work_items:
            assert item.source_system == "test"
            assert item.source_name == "test_source"
            assert item.priority == 50


class TestCreateTestWorkItems:
    """Tests for create_test_work_items helper function."""
    
    def test_create_default_count(self):
        """Test creating default number of work items."""
        items = create_test_work_items()
        
        assert len(items) == 5
    
    def test_create_custom_count(self):
        """Test creating custom number of work items."""
        items = create_test_work_items(count=10)
        
        assert len(items) == 10
    
    def test_work_item_ids_are_predictable(self):
        """Test that work item resource IDs are predictable."""
        items = create_test_work_items(count=3)
        
        assert items[0].resource_id == "test_resource_000"
        assert items[1].resource_id == "test_resource_001"
        assert items[2].resource_id == "test_resource_002"
    
    def test_custom_source_name(self):
        """Test custom source name."""
        items = create_test_work_items(source_name="custom_source")
        
        for item in items:
            assert item.source_name == "custom_source"
