"""
HTTP connector for raw HTTP fetching and web scraping.
"""

import json
import logging
import time
from typing import Dict, Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    requests = None

from ...core.connector import Connector, ConnectorRequest, ConnectorResponse


logger = logging.getLogger(__name__)


class HttpConnector(Connector):
    """
    Generic HTTP connector for making HTTP requests.
    
    Supports:
    - GET and POST requests
    - Custom headers
    - Rate limiting
    - Retries with exponential backoff
    """

    def __init__(
        self,
        name: str = "http",
        rate_limit_delay: float = 0.0,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the HTTP connector.
        
        Args:
            name: Connector name
            rate_limit_delay: Minimum seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            user_agent: Custom User-Agent header
        """
        if requests is None:
            raise ImportError(
                "requests library is required for HttpConnector. "
                "Install with: pip install requests"
            )
        
        self.name = name
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or "HolocronAnalytics/1.0"
        self.last_request_time = 0.0
        self.session = requests.Session()

    def fetch(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Fetch data via HTTP.
        
        Args:
            request: The request to execute
            
        Returns:
            ConnectorResponse with the result
        """
        # Rate limiting
        self._wait_for_rate_limit()

        # Prepare headers
        headers = request.headers or {}
        if "User-Agent" not in headers:
            headers["User-Agent"] = self.user_agent

        # Build URL with query params
        url = request.uri
        if request.params:
            url = f"{url}?{urlencode(request.params)}"

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                if request.method.upper() == "GET":
                    response = self.session.get(
                        url,
                        headers=headers,
                        timeout=self.timeout
                    )
                elif request.method.upper() == "POST":
                    response = self.session.post(
                        url,
                        headers=headers,
                        data=request.body,
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {request.method}")

                duration_ms = int((time.time() - start_time) * 1000)
                
                # Try to parse as JSON, fall back to text
                try:
                    payload = response.json()
                except (json.JSONDecodeError, ValueError):
                    # Wrap non-JSON responses in a JSON structure
                    payload = {
                        "content_type": response.headers.get("Content-Type", "unknown"),
                        "text": response.text,
                        "encoding": response.encoding,
                    }

                return ConnectorResponse(
                    status_code=response.status_code,
                    payload=payload,
                    headers=dict(response.headers),
                    duration_ms=duration_ms,
                )

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                    continue

        # All retries exhausted
        return ConnectorResponse(
            status_code=0,
            payload={},
            error_message=f"Request failed after {self.max_retries} attempts: {last_error}",
        )

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def get_name(self) -> str:
        """Return the connector name."""
        return self.name

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
