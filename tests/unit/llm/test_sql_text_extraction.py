"""
Unit tests for SQL evidence text extraction.

Tests for:
- SQL result set text formatting
- Row/column bounding
- Sampling strategies (first_only, first_last, stride)
- Metadata recording
"""

import pytest

from llm.evidence.text_extractors import extract_sql_result_text


class TestExtractSqlResultText:
    """Tests for SQL result text extraction."""
    
    def test_simple_result(self):
        """Test simple SQL result extraction."""
        rows = [
            ["Alice", 30],
            ["Bob", 25],
        ]
        columns = ["name", "age"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=10, max_cols=10)
        
        assert "Alice" in text
        assert "Bob" in text
        assert "name" in text
        assert "age" in text
        assert meta["total_rows"] == 2
        assert meta["total_cols"] == 2
        assert meta["sampled_rows"] == 2
    
    def test_all_rows_included(self):
        """Test when all rows fit within limit."""
        rows = [[i] for i in range(5)]
        columns = ["value"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=10, max_cols=10)
        
        assert meta["sampling_note"] == "All rows included"
        assert meta["sampled_rows"] == 5
    
    def test_first_only_sampling(self):
        """Test first_only sampling strategy."""
        rows = [[i] for i in range(20)]
        columns = ["value"]
        
        text, meta = extract_sql_result_text(
            rows, columns, max_rows=5, max_cols=10, sampling_strategy="first_only"
        )
        
        assert meta["sampled_rows"] == 5
        assert meta["total_rows"] == 20
        assert "First 5 rows" in meta["sampling_note"]
        # First rows should be present
        assert "Row 0" in text
        assert "Row 4" in text
    
    def test_first_last_sampling(self):
        """Test first_last sampling strategy."""
        rows = [[i] for i in range(20)]
        columns = ["value"]
        
        text, meta = extract_sql_result_text(
            rows, columns, max_rows=10, max_cols=10, sampling_strategy="first_last"
        )
        
        assert meta["sampled_rows"] == 10
        assert "First 5 and last 5 rows" in meta["sampling_note"]
        # Should include first and last
        assert "Row 0" in text  # First row
        assert "Row 4" in text  # Last of first half
    
    def test_stride_sampling(self):
        """Test stride sampling strategy."""
        rows = [[i] for i in range(100)]
        columns = ["value"]
        
        text, meta = extract_sql_result_text(
            rows, columns, max_rows=10, max_cols=10, sampling_strategy="stride"
        )
        
        assert meta["sampled_rows"] == 10
        # Check for "every Nth row" pattern in sampling note
        assert "every" in meta["sampling_note"].lower() or "stride" in meta["sampling_note"].lower()
    
    def test_column_truncation(self):
        """Test column truncation."""
        rows = [[1, 2, 3, 4, 5]]
        columns = ["col1", "col2", "col3", "col4", "col5"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=10, max_cols=3)
        
        assert meta["sampled_cols"] == 3
        assert meta["total_cols"] == 5
        assert meta["cols_truncated"] is True
        assert "Showing 3 of 5 columns" in text
    
    def test_dict_rows(self):
        """Test handling dict rows."""
        rows = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        columns = ["name", "age"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=10, max_cols=10)
        
        assert "Alice" in text
        assert "Bob" in text
        assert meta["total_rows"] == 2
    
    def test_empty_result(self):
        """Test empty result set."""
        rows = []
        columns = ["col1", "col2"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=10, max_cols=10)
        
        assert meta["total_rows"] == 0
        assert meta["sampled_rows"] == 0
        assert "0 rows" in text
    
    def test_metadata_structure(self):
        """Test metadata structure."""
        rows = [[i] for i in range(10)]
        columns = ["value"]
        
        text, meta = extract_sql_result_text(rows, columns, max_rows=5, max_cols=10)
        
        assert "total_rows" in meta
        assert "total_cols" in meta
        assert "sampled_rows" in meta
        assert "sampled_cols" in meta
        assert "sampling_strategy" in meta
        assert "sampling_note" in meta
        assert "cols_truncated" in meta
    
    def test_large_result_set(self):
        """Test handling of large result set."""
        rows = [[f"value_{i}"] for i in range(1000)]
        columns = ["data"]
        
        text, meta = extract_sql_result_text(
            rows, columns, max_rows=50, max_cols=10, sampling_strategy="first_only"
        )
        
        assert meta["sampled_rows"] == 50
        assert meta["total_rows"] == 1000
        assert len(text) < len(str(rows))  # Should be bounded
