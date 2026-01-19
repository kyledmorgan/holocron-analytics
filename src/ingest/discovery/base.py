"""
Discovery interface for extracting new work items from responses.
"""

from abc import ABC, abstractmethod
from typing import List

from ..core.models import WorkItem, IngestRecord


class Discovery(ABC):
    """
    Abstract base class for discovery plugins.
    
    Discovery plugins analyze ingestion results and extract
    new work items to be added to the queue (e.g., following links).
    """

    @abstractmethod
    def discover(self, record: IngestRecord, parent_work_item: WorkItem) -> List[WorkItem]:
        """
        Discover new work items from an ingestion record.
        
        Args:
            record: The ingestion record to analyze
            parent_work_item: The work item that produced this record
            
        Returns:
            List of new work items discovered
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the discovery plugin name."""
        pass
