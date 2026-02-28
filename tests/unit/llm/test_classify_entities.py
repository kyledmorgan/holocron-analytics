"""
Unit tests for the Entity Classification CLI and Service.

Tests cover:
- Classification predicate logic (is_entity_classified)
- RunStats tracking
- ClassifyConfig construction
- CLI argument parsing
- Service candidate filtering and job enqueue logic
- Idempotent resume behavior
- Dry-run mode
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from llm.cli.classify_entities import (
    is_entity_classified,
    RunStats,
    ClassifyConfig,
    EntityClassificationService,
    build_parser,
    main,
    MODE_FRESH,
    MODE_RESUME,
    MODE_RERUN,
    ONLY_FAILED,
)


# ---------------------------------------------------------------------------
# is_entity_classified predicate
# ---------------------------------------------------------------------------

class TestIsEntityClassified:
    """Test the 'already done' predicate."""

    def test_classified_when_entity_type_set(self):
        row = {"EntityType": "PersonCharacter", "IsLatest": True, "IsActive": True}
        assert is_entity_classified(row) is True

    def test_not_classified_when_entity_type_null(self):
        row = {"EntityType": None, "IsLatest": True, "IsActive": True}
        assert is_entity_classified(row) is False

    def test_not_classified_when_entity_type_empty(self):
        row = {"EntityType": "", "IsLatest": True, "IsActive": True}
        assert is_entity_classified(row) is False

    def test_not_classified_when_not_latest(self):
        row = {"EntityType": "Droid", "IsLatest": False, "IsActive": True}
        assert is_entity_classified(row) is False

    def test_not_classified_when_not_active(self):
        row = {"EntityType": "Droid", "IsLatest": True, "IsActive": False}
        assert is_entity_classified(row) is False

    def test_require_normalization_missing(self):
        row = {
            "EntityType": "Droid",
            "IsLatest": True,
            "IsActive": True,
            "DisplayNameNormalized": None,
            "SortName": "r2d2",
        }
        assert is_entity_classified(row, require_normalization=True) is False

    def test_require_normalization_present(self):
        row = {
            "EntityType": "Droid",
            "IsLatest": True,
            "IsActive": True,
            "DisplayNameNormalized": "R2-D2",
            "SortName": "r2d2",
        }
        assert is_entity_classified(row, require_normalization=True) is True

    def test_require_tags_missing(self):
        row = {
            "EntityType": "Droid",
            "IsLatest": True,
            "IsActive": True,
            "AliasCsv": None,
        }
        assert is_entity_classified(row, require_tags=True) is False

    def test_require_tags_present(self):
        row = {
            "EntityType": "Droid",
            "IsLatest": True,
            "IsActive": True,
            "AliasCsv": "Artoo,R2",
        }
        assert is_entity_classified(row, require_tags=True) is True

    def test_defaults_for_missing_keys(self):
        """If IsLatest/IsActive are not in row, default to True."""
        row = {"EntityType": "Location"}
        assert is_entity_classified(row) is True


# ---------------------------------------------------------------------------
# RunStats
# ---------------------------------------------------------------------------

class TestRunStats:
    def test_defaults(self):
        stats = RunStats()
        assert stats.attempted == 0
        assert stats.to_dict()["error_count"] == 0

    def test_to_dict(self):
        stats = RunStats(attempted=5, succeeded=3, failed=1, skipped=1)
        d = stats.to_dict()
        assert d["attempted"] == 5
        assert d["succeeded"] == 3
        assert d["failed"] == 1
        assert d["error_count"] == 0

    def test_errors_truncated(self):
        stats = RunStats()
        stats.errors = [f"err-{i}" for i in range(30)]
        d = stats.to_dict()
        assert len(d["errors"]) == 20


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLIParsing:
    def test_default_mode_is_resume(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.mode == "resume"

    def test_fresh_mode(self):
        parser = build_parser()
        args = parser.parse_args(["--mode", "fresh"])
        assert args.mode == "fresh"

    def test_batch_size(self):
        parser = build_parser()
        args = parser.parse_args(["--batch-size", "500"])
        assert args.batch_size == 500

    def test_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_entity_keys_multiple(self):
        parser = build_parser()
        args = parser.parse_args(["--entity-keys", "1", "2", "3"])
        assert args.entity_keys == [1, 2, 3]

    def test_only_failed(self):
        parser = build_parser()
        args = parser.parse_args(["--only", "failed"])
        assert args.only == "failed"

    def test_fill_missing_only(self):
        parser = build_parser()
        args = parser.parse_args(["--fill-missing-only"])
        assert args.fill_missing_only is True

    def test_require_tags(self):
        parser = build_parser()
        args = parser.parse_args(["--require-tags"])
        assert args.require_tags is True

    def test_revalidate_existing(self):
        parser = build_parser()
        args = parser.parse_args(["--revalidate-existing"])
        assert args.revalidate_existing is True

    def test_priority(self):
        parser = build_parser()
        args = parser.parse_args(["--priority", "50"])
        assert args.priority == 50


# ---------------------------------------------------------------------------
# EntityClassificationService
# ---------------------------------------------------------------------------

class TestEntityClassificationService:

    def _make_service(self, config=None, candidates=None, enqueue_result=None):
        """Helper to build service with mock queue."""
        mock_queue = MagicMock()

        # Mock the connection for _execute_query
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_queue._get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        if candidates is not None:
            # Set up cursor to return candidate rows
            columns = [
                "EntityKey", "EntityGuid", "DisplayName", "EntityType",
                "DisplayNameNormalized", "SortName", "AliasCsv",
                "IsLatest", "IsActive", "ExternalKey", "SourcePageId",
            ]
            mock_cursor.description = [(c,) for c in columns]
            mock_cursor.fetchall.return_value = [
                tuple(row.get(c) for c in columns)
                for row in candidates
            ]

        if enqueue_result is not None:
            mock_queue.enqueue_job_idempotent.return_value = enqueue_result

        cfg = config or ClassifyConfig()
        service = EntityClassificationService(queue=mock_queue, config=cfg)
        return service, mock_queue

    def test_resume_skips_classified_entities(self):
        """Entities with EntityType set should be skipped in resume mode."""
        candidates = [
            {
                "EntityKey": 1, "EntityGuid": "guid-1",
                "DisplayName": "Luke", "EntityType": "PersonCharacter",
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        config = ClassifyConfig(mode=MODE_RESUME)
        service, mock_queue = self._make_service(config=config, candidates=candidates)
        stats = service.run()

        assert stats.already_classified == 1
        assert stats.skipped == 1
        assert stats.attempted == 0
        mock_queue.enqueue_job_idempotent.assert_not_called()

    def test_resume_enqueues_unclassified_entities(self):
        """Entities without EntityType should be enqueued."""
        candidates = [
            {
                "EntityKey": 2, "EntityGuid": "guid-2",
                "DisplayName": "R2-D2", "EntityType": None,
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        enqueue_result = {"job_id": "job-1", "is_duplicate": False, "existing_status": None}
        config = ClassifyConfig(mode=MODE_RESUME)
        service, mock_queue = self._make_service(
            config=config, candidates=candidates, enqueue_result=enqueue_result,
        )
        stats = service.run()

        assert stats.attempted == 1
        assert stats.succeeded == 1
        mock_queue.enqueue_job_idempotent.assert_called_once()
        call_kwargs = mock_queue.enqueue_job_idempotent.call_args
        assert call_kwargs[1]["dedupe_key"] == "entity_classify:2"

    def test_duplicate_job_skipped(self):
        """If idempotent enqueue finds an existing SUCCEEDED job, skip it."""
        candidates = [
            {
                "EntityKey": 3, "EntityGuid": "guid-3",
                "DisplayName": "C-3PO", "EntityType": None,
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        enqueue_result = {"job_id": "job-existing", "is_duplicate": True, "existing_status": "SUCCEEDED"}
        config = ClassifyConfig(mode=MODE_RESUME)
        service, mock_queue = self._make_service(
            config=config, candidates=candidates, enqueue_result=enqueue_result,
        )
        stats = service.run()

        assert stats.skipped == 1
        assert stats.already_classified == 1

    def test_dry_run_does_not_enqueue(self):
        """Dry run should count but never call enqueue."""
        candidates = [
            {
                "EntityKey": 4, "EntityGuid": "guid-4",
                "DisplayName": "Yoda", "EntityType": None,
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        config = ClassifyConfig(mode=MODE_RESUME, dry_run=True)
        service, mock_queue = self._make_service(config=config, candidates=candidates)
        stats = service.run()

        assert stats.dry_run_would_process == 1
        assert stats.attempted == 1
        mock_queue.enqueue_job_idempotent.assert_not_called()

    def test_rerun_mode_does_not_skip_classified(self):
        """In rerun mode, classified entities should still be processed."""
        candidates = [
            {
                "EntityKey": 5, "EntityGuid": "guid-5",
                "DisplayName": "Vader", "EntityType": "PersonCharacter",
                "DisplayNameNormalized": "vader", "SortName": "vader",
                "AliasCsv": "Anakin", "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        enqueue_result = {"job_id": "job-5", "is_duplicate": False, "existing_status": None}
        config = ClassifyConfig(mode=MODE_RERUN, entity_keys=[5])
        service, mock_queue = self._make_service(
            config=config, candidates=candidates, enqueue_result=enqueue_result,
        )
        stats = service.run()

        assert stats.attempted == 1
        assert stats.succeeded == 1

    def test_revalidate_existing_processes_classified(self):
        """--revalidate-existing should process already-classified entities."""
        candidates = [
            {
                "EntityKey": 6, "EntityGuid": "guid-6",
                "DisplayName": "Leia", "EntityType": "PersonCharacter",
                "DisplayNameNormalized": "leia", "SortName": "organa",
                "AliasCsv": "Princess", "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        enqueue_result = {"job_id": "job-6", "is_duplicate": False, "existing_status": None}
        config = ClassifyConfig(mode=MODE_RESUME, revalidate_existing=True)
        service, mock_queue = self._make_service(
            config=config, candidates=candidates, enqueue_result=enqueue_result,
        )
        stats = service.run()

        assert stats.attempted == 1
        assert stats.succeeded == 1

    def test_enqueue_failure_tracked(self):
        """Enqueue exceptions should be recorded in stats.errors."""
        candidates = [
            {
                "EntityKey": 7, "EntityGuid": "guid-7",
                "DisplayName": "Han", "EntityType": None,
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        config = ClassifyConfig(mode=MODE_RESUME)
        service, mock_queue = self._make_service(config=config, candidates=candidates)
        mock_queue.enqueue_job_idempotent.side_effect = RuntimeError("DB down")
        stats = service.run()

        assert stats.failed == 1
        assert len(stats.errors) == 1
        assert "DB down" in stats.errors[0]

    def test_no_candidates_returns_empty_stats(self):
        """When no candidates found, stats should all be zero."""
        config = ClassifyConfig(mode=MODE_RESUME)
        service, _ = self._make_service(config=config, candidates=[])
        stats = service.run()

        assert stats.attempted == 0
        assert stats.succeeded == 0
        assert stats.failed == 0

    def test_fill_missing_only_flag_in_job_input(self):
        """fill_missing_only should be passed through to job input."""
        candidates = [
            {
                "EntityKey": 8, "EntityGuid": "guid-8",
                "DisplayName": "Chewie", "EntityType": None,
                "DisplayNameNormalized": None, "SortName": None,
                "AliasCsv": None, "IsLatest": True, "IsActive": True,
                "ExternalKey": None, "SourcePageId": None,
            },
        ]
        enqueue_result = {"job_id": "job-8", "is_duplicate": False, "existing_status": None}
        config = ClassifyConfig(mode=MODE_RESUME, fill_missing_only=True)
        service, mock_queue = self._make_service(
            config=config, candidates=candidates, enqueue_result=enqueue_result,
        )
        stats = service.run()

        call_kwargs = mock_queue.enqueue_job_idempotent.call_args[1]
        input_payload = json.loads(call_kwargs["input_json"])
        assert input_payload["fill_missing_only"] is True


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

class TestMainEntrypoint:
    def test_main_dry_run_returns_zero(self):
        """main() with --dry-run and no candidates should return 0."""
        with patch.object(EntityClassificationService, "run", return_value=RunStats()):
            result = main(["--mode", "resume", "--dry-run"])
        assert result == 0

    def test_main_with_failures_returns_one(self):
        """main() should return 1 when there are failures."""
        stats = RunStats(failed=1)
        stats.errors.append("some error")
        with patch.object(EntityClassificationService, "run", return_value=stats):
            result = main(["--mode", "resume"])
        assert result == 1
