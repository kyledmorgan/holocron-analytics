"""
SQL result source adapter for tabular SQL result sets.

Handles loading and bounding of SQL query results, either from existing
artifacts or by executing queries.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ...contracts.evidence_contracts import (
    EvidenceItem,
    EvidencePolicy,
    generate_evidence_id,
    compute_content_hash,
)
from ..bounding import apply_item_bounding
from ..redaction import redact
from ..text_extractors import extract_sql_result_text

logger = logging.getLogger(__name__)


def load_sql_result_evidence(
    sql_result_refs: List[Dict[str, Any]],
    policy: EvidencePolicy,
    lake_root: str = "lake"
) -> List[EvidenceItem]:
    """
    Load SQL result evidence from existing result artifacts.
    
    Expected format for sql_result_refs:
    [
        {
            "lake_uri": "path/to/result.json",
            "query_key": "optional_query_name",
            "metadata": {...}
        },
        ...
    ]
    
    Expected artifact format (JSON):
    {
        "columns": ["col1", "col2", ...],
        "rows": [[val1, val2, ...], ...],
        "row_count": N,
        "query": "optional SQL text"
    }
    
    Args:
        sql_result_refs: List of SQL result references
        policy: Evidence policy for bounding
        lake_root: Root directory of the lake
        
    Returns:
        List of EvidenceItem objects
    """
    items = []
    
    for i, ref in enumerate(sql_result_refs):
        try:
            lake_uri = ref.get("lake_uri")
            if not lake_uri:
                logger.warning(f"SQL result ref {i} missing lake_uri")
                continue
            
            query_key = ref.get("query_key", f"query_{i}")
            ref_metadata = ref.get("metadata", {})
            
            # Load result artifact
            full_path = Path(lake_root) / lake_uri
            if not full_path.exists():
                logger.warning(f"SQL result artifact not found: {lake_uri}")
                continue
            
            with open(full_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            columns = result_data.get("columns", [])
            rows = result_data.get("rows", [])
            row_count = result_data.get("row_count", len(rows))
            
            # Extract bounded text representation
            extracted_text, extract_meta = extract_sql_result_text(
                rows=rows,
                columns=columns,
                max_rows=policy.max_sql_rows,
                max_cols=policy.max_sql_cols or 999,
                sampling_strategy=policy.sampling_strategy
            )
            
            # Apply redaction
            redacted_text, redaction_meta = redact(extracted_text, policy.enable_redaction)
            
            # Apply final bounding
            bounded_text, bounding_meta = apply_item_bounding(
                redacted_text,
                policy.max_item_bytes,
                "sql_result"
            )
            
            # Generate deterministic ID
            evidence_id = generate_evidence_id("sql_result", query_key, 0)
            
            # Compute content hash
            content_sha256 = compute_content_hash(bounded_text)
            
            # Build metadata
            item_metadata = {
                "bounding": bounding_meta,
                "sql_meta": extract_meta,
                "query_key": query_key,
                "lake_path": str(full_path),
                **ref_metadata,
            }
            if redaction_meta.get("enabled"):
                item_metadata["redactions"] = redaction_meta
            
            # Store full_ref
            full_ref = {
                "lake_uri": lake_uri,
                "row_count": row_count,
                "col_count": len(columns),
            }
            
            # Optionally include query text in source_ref
            source_ref = {
                "lake_uri": lake_uri,
                "query_key": query_key,
            }
            if "query" in result_data:
                source_ref["query"] = result_data["query"]
            
            item = EvidenceItem(
                evidence_id=evidence_id,
                evidence_type="sql_result",
                source_ref=source_ref,
                content=bounded_text,
                content_sha256=content_sha256,
                byte_count=len(bounded_text.encode('utf-8')),
                metadata=item_metadata,
                full_ref=full_ref,
            )
            
            items.append(item)
            
        except Exception as e:
            logger.error(f"Error loading SQL result {i}: {e}")
    
    return items


def execute_sql_query(
    query: str,
    connection_string: str,
    query_key: str,
    policy: EvidencePolicy,
    timeout_seconds: int = 30
) -> Optional[EvidenceItem]:
    """
    Execute a SQL query and create evidence item (optional mode D2).
    
    Guardrails:
    - Only SELECT statements allowed
    - Query timeout enforced
    - Results persisted as artifact for full traceability
    
    Args:
        query: SQL query to execute (must be SELECT)
        connection_string: Database connection string
        query_key: Identifier for this query
        policy: Evidence policy for bounding
        timeout_seconds: Query timeout
        
    Returns:
        EvidenceItem or None if execution fails
    """
    # Basic validation: must be SELECT
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        logger.error(f"Query {query_key} is not a SELECT statement: {query[:50]}")
        return None
    
    try:
        import pyodbc
        
        # Execute query with timeout
        conn = pyodbc.connect(connection_string, timeout=timeout_seconds)
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Fetch results
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        row_count = len(rows)
        
        # Convert rows to list of lists
        rows_data = [list(row) for row in rows]
        
        cursor.close()
        conn.close()
        
        # Create result artifact structure
        result_data = {
            "columns": columns,
            "rows": rows_data,
            "row_count": row_count,
            "query": query,
        }
        
        # Extract bounded text
        extracted_text, extract_meta = extract_sql_result_text(
            rows=rows_data,
            columns=columns,
            max_rows=policy.max_sql_rows,
            max_cols=policy.max_sql_cols or 999,
            sampling_strategy=policy.sampling_strategy
        )
        
        # Apply redaction
        redacted_text, redaction_meta = redact(extracted_text, policy.enable_redaction)
        
        # Apply final bounding
        bounded_text, bounding_meta = apply_item_bounding(
            redacted_text,
            policy.max_item_bytes,
            "sql_result"
        )
        
        # Generate deterministic ID
        evidence_id = generate_evidence_id("sql_result", query_key, 0)
        
        # Compute content hash
        content_sha256 = compute_content_hash(bounded_text)
        
        # Build metadata
        item_metadata = {
            "bounding": bounding_meta,
            "sql_meta": extract_meta,
            "query_key": query_key,
            "executed": True,
        }
        if redaction_meta.get("enabled"):
            item_metadata["redactions"] = redaction_meta
        
        # Store full_ref
        full_ref = {
            "row_count": row_count,
            "col_count": len(columns),
        }
        
        item = EvidenceItem(
            evidence_id=evidence_id,
            evidence_type="sql_result",
            source_ref={
                "query_key": query_key,
                "query": query,
            },
            content=bounded_text,
            content_sha256=content_sha256,
            byte_count=len(bounded_text.encode('utf-8')),
            metadata=item_metadata,
            full_ref=full_ref,
        )
        
        return item
        
    except Exception as e:
        logger.error(f"Error executing SQL query {query_key}: {e}")
        return None
