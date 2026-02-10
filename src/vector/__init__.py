"""
Vector Runtime Module

This module provides infrastructure for embedding generation, storage, and
retrieval. It operates on the `vector` schema, separate from the `llm` 
chat runtime schema.

Key components:
- contracts/: Data models for vector operations
- store.py: VectorStore class for database operations

Key concepts:
- Embedding Space: First-class identity for embedding models. Vectors from
  different spaces must not be compared.
- Chunk: A bounded unit of text for embedding and retrieval.
- Embedding: A vector representation of a chunk with lineage tracking.
- Retrieval: Query logging for audit and evaluation.

Phase 1 of the schema refactor (additive, parallel with legacy llm.* tables).
"""

__version__ = "0.1.0"
