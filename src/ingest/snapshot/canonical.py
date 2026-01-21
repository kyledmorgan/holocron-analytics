"""
Canonical JSON serialization and content hashing.

Provides stable, platform-independent serialization for content hashing.
The canonicalization ensures:
- Keys are sorted recursively
- Unicode is normalized (NFC)
- No insignificant whitespace
- Stable float formatting
- Consistent null handling
"""

import hashlib
import json
import unicodedata
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExchangeRecord


def canonicalize(obj: Any) -> str:
    """
    Canonicalize a Python object to a stable JSON string.
    
    This function ensures:
    - Keys are sorted recursively at all levels
    - Unicode is normalized (NFC form)
    - No extra whitespace
    - Consistent float formatting
    - None values are represented as JSON null
    
    Args:
        obj: The object to canonicalize
        
    Returns:
        Canonical JSON string
    """
    return json.dumps(
        _normalize_for_canonical(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_canonical_default,
    )


def _normalize_for_canonical(obj: Any) -> Any:
    """
    Recursively normalize an object for canonical serialization.
    
    - Normalizes unicode strings (NFC)
    - Recursively processes dicts and lists
    - Handles special types
    """
    if obj is None:
        return None
    
    if isinstance(obj, str):
        # Normalize unicode to NFC form
        return unicodedata.normalize("NFC", obj)
    
    if isinstance(obj, bool):
        # Handle bool before int (bool is subclass of int)
        return obj
    
    if isinstance(obj, (int, float)):
        return obj
    
    if isinstance(obj, dict):
        # Recursively normalize dict values
        return {
            _normalize_for_canonical(k): _normalize_for_canonical(v)
            for k, v in obj.items()
        }
    
    if isinstance(obj, (list, tuple)):
        # Recursively normalize list items
        return [_normalize_for_canonical(item) for item in obj]
    
    # For other types, convert to string and normalize
    return unicodedata.normalize("NFC", str(obj))


def _canonical_default(obj: Any) -> Any:
    """
    Default handler for JSON serialization of non-standard types.
    """
    if hasattr(obj, "isoformat"):
        # datetime objects
        return obj.isoformat()
    
    if hasattr(obj, "to_dict"):
        # Objects with to_dict method
        return obj.to_dict()
    
    # Last resort: string conversion
    return str(obj)


def compute_content_hash(record: "ExchangeRecord") -> str:
    """
    Compute SHA256 hash of an ExchangeRecord's semantic content.
    
    The hash is computed over the canonical representation of:
    - exchange_type
    - source_system
    - entity_type
    - natural_key
    - request
    - response
    
    Note: observed_at_utc is explicitly excluded from the hash to allow
    re-fetching the same content without hash collision.
    
    Args:
        record: The ExchangeRecord to hash
        
    Returns:
        Hex-encoded SHA256 hash string
    """
    hash_input = build_hash_input(
        exchange_type=record.exchange_type,
        source_system=record.source_system,
        entity_type=record.entity_type,
        natural_key=record.natural_key,
        request=record.request,
        response=record.response,
    )
    
    canonical_str = canonicalize(hash_input)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def build_hash_input(
    exchange_type: str,
    source_system: str,
    entity_type: str,
    natural_key: Optional[str] = None,
    request: Optional[Dict[str, Any]] = None,
    response: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Build the hash input object from components.
    
    This is the semantic identity of a record that determines its content hash.
    """
    return {
        "exchange_type": exchange_type,
        "source_system": source_system,
        "entity_type": entity_type,
        "natural_key": natural_key,
        "request": request,
        "response": response,
    }


def verify_content_hash(record: "ExchangeRecord") -> bool:
    """
    Verify that a record's content_sha256 matches its computed hash.
    
    Args:
        record: The ExchangeRecord to verify
        
    Returns:
        True if the hash matches, False otherwise
    """
    computed = compute_content_hash(record)
    return computed == record.content_sha256
