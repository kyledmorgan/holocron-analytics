"""
Unit tests for core models.

These tests verify the data models without external dependencies.
"""

import pytest
from datetime import datetime, timezone

from ingest.core.models import WorkItem, WorkItemStatus, IngestRecord, AcquisitionVariant


class TestWorkItem:
    """Tests for WorkItem model."""
    
    def test_work_item_creation(self):
        """Test basic work item creation."""
        work_item = WorkItem(
            source_system="test",
            source_name="test_source",
            resource_type="item",
            resource_id="123",
            request_uri="https://example.com/123",
        )
        
        assert work_item.source_system == "test"
        assert work_item.source_name == "test_source"
        assert work_item.resource_type == "item"
        assert work_item.resource_id == "123"
        assert work_item.status == WorkItemStatus.PENDING
        assert work_item.attempt == 0
        assert work_item.work_item_id is not None
    
    def test_work_item_dedupe_key(self):
        """Test dedupe key generation."""
        work_item = WorkItem(
            source_system="mediawiki",
            source_name="wikipedia",
            resource_type="page",
            resource_id="Star_Wars",
            request_uri="https://en.wikipedia.org/wiki/Star_Wars",
        )
        
        expected_key = "mediawiki:wikipedia:page:Star_Wars"
        assert work_item.get_dedupe_key() == expected_key
    
    def test_work_item_dedupe_key_with_variant(self):
        """Test dedupe key includes variant when set."""
        work_item_raw = WorkItem(
            source_system="mediawiki",
            source_name="wikipedia",
            resource_type="content",
            resource_id="Star_Wars",
            request_uri="https://en.wikipedia.org/api.php?action=query",
            variant=AcquisitionVariant.RAW,
        )
        
        work_item_html = WorkItem(
            source_system="mediawiki",
            source_name="wikipedia",
            resource_type="content",
            resource_id="Star_Wars",
            request_uri="https://en.wikipedia.org/api.php?action=parse",
            variant=AcquisitionVariant.HTML,
        )
        
        assert work_item_raw.get_dedupe_key() == "mediawiki:wikipedia:content:Star_Wars:raw"
        assert work_item_html.get_dedupe_key() == "mediawiki:wikipedia:content:Star_Wars:html"
        
        # Keys should be different
        assert work_item_raw.get_dedupe_key() != work_item_html.get_dedupe_key()
    
    def test_work_item_default_values(self):
        """Test default values are set correctly."""
        work_item = WorkItem(
            source_system="test",
            source_name="test_source",
            resource_type="item",
            resource_id="123",
            request_uri="https://example.com/123",
        )
        
        assert work_item.request_method == "GET"
        assert work_item.priority == 100
        assert work_item.metadata == {}
        assert work_item.request_headers is None
        assert work_item.request_body is None
        assert work_item.variant is None
        assert work_item.rank is None
    
    def test_work_item_with_metadata(self):
        """Test work item with metadata."""
        metadata = {"key": "value", "count": 42}
        work_item = WorkItem(
            source_system="test",
            source_name="test_source",
            resource_type="item",
            resource_id="123",
            request_uri="https://example.com/123",
            metadata=metadata,
        )
        
        assert work_item.metadata == metadata
    
    def test_work_item_with_variant_and_rank(self):
        """Test work item with variant and rank fields."""
        work_item = WorkItem(
            source_system="mediawiki",
            source_name="wookieepedia",
            resource_type="content",
            resource_id="Luke Skywalker",
            request_uri="https://starwars.fandom.com/api.php?action=query",
            variant=AcquisitionVariant.RAW,
            rank=1,
        )
        
        assert work_item.variant == AcquisitionVariant.RAW
        assert work_item.rank == 1


class TestAcquisitionVariant:
    """Tests for AcquisitionVariant enum."""
    
    def test_variant_values(self):
        """Test all variant values are defined."""
        assert AcquisitionVariant.RAW.value == "raw"
        assert AcquisitionVariant.HTML.value == "html"
    
    def test_variant_from_string(self):
        """Test creating variant from string."""
        variant = AcquisitionVariant("raw")
        assert variant == AcquisitionVariant.RAW


class TestWorkItemStatus:
    """Tests for WorkItemStatus enum."""
    
    def test_status_values(self):
        """Test all status values are defined."""
        assert WorkItemStatus.PENDING.value == "pending"
        assert WorkItemStatus.IN_PROGRESS.value == "in_progress"
        assert WorkItemStatus.COMPLETED.value == "completed"
        assert WorkItemStatus.FAILED.value == "failed"
        assert WorkItemStatus.SKIPPED.value == "skipped"
    
    def test_status_from_string(self):
        """Test creating status from string."""
        status = WorkItemStatus("pending")
        assert status == WorkItemStatus.PENDING


class TestIngestRecord:
    """Tests for IngestRecord model."""
    
    def test_ingest_record_creation(self):
        """Test basic ingest record creation."""
        now = datetime.now(timezone.utc)
        record = IngestRecord(
            ingest_id="record-123",
            source_system="test",
            source_name="test_source",
            resource_type="item",
            resource_id="123",
            request_uri="https://example.com/123",
            request_method="GET",
            status_code=200,
            payload={"data": "test"},
            fetched_at_utc=now,
        )
        
        assert record.ingest_id == "record-123"
        assert record.status_code == 200
        assert record.payload == {"data": "test"}
        assert record.attempt == 1
    
    def test_ingest_record_with_error(self):
        """Test ingest record with error message."""
        now = datetime.now(timezone.utc)
        record = IngestRecord(
            ingest_id="record-123",
            source_system="test",
            source_name="test_source",
            resource_type="item",
            resource_id="123",
            request_uri="https://example.com/123",
            request_method="GET",
            status_code=500,
            payload={},
            fetched_at_utc=now,
            error_message="Internal server error",
        )
        
        assert record.status_code == 500
        assert record.error_message == "Internal server error"
    
    def test_ingest_record_with_extended_fields(self):
        """Test ingest record with extended response metadata fields."""
        now = datetime.now(timezone.utc)
        record = IngestRecord(
            ingest_id="record-456",
            source_system="mediawiki",
            source_name="wookieepedia",
            resource_type="content",
            resource_id="Luke Skywalker",
            request_uri="https://starwars.fandom.com/api.php?action=query",
            request_method="GET",
            status_code=200,
            payload={"query": {"pages": []}},
            fetched_at_utc=now,
            variant=AcquisitionVariant.RAW,
            content_type="application/json",
            content_length=1234,
            file_path="/data/mediawiki/wookieepedia/content/Luke_Skywalker_raw.json",
            request_timestamp=now,
            response_timestamp=now,
        )
        
        assert record.variant == AcquisitionVariant.RAW
        assert record.content_type == "application/json"
        assert record.content_length == 1234
        assert record.file_path == "/data/mediawiki/wookieepedia/content/Luke_Skywalker_raw.json"
        assert record.request_timestamp == now
        assert record.response_timestamp == now
