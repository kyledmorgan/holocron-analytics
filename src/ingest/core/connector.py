"""
Connector interface for fetching data from external sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ConnectorRequest:
    """
    Request to be sent by a connector.
    
    Attributes:
        uri: The URI to fetch
        method: HTTP method (GET, POST, etc.)
        headers: Optional request headers
        body: Optional request body
        params: Optional query parameters
        metadata: Additional connector-specific metadata
    """
    uri: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConnectorResponse:
    """
    Response from a connector.
    
    Attributes:
        status_code: HTTP status code
        payload: Response payload as dict (parsed JSON)
        headers: Response headers
        duration_ms: Time taken for the request in milliseconds
        error_message: Error message if request failed
    """
    status_code: int
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class Connector(ABC):
    """
    Abstract base class for all connectors.
    
    Connectors are responsible for fetching data from external sources
    and returning structured responses.
    """

    @abstractmethod
    def fetch(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Fetch data from the external source.
        
        Args:
            request: The request to execute
            
        Returns:
            ConnectorResponse with the result
            
        Raises:
            Exception if the fetch fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the connector name/identifier."""
        pass
