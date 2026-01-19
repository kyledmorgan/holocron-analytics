"""
State store interface for managing work item queue and status.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..core.models import WorkItem, WorkItemStatus


class StateStore(ABC):
    """
    Abstract base class for state stores.
    
    State stores manage the queue of work items and track their status,
    enabling resumability and deduplication.
    """

    @abstractmethod
    def enqueue(self, work_item: WorkItem) -> bool:
        """
        Add a work item to the queue if it doesn't already exist.
        
        Args:
            work_item: The work item to enqueue
            
        Returns:
            True if enqueued, False if already exists
        """
        pass

    @abstractmethod
    def dequeue(self, limit: int = 1) -> List[WorkItem]:
        """
        Get pending work items from the queue.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of work items
        """
        pass

    @abstractmethod
    def update_status(
        self,
        work_item_id: str,
        status: WorkItemStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of a work item.
        
        Args:
            work_item_id: ID of the work item
            status: New status
            error_message: Optional error message for failed items
            
        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_work_item(self, work_item_id: str) -> Optional[WorkItem]:
        """
        Get a specific work item by ID.
        
        Args:
            work_item_id: ID of the work item
            
        Returns:
            WorkItem if found, None otherwise
        """
        pass

    @abstractmethod
    def exists(self, dedupe_key: str) -> bool:
        """
        Check if a work item with the given dedupe key already exists.
        
        Args:
            dedupe_key: The deduplication key to check
            
        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """
        Get statistics about the work queue.
        
        Returns:
            Dictionary with counts by status
        """
        pass

    def close(self) -> None:
        """Close any open resources. Optional."""
        pass
