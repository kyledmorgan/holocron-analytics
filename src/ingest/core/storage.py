"""
Storage interface for persisting ingestion results.
"""

from abc import ABC, abstractmethod
from ..core.models import IngestRecord


class StorageWriter(ABC):
    """
    Abstract base class for storage writers.
    
    Storage writers persist ingestion records to various targets
    (files, databases, etc.).
    """

    @abstractmethod
    def write(self, record: IngestRecord) -> bool:
        """
        Write an ingestion record to storage.
        
        Args:
            record: The ingestion record to write
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception if write fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the storage writer name/identifier."""
        pass

    def close(self) -> None:
        """Close any open resources. Optional."""
        pass
