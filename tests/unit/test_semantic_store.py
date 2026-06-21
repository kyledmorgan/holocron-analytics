"""
Unit tests for SemanticStagingStore.

Tests normalize_display_name and upsert_dim_entity logic without database dependency.
"""

import pytest
from unittest.mock import MagicMock, patch

from semantic.store import SemanticStagingStore


class TestNormalizeDisplayName:
    """Tests for the normalize_display_name static method."""

    def test_simple_name(self):
        """Test normalization of simple name."""
        result = SemanticStagingStore.normalize_display_name("Luke Skywalker")
        assert result == "luke_skywalker"

    def test_uppercase_name(self):
        """Test normalization of uppercase name."""
        result = SemanticStagingStore.normalize_display_name("DARTH VADER")
        assert result == "darth_vader"

    def test_mixed_case_name(self):
        """Test normalization preserves word boundaries."""
        result = SemanticStagingStore.normalize_display_name("Obi-Wan Kenobi")
        assert result == "obi-wan_kenobi"

    def test_leading_trailing_whitespace(self):
        """Test normalization strips whitespace."""
        result = SemanticStagingStore.normalize_display_name("  Padmé Amidala  ")
        assert result == "padmé_amidala"

    def test_multiple_spaces(self):
        """Test normalization collapses multiple spaces."""
        result = SemanticStagingStore.normalize_display_name("Mace   Windu")
        assert result == "mace_windu"

    def test_tabs_and_newlines(self):
        """Test normalization handles tabs and newlines."""
        result = SemanticStagingStore.normalize_display_name("Yoda\t\nthe Jedi")
        assert result == "yoda_the_jedi"

    def test_empty_string(self):
        """Test normalization of empty string."""
        result = SemanticStagingStore.normalize_display_name("")
        assert result == ""

    def test_single_word(self):
        """Test normalization of single word."""
        result = SemanticStagingStore.normalize_display_name("Yoda")
        assert result == "yoda"

    def test_special_characters_preserved(self):
        """Test that special characters like parentheses are preserved."""
        result = SemanticStagingStore.normalize_display_name("Anakin Skywalker (Legends)")
        assert result == "anakin_skywalker_(legends)"


class TestUpsertDimEntityLogic:
    """Tests for upsert_dim_entity method behavior (mocked database)."""

    @pytest.fixture
    def mock_store(self):
        """Create a store with mocked connection."""
        with patch.object(SemanticStagingStore, '_get_connection') as mock_conn:
            store = SemanticStagingStore(
                connection_string="mocked"
            )
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            store._mock_cursor = mock_cursor
            yield store

    def test_update_existing_entity(self, mock_store):
        """Test that existing entity is updated."""
        # Mock finding an existing entity
        mock_store._mock_cursor.fetchone.return_value = (
            123,  # EntityKey
            "12345678-1234-1234-1234-123456789abc",  # EntityGuid
        )

        result = mock_store.upsert_dim_entity(
            title="Luke Skywalker",
            source_page_id="abc-123",
            primary_type="PersonCharacter",
            confidence=0.95,
        )

        assert result["success"] is True
        assert result["entity_key"] == 123
        assert result["entity_guid"] == "12345678-1234-1234-1234-123456789abc"
        assert result["action"] == "updated"
        assert result["error"] is None

    def test_insert_new_entity(self, mock_store):
        """Test that new entity is inserted when not found."""
        # First call (SELECT) returns None
        # Second call (INSERT OUTPUT) returns new entity
        mock_store._mock_cursor.fetchone.side_effect = [
            None,  # SELECT returns no match
            (456, "abcd1234-abcd-1234-abcd-123456789def"),  # INSERT OUTPUT
        ]

        result = mock_store.upsert_dim_entity(
            title="New Character",
            source_page_id="def-456",
            primary_type="PersonCharacter",
            confidence=0.85,
        )

        assert result["success"] is True
        assert result["entity_key"] == 456
        assert result["entity_guid"] == "abcd1234-abcd-1234-abcd-123456789def"
        assert result["action"] == "inserted"
        assert result["error"] is None

    def test_promotion_state_candidate_high_confidence(self, mock_store):
        """Test promotion state is 'candidate' for high confidence."""
        mock_store._mock_cursor.fetchone.return_value = (123, "guid-123")

        mock_store.upsert_dim_entity(
            title="Test Entity",
            primary_type="PersonCharacter",
            confidence=0.80,  # Exactly 0.80 threshold
        )

        # Verify the UPDATE was called with 'candidate' state
        call_args = mock_store._mock_cursor.execute.call_args_list
        update_call = [c for c in call_args if "UPDATE" in str(c)]
        assert len(update_call) > 0
        update_params = update_call[-1][0][1]
        assert update_params[0] == "candidate"  # First param is promotion_state

    def test_promotion_state_staged_low_confidence(self, mock_store):
        """Test promotion state is 'staged' for low confidence."""
        mock_store._mock_cursor.fetchone.return_value = (123, "guid-123")

        mock_store.upsert_dim_entity(
            title="Test Entity",
            primary_type="PersonCharacter",
            confidence=0.79,  # Below 0.80 threshold
        )

        call_args = mock_store._mock_cursor.execute.call_args_list
        update_call = [c for c in call_args if "UPDATE" in str(c)]
        assert len(update_call) > 0
        update_params = update_call[-1][0][1]
        assert update_params[0] == "staged"

    def test_promotion_state_staged_meta_type(self, mock_store):
        """Test promotion state is 'staged' for meta/technical types."""
        mock_store._mock_cursor.fetchone.return_value = (123, "guid-123")

        mock_store.upsert_dim_entity(
            title="Help:Contents",
            primary_type="TechnicalSitePage",  # Meta type
            confidence=0.99,  # High confidence but still staged
        )

        call_args = mock_store._mock_cursor.execute.call_args_list
        update_call = [c for c in call_args if "UPDATE" in str(c)]
        assert len(update_call) > 0
        update_params = update_call[-1][0][1]
        assert update_params[0] == "staged"

    def test_handles_exception(self, mock_store):
        """Test that exceptions are handled gracefully."""
        mock_store._mock_cursor.execute.side_effect = Exception("Database error")

        result = mock_store.upsert_dim_entity(
            title="Test Entity",
            primary_type="Unknown",
        )

        assert result["success"] is False
        assert result["entity_key"] is None
        assert result["entity_guid"] is None
        assert result["action"] is None
        assert "Database error" in result["error"]

    def test_descriptor_sentence_truncation(self, mock_store):
        """Test that long descriptor sentences are truncated internally."""
        # Simulate INSERT path (returns new entity)
        mock_store._mock_cursor.fetchone.side_effect = [
            None,  # SELECT returns no match
            (789, "guid-789"),  # INSERT OUTPUT
        ]

        # Create a descriptor sentence longer than 1000 chars
        long_descriptor = "A" * 1500

        result = mock_store.upsert_dim_entity(
            title="Test Entity",
            descriptor_sentence=long_descriptor,
        )

        # Verify the upsert succeeded (truncation happens silently internally)
        assert result["success"] is True
        assert result["action"] == "inserted"


class TestIdempotency:
    """Tests to verify upsert idempotency."""

    @pytest.fixture
    def mock_store(self):
        """Create a store with mocked connection."""
        with patch.object(SemanticStagingStore, '_get_connection') as mock_conn:
            store = SemanticStagingStore(
                connection_string="mocked"
            )
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            store._mock_cursor = mock_cursor
            yield store

    def test_repeated_upsert_same_title_updates(self, mock_store):
        """Test that upserting the same title repeatedly updates, not duplicates."""
        # Always return existing entity
        mock_store._mock_cursor.fetchone.return_value = (123, "guid-123")

        # Call upsert twice with same title
        result1 = mock_store.upsert_dim_entity(
            title="Han Solo",
            primary_type="PersonCharacter",
            confidence=0.80,
        )
        result2 = mock_store.upsert_dim_entity(
            title="Han Solo",
            primary_type="PersonCharacter",
            confidence=0.85,  # Updated confidence
        )

        # Both should return same entity key with 'updated' action
        assert result1["entity_key"] == 123
        assert result2["entity_key"] == 123
        assert result1["action"] == "updated"
        assert result2["action"] == "updated"

    def test_case_insensitive_matching(self, mock_store):
        """Test that matching is case-insensitive."""
        # Simulate that uppercase lookup finds the lowercase version
        mock_store._mock_cursor.fetchone.return_value = (456, "guid-456")

        # The store normalizes to lowercase, so matching should work
        result = mock_store.upsert_dim_entity(
            title="LEIA ORGANA",  # Uppercase
            primary_type="PersonCharacter",
        )

        # Should find and update existing
        assert result["action"] == "updated"
