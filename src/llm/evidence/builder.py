"""
Evidence Bundle Builder - Main entry point for Phase 2 evidence assembly.

Orchestrates the loading, bounding, and packaging of evidence from various
sources into a deterministic, auditable evidence bundle.
"""

import logging
from typing import Dict, Any, List, Optional
from ..contracts.evidence_contracts import (
    EvidenceBundle,
    EvidenceItem,
    EvidencePolicy,
)
from .bounding import apply_bundle_bounding, validate_policy
from .sources.inline_source import load_inline_evidence
from .sources.lake_text_source import load_lake_text_evidence
from .sources.lake_http_source import load_lake_http_evidence
from .sources.sql_result_source import load_sql_result_evidence, execute_sql_query
from .sources.sql_query_source import load_sql_query_definitions

logger = logging.getLogger(__name__)


class EvidenceBundleBuilder:
    """
    Builder for creating evidence bundles from various sources.
    
    Supports:
    - Inline text evidence (provided in job payload)
    - Lake text artifacts (files in the artifact lake)
    - Lake HTTP artifacts (raw HTTP responses)
    - SQL result sets (existing artifacts or executed queries)
    - SQL query definitions (for transparency)
    
    Applies deterministic bounding and redaction rules according to policy.
    """
    
    def __init__(self, policy: Optional[EvidencePolicy] = None, lake_root: str = "lake"):
        """
        Initialize builder.
        
        Args:
            policy: Evidence bounding policy (uses default if not provided)
            lake_root: Root directory of the artifact lake
        """
        self.policy = policy or EvidencePolicy()
        self.lake_root = lake_root
        
        # Validate policy
        errors = validate_policy(self.policy)
        if errors:
            raise ValueError(f"Invalid evidence policy: {'; '.join(errors)}")
    
    def build(
        self,
        job_input: Dict[str, Any],
        evidence_refs: Optional[Dict[str, Any]] = None
    ) -> EvidenceBundle:
        """
        Build evidence bundle from job input and evidence references.
        
        Args:
            job_input: Job input envelope (may contain inline evidence)
            evidence_refs: Evidence references (lake URIs, SQL refs, etc.)
            
        Returns:
            Complete evidence bundle ready for LLM interrogation
        """
        items: List[EvidenceItem] = []
        
        # Load inline evidence (from job extra_params)
        inline_data = job_input.get("extra_params", {}).get("evidence", [])
        if inline_data:
            logger.info(f"Loading {len(inline_data)} inline evidence items")
            items.extend(load_inline_evidence(inline_data, self.policy))
        
        # Load evidence from references
        if evidence_refs:
            # Lake text artifacts
            lake_text_refs = evidence_refs.get("lake_text", [])
            if lake_text_refs:
                logger.info(f"Loading {len(lake_text_refs)} lake text artifacts")
                items.extend(load_lake_text_evidence(
                    lake_text_refs,
                    self.policy,
                    self.lake_root
                ))
            
            # Lake HTTP artifacts
            lake_http_refs = evidence_refs.get("lake_http", [])
            if lake_http_refs:
                logger.info(f"Loading {len(lake_http_refs)} lake HTTP artifacts")
                items.extend(load_lake_http_evidence(
                    lake_http_refs,
                    self.policy,
                    self.lake_root
                ))
            
            # SQL results (existing artifacts)
            sql_result_refs = evidence_refs.get("sql_results", [])
            if sql_result_refs:
                logger.info(f"Loading {len(sql_result_refs)} SQL result artifacts")
                items.extend(load_sql_result_evidence(
                    sql_result_refs,
                    self.policy,
                    self.lake_root
                ))
            
            # SQL query definitions (optional transparency)
            sql_query_defs = evidence_refs.get("sql_queries", [])
            if sql_query_defs:
                logger.info(f"Loading {len(sql_query_defs)} SQL query definitions")
                items.extend(load_sql_query_definitions(sql_query_defs, self.policy))
        
        # Apply bundle-level bounding
        bounded_items, bounding_meta = apply_bundle_bounding(items, self.policy)
        
        logger.info(
            f"Built evidence bundle with {len(bounded_items)} items "
            f"({bounding_meta['total_bytes']} bytes)"
        )
        
        # Create bundle
        bundle = EvidenceBundle(
            policy=self.policy,
            items=bounded_items,
        )
        
        # Compute summary
        bundle.compute_summary()
        
        # Add bounding metadata to summary
        bundle.summary["bundle_bounding"] = bounding_meta
        
        return bundle


def build_evidence_bundle(
    job_input: Dict[str, Any],
    evidence_refs: Optional[Dict[str, Any]] = None,
    policy: Optional[EvidencePolicy] = None,
    lake_root: str = "lake"
) -> EvidenceBundle:
    """
    Convenience function to build an evidence bundle.
    
    Args:
        job_input: Job input envelope
        evidence_refs: Evidence references
        policy: Evidence bounding policy (uses default if not provided)
        lake_root: Root directory of the artifact lake
        
    Returns:
        Complete evidence bundle
    """
    builder = EvidenceBundleBuilder(policy=policy, lake_root=lake_root)
    return builder.build(job_input, evidence_refs)
