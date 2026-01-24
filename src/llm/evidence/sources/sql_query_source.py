"""
SQL query source adapter for query definitions.

Handles storing SQL query definitions as evidence items (for transparency).
"""

import logging
from typing import List, Dict, Any
from ...contracts.evidence_contracts import (
    EvidenceItem,
    EvidencePolicy,
    generate_evidence_id,
    compute_content_hash,
)
from ..bounding import apply_item_bounding

logger = logging.getLogger(__name__)


def load_sql_query_definitions(
    query_defs: List[Dict[str, Any]],
    policy: EvidencePolicy
) -> List[EvidenceItem]:
    """
    Load SQL query definitions as evidence items.
    
    This allows the LLM to see what queries were run to produce results,
    providing transparency and context.
    
    Expected format:
    [
        {
            "query_key": "entity_facts",
            "query": "SELECT ...",
            "description": "optional description",
            "metadata": {...}
        },
        ...
    ]
    
    Args:
        query_defs: List of query definition dictionaries
        policy: Evidence policy for bounding
        
    Returns:
        List of EvidenceItem objects
    """
    items = []
    
    for query_def in query_defs:
        try:
            query_key = query_def.get("query_key", "unknown")
            query_text = query_def.get("query", "")
            description = query_def.get("description", "")
            ref_metadata = query_def.get("metadata", {})
            
            # Format query as evidence content
            content_parts = [
                f"Query: {query_key}",
            ]
            if description:
                content_parts.append(f"Description: {description}")
            content_parts.append("")
            content_parts.append(query_text)
            
            content = "\n".join(content_parts)
            
            # Apply bounding
            bounded_content, bounding_meta = apply_item_bounding(
                content,
                policy.max_item_bytes,
                "sql_query_def"
            )
            
            # Generate deterministic ID
            evidence_id = generate_evidence_id("sql_query_def", query_key, 0)
            
            # Compute content hash
            content_sha256 = compute_content_hash(bounded_content)
            
            # Build metadata
            item_metadata = {
                "bounding": bounding_meta,
                "query_key": query_key,
                **ref_metadata,
            }
            
            item = EvidenceItem(
                evidence_id=evidence_id,
                evidence_type="sql_query_def",
                source_ref={
                    "query_key": query_key,
                    "description": description,
                },
                content=bounded_content,
                content_sha256=content_sha256,
                byte_count=len(bounded_content.encode('utf-8')),
                metadata=item_metadata,
            )
            
            items.append(item)
            
        except Exception as e:
            logger.error(f"Error loading SQL query definition: {e}")
    
    return items
