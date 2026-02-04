"""
Unit tests for Phase 3 retrieval search functionality.

Tests for:
- Cosine similarity scoring
- Retrieval ranking and ordering
- Deterministic tie-breaking
"""

import pytest

from llm.retrieval.search import cosine_similarity, retrieve_chunks
from llm.contracts.retrieval_contracts import RetrievalPolicy


class TestCosineSimilarity:
    """Tests for the cosine_similarity function."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors is 1.0."""
        vec = [1.0, 2.0, 3.0, 4.0]
        similarity = cosine_similarity(vec, vec)
        
        assert abs(similarity - 1.0) < 1e-9
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors is 0.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec_a, vec_b)
        
        assert abs(similarity) < 1e-9
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors is -1.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]
        similarity = cosine_similarity(vec_a, vec_b)
        
        assert abs(similarity - (-1.0)) < 1e-9
    
    def test_similar_vectors(self):
        """Test similarity of similar vectors is high."""
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [1.1, 2.1, 3.1]
        similarity = cosine_similarity(vec_a, vec_b)
        
        assert similarity > 0.99
    
    def test_different_vectors(self):
        """Test similarity of different vectors."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 1.0, 0.0]
        similarity = cosine_similarity(vec_a, vec_b)
        
        # cos(45°) ≈ 0.707
        assert 0.7 < similarity < 0.72
    
    def test_empty_vector_error(self):
        """Test that empty vectors raise error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            cosine_similarity([], [1.0])
        
        with pytest.raises(ValueError, match="cannot be empty"):
            cosine_similarity([1.0], [])
    
    def test_dimension_mismatch_error(self):
        """Test that mismatched dimensions raise error."""
        with pytest.raises(ValueError, match="dimensions must match"):
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
    
    def test_zero_vector(self):
        """Test similarity with zero vector is 0."""
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [0.0, 0.0, 0.0]
        similarity = cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0
    
    def test_normalized_vectors(self):
        """Test with already normalized vectors."""
        import math
        vec_a = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2)]
        vec_b = [1.0, 0.0]
        similarity = cosine_similarity(vec_a, vec_b)
        
        assert abs(similarity - (1.0 / math.sqrt(2))) < 1e-9


class TestRetrieveChunks:
    """Tests for the retrieve_chunks function."""
    
    def test_basic_retrieval(self):
        """Test basic top-K retrieval."""
        query_embedding = [1.0, 0.0, 0.0]
        candidates = [
            {"chunk_id": "a", "vector": [1.0, 0.0, 0.0]},  # Perfect match
            {"chunk_id": "b", "vector": [0.9, 0.1, 0.0]},  # Good match
            {"chunk_id": "c", "vector": [0.0, 1.0, 0.0]},  # Orthogonal
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test query",
            embedding_model="test-model",
            top_k=2,
        )
        
        assert len(result.hits) == 2
        assert result.hits[0].chunk_id == "a"  # Best match first
        assert result.hits[0].score > result.hits[1].score
    
    def test_ranking_order(self):
        """Test that results are ranked by score descending."""
        query_embedding = [1.0, 0.0]
        candidates = [
            {"chunk_id": "c", "vector": [0.5, 0.5]},  # Medium
            {"chunk_id": "a", "vector": [1.0, 0.0]},  # Best
            {"chunk_id": "b", "vector": [0.7, 0.3]},  # Good
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=3,
        )
        
        # Verify descending score order
        scores = [hit.score for hit in result.hits]
        assert scores == sorted(scores, reverse=True)
    
    def test_deterministic_tie_breaking(self):
        """Test that ties are broken by chunk_id."""
        query_embedding = [1.0, 0.0]
        # All same score
        candidates = [
            {"chunk_id": "c", "vector": [1.0, 0.0]},
            {"chunk_id": "a", "vector": [1.0, 0.0]},
            {"chunk_id": "b", "vector": [1.0, 0.0]},
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=3,
        )
        
        # Should be sorted by chunk_id for ties
        chunk_ids = [hit.chunk_id for hit in result.hits]
        assert chunk_ids == ["a", "b", "c"]
    
    def test_top_k_limit(self):
        """Test that top_k limits results."""
        query_embedding = [1.0, 0.0, 0.0]
        candidates = [
            {"chunk_id": f"chunk{i}", "vector": [1.0, 0.0, 0.0]}
            for i in range(10)
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=5,
        )
        
        assert len(result.hits) == 5
    
    def test_fewer_candidates_than_top_k(self):
        """Test when fewer candidates than top_k."""
        query_embedding = [1.0, 0.0]
        candidates = [
            {"chunk_id": "a", "vector": [1.0, 0.0]},
            {"chunk_id": "b", "vector": [0.9, 0.1]},
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=10,
        )
        
        assert len(result.hits) == 2
    
    def test_empty_candidates(self):
        """Test with no candidates."""
        query_embedding = [1.0, 0.0]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=[],
            query_text="test",
            embedding_model="model",
            top_k=5,
        )
        
        assert len(result.hits) == 0
        assert result.total_candidates == 0
    
    def test_min_score_threshold(self):
        """Test minimum score threshold filtering."""
        query_embedding = [1.0, 0.0]
        candidates = [
            {"chunk_id": "a", "vector": [1.0, 0.0]},  # Score 1.0
            {"chunk_id": "b", "vector": [0.0, 1.0]},  # Score 0.0
        ]
        
        policy = RetrievalPolicy(min_score_threshold=0.5)
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=10,
            policy=policy,
        )
        
        assert len(result.hits) == 1
        assert result.hits[0].chunk_id == "a"
    
    def test_rank_assignment(self):
        """Test that ranks are assigned correctly (1-indexed)."""
        query_embedding = [1.0, 0.0]
        candidates = [
            {"chunk_id": "a", "vector": [1.0, 0.0]},
            {"chunk_id": "b", "vector": [0.9, 0.1]},
            {"chunk_id": "c", "vector": [0.8, 0.2]},
        ]
        
        result = retrieve_chunks(
            query_embedding=query_embedding,
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=3,
        )
        
        ranks = [hit.rank for hit in result.hits]
        assert ranks == [1, 2, 3]
    
    def test_retrieval_id_generated(self):
        """Test that retrieval ID is generated."""
        result = retrieve_chunks(
            query_embedding=[1.0, 0.0],
            candidate_embeddings=[{"chunk_id": "a", "vector": [1.0, 0.0]}],
            query_text="test",
            embedding_model="model",
            top_k=1,
        )
        
        assert result.query.retrieval_id
        assert len(result.query.retrieval_id) == 36  # UUID format
    
    def test_metadata_preserved(self):
        """Test that candidate metadata is preserved in hits."""
        candidates = [
            {
                "chunk_id": "a",
                "vector": [1.0, 0.0],
                "metadata": {"source_type": "doc", "custom": "value"},
            }
        ]
        
        result = retrieve_chunks(
            query_embedding=[1.0, 0.0],
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=1,
        )
        
        assert result.hits[0].metadata["source_type"] == "doc"
        assert result.hits[0].metadata["custom"] == "value"
    
    def test_result_contains_query_info(self):
        """Test that result contains query information."""
        result = retrieve_chunks(
            query_embedding=[1.0, 0.0],
            candidate_embeddings=[{"chunk_id": "a", "vector": [1.0, 0.0]}],
            query_text="my test query",
            embedding_model="nomic-embed-text",
            top_k=5,
            run_id="run-123",
        )
        
        assert result.query.query_text == "my test query"
        assert result.query.query_embedding_model == "nomic-embed-text"
        assert result.query.top_k == 5
        assert result.query.run_id == "run-123"
    
    def test_execution_time_recorded(self):
        """Test that execution time is recorded."""
        result = retrieve_chunks(
            query_embedding=[1.0, 0.0],
            candidate_embeddings=[{"chunk_id": "a", "vector": [1.0, 0.0]}],
            query_text="test",
            embedding_model="model",
            top_k=1,
        )
        
        assert result.execution_ms is not None
        assert result.execution_ms >= 0
    
    def test_total_candidates_count(self):
        """Test that total candidates count is accurate."""
        candidates = [
            {"chunk_id": f"c{i}", "vector": [1.0, 0.0]}
            for i in range(20)
        ]
        
        result = retrieve_chunks(
            query_embedding=[1.0, 0.0],
            candidate_embeddings=candidates,
            query_text="test",
            embedding_model="model",
            top_k=5,
        )
        
        assert result.total_candidates == 20
        assert len(result.hits) == 5
