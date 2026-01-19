"""
OpenAlex API connector for fetching academic works metadata.

OpenAlex API documentation: https://docs.openalex.org/
"""

import logging
from typing import Optional

from ...connectors.http.http_connector import HttpConnector
from ...core.connector import ConnectorRequest, ConnectorResponse


logger = logging.getLogger(__name__)


class OpenAlexConnector(HttpConnector):
    """
    Connector for the OpenAlex API.
    
    OpenAlex is a free and open catalog of the world's scholarly literature.
    This connector extends the base HTTP connector with OpenAlex-specific
    conventions and best practices.
    
    API documentation: https://docs.openalex.org/
    """
    
    BASE_URL = "https://api.openalex.org"
    
    def __init__(
        self,
        email: Optional[str] = None,
        rate_limit_delay: float = 0.1,  # OpenAlex recommends max 10 req/sec for polite pool
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the OpenAlex connector.
        
        Args:
            email: Email for polite pool access (recommended for faster responses)
            rate_limit_delay: Minimum seconds between requests (default 0.1 = 10 req/sec)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        # Build user agent with email if provided
        user_agent = "HolocronAnalytics/1.0"
        if email:
            user_agent += f" (mailto:{email})"
        
        super().__init__(
            name="openalex",
            rate_limit_delay=rate_limit_delay,
            timeout=timeout,
            max_retries=max_retries,
            user_agent=user_agent,
        )
        
        self.email = email
        logger.info(
            f"Initialized OpenAlex connector"
            f"{' with polite pool access' if email else ''}"
        )
    
    def fetch(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Fetch data from OpenAlex API.
        
        Adds email parameter to requests if configured for polite pool.
        
        Args:
            request: The request to execute
            
        Returns:
            ConnectorResponse with the result
        """
        # If email is configured and not already in params, add it
        if self.email:
            params = request.params or {}
            if "mailto" not in params:
                params["mailto"] = self.email
                # Create new request with updated params
                request = ConnectorRequest(
                    uri=request.uri,
                    method=request.method,
                    headers=request.headers,
                    body=request.body,
                    params=params,
                    metadata=request.metadata,
                )
        
        # Use parent HTTP connector implementation
        return super().fetch(request)
    
    def get_name(self) -> str:
        """Return the connector name."""
        return "openalex"
