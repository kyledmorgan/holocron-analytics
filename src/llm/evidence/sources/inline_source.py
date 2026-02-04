"""
Inline source adapter for job-provided evidence.

Handles evidence provided directly in the job input payload.
"""

from typing import List, Dict, Any
from ...contracts.evidence_contracts import (
    EvidenceItem,
    EvidencePolicy,
    generate_evidence_id,
    compute_content_hash,
)
from ..bounding import apply_item_bounding
from ..redaction import redact


def load_inline_evidence(
    inline_data: List[Dict[str, Any]],
    policy: EvidencePolicy
) -> List[EvidenceItem]:
    """
    Load evidence from inline data in job payload.
    
    Expected format:
    [
        {"text": "...", "source_uri": "...", "metadata": {...}},
        ...
    ]
    
    Args:
        inline_data: List of inline evidence dictionaries
        policy: Evidence policy for bounding
        
    Returns:
        List of EvidenceItem objects
    """
    items = []
    
    for i, data in enumerate(inline_data):
        text = data.get("text", "")
        source_uri = data.get("source_uri", "inline")
        metadata = data.get("metadata", {})
        
        # Apply redaction if enabled
        redacted_text, redaction_meta = redact(text, policy.enable_redaction)
        
        # Apply bounding
        bounded_text, bounding_meta = apply_item_bounding(
            redacted_text,
            policy.max_item_bytes,
            "inline_text"
        )
        
        # Generate deterministic ID
        evidence_id = generate_evidence_id("inline_text", str(i), i)
        
        # Compute content hash
        content_sha256 = compute_content_hash(bounded_text)
        
        # Merge metadata
        item_metadata = {
            **metadata,
            "bounding": bounding_meta,
        }
        if redaction_meta.get("enabled"):
            item_metadata["redactions"] = redaction_meta
        
        item = EvidenceItem(
            evidence_id=evidence_id,
            evidence_type="inline_text",
            source_ref={"source_uri": source_uri, "index": i},
            content=bounded_text,
            content_sha256=content_sha256,
            byte_count=len(bounded_text.encode('utf-8')),
            metadata=item_metadata,
        )
        
        items.append(item)
    
    return items
