"""
Indexer - Index sources into chunks with embeddings for retrieval.

Implements:
- Source manifest parsing
- Full and incremental indexing modes
- Chunk creation and embedding generation
- Persistence to SQL Server and lake artifacts

NOTE: As of Phase 2, this module uses the `vector` schema exclusively via VectorStore.
      The legacy `llm.*` vector tables are deprecated.

Usage:
    python -m src.llm.retrieval.indexer --source-manifest <path> --mode full
    python -m src.llm.retrieval.indexer --source-manifest <path> --mode incremental
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..contracts.retrieval_contracts import (
    ChunkingPolicy,
    ChunkRecord,
    EmbeddingRecord,
    compute_content_hash,
    compute_vector_hash,
)
from ..core.types import LLMConfig
from ..providers.ollama_client import OllamaClient
from .chunker import Chunker

# Phase 2: Use VectorStore from the vector schema (primary)
from ...vector.store import VectorStore
from ...vector.contracts.models import (
    VectorChunk,
    VectorEmbedding,
    VectorSourceRegistry,
    SourceStatus,
)


logger = logging.getLogger(__name__)


@dataclass
class IndexerConfig:
    """Configuration for the indexer."""
    ollama_base_url: str = "http://ollama:11434"
    embed_model: str = "nomic-embed-text"
    chunk_size: int = 2000
    chunk_overlap: int = 200
    max_chunks_per_source: int = 100
    embed_concurrency: int = 1
    lake_root: str = "lake"
    
    @classmethod
    def from_env(cls) -> "IndexerConfig":
        """Create config from environment variables."""
        return cls(
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            embed_model=os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            chunk_size=int(os.environ.get("INDEX_CHUNK_SIZE", "2000")),
            chunk_overlap=int(os.environ.get("INDEX_CHUNK_OVERLAP", "200")),
            max_chunks_per_source=int(os.environ.get("INDEX_MAX_CHUNKS_PER_SOURCE", "100")),
            embed_concurrency=int(os.environ.get("INDEX_EMBED_CONCURRENCY", "1")),
            lake_root=os.environ.get("LAKE_ROOT", "lake"),
        )


@dataclass
class SourceManifest:
    """
    Manifest of sources to index.
    
    Format:
    {
        "version": "1.0",
        "sources": [
            {
                "source_id": "unique-id",
                "source_type": "lake_text",
                "lake_uri": "path/to/file.txt",
                "tags": {"franchise": "starwars"}
            }
        ]
    }
    """
    version: str
    sources: List[Dict[str, Any]]
    
    @classmethod
    def from_file(cls, path: str) -> "SourceManifest":
        """Load manifest from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            version=data.get("version", "1.0"),
            sources=data.get("sources", []),
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceManifest":
        """Create from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            sources=data.get("sources", []),
        )


class Indexer:
    """
    Indexes sources into chunks with embeddings.
    
    Workflow:
    1. Read source manifest
    2. For each source:
       a. Extract text content
       b. Chunk into searchable units
       c. Generate embeddings
       d. Store chunks and embeddings
    3. Write indexing run manifest to lake
    
    NOTE: As of Phase 2, this uses VectorStore exclusively (vector schema).
    """
    
    def __init__(
        self,
        config: IndexerConfig,
        store: Optional[VectorStore] = None,
        embedding_space_id: Optional[str] = None,
    ):
        """
        Initialize the indexer.
        
        Args:
            config: Indexer configuration
            store: VectorStore for database operations (uses vector.* tables)
            embedding_space_id: Optional embedding space ID for lineage
        """
        self.config = config
        self.store = store
        self.embedding_space_id = embedding_space_id
        
        # Create chunking policy
        self.chunking_policy = ChunkingPolicy(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap,
            max_chunks_per_source=config.max_chunks_per_source,
        )
        self.chunker = Chunker(self.chunking_policy)
        
        # Create Ollama client for embeddings
        llm_config = LLMConfig(
            provider="ollama",
            model=config.embed_model,
            base_url=config.ollama_base_url,
            timeout_seconds=120,
        )
        self.ollama = OllamaClient(llm_config)
    
    def index_manifest(
        self,
        manifest: SourceManifest,
        mode: str = "full",
    ) -> Dict[str, Any]:
        """
        Index all sources in a manifest.
        
        Args:
            manifest: Source manifest to index
            mode: "full" (re-index all) or "incremental" (skip unchanged)
            
        Returns:
            Indexing run summary
        """
        run_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Starting indexing run {run_id} ({mode} mode)")
        logger.info(f"Processing {len(manifest.sources)} sources")
        
        stats = {
            "run_id": run_id,
            "mode": mode,
            "sources_processed": 0,
            "sources_skipped": 0,
            "chunks_created": 0,
            "embeddings_created": 0,
            "errors": [],
        }
        
        for source in manifest.sources:
            try:
                result = self._index_source(source, mode)
                if result["skipped"]:
                    stats["sources_skipped"] += 1
                else:
                    stats["sources_processed"] += 1
                    stats["chunks_created"] += result["chunks_created"]
                    stats["embeddings_created"] += result["embeddings_created"]
            except Exception as e:
                logger.error(f"Error indexing source {source.get('source_id')}: {e}")
                stats["errors"].append({
                    "source_id": source.get("source_id"),
                    "error": str(e),
                })
        
        stats["duration_seconds"] = round(time.time() - start_time, 2)
        
        # Write run manifest to lake
        self._write_run_manifest(run_id, manifest, stats)
        
        logger.info(
            f"Indexing run {run_id} complete: "
            f"{stats['sources_processed']} processed, "
            f"{stats['sources_skipped']} skipped, "
            f"{stats['chunks_created']} chunks, "
            f"{stats['embeddings_created']} embeddings"
        )
        
        return stats
    
    def _index_source(self, source: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        Index a single source.
        
        Args:
            source: Source definition from manifest
            mode: "full" or "incremental"
            
        Returns:
            Indexing result for this source
        """
        source_id = source.get("source_id")
        source_type = source.get("source_type", "lake_text")
        lake_uri = source.get("lake_uri")
        tags = source.get("tags", {})
        
        logger.debug(f"Indexing source {source_id} ({source_type})")
        
        # Load content
        content = self._load_source_content(source)
        if not content:
            logger.warning(f"No content for source {source_id}")
            return {"skipped": True, "chunks_created": 0, "embeddings_created": 0}
        
        content_hash = compute_content_hash(content)
        
        # Incremental mode: check if already indexed with same content
        if mode == "incremental" and self.store:
            if self._source_already_indexed(source_id, content_hash):
                logger.debug(f"Source {source_id} already indexed with same content, skipping")
                return {"skipped": True, "chunks_created": 0, "embeddings_created": 0}
        
        # Build source reference
        source_ref = {
            "source_id": source_id,
            "lake_uri": lake_uri,
            "tags": tags,
        }
        
        # Chunk the content
        chunks = self.chunker.chunk(
            content=content,
            source_id=source_id,
            source_type=source_type,
            source_ref=source_ref,
        )
        
        if not chunks:
            return {"skipped": False, "chunks_created": 0, "embeddings_created": 0}
        
        # Save chunks to database using VectorStore (vector schema)
        if self.store:
            for chunk in chunks:
                # Convert ChunkRecord to VectorChunk for the new schema
                vector_chunk = VectorChunk(
                    chunk_id=chunk.chunk_id,
                    source_id=source_id,
                    source_type=chunk.source_type,
                    source_ref=chunk.source_ref,
                    offsets=chunk.offsets,
                    content=chunk.content,
                    content_sha256=chunk.content_sha256,
                    byte_count=chunk.byte_count,
                    policy=chunk.policy,
                )
                self.store.save_chunk(vector_chunk)
        
        # Generate embeddings
        embeddings_created = 0
        chunk_texts = [chunk.content for chunk in chunks]
        
        # Batch embedding for efficiency
        try:
            embed_response = self.ollama.embed(chunk_texts, model=self.config.embed_model)
            
            if embed_response.success and embed_response.embeddings:
                for chunk, vector in zip(chunks, embed_response.embeddings):
                    # Use VectorEmbedding for the new schema (requires embedding_space_id)
                    if self.store and self.embedding_space_id:
                        vector_embedding = VectorEmbedding.create_new(
                            chunk_id=chunk.chunk_id,
                            embedding_space_id=self.embedding_space_id,
                            input_content_sha256=chunk.content_sha256,
                            vector=vector,
                        )
                        self.store.save_embedding(vector_embedding)
                    
                    embeddings_created += 1
        except Exception as e:
            logger.error(f"Error generating embeddings for source {source_id}: {e}")
        
        # Update source registry for incremental indexing support
        self._update_source_registry(
            source_id=source_id,
            source_type=source_type,
            source_ref=source_ref,
            content_hash=content_hash,
            chunk_count=len(chunks),
            tags=tags,
        )
        
        return {
            "skipped": False,
            "chunks_created": len(chunks),
            "embeddings_created": embeddings_created,
        }
    
    def _load_source_content(self, source: Dict[str, Any]) -> Optional[str]:
        """
        Load content from a source.
        
        Supports:
        - lake_text: Read file from lake
        - lake_http: Read HTTP response artifact
        - inline: Use content directly from source
        
        Args:
            source: Source definition
            
        Returns:
            Text content, or None if not loadable
        """
        source_type = source.get("source_type", "lake_text")
        
        if source_type == "inline":
            return source.get("content")
        
        lake_uri = source.get("lake_uri")
        if not lake_uri:
            return None
        
        # Construct full path
        full_path = Path(self.config.lake_root) / lake_uri
        
        if not full_path.exists():
            logger.warning(f"Source file not found: {full_path}")
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading source {lake_uri}: {e}")
            return None
    
    def _source_already_indexed(self, source_id: str, content_hash: str) -> bool:
        """
        Check if a source has already been indexed with the same content.
        
        Uses the VectorStore.source_already_indexed method to check vector.source_registry.
        
        Args:
            source_id: Source identifier
            content_hash: SHA256 hash of content
            
        Returns:
            True if source is already indexed with same content
        """
        if not self.store:
            return False
        
        try:
            return self.store.source_already_indexed(source_id, content_hash)
        except Exception as e:
            logger.debug(f"Could not check source registry: {e}")
            return False
    
    def _update_source_registry(
        self,
        source_id: str,
        source_type: str,
        source_ref: Dict[str, Any],
        content_hash: str,
        chunk_count: int,
        tags: Dict[str, Any],
    ) -> None:
        """
        Update the source registry with indexing information.
        
        Uses VectorStore.save_source_registry to update vector.source_registry.
        
        Args:
            source_id: Source identifier
            source_type: Type of source
            source_ref: Source reference metadata
            content_hash: Content hash
            chunk_count: Number of chunks created
            tags: Source tags
        """
        if not self.store:
            return
        
        try:
            source_entry = VectorSourceRegistry(
                source_id=source_id,
                source_type=source_type,
                source_ref=source_ref,
                content_sha256=content_hash,
                last_indexed_utc=datetime.now(timezone.utc),
                chunk_count=chunk_count,
                tags=tags,
                status=SourceStatus.INDEXED,
            )
            self.store.save_source_registry(source_entry)
            
        except Exception as e:
            logger.warning(f"Could not update source registry: {e}")
    
    def _write_run_manifest(
        self,
        run_id: str,
        manifest: SourceManifest,
        stats: Dict[str, Any],
    ) -> None:
        """
        Write indexing run manifest to lake.
        
        Args:
            run_id: Run ID
            manifest: Source manifest
            stats: Indexing statistics
        """
        run_manifest = {
            "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_version": manifest.version,
            "source_count": len(manifest.sources),
            "chunking_policy": self.chunking_policy.to_dict(),
            "embedding_model": self.config.embed_model,
            "stats": stats,
        }
        
        # Write to lake
        lake_dir = Path(self.config.lake_root) / "llm_index" / run_id
        lake_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = lake_dir / "run_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(run_manifest, f, indent=2)
        
        logger.debug(f"Wrote run manifest to {manifest_path}")


def main():
    """CLI entry point for the indexer."""
    parser = argparse.ArgumentParser(
        description="Index sources for retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--source-manifest",
        type=str,
        required=True,
        help="Path to source manifest JSON file"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Indexing mode (default: full)"
    )
    parser.add_argument(
        "--embed-model",
        type=str,
        default=None,
        help="Embedding model (default: from OLLAMA_EMBED_MODEL or nomic-embed-text)"
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=None,
        help="Ollama base URL (default: from OLLAMA_BASE_URL)"
    )
    parser.add_argument(
        "--lake-root",
        type=str,
        default=None,
        help="Lake root directory (default: from LAKE_ROOT)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size in characters (default: 2000)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Chunk overlap in characters (default: 200)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Build config
    config = IndexerConfig.from_env()
    
    if args.embed_model:
        config.embed_model = args.embed_model
    if args.ollama_url:
        config.ollama_base_url = args.ollama_url
    if args.lake_root:
        config.lake_root = args.lake_root
    if args.chunk_size:
        config.chunk_size = args.chunk_size
    if args.chunk_overlap:
        config.chunk_overlap = args.chunk_overlap
    
    # Load manifest
    try:
        manifest = SourceManifest.from_file(args.source_manifest)
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        sys.exit(1)
    
    # Create indexer (no DB store for CLI mode - will use lake only)
    indexer = Indexer(config, store=None)
    
    # Run indexing
    try:
        stats = indexer.index_manifest(manifest, mode=args.mode)
        
        # Output summary
        print(f"\nIndexing complete:")
        print(f"  Run ID: {stats['run_id']}")
        print(f"  Sources processed: {stats['sources_processed']}")
        print(f"  Sources skipped: {stats['sources_skipped']}")
        print(f"  Chunks created: {stats['chunks_created']}")
        print(f"  Embeddings created: {stats['embeddings_created']}")
        print(f"  Duration: {stats['duration_seconds']}s")
        
        if stats['errors']:
            print(f"  Errors: {len(stats['errors'])}")
            for err in stats['errors']:
                print(f"    - {err['source_id']}: {err['error']}")
        
        sys.exit(0 if not stats['errors'] else 1)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
