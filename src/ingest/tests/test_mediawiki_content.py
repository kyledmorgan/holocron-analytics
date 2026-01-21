#!/usr/bin/env python3
"""
Tests for MediaWiki connector content fetching methods.

Tests the request building logic without making actual API calls.
"""

import sys
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingest.connectors.mediawiki import MediaWikiConnector


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class MockHttpConnector:
    """Mock HTTP connector for testing request building."""
    
    def __init__(self):
        self.last_request = None
        self.last_url = None
    
    def fetch(self, request):
        """Capture the request for verification."""
        from ingest.core.connector import ConnectorResponse
        
        self.last_request = request
        
        # Build full URL with params
        if request.params:
            from urllib.parse import urlencode
            self.last_url = f"{request.uri}?{urlencode(request.params)}"
        else:
            self.last_url = request.uri
        
        # Return a mock successful response
        return ConnectorResponse(
            status_code=200,
            payload={"mock": "response"},
            duration_ms=100,
        )
    
    def close(self):
        pass


def test_fetch_raw_content_by_id():
    """Test building raw content request by page ID."""
    logger.info("Testing fetch_raw_content_by_id...")
    
    connector = MediaWikiConnector(
        name="test",
        api_url="https://test.fandom.com/api.php",
    )
    
    # Replace HTTP connector with mock
    mock_http = MockHttpConnector()
    connector.http = mock_http
    
    # Make the call
    response = connector.fetch_raw_content_by_id(page_id=12345)
    
    # Verify request was built correctly
    assert mock_http.last_request is not None
    assert mock_http.last_request.uri == "https://test.fandom.com/api.php"
    
    params = mock_http.last_request.params
    assert params["action"] == "query"
    assert params["pageids"] == "12345"
    assert params["prop"] == "revisions"
    assert params["rvprop"] == "content"
    assert params["rvslots"] == "main"
    assert params["formatversion"] == "2"
    
    assert response.status_code == 200
    
    logger.info("✓ fetch_raw_content_by_id works correctly")


def test_fetch_html_content_by_id():
    """Test building HTML content request by page ID."""
    logger.info("Testing fetch_html_content_by_id...")
    
    connector = MediaWikiConnector(
        name="test",
        api_url="https://test.fandom.com/api.php",
    )
    
    mock_http = MockHttpConnector()
    connector.http = mock_http
    
    response = connector.fetch_html_content_by_id(page_id=67890)
    
    params = mock_http.last_request.params
    assert params["action"] == "parse"
    assert params["pageid"] == "67890"
    assert params["prop"] == "text"
    assert params["formatversion"] == "2"
    
    assert response.status_code == 200
    
    logger.info("✓ fetch_html_content_by_id works correctly")


def test_fetch_raw_content_by_title():
    """Test building raw content request by title."""
    logger.info("Testing fetch_raw_content...")
    
    connector = MediaWikiConnector(
        name="test",
        api_url="https://test.fandom.com/api.php",
    )
    
    mock_http = MockHttpConnector()
    connector.http = mock_http
    
    response = connector.fetch_raw_content(title="Luke Skywalker")
    
    params = mock_http.last_request.params
    assert params["action"] == "query"
    assert params["titles"] == "Luke Skywalker"
    assert params["prop"] == "revisions"
    assert params["rvprop"] == "content"
    assert params["rvslots"] == "main"
    assert params["formatversion"] == "2"
    
    assert response.status_code == 200
    
    logger.info("✓ fetch_raw_content works correctly")


def test_fetch_html_content_by_title():
    """Test building HTML content request by title."""
    logger.info("Testing fetch_html_content...")
    
    connector = MediaWikiConnector(
        name="test",
        api_url="https://test.fandom.com/api.php",
    )
    
    mock_http = MockHttpConnector()
    connector.http = mock_http
    
    response = connector.fetch_html_content(title="Darth Vader")
    
    params = mock_http.last_request.params
    assert params["action"] == "parse"
    assert params["page"] == "Darth Vader"
    assert params["prop"] == "text"
    assert params["formatversion"] == "2"
    
    assert response.status_code == 200
    
    logger.info("✓ fetch_html_content works correctly")


def main():
    """Run all tests."""
    logger.info("Starting MediaWiki connector content tests...")
    logger.info("=" * 60)
    
    try:
        test_fetch_raw_content_by_id()
        test_fetch_html_content_by_id()
        test_fetch_raw_content_by_title()
        test_fetch_html_content_by_title()
        
        logger.info("=" * 60)
        logger.info("✓ All MediaWiki connector content tests passed!")
        return 0
        
    except Exception as e:
        logger.exception(f"✗ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
