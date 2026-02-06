"""
Core abstractions and interfaces for the Holocron Analytics ingestion framework.
"""

from .models import (
    WorkItem, IngestRecord, WorkItemStatus, AcquisitionVariant,
    WorkerInfo, WorkerStatus, QueueStats
)
from .connector import Connector, ConnectorRequest, ConnectorResponse
from .storage import StorageWriter
from .state_store import StateStore

__all__ = [
    "WorkItem",
    "IngestRecord",
    "WorkItemStatus",
    "AcquisitionVariant",
    "WorkerInfo",
    "WorkerStatus",
    "QueueStats",
    "Connector",
    "ConnectorRequest",
    "ConnectorResponse",
    "StorageWriter",
    "StateStore",
]
