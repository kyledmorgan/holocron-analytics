"""
Retrieval module for RAG (2026_01_llm_derived_data_phase_3).

This module provides:
- Chunking: Split documents into searchable units
- Indexing: Generate embeddings and store in database
- Search: Retrieve relevant chunks for queries
"""

from .chunker import Chunker, chunk_text
from .search import retrieve_chunks, cosine_similarity

__all__ = [
    "Chunker",
    "chunk_text",
    "retrieve_chunks",
    "cosine_similarity",
]
