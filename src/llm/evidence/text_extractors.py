"""
Text extraction utilities for evidence items.

Provides helpers to extract bounded text content from various artifact types.
"""

import json
from typing import Any, Dict, Tuple


def extract_plain_text(content: str, max_bytes: int) -> Tuple[str, Dict[str, Any]]:
    """
    Extract bounded plain text.
    
    Args:
        content: Plain text content
        max_bytes: Maximum bytes to return
        
    Returns:
        Tuple of (bounded_text, metadata)
    """
    content_bytes = content.encode('utf-8')
    original_size = len(content_bytes)
    
    if original_size <= max_bytes:
        return content, {
            "original_size": original_size,
            "truncated": False
        }
    
    # Truncate to max_bytes
    bounded_bytes = content_bytes[:max_bytes]
    # Try to decode, handling partial UTF-8 characters
    try:
        bounded_text = bounded_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # Back off to avoid partial characters
        bounded_text = bounded_bytes[:-3].decode('utf-8', errors='ignore')
    
    return bounded_text, {
        "original_size": original_size,
        "bounded_size": len(bounded_text.encode('utf-8')),
        "truncated": True,
        "truncation_note": f"Truncated from {original_size} to ~{max_bytes} bytes"
    }


def extract_json(data: Any, max_bytes: int) -> Tuple[str, Dict[str, Any]]:
    """
    Extract bounded JSON representation.
    
    Args:
        data: JSON-serializable data
        max_bytes: Maximum bytes to return
        
    Returns:
        Tuple of (bounded_json_text, metadata)
    """
    # Pretty-print JSON
    full_json = json.dumps(data, indent=2)
    return extract_plain_text(full_json, max_bytes)


def extract_http_response(response_data: Dict[str, Any], max_bytes: int) -> Tuple[str, Dict[str, Any]]:
    """
    Extract bounded text from HTTP response artifact.
    
    Args:
        response_data: HTTP response data (status, headers, body)
        max_bytes: Maximum bytes for body content
        
    Returns:
        Tuple of (formatted_text, metadata)
    """
    # Build header summary (always include)
    header_lines = [
        f"HTTP {response_data.get('status_code', 'UNKNOWN')} {response_data.get('reason', '')}",
        f"URL: {response_data.get('url', 'unknown')}",
    ]
    
    # Add key headers
    headers = response_data.get('headers', {})
    for key in ['content-type', 'content-length', 'date']:
        if key in headers:
            header_lines.append(f"{key}: {headers[key]}")
    
    header_text = "\n".join(header_lines)
    header_size = len(header_text.encode('utf-8'))
    
    # Reserve space for body
    body_max_bytes = max(max_bytes - header_size - 100, 1000)  # At least 1KB for body
    
    body = response_data.get('body', '')
    bounded_body, body_meta = extract_plain_text(body, body_max_bytes)
    
    # Combine
    full_text = f"{header_text}\n\n--- Response Body ---\n{bounded_body}"
    
    metadata = {
        "status_code": response_data.get('status_code'),
        "url": response_data.get('url'),
        "header_size": header_size,
        "body_original_size": body_meta.get("original_size", 0),
        "body_truncated": body_meta.get("truncated", False),
    }
    
    return full_text, metadata


def extract_sql_result_text(
    rows: list,
    columns: list,
    max_rows: int,
    max_cols: int,
    sampling_strategy: str = "first_last"
) -> Tuple[str, Dict[str, Any]]:
    """
    Extract bounded textual representation of SQL result.
    
    Args:
        rows: List of row data (list of lists or list of dicts)
        columns: Column names
        max_rows: Maximum rows to include
        max_cols: Maximum columns to include
        sampling_strategy: How to sample rows ("first_only", "first_last", "stride")
        
    Returns:
        Tuple of (formatted_text, metadata)
    """
    total_rows = len(rows)
    total_cols = len(columns)
    
    # Bound columns
    bounded_cols = columns[:max_cols] if max_cols and total_cols > max_cols else columns
    col_truncated = max_cols and total_cols > max_cols
    
    # Header
    lines = [
        f"SQL Result Set ({total_rows} rows, {total_cols} columns)",
        f"Columns: {', '.join(bounded_cols)}",
    ]
    
    if col_truncated:
        lines.append(f"(Note: Showing {len(bounded_cols)} of {total_cols} columns)")
    
    lines.append("")  # Blank line
    
    # Sample rows
    if total_rows <= max_rows:
        sampled_rows = rows
        sampling_note = "All rows included"
    elif sampling_strategy == "first_only":
        sampled_rows = rows[:max_rows]
        sampling_note = f"First {max_rows} rows of {total_rows}"
    elif sampling_strategy == "first_last":
        half = max_rows // 2
        sampled_rows = rows[:half] + rows[-half:]
        sampling_note = f"First {half} and last {half} rows of {total_rows}"
    elif sampling_strategy == "stride":
        stride = max(total_rows // max_rows, 1)
        sampled_rows = [rows[i] for i in range(0, total_rows, stride)][:max_rows]
        sampling_note = f"Every {stride}th row (sampled {len(sampled_rows)} of {total_rows})"
    else:
        sampled_rows = rows[:max_rows]
        sampling_note = f"First {max_rows} rows of {total_rows}"
    
    lines.append(f"Sampling: {sampling_note}")
    lines.append("")
    
    # Format rows
    for i, row in enumerate(sampled_rows):
        if isinstance(row, dict):
            # Dict row
            row_data = {k: row.get(k) for k in bounded_cols}
        else:
            # List row
            row_data = {bounded_cols[j]: row[j] for j in range(min(len(bounded_cols), len(row)))}
        
        lines.append(f"Row {i}: {json.dumps(row_data)}")
    
    text = "\n".join(lines)
    
    metadata = {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "sampled_rows": len(sampled_rows),
        "sampled_cols": len(bounded_cols),
        "sampling_strategy": sampling_strategy,
        "sampling_note": sampling_note,
        "cols_truncated": col_truncated,
    }
    
    return text, metadata
