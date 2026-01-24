"""
Deterministic bounding rules for evidence items.

Implements rules to ensure evidence bundles fit within model context limits
while maintaining determinism and auditability.
"""

import logging
from typing import List, Dict, Any, Tuple
from ..contracts.evidence_contracts import EvidenceItem, EvidencePolicy

logger = logging.getLogger(__name__)


def apply_item_bounding(
    content: str,
    max_bytes: int,
    evidence_type: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Apply byte limit to a single evidence item.
    
    Args:
        content: Content to bound
        max_bytes: Maximum bytes allowed
        evidence_type: Type of evidence (for logging)
        
    Returns:
        Tuple of (bounded_content, bounding_metadata)
    """
    content_bytes = content.encode('utf-8')
    original_size = len(content_bytes)
    
    if original_size <= max_bytes:
        return content, {
            "applied": False,
            "original_size": original_size,
            "bounded_size": original_size,
        }
    
    # Truncate
    bounded_bytes = content_bytes[:max_bytes]
    try:
        bounded_content = bounded_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # Handle partial UTF-8 characters
        bounded_content = bounded_bytes[:-3].decode('utf-8', errors='ignore')
    
    bounded_size = len(bounded_content.encode('utf-8'))
    
    logger.debug(
        f"Bounded {evidence_type} item from {original_size} to {bounded_size} bytes"
    )
    
    return bounded_content, {
        "applied": True,
        "original_size": original_size,
        "bounded_size": bounded_size,
        "truncation_point": bounded_size,
        "note": f"Truncated to {max_bytes} byte limit"
    }


def apply_bundle_bounding(
    items: List[EvidenceItem],
    policy: EvidencePolicy
) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
    """
    Apply global bundle limits (max items, max total bytes).
    
    If bundle exceeds limits, items are dropped starting from the end
    (preserving earlier items which are typically more important).
    
    Args:
        items: List of evidence items
        policy: Evidence bounding policy
        
    Returns:
        Tuple of (bounded_items, bounding_metadata)
    """
    original_count = len(items)
    
    # Apply max_items limit
    if original_count > policy.max_items:
        items = items[:policy.max_items]
        logger.warning(
            f"Dropped {original_count - policy.max_items} items to meet max_items={policy.max_items}"
        )
    
    # Apply max_total_bytes limit
    total_bytes = sum(item.byte_count for item in items)
    if total_bytes > policy.max_total_bytes:
        # Drop items from end until under limit
        bounded_items = []
        running_total = 0
        for item in items:
            if running_total + item.byte_count <= policy.max_total_bytes:
                bounded_items.append(item)
                running_total += item.byte_count
            else:
                logger.debug(
                    f"Dropped item {item.evidence_id} to stay under max_total_bytes"
                )
        
        items = bounded_items
        total_bytes = running_total
    
    final_count = len(items)
    
    metadata = {
        "applied": final_count < original_count or total_bytes > policy.max_total_bytes,
        "original_count": original_count,
        "final_count": final_count,
        "items_dropped": original_count - final_count,
        "total_bytes": total_bytes,
        "max_total_bytes": policy.max_total_bytes,
    }
    
    if metadata["items_dropped"] > 0:
        metadata["note"] = f"Dropped {metadata['items_dropped']} items to meet bundle limits"
    
    return items, metadata


def validate_policy(policy: EvidencePolicy) -> List[str]:
    """
    Validate evidence policy configuration.
    
    Args:
        policy: Policy to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if policy.max_items < 1:
        errors.append("max_items must be at least 1")
    
    if policy.max_total_bytes < 1000:
        errors.append("max_total_bytes must be at least 1000 bytes")
    
    if policy.max_item_bytes < 100:
        errors.append("max_item_bytes must be at least 100 bytes")
    
    if policy.max_item_bytes > policy.max_total_bytes:
        errors.append("max_item_bytes cannot exceed max_total_bytes")
    
    if policy.max_sql_rows < 1:
        errors.append("max_sql_rows must be at least 1")
    
    if policy.max_sql_cols and policy.max_sql_cols < 1:
        errors.append("max_sql_cols must be at least 1 if specified")
    
    if policy.chunk_size < 100:
        errors.append("chunk_size must be at least 100 bytes")
    
    if policy.chunk_overlap < 0:
        errors.append("chunk_overlap must be non-negative")
    
    if policy.chunk_overlap >= policy.chunk_size:
        errors.append("chunk_overlap must be less than chunk_size")
    
    if policy.sampling_strategy not in ["first_only", "first_last", "stride"]:
        errors.append(f"Invalid sampling_strategy: {policy.sampling_strategy}")
    
    return errors
