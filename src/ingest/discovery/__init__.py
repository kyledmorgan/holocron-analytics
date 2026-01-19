"""
Discovery plugins for extracting new work items from responses.
"""

from .base import Discovery
from .mediawiki_discovery import MediaWikiDiscovery

__all__ = ["Discovery", "MediaWikiDiscovery"]
