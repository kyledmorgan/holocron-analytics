"""
Evidence Conversion - Convert retrieval hits to evidence items.

Bridges Phase 3 retrieval with Phase 2 evidence builder, converting
retrieved chunks into EvidenceItem objects for LLM interrogation.
"""

import logging
from typing import Any, Dict, List, Optional

from ..contracts.evidence_contracts import (
    EvidenceItem,
    generate_evidence_id,
    compute_content_hash,
)
from ..contracts.retrieval_contracts import (
    RetrievalHit,
    RetrievalResult,
)

logger = logging.getLogger(__name__)


def convert_retrieval_to_evidence(
    result: RetrievalResult,
    chunk_contents: Dict[str, str],
) -> List[EvidenceItem]:
    """
    Convert retrieval hits to evidence items.
    
    Takes a retrieval result and the corresponding chunk contents, and produces
    EvidenceItem objects suitable for the Phase 2 evidence builder.
    
    Args:
        result: RetrievalResult with hits
        chunk_contents: Mapping of chunk_id to content
        
    Returns:
        List of EvidenceItem objects
    """
    evidence_items = []
    
    for hit in result.hits:
        chunk_id = hit.chunk_id
        content = chunk_contents.get(chunk_id, "")
        
        if not content:
            logger.warning(f"No content found for chunk {chunk_id}")
            continue
        
        # Build source reference from hit metadata
        metadata = hit.metadata or {}
        source_ref = {
            "chunk_id": chunk_id,
            "source_type": metadata.get("source_type", "doc_chunk"),
            "source_ref": metadata.get("source_ref", {}),
            "retrieval_id": hit.retrieval_id,
            "retrieval_rank": hit.rank,
            "retrieval_score": hit.score,
        }
        
        # Generate evidence ID
        evidence_id = generate_evidence_id(
            evidence_type="doc_chunk",
            source_identifier=chunk_id,
            chunk_index=hit.rank - 1,  # 0-indexed for evidence ID
        )
        
        # Compute content hash
        content_hash = compute_content_hash(content)
        
        # Create evidence item
        item = EvidenceItem(
            evidence_id=evidence_id,
            evidence_type="doc_chunk",
            source_ref=source_ref,
            content=content,
            content_sha256=content_hash,
            byte_count=len(content.encode('utf-8')),
            metadata={
                "retrieval_score": hit.score,
                "retrieval_rank": hit.rank,
                "offsets": metadata.get("offsets", {}),
            },
            offsets=metadata.get("offsets"),
        )
        
        evidence_items.append(item)
    
    logger.info(f"Converted {len(evidence_items)} retrieval hits to evidence items")
    return evidence_items


def build_retrieval_evidence_refs(
    retrieval_result: RetrievalResult,
) -> Dict[str, Any]:
    """
    Build evidence references from a retrieval result.
    
    Creates the evidence_refs dict format expected by the evidence builder,
    specifically for retrieval-sourced evidence.
    
    Args:
        retrieval_result: The retrieval result
        
    Returns:
        Evidence references dict with retrieval metadata
    """
    return {
        "retrieval": {
            "retrieval_id": retrieval_result.query.retrieval_id,
            "query_text": retrieval_result.query.query_text,
            "embedding_model": retrieval_result.query.query_embedding_model,
            "top_k": retrieval_result.query.top_k,
            "hit_count": len(retrieval_result.hits),
            "hits": [
                {
                    "chunk_id": hit.chunk_id,
                    "score": hit.score,
                    "rank": hit.rank,
                }
                for hit in retrieval_result.hits
            ],
        }
    }
