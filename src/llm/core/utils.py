"""
Core Utilities - Shared utility functions for the LLM module.

Provides common helper functions used across contracts, retrieval, and other modules.
"""

import hashlib
import json
from typing import List


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of text content.
    
    This is a shared utility for content hashing used by evidence contracts,
    retrieval contracts, and other modules that need content integrity checks.
    
    Args:
        content: Text content to hash
        
    Returns:
        Hex-encoded SHA256 hash (64 characters)
        
    Example:
        >>> compute_content_hash("Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
    """
    return hashlib.sha256(content.encode()).hexdigest()


def compute_vector_hash(vector: List[float]) -> str:
    """
    Compute SHA256 hash of an embedding vector.
    
    Serializes the vector to a consistent JSON format before hashing to ensure
    deterministic results across different Python versions and environments.
    
    Args:
        vector: Embedding vector as list of floats
        
    Returns:
        Hex-encoded SHA256 hash (64 characters)
        
    Example:
        >>> compute_vector_hash([0.1, 0.2, 0.3])
        # Returns consistent hash for the vector
    """
    # Use high precision to avoid floating point representation issues
    vector_str = json.dumps([round(v, 10) for v in vector], separators=(',', ':'))
    return hashlib.sha256(vector_str.encode()).hexdigest()
