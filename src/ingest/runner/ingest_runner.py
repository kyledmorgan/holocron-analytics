"""
Main execution runner for the ingestion pipeline.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.models import WorkItem, IngestRecord, WorkItemStatus
from ..core.connector import Connector, ConnectorRequest
from ..core.storage import StorageWriter
from ..core.state_store import StateStore
from ..discovery.base import Discovery


logger = logging.getLogger(__name__)


class IngestRunner:
    """
    Main orchestrator for the ingestion pipeline.
    
    Manages the workflow:
    1. Dequeue work items
    2. Fetch data via connectors
    3. Store results via storage writers
    4. Discover new work items
    5. Update state
    """

    def __init__(
        self,
        state_store: StateStore,
        connectors: Dict[str, Connector],
        storage_writers: List[StorageWriter],
        discovery_plugins: Optional[List[Discovery]] = None,
        max_retries: int = 3,
        enable_discovery: bool = True,
    ):
        """
        Initialize the ingest runner.
        
        Args:
            state_store: State store for work queue management
            connectors: Dictionary of connectors by name
            storage_writers: List of storage writers
            discovery_plugins: Optional list of discovery plugins
            max_retries: Maximum retry attempts for failed items
            enable_discovery: Whether to enable discovery
        """
        self.state_store = state_store
        self.connectors = connectors
        self.storage_writers = storage_writers
        self.discovery_plugins = discovery_plugins or []
        self.max_retries = max_retries
        self.enable_discovery = enable_discovery
        
        # Metrics
        self.metrics = {
            "items_processed": 0,
            "items_succeeded": 0,
            "items_failed": 0,
            "items_discovered": 0,
        }

    def run(
        self,
        batch_size: int = 10,
        max_items: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> Dict:
        """
        Run the ingestion pipeline.
        
        Args:
            batch_size: Number of items to process per batch
            max_items: Maximum total items to process (None = unlimited)
            run_id: Optional run identifier
            
        Returns:
            Dictionary with run statistics
        """
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        logger.info(f"Starting ingestion run: {run_id}")
        logger.info(f"Batch size: {batch_size}, Max items: {max_items}")
        
        # Reset metrics
        self.metrics = {
            "items_processed": 0,
            "items_succeeded": 0,
            "items_failed": 0,
            "items_discovered": 0,
            "run_id": run_id,
        }
        
        total_processed = 0
        
        while True:
            # Check if we've reached max items
            if max_items and total_processed >= max_items:
                logger.info(f"Reached max items limit: {max_items}")
                break
            
            # Dequeue work items
            remaining = max_items - total_processed if max_items else batch_size
            batch = self.state_store.dequeue(min(batch_size, remaining))
            
            if not batch:
                logger.info("No more work items in queue")
                break
            
            logger.info(f"Processing batch of {len(batch)} items")
            
            # Process each work item
            for work_item in batch:
                self._process_work_item(work_item)
                total_processed += 1
            
            # Log progress
            stats = self.state_store.get_stats()
            logger.info(f"Queue stats: {stats}")
        
        # Final summary
        logger.info(f"Run complete: {run_id}")
        logger.info(f"Metrics: {json.dumps(self.metrics, indent=2)}")
        
        return self.metrics

    def _process_work_item(self, work_item: WorkItem) -> None:
        """Process a single work item."""
        self.metrics["items_processed"] += 1
        
        logger.info(
            f"Processing: {work_item.source_system}:{work_item.source_name}:"
            f"{work_item.resource_type}:{work_item.resource_id}"
        )
        
        try:
            # Get appropriate connector
            connector_key = work_item.source_system
            if connector_key not in self.connectors:
                raise ValueError(f"No connector found for: {connector_key}")
            
            connector = self.connectors[connector_key]
            
            # Build connector request
            request = ConnectorRequest(
                uri=work_item.request_uri,
                method=work_item.request_method,
                headers=work_item.request_headers,
                body=work_item.request_body,
            )
            
            # Fetch data
            response = connector.fetch(request)
            
            # Check if successful
            if response.status_code < 200 or response.status_code >= 300:
                # Failed response
                error_msg = response.error_message or f"HTTP {response.status_code}"
                
                if work_item.attempt < self.max_retries:
                    # Retry
                    work_item.attempt += 1
                    work_item.status = WorkItemStatus.PENDING
                    self.state_store.update_status(
                        work_item.work_item_id,
                        WorkItemStatus.PENDING,
                        error_msg,
                    )
                    logger.warning(
                        f"Retry {work_item.attempt}/{self.max_retries} for "
                        f"{work_item.resource_id}: {error_msg}"
                    )
                else:
                    # Max retries reached
                    self.state_store.update_status(
                        work_item.work_item_id,
                        WorkItemStatus.FAILED,
                        error_msg,
                    )
                    self.metrics["items_failed"] += 1
                    logger.error(f"Failed after {self.max_retries} attempts: {error_msg}")
                
                return
            
            # Create ingest record
            ingest_record = IngestRecord(
                ingest_id=str(uuid.uuid4()),
                source_system=work_item.source_system,
                source_name=work_item.source_name,
                resource_type=work_item.resource_type,
                resource_id=work_item.resource_id,
                request_uri=work_item.request_uri,
                request_method=work_item.request_method,
                request_headers=work_item.request_headers,
                status_code=response.status_code,
                response_headers=response.headers,
                payload=response.payload,
                fetched_at_utc=datetime.utcnow(),
                hash_sha256=self._compute_hash(response.payload),
                run_id=work_item.run_id,
                work_item_id=work_item.work_item_id,
                attempt=work_item.attempt,
                duration_ms=response.duration_ms,
            )
            
            # Write to storage
            for writer in self.storage_writers:
                try:
                    writer.write(ingest_record)
                    logger.debug(f"Wrote to {writer.get_name()}")
                except Exception as e:
                    logger.error(f"Storage write failed ({writer.get_name()}): {e}")
            
            # Discovery
            if self.enable_discovery and self.discovery_plugins:
                discovered_items = []
                
                for plugin in self.discovery_plugins:
                    try:
                        items = plugin.discover(ingest_record, work_item)
                        discovered_items.extend(items)
                    except Exception as e:
                        logger.error(f"Discovery failed ({plugin.get_name()}): {e}")
                
                # Enqueue discovered items
                enqueued = 0
                for item in discovered_items:
                    if self.state_store.enqueue(item):
                        enqueued += 1
                
                if enqueued > 0:
                    logger.info(f"Discovered and enqueued {enqueued} new items")
                    self.metrics["items_discovered"] += enqueued
            
            # Mark as completed
            self.state_store.update_status(
                work_item.work_item_id,
                WorkItemStatus.COMPLETED,
            )
            self.metrics["items_succeeded"] += 1
            logger.info(f"Successfully processed: {work_item.resource_id}")
            
        except Exception as e:
            # Unexpected error
            error_msg = str(e)
            logger.exception(f"Unexpected error processing work item: {error_msg}")
            
            self.state_store.update_status(
                work_item.work_item_id,
                WorkItemStatus.FAILED,
                error_msg,
            )
            self.metrics["items_failed"] += 1

    def _compute_hash(self, payload: dict) -> str:
        """Compute SHA256 hash of payload for change detection."""
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload_json.encode('utf-8')).hexdigest()

    def seed_queue(self, work_items: List[WorkItem]) -> int:
        """
        Seed the queue with initial work items.
        
        Args:
            work_items: List of work items to add
            
        Returns:
            Number of items successfully enqueued
        """
        enqueued = 0
        
        for item in work_items:
            if self.state_store.enqueue(item):
                enqueued += 1
        
        logger.info(f"Seeded queue with {enqueued} items")
        return enqueued

    def get_stats(self) -> Dict:
        """Get current queue and run statistics."""
        queue_stats = self.state_store.get_stats()
        
        return {
            "queue": queue_stats,
            "run_metrics": self.metrics,
        }

    def close(self) -> None:
        """Close all resources."""
        logger.info("Closing runner resources")
        
        # Close connectors
        for connector in self.connectors.values():
            if hasattr(connector, 'close'):
                connector.close()
        
        # Close storage writers
        for writer in self.storage_writers:
            writer.close()
        
        # Close state store
        self.state_store.close()
