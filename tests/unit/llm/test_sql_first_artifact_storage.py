"""
Unit tests for SQL-first artifact content storage.

Tests that:
- SqlJobQueue.create_artifact accepts and passes content + storage flags
- SqlJobQueue.create_evidence_bundle accepts bundle_json
- Phase1Runner passes literal content alongside lake writes
- Backward compatibility is maintained (content is optional)
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from llm.storage.sql_job_queue import SqlJobQueue, QueueConfig
from llm.storage.lake_writer import LakeWriter, ArtifactInfo


class TestSqlJobQueueArtifactContent:
    """Tests for SqlJobQueue.create_artifact with content support."""

    def _make_queue_with_mock_conn(self):
        """Create a SqlJobQueue with a mocked connection."""
        config = QueueConfig(
            host="localhost",
            port=1433,
            database="TestDB",
            username="sa",
            password="test",
            schema="llm",
        )
        queue = SqlJobQueue(config)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Return a fake artifact_id
        mock_cursor.fetchone.return_value = ("artifact-id-123",)
        queue._conn = mock_conn
        return queue, mock_cursor

    def test_create_artifact_with_content(self):
        """Test that content and storage flags are passed to SQL."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        artifact_id = queue.create_artifact(
            run_id="run-123",
            artifact_type="request_json",
            lake_uri="2026/02/21/run-123/request.json",
            content_sha256="abc123",
            byte_count=500,
            content='{"model": "llama3.2"}',
            content_mime_type="application/json",
            stored_in_sql=True,
            mirrored_to_lake=True,
        )

        assert artifact_id == "artifact-id-123"
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # Verify the SQL includes content and flag parameters
        assert "@content" in sql
        assert "@content_mime_type" in sql
        assert "@stored_in_sql" in sql
        assert "@mirrored_to_lake" in sql

        # Verify parameter values
        assert params[0] == "run-123"  # run_id
        assert params[1] == "request_json"  # artifact_type
        assert params[2] == "2026/02/21/run-123/request.json"  # lake_uri
        assert params[5] == '{"model": "llama3.2"}'  # content
        assert params[6] == "application/json"  # content_mime_type
        assert params[7] == 1  # stored_in_sql (True → 1)
        assert params[8] == 1  # mirrored_to_lake (True → 1)

    def test_create_artifact_without_content_backward_compat(self):
        """Test backward compatibility: content is optional."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        artifact_id = queue.create_artifact(
            run_id="run-456",
            artifact_type="prompt_text",
            lake_uri="2026/02/21/run-456/prompt.txt",
            content_sha256="def456",
            byte_count=200,
        )

        assert artifact_id == "artifact-id-123"
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # content and mime_type should be None
        assert params[5] is None  # content
        assert params[6] is None  # content_mime_type
        assert params[7] == 0  # stored_in_sql default False
        assert params[8] == 0  # mirrored_to_lake default False

    def test_create_artifact_sql_only_no_lake_uri(self):
        """Test SQL-only storage (no lake_uri)."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        artifact_id = queue.create_artifact(
            run_id="run-789",
            artifact_type="response_json",
            content='{"response": "hello"}',
            content_sha256="ghi789",
            byte_count=25,
            content_mime_type="application/json",
            stored_in_sql=True,
            mirrored_to_lake=False,
        )

        assert artifact_id == "artifact-id-123"
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # lake_uri should be None
        assert params[2] is None  # lake_uri
        assert params[5] == '{"response": "hello"}'  # content
        assert params[7] == 1  # stored_in_sql
        assert params[8] == 0  # mirrored_to_lake


class TestSqlJobQueueEvidenceBundleContent:
    """Tests for SqlJobQueue.create_evidence_bundle with bundle_json."""

    def _make_queue_with_mock_conn(self):
        """Create a SqlJobQueue with a mocked connection."""
        config = QueueConfig(
            host="localhost",
            port=1433,
            database="TestDB",
            username="sa",
            password="test",
            schema="llm",
        )
        queue = SqlJobQueue(config)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        queue._conn = mock_conn
        return queue, mock_cursor

    def test_create_evidence_bundle_with_bundle_json(self):
        """Test that bundle_json is passed to SQL."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        bundle_content = json.dumps({"items": [{"id": "inline:0", "content": "test"}]})

        queue.create_evidence_bundle(
            bundle_id="bundle-123",
            build_version="2.0",
            policy_json='{"max_items": 50}',
            summary_json='{"item_count": 1}',
            lake_uri="2026/02/21/run-123/evidence.json",
            bundle_json=bundle_content,
        )

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # Verify bundle_json is in the INSERT
        assert "bundle_json" in sql
        # Verify parameter value (bundle_json is last)
        assert params[-1] == bundle_content

    def test_create_evidence_bundle_without_bundle_json(self):
        """Test backward compatibility: bundle_json is optional."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        queue.create_evidence_bundle(
            bundle_id="bundle-456",
            build_version="2.0",
            policy_json='{"max_items": 50}',
            summary_json='{"item_count": 1}',
            lake_uri="2026/02/21/run-456/evidence.json",
        )

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # bundle_json should be None (default)
        assert params[-1] is None

    def test_create_evidence_bundle_sql_only(self):
        """Test SQL-only evidence bundle (no lake_uri, but has bundle_json)."""
        queue, mock_cursor = self._make_queue_with_mock_conn()

        bundle_content = json.dumps({"items": []})

        queue.create_evidence_bundle(
            bundle_id="bundle-789",
            build_version="2.0",
            policy_json='{}',
            summary_json='{}',
            bundle_json=bundle_content,
        )

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # lake_uri should be None, bundle_json should have content
        assert params[4] is None  # lake_uri
        assert params[5] == bundle_content  # bundle_json
