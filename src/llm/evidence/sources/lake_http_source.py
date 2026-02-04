"""
Lake HTTP source adapter for raw HTTP response artifacts.

Handles loading and extracting text from HTTP response artifacts in the lake.
"""

import json
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
from ..text_extractors import extract_http_response

logger = logging.getLogger(__name__)


def load_lake_http_evidence(
    lake_uris: List[str],
    policy: EvidencePolicy,
    lake_root: str = "lake"
) -> List[EvidenceItem]:
    """
    Load HTTP response evidence from lake artifacts.
    
    Expected artifact format (JSON):
    {
        "url": "...",
        "status_code": 200,
        "reason": "OK",
        "headers": {...},
        "body": "..."
    }
    
    Args:
        lake_uris: List of lake URIs pointing to HTTP response artifacts
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
            
            # Read HTTP response artifact
            with open(full_path, 'r', encoding='utf-8') as f:
                response_data = json.load(f)
            
            # Extract text from HTTP response
            extracted_text, extract_meta = extract_http_response(
                response_data,
                policy.max_item_bytes
            )
            
            # Apply redaction
            redacted_text, redaction_meta = redact(extracted_text, policy.enable_redaction)
            
            # Apply final bounding (if needed after redaction)
            bounded_text, bounding_meta = apply_item_bounding(
                redacted_text,
                policy.max_item_bytes,
                "lake_http"
            )
            
            # Generate deterministic ID
            evidence_id = generate_evidence_id("lake_http", lake_uri, 0)
            
            # Compute content hash
            content_sha256 = compute_content_hash(bounded_text)
            
            # Build metadata
            item_metadata = {
                "bounding": bounding_meta,
                "http_meta": extract_meta,
                "lake_path": str(full_path),
            }
            if redaction_meta.get("enabled"):
                item_metadata["redactions"] = redaction_meta
            
            # Store full_ref
            full_ref = {
                "lake_uri": lake_uri,
                "full_size": extract_meta.get("body_original_size", 0)
            }
            
            item = EvidenceItem(
                evidence_id=evidence_id,
                evidence_type="lake_http",
                source_ref={
                    "lake_uri": lake_uri,
                    "url": response_data.get("url", "unknown"),
                },
                content=bounded_text,
                content_sha256=content_sha256,
                byte_count=len(bounded_text.encode('utf-8')),
                metadata=item_metadata,
                full_ref=full_ref,
            )
            
            items.append(item)
            
        except Exception as e:
            logger.error(f"Error loading lake HTTP artifact {lake_uri}: {e}")
    
    return items
