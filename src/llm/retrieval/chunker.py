"""
Chunker - Split documents into searchable units for retrieval.

Implements configurable chunking with:
- Chunk size and overlap
- Deterministic chunk IDs
- Maximum chunks per source
"""

import logging
from typing import List, Optional

from ..contracts.retrieval_contracts import (
    ChunkRecord,
    ChunkingPolicy,
    compute_content_hash,
    generate_chunk_id,
)

logger = logging.getLogger(__name__)


class Chunker:
    """
    Chunks text content into searchable units.
    
    Produces deterministic chunks with stable IDs for reproducible indexing.
    
    Example:
        >>> chunker = Chunker(ChunkingPolicy(chunk_size=1000, overlap=100))
        >>> chunks = chunker.chunk(
        ...     content="Long document text...",
        ...     source_id="lake://docs/example.txt",
        ...     source_type="lake_text"
        ... )
    """
    
    def __init__(self, policy: Optional[ChunkingPolicy] = None):
        """
        Initialize the chunker.
        
        Args:
            policy: Chunking policy (uses default if not provided)
        """
        self.policy = policy or ChunkingPolicy()
    
    def chunk(
        self,
        content: str,
        source_id: str,
        source_type: str,
        source_ref: Optional[dict] = None,
    ) -> List[ChunkRecord]:
        """
        Split content into chunks.
        
        Args:
            content: Text content to chunk
            source_id: Unique identifier for the source
            source_type: Type of source (lake_text, lake_http, doc, etc.)
            source_ref: Optional source reference metadata
            
        Returns:
            List of ChunkRecord objects
        """
        if not content:
            return []
        
        source_ref = source_ref or {"source_id": source_id}
        
        # Split content into chunks
        raw_chunks = chunk_text(
            content,
            chunk_size=self.policy.chunk_size,
            overlap=self.policy.overlap,
        )
        
        # Limit number of chunks per source
        if len(raw_chunks) > self.policy.max_chunks_per_source:
            logger.warning(
                f"Source {source_id} has {len(raw_chunks)} chunks, "
                f"limiting to {self.policy.max_chunks_per_source}"
            )
            raw_chunks = raw_chunks[:self.policy.max_chunks_per_source]
        
        # Create chunk records
        chunks = []
        for i, (chunk_content, start_offset, end_offset) in enumerate(raw_chunks):
            chunk_id = generate_chunk_id(
                source_id=source_id,
                chunk_index=i,
                start_offset=start_offset,
                end_offset=end_offset,
                policy_version=self.policy.version,
            )
            
            content_hash = compute_content_hash(chunk_content)
            byte_count = len(chunk_content.encode('utf-8'))
            
            chunk = ChunkRecord(
                chunk_id=chunk_id,
                source_type=source_type,
                source_ref=source_ref,
                offsets={
                    "chunk_index": i,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                },
                content=chunk_content,
                content_sha256=content_hash,
                byte_count=byte_count,
                policy=self.policy.to_dict(),
            )
            chunks.append(chunk)
        
        logger.debug(f"Created {len(chunks)} chunks from source {source_id}")
        return chunks


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200,
) -> List[tuple]:
    """
    Split text into overlapping chunks.
    
    Returns chunks with their character offsets for reproducibility.
    
    Args:
        text: Text content to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of tuples: (chunk_content, start_offset, end_offset)
    """
    if not text:
        return []
    
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")
    
    chunks = []
    text_len = len(text)
    step = chunk_size - overlap
    
    start = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_content = text[start:end]
        
        # Try to break at word boundary if not at end
        if end < text_len and len(chunk_content) == chunk_size:
            # Find last space in the chunk
            last_space = chunk_content.rfind(' ')
            if last_space > chunk_size // 2:
                # Adjust end to word boundary
                end = start + last_space
                chunk_content = text[start:end]
        
        chunks.append((chunk_content, start, end))
        
        # Move to next chunk
        start = start + step
        
        # If we're at the end, stop
        if end >= text_len:
            break
    
    return chunks
