"""
Test connector for E2E testing.

Provides a deterministic connector that returns synthetic data without
any external network dependencies. Used for integration and E2E testing.

The connector returns a fixed, known dataset that exercises the full
ingestion pipeline path while remaining predictable and reproducible.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from ..core.connector import Connector, ConnectorRequest, ConnectorResponse
from ..core.models import WorkItem

logger = logging.getLogger(__name__)


# Fixed synthetic dataset for testing
# These resources are designed to test various ingestion scenarios
SYNTHETIC_RESOURCES = [
    {
        "id": "test_resource_001",
        "title": "Star Wars Episode IV: A New Hope",
        "type": "film",
        "url": "https://test.example.com/films/001",
        "metadata": {
            "year": 1977,
            "director": "George Lucas",
            "genre": ["sci-fi", "adventure"],
        },
    },
    {
        "id": "test_resource_002",
        "title": "Luke Skywalker",
        "type": "character",
        "url": "https://test.example.com/characters/001",
        "metadata": {
            "species": "Human",
            "homeworld": "Tatooine",
            "affiliations": ["Rebel Alliance", "Jedi Order"],
        },
    },
    {
        "id": "test_resource_003",
        "title": "Millennium Falcon",
        "type": "vehicle",
        "url": "https://test.example.com/vehicles/001",
        "metadata": {
            "model": "YT-1300 light freighter",
            "manufacturer": "Corellian Engineering Corporation",
            "crew": 4,
        },
    },
    {
        "id": "test_resource_004",
        "title": "The Force",
        "type": "concept",
        "url": "https://test.example.com/concepts/001",
        "metadata": {
            "description": "An energy field created by all living things",
            "aspects": ["Light Side", "Dark Side"],
        },
    },
    {
        "id": "test_resource_005",
        "title": "Tatooine",
        "type": "planet",
        "url": "https://test.example.com/planets/001",
        "metadata": {
            "system": "Tatoo",
            "suns": 2,
            "climate": "arid",
        },
    },
]


class TestConnector(Connector):
    """
    Deterministic test connector for E2E testing.
    
    Returns synthetic data from a fixed dataset without making any
    external network calls. Designed to be predictable and reproducible.
    
    Features:
    - Deterministic responses based on resource ID
    - Configurable latency simulation
    - Error simulation for specific resource IDs
    - Full payload compatible with production pipeline
    """
    
    def __init__(
        self,
        simulate_latency_ms: int = 0,
        error_resource_ids: Optional[List[str]] = None,
        custom_resources: Optional[List[dict]] = None,
    ):
        """
        Initialize the test connector.
        
        Args:
            simulate_latency_ms: Simulated latency in milliseconds (default: 0)
            error_resource_ids: List of resource IDs that should return errors
            custom_resources: Custom resources to use instead of defaults
        """
        self.simulate_latency_ms = simulate_latency_ms
        self.error_resource_ids = set(error_resource_ids or [])
        self.resources = custom_resources or SYNTHETIC_RESOURCES
        
        # Build lookup by ID
        self._resource_map = {r["id"]: r for r in self.resources}
        
        # Track requests for testing
        self.request_history: List[ConnectorRequest] = []
        
        logger.debug(
            f"TestConnector initialized with {len(self.resources)} resources"
        )
    
    def fetch(self, request: ConnectorRequest) -> ConnectorResponse:
        """
        Fetch data from the synthetic dataset.
        
        The resource is looked up based on the request URI. The connector
        parses the resource ID from the URI and returns the corresponding
        synthetic data.
        
        Args:
            request: The connector request
            
        Returns:
            ConnectorResponse with synthetic data
        """
        import time
        
        start_time = time.time()
        
        # Track request
        self.request_history.append(request)
        
        # Simulate latency if configured
        if self.simulate_latency_ms > 0:
            time.sleep(self.simulate_latency_ms / 1000.0)
        
        # Extract resource ID from URI
        resource_id = self._extract_resource_id(request.uri)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Check for simulated errors
        if resource_id in self.error_resource_ids:
            logger.debug(f"Simulating error for resource: {resource_id}")
            return ConnectorResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                payload={"error": "Simulated error for testing"},
                error_message=f"Simulated error for resource {resource_id}",
                duration_ms=duration_ms,
            )
        
        # Look up resource
        if resource_id in self._resource_map:
            resource = self._resource_map[resource_id]
            logger.debug(f"Returning synthetic data for: {resource_id}")
            return ConnectorResponse(
                status_code=200,
                headers={
                    "Content-Type": "application/json",
                    "X-Test-Connector": "true",
                },
                payload={
                    "resource": resource,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "test_connector",
                },
                duration_ms=duration_ms,
            )
        
        # Resource not found
        logger.debug(f"Resource not found: {resource_id}")
        return ConnectorResponse(
            status_code=404,
            headers={"Content-Type": "application/json"},
            payload={"error": f"Resource not found: {resource_id}"},
            error_message=f"Resource not found: {resource_id}",
            duration_ms=duration_ms,
        )
    
    def _extract_resource_id(self, uri: str) -> str:
        """
        Extract resource ID from URI.
        
        Supports multiple URI patterns:
        - /resources/{id}
        - /test/{id}
        - Direct resource ID
        """
        # Try to extract from path
        parts = uri.rstrip("/").split("/")
        
        # Check for known patterns
        for i, part in enumerate(parts):
            if part in ("resources", "test", "items"):
                if i + 1 < len(parts):
                    return parts[i + 1]
        
        # Fall back to last path segment
        if parts:
            return parts[-1]
        
        return uri
    
    def get_name(self) -> str:
        """Return connector name."""
        return "test"
    
    def get_seed_work_items(
        self,
        source_name: str = "test_source",
        priority: int = 100,
    ) -> List[WorkItem]:
        """
        Get seed work items for all synthetic resources.
        
        This method generates work items that can be used to seed
        the ingestion queue for testing.
        
        Args:
            source_name: Name for the source
            priority: Priority for work items
            
        Returns:
            List of WorkItem objects for all synthetic resources
        """
        work_items = []
        
        for resource in self.resources:
            work_item = WorkItem(
                source_system="test",
                source_name=source_name,
                resource_type=resource.get("type", "unknown"),
                resource_id=resource["id"],
                request_uri=f"https://test.example.com/resources/{resource['id']}",
                request_method="GET",
                priority=priority,
                metadata={
                    "test_connector": True,
                    "title": resource.get("title"),
                },
            )
            work_items.append(work_item)
        
        return work_items
    
    def reset(self) -> None:
        """Reset the connector state (clear request history)."""
        self.request_history.clear()
    
    def close(self) -> None:
        """Close the connector (no-op for test connector)."""
        pass


def create_test_work_items(
    count: int = 5,
    source_name: str = "test_source",
    resource_type: str = "test_item",
    priority: int = 100,
) -> List[WorkItem]:
    """
    Create a list of test work items with predictable IDs.
    
    This is a convenience function for creating test fixtures.
    
    Args:
        count: Number of work items to create
        source_name: Name for the source
        resource_type: Type for all resources
        priority: Priority for work items
        
    Returns:
        List of WorkItem objects
    """
    work_items = []
    
    for i in range(count):
        work_item = WorkItem(
            source_system="test",
            source_name=source_name,
            resource_type=resource_type,
            resource_id=f"test_resource_{i:03d}",
            request_uri=f"https://test.example.com/resources/test_resource_{i:03d}",
            request_method="GET",
            priority=priority,
            metadata={"index": i, "test": True},
        )
        work_items.append(work_item)
    
    return work_items
