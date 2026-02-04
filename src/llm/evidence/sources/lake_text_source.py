"""
Lake text source adapter for text artifacts in the lake.

Handles loading and bounding of text files from the artifact lake.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from ...contracts.evidence_contracts import (
    EvidenceItem,
    EvidencePolicy,
    generate_evidence_id,
    compute_content_hash,
)
from ..bounding import apply_item_bounding
from ..redaction import redact
from ..text_extractors import extract_plain_text

logger = logging.getLogger(__name__)


def load_lake_text_evidence(
    lake_uris: List[str],
    policy: EvidencePolicy,
    lake_root: str = "lake"
) -> List[EvidenceItem]:
    """
    Load text evidence from lake artifacts.
    
    Args:
        lake_uris: List of lake URIs (relative paths in lake)
        policy: Evidence policy for bounding
        lake_root: Root directory of the lake
        
    Returns:
        List of EvidenceItem objects
    """
    items = []
    
    for lake_uri in lake_uris:
        try:
            # Construct full path
            full_path = Path(lake_root) / lake_uri
            
            if not full_path.exists():
                logger.warning(f"Lake artifact not found: {lake_uri}")
                continue
            
            # Read content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply redaction
            redacted_content, redaction_meta = redact(content, policy.enable_redaction)
            
            # Apply bounding
            bounded_content, bounding_meta = apply_item_bounding(
                redacted_content,
                policy.max_item_bytes,
                "lake_text"
            )
            
            # Generate deterministic ID
            evidence_id = generate_evidence_id("lake_text", lake_uri, 0)
            
            # Compute content hash
            content_sha256 = compute_content_hash(bounded_content)
            
            # Build metadata
            item_metadata = {
                "bounding": bounding_meta,
                "lake_path": str(full_path),
            }
            if redaction_meta.get("enabled"):
                item_metadata["redactions"] = redaction_meta
            
            # Store full_ref if truncated
            full_ref = None
            if bounding_meta.get("applied"):
                full_ref = {
                    "lake_uri": lake_uri,
                    "full_size": bounding_meta["original_size"]
                }
            
            item = EvidenceItem(
                evidence_id=evidence_id,
                evidence_type="lake_text",
                source_ref={"lake_uri": lake_uri},
                content=bounded_content,
                content_sha256=content_sha256,
                byte_count=len(bounded_content.encode('utf-8')),
                metadata=item_metadata,
                full_ref=full_ref,
            )
            
            items.append(item)
            
        except Exception as e:
            logger.error(f"Error loading lake text {lake_uri}: {e}")
    
    return items
