"""
Discovery plugins for extracting new work items from responses.
"""

from .base import Discovery
from .mediawiki_discovery import MediaWikiDiscovery
from .openalex_discovery import OpenAlexDiscovery
from .entity_matcher import EntityMatcher

__all__ = ["Discovery", "MediaWikiDiscovery", "OpenAlexDiscovery", "EntityMatcher"]
