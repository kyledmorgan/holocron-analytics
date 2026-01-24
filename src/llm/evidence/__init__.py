"""
Evidence Bundle Builder - Phase 2 evidence assembly system.

This module provides functionality for building deterministic, bounded,
and auditable evidence bundles from various sources.
"""

from .builder import EvidenceBundleBuilder, build_evidence_bundle

__all__ = [
    "EvidenceBundleBuilder",
    "build_evidence_bundle",
]
