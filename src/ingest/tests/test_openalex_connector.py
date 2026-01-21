#!/usr/bin/env python3
"""
Unit tests for OpenAlex connector.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.connectors.openalex import OpenAlexConnector
from ingest.core.connector import ConnectorRequest, ConnectorResponse


class TestOpenAlexConnector(unittest.TestCase):
    """Test cases for OpenAlexConnector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connector = OpenAlexConnector(
            email="test@example.com",
            rate_limit_delay=0.0,  # No delay for testing
        )
    
    def test_initialization(self):
        """Test connector initialization."""
        self.assertEqual(self.connector.get_name(), "openalex")
        self.assertEqual(self.connector.email, "test@example.com")
    
    def test_initialization_without_email(self):
        """Test connector initialization without email."""
        connector = OpenAlexConnector(rate_limit_delay=0.0)
        self.assertIsNone(connector.email)
        self.assertEqual(connector.get_name(), "openalex")
    
    @patch('ingest.connectors.openalex.openalex_connector.HttpConnector.fetch')
    def test_fetch_adds_email_to_params(self, mock_fetch):
        """Test that email is added to request params."""
        # Setup mock
        mock_fetch.return_value = ConnectorResponse(
            status_code=200,
            payload={"id": "W123456"},
        )
        
        # Create request without email
        request = ConnectorRequest(
            uri="https://api.openalex.org/works/W123456",
            method="GET",
        )
        
        # Fetch
        response = self.connector.fetch(request)
        
        # Verify mock was called
        self.assertTrue(mock_fetch.called)
        
        # Check that the request passed to parent had email added
        called_request = mock_fetch.call_args[0][0]
        self.assertIsNotNone(called_request.params)
        self.assertEqual(called_request.params.get("mailto"), "test@example.com")
    
    @patch('ingest.connectors.openalex.openalex_connector.HttpConnector.fetch')
    def test_fetch_preserves_existing_params(self, mock_fetch):
        """Test that existing params are preserved."""
        # Setup mock
        mock_fetch.return_value = ConnectorResponse(
            status_code=200,
            payload={"results": []},
        )
        
        # Create request with existing params
        request = ConnectorRequest(
            uri="https://api.openalex.org/works",
            method="GET",
            params={"filter": "is_oa:true", "per_page": "25"},
        )
        
        # Fetch
        response = self.connector.fetch(request)
        
        # Check that params were preserved and email was added
        called_request = mock_fetch.call_args[0][0]
        self.assertEqual(called_request.params.get("filter"), "is_oa:true")
        self.assertEqual(called_request.params.get("per_page"), "25")
        self.assertEqual(called_request.params.get("mailto"), "test@example.com")
    
    @patch('ingest.connectors.openalex.openalex_connector.HttpConnector.fetch')
    def test_fetch_without_email(self, mock_fetch):
        """Test fetch when no email is configured."""
        # Create connector without email
        connector = OpenAlexConnector(rate_limit_delay=0.0)
        
        # Setup mock
        mock_fetch.return_value = ConnectorResponse(
            status_code=200,
            payload={"id": "W123456"},
        )
        
        # Create request
        request = ConnectorRequest(
            uri="https://api.openalex.org/works/W123456",
            method="GET",
        )
        
        # Fetch
        response = connector.fetch(request)
        
        # Verify no params were added
        called_request = mock_fetch.call_args[0][0]
        self.assertIsNone(called_request.params)


if __name__ == "__main__":
    unittest.main()
