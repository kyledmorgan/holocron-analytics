"""
MediaWiki API connector for fetching data from MediaWiki-based wikis.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..http import HttpConnector
from ...core.connector import Connector, ConnectorRequest, ConnectorResponse


logger = logging.getLogger(__name__)


class MediaWikiConnector(Connector):
    """
    Connector for MediaWiki API.
    
    Supports common MediaWiki API actions:
    - query: Get page content, links, categories, etc.
    - parse: Parse wikitext
    - opensearch: Search functionality
    
    See: https://www.mediawiki.org/wiki/API:Main_page
    """

    def __init__(
        self,
        name: str,
        api_url: str,
        rate_limit_delay: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the MediaWiki connector.
        
        Args:
            name: Connector name (e.g., 'wikipedia', 'wookieepedia')
            api_url: Base API URL (e.g., 'https://en.wikipedia.org/w/api.php')
            rate_limit_delay: Minimum seconds between requests (be polite!)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: Custom User-Agent (important for MediaWiki etiquette)
        """
        self.name = name
        self.api_url = api_url
        
        # Use HTTP connector as the transport layer
        self.http = HttpConnector(
            name=f"mediawiki_{name}",
            rate_limit_delay=rate_limit_delay,
            timeout=timeout,
            max_retries=max_retries,
            user_agent=user_agent or f"HolocronAnalytics/1.0 (MediaWiki; {name})",
        )

    def fetch(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Fetch data from MediaWiki API.
        
        Args:
            request: The request to execute
            
        Returns:
            ConnectorResponse with the result
        """
        # MediaWiki API requests are typically GET with query params
        # We'll delegate to the HTTP connector
        return self.http.fetch(request)

    def fetch_page(
        self,
        titles: List[str],
        props: Optional[List[str]] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Fetch page(s) by title.
        
        Args:
            titles: List of page titles to fetch
            props: Properties to retrieve (e.g., 'content', 'links', 'categories')
            additional_params: Additional API parameters
            
        Returns:
            ConnectorResponse with the result
        """
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(titles),
        }
        
        if props:
            params["prop"] = "|".join(props)
        
        if additional_params:
            params.update(additional_params)
        
        request = ConnectorRequest(
            uri=self.api_url,
            method="GET",
            params=params,
        )
        
        return self.fetch(request)

    def fetch_page_by_id(
        self,
        page_ids: List[int],
        props: Optional[List[str]] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Fetch page(s) by page ID.
        
        Args:
            page_ids: List of page IDs to fetch
            props: Properties to retrieve
            additional_params: Additional API parameters
            
        Returns:
            ConnectorResponse with the result
        """
        params = {
            "action": "query",
            "format": "json",
            "pageids": "|".join(str(pid) for pid in page_ids),
        }
        
        if props:
            params["prop"] = "|".join(props)
        
        if additional_params:
            params.update(additional_params)
        
        request = ConnectorRequest(
            uri=self.api_url,
            method="GET",
            params=params,
        )
        
        return self.fetch(request)

    def search(
        self,
        search_term: str,
        limit: int = 10,
        namespace: Optional[int] = None
    ) -> ConnectorResponse:
        """
        Search for pages using opensearch.
        
        Args:
            search_term: Term to search for
            limit: Maximum results to return
            namespace: Optional namespace filter
            
        Returns:
            ConnectorResponse with the result
        """
        params = {
            "action": "opensearch",
            "format": "json",
            "search": search_term,
            "limit": limit,
        }
        
        if namespace is not None:
            params["namespace"] = namespace
        
        request = ConnectorRequest(
            uri=self.api_url,
            method="GET",
            params=params,
        )
        
        return self.fetch(request)

    def fetch_categories(
        self,
        titles: List[str],
        limit: int = 500
    ) -> ConnectorResponse:
        """
        Fetch categories for page(s).
        
        Args:
            titles: List of page titles
            limit: Maximum categories to return per page
            
        Returns:
            ConnectorResponse with the result
        """
        return self.fetch_page(
            titles=titles,
            props=["categories"],
            additional_params={"cllimit": limit}
        )

    def fetch_links(
        self,
        titles: List[str],
        limit: int = 500
    ) -> ConnectorResponse:
        """
        Fetch links from page(s).
        
        Args:
            titles: List of page titles
            limit: Maximum links to return per page
            
        Returns:
            ConnectorResponse with the result
        """
        return self.fetch_page(
            titles=titles,
            props=["links"],
            additional_params={"pllimit": limit}
        )

    def get_name(self) -> str:
        """Return the connector name."""
        return self.name

    def close(self) -> None:
        """Close the HTTP session."""
        if self.http:
            self.http.close()
