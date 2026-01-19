"""
Core abstractions and interfaces for the Holocron Analytics ingestion framework.
"""

from .models import WorkItem, IngestRecord, WorkItemStatus
from .connector import Connector, ConnectorRequest, ConnectorResponse
from .storage import StorageWriter
from .state_store import StateStore

__all__ = [
    "WorkItem",
    "IngestRecord",
    "WorkItemStatus",
    "Connector",
    "ConnectorRequest",
    "ConnectorResponse",
    "StorageWriter",
    "StateStore",
]
