"""
Evidence Bundle Builder - evidence assembly system (2026_01_llm_derived_data_phase_2).

This module provides functionality for building deterministic, bounded,
and auditable evidence bundles from various sources.
"""

from .builder import EvidenceBundleBuilder, build_evidence_bundle

__all__ = [
    "EvidenceBundleBuilder",
    "build_evidence_bundle",
]
