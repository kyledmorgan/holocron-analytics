"""
Storage implementations for persisting ingestion results.
"""

from .file_lake import FileLakeWriter
from .sqlserver import SqlServerIngestWriter

__all__ = ["FileLakeWriter", "SqlServerIngestWriter"]
