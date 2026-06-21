"""
Concurrent runner for processing work items with multiple workers.

This module provides a ThreadPoolExecutor-based concurrent runner that:
- Spawns N configurable worker threads
- Each worker atomically claims work items from the shared queue
- Supports lease-based ownership to handle worker failures
- Provides graceful shutdown, pause, and drain modes
- Tracks worker heartbeats for visibility
"""

import hashlib
import json
import logging
import os
import random
import signal
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from ..core.models import (
    WorkItem, IngestRecord, WorkItemStatus, 
    WorkerInfo, WorkerStatus, QueueStats
)
from ..core.connector import Connector, ConnectorRequest
from ..core.storage import StorageWriter
from ..state.sqlserver_store import SqlServerStateStore
from ..discovery.base import Discovery


logger = logging.getLogger(__name__)


@dataclass
class RunnerConfig:
    """
    Configuration for the concurrent runner.
    
    Attributes:
        max_workers: Maximum number of concurrent worker threads
        lease_seconds: How long a work item lease is valid
        heartbeat_interval: Seconds between worker heartbeats
        batch_size: Number of items a worker processes before checking for signals
        max_items: Maximum total items to process (None = unlimited)
        stop_after: Stop after processing this many items (for testing)
        max_retries: Maximum retry attempts for failed items
        enable_discovery: Whether to discover new items from fetched content
        source_filter: Only process items from this source_system
        
        # Backoff settings
        base_backoff_seconds: Base delay for exponential backoff
        max_backoff_seconds: Maximum backoff delay
        respect_retry_after: Honor Retry-After header from responses
        
        # Rate limiting
        requests_per_second: Global rate limit (0 = unlimited)
    """
    max_workers: int = 4
    lease_seconds: int = 300
    heartbeat_interval: int = 30
    batch_size: int = 10
    max_items: Optional[int] = None
    stop_after: Optional[int] = None
    max_retries: int = 3
    enable_discovery: bool = True
    source_filter: Optional[str] = None
    
    # Backoff settings
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 300.0
    respect_retry_after: bool = True
    
    # Rate limiting  
    requests_per_second: float = 0.0  # 0 = unlimited


@dataclass
class RunMetrics:
    """Aggregate metrics for a run."""
    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    items_discovered: int = 0
    retry_count: int = 0
    backoff_events: int = 0
    status: str = "running"
    
    # Per-worker metrics
    worker_metrics: Dict[str, dict] = field(default_factory=dict)


class ConcurrentRunner:
    """
    Multi-worker concurrent runner for processing ingestion work items.
    
    Features:
    - Configurable number of worker threads
    - Atomic claim/lease semantics for concurrent safety
    - Graceful shutdown with drain mode
    - Worker heartbeat tracking
    - Comprehensive metrics and logging
    """
    
    def __init__(
        self,
        state_store: SqlServerStateStore,
        connectors: Dict[str, Connector],
        storage_writers: List[StorageWriter],
        discovery_plugins: Optional[List[Discovery]] = None,
        config: Optional[RunnerConfig] = None,
    ):
        """
        Initialize the concurrent runner.
        
        Args:
            state_store: SQL Server state store for work queue
            connectors: Dictionary of connectors by source_system name
            storage_writers: List of storage writers for persisting results
            discovery_plugins: Optional discovery plugins for finding new items
            config: Runner configuration (uses defaults if not provided)
        """
        self.state_store = state_store
        self.connectors = connectors
        self.storage_writers = storage_writers
        self.discovery_plugins = discovery_plugins or []
        self.config = config or RunnerConfig()
        
        # Runtime state
        self._executor: Optional[ThreadPoolExecutor] = None
        self._workers: Dict[str, Future] = {}
        self._shutdown_event = threading.Event()
        self._pause_event = threading.Event()
        self._drain_mode = False
        
        # Metrics
        self._metrics_lock = threading.Lock()
        self._run_metrics: Optional[RunMetrics] = None
        
        # Rate limiting
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = 0.0
        
        # Hostname and PID for worker identification
        self._hostname = socket.gethostname()
        self._pid = os.getpid()
    
    def run(self, run_id: Optional[str] = None) -> RunMetrics:
        """
        Run the concurrent ingestion pipeline.
        
        Spawns worker threads and processes items until:
        - Queue is empty
        - max_items limit reached
        - stop_after limit reached
        - Shutdown signal received
        
        Args:
            run_id: Optional run identifier (auto-generated if not provided)
            
        Returns:
            RunMetrics with aggregate statistics
        """
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        logger.info(f"Starting concurrent run: {run_id}")
        logger.info(f"Configuration: max_workers={self.config.max_workers}, "
                   f"lease_seconds={self.config.lease_seconds}")
        
        # Initialize metrics
        self._run_metrics = RunMetrics(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
        )
        
        # Reset state
        self._shutdown_event.clear()
        self._pause_event.clear()
        self._drain_mode = False
        
        # Recover any expired leases before starting
        recovered = self.state_store.recover_expired_leases()
        if recovered > 0:
            logger.info(f"Recovered {recovered} items with expired leases")
        
        # Install signal handlers for graceful shutdown (Ctrl+C / SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        def _handle_shutdown_signal(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown()

        signal.signal(signal.SIGINT, _handle_shutdown_signal)
        signal.signal(signal.SIGTERM, _handle_shutdown_signal)

        try:
            # Start worker threads
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix="ingest-worker"
            )
            
            # Submit worker tasks
            for i in range(self.config.max_workers):
                worker_id = f"{self._hostname}-{self._pid}-{i}"
                future = self._executor.submit(self._worker_loop, worker_id)
                self._workers[worker_id] = future
                logger.info(f"Started worker: {worker_id}")
            
            # Wait for all workers to complete (poll to allow Ctrl+C)
            while True:
                all_done = True
                for worker_id, future in list(self._workers.items()):
                    if future.done():
                        if future.exception():
                            logger.error(
                                f"Worker {worker_id} failed with error: {future.exception()}"
                            )
                    else:
                        all_done = False
                if all_done:
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, initiating shutdown...")
            self.shutdown()
        finally:
            # Restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            self._cleanup()
        
        # Finalize metrics
        self._run_metrics.ended_at = datetime.now(timezone.utc)
        self._run_metrics.status = "completed"
        
        logger.info(f"Run complete: {run_id}")
        logger.info(f"Metrics: processed={self._run_metrics.items_processed}, "
                   f"succeeded={self._run_metrics.items_succeeded}, "
                   f"failed={self._run_metrics.items_failed}")
        
        return self._run_metrics
    
    def _worker_loop(self, worker_id: str) -> None:
        """
        Main worker loop.
        
        Continuously claims and processes work items until:
        - Shutdown signal
        - No more items available
        - Limits reached
        """
        logger.info(f"Worker {worker_id} starting")
        
        worker_metrics = {
            "items_processed": 0,
            "items_succeeded": 0,
            "items_failed": 0,
        }
        
        last_heartbeat = time.time()
        
        try:
            while not self._shutdown_event.is_set():
                # Check if paused
                while self._pause_event.is_set() and not self._shutdown_event.is_set():
                    self._update_heartbeat(worker_id, "paused", worker_metrics)
                    time.sleep(1)
                
                # Check if draining (no new claims)
                if self._drain_mode:
                    logger.info(f"Worker {worker_id} exiting (drain mode)")
                    break
                
                # Check limits
                if self._should_stop(worker_metrics["items_processed"]):
                    logger.info(f"Worker {worker_id} reached limit, exiting")
                    break
                
                # Send heartbeat if needed
                if time.time() - last_heartbeat > self.config.heartbeat_interval:
                    self._update_heartbeat(worker_id, "active", worker_metrics)
                    last_heartbeat = time.time()
                
                # Claim next work item
                work_item = self.state_store.claim_work_item(
                    worker_id=worker_id,
                    lease_seconds=self.config.lease_seconds,
                    source_filter=self.config.source_filter,
                )
                
                if work_item is None:
                    # No items available, wait and retry
                    self._update_heartbeat(worker_id, "idle", worker_metrics)
                    time.sleep(1)
                    continue
                
                # Update heartbeat with current item
                self._update_heartbeat(
                    worker_id, "active", worker_metrics,
                    current_work_item_id=work_item.work_item_id
                )
                
                # Process the work item
                try:
                    self._process_work_item(work_item, worker_id)
                    worker_metrics["items_succeeded"] += 1
                    with self._metrics_lock:
                        self._run_metrics.items_succeeded += 1
                except Exception as e:
                    worker_metrics["items_failed"] += 1
                    with self._metrics_lock:
                        self._run_metrics.items_failed += 1
                    logger.error(f"Worker {worker_id} failed to process "
                               f"{work_item.work_item_id}: {e}")
                
                worker_metrics["items_processed"] += 1
                with self._metrics_lock:
                    self._run_metrics.items_processed += 1
                
        except Exception as e:
            logger.exception(f"Worker {worker_id} crashed: {e}")
        finally:
            # Mark worker as stopped
            self._update_heartbeat(worker_id, "stopped", worker_metrics)
            
            # Store final metrics
            with self._metrics_lock:
                self._run_metrics.worker_metrics[worker_id] = worker_metrics
            
            logger.info(f"Worker {worker_id} stopped. Processed: {worker_metrics['items_processed']}")
    
    def _process_work_item(self, work_item: WorkItem, worker_id: str) -> None:
        """
        Process a single work item.
        
        Args:
            work_item: The item to process
            worker_id: ID of the worker processing this item
        """
        logger.info(
            f"[{worker_id}] Processing: {work_item.source_system}:"
            f"{work_item.source_name}:{work_item.resource_type}:"
            f"{work_item.resource_id} (attempt {work_item.attempt})"
        )
        
        start_time = time.time()
        
        try:
            # Get appropriate connector
            connector_key = work_item.source_system
            if connector_key not in self.connectors:
                raise ValueError(f"No connector found for: {connector_key}")
            
            connector = self.connectors[connector_key]
            
            # Rate limiting
            self._apply_rate_limit()
            
            # Build request
            request = ConnectorRequest(
                uri=work_item.request_uri,
                method=work_item.request_method,
                headers=work_item.request_headers,
                body=work_item.request_body,
            )
            
            # Capture request timestamp
            request_timestamp = datetime.now(timezone.utc)
            
            # Execute fetch
            response = connector.fetch(request)
            
            # Capture response timestamp
            response_timestamp = datetime.now(timezone.utc)
            
            # Check for throttling/error responses
            if response.status_code == 429 or response.status_code >= 500:
                # Handle throttling with backoff
                backoff_seconds = self._calculate_backoff(
                    work_item.attempt,
                    response.headers,
                )
                
                with self._metrics_lock:
                    self._run_metrics.backoff_events += 1
                
                logger.warning(
                    f"[{worker_id}] Throttled/Error {response.status_code} for "
                    f"{work_item.resource_id}, backoff {backoff_seconds}s"
                )
                
                self.state_store.fail_work_item(
                    work_item_id=work_item.work_item_id,
                    worker_id=worker_id,
                    error_message=f"HTTP {response.status_code}: {response.error_message or 'Throttled'}",
                    retryable=True,
                    backoff_seconds=backoff_seconds,
                    max_retries=self.config.max_retries,
                )
                return
            
            # Check for other errors
            if response.status_code < 200 or response.status_code >= 300:
                error_msg = response.error_message or f"HTTP {response.status_code}"
                
                self.state_store.fail_work_item(
                    work_item_id=work_item.work_item_id,
                    worker_id=worker_id,
                    error_message=error_msg,
                    retryable=(response.status_code >= 500),
                    max_retries=self.config.max_retries,
                )
                return
            
            # Success - create ingest record
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract content metadata
            content_type = None
            content_length = None
            if response.headers:
                content_type = (response.headers.get("Content-Type") or 
                              response.headers.get("content-type"))
                length_str = (response.headers.get("Content-Length") or 
                             response.headers.get("content-length"))
                if length_str:
                    try:
                        content_length = int(length_str)
                    except ValueError:
                        pass
            
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
                fetched_at_utc=response_timestamp,
                hash_sha256=self._compute_hash(response.payload),
                run_id=self._run_metrics.run_id if self._run_metrics else None,
                work_item_id=work_item.work_item_id,
                attempt=work_item.attempt,
                duration_ms=duration_ms,
                variant=work_item.variant,
                content_type=content_type,
                content_length=content_length,
                request_timestamp=request_timestamp,
                response_timestamp=response_timestamp,
            )
            
            # Write to storage
            for writer in self.storage_writers:
                try:
                    writer.write(ingest_record)
                    logger.debug(f"[{worker_id}] Wrote to {writer.get_name()}")
                except Exception as e:
                    logger.error(f"[{worker_id}] Storage write failed "
                               f"({writer.get_name()}): {e}")
            
            # Discovery
            if self.config.enable_discovery and self.discovery_plugins:
                discovered = self._run_discovery(ingest_record, work_item)
                with self._metrics_lock:
                    self._run_metrics.items_discovered += discovered
            
            # Mark as completed
            self.state_store.complete_work_item(
                work_item_id=work_item.work_item_id,
                worker_id=worker_id,
            )
            
            logger.info(
                f"[{worker_id}] Completed: {work_item.resource_id} "
                f"({response.status_code}, {duration_ms}ms)"
            )
            
        except Exception as e:
            # Unexpected error
            logger.exception(f"[{worker_id}] Unexpected error: {e}")
            
            self.state_store.fail_work_item(
                work_item_id=work_item.work_item_id,
                worker_id=worker_id,
                error_message=str(e),
                retryable=True,
                max_retries=self.config.max_retries,
            )
            raise
    
    def _run_discovery(self, record: IngestRecord, work_item: WorkItem) -> int:
        """Run discovery plugins and enqueue new items."""
        enqueued = 0
        
        for plugin in self.discovery_plugins:
            try:
                items = plugin.discover(record, work_item)
                for item in items:
                    if self.state_store.enqueue(item):
                        enqueued += 1
            except Exception as e:
                logger.error(f"Discovery failed ({plugin.get_name()}): {e}")
        
        if enqueued > 0:
            logger.info(f"Discovered and enqueued {enqueued} new items")
        
        return enqueued
    
    def _calculate_backoff(
        self, 
        attempt: int, 
        headers: Optional[Dict[str, str]]
    ) -> int:
        """
        Calculate backoff delay for retry.
        
        Respects Retry-After header if present, otherwise uses
        exponential backoff with jitter.
        """
        # Check for Retry-After header
        if headers and self.config.respect_retry_after:
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    pass  # Not an integer, fall through to default
        
        # Exponential backoff with jitter
        base = self.config.base_backoff_seconds * (2 ** attempt)
        jitter = random.uniform(0, 1) * base * 0.5
        delay = min(base + jitter, self.config.max_backoff_seconds)
        
        return int(delay)
    
    def _compute_hash(self, payload: dict) -> str:
        """Compute SHA256 hash of payload."""
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    
    def _apply_rate_limit(self) -> None:
        """Apply global rate limiting."""
        if self.config.requests_per_second <= 0:
            return
        
        min_interval = 1.0 / self.config.requests_per_second
        
        with self._rate_limit_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_time = time.time()
    
    def _update_heartbeat(
        self,
        worker_id: str,
        status: str,
        metrics: dict,
        current_work_item_id: Optional[str] = None,
    ) -> None:
        """Update worker heartbeat in database."""
        try:
            self.state_store.update_worker_heartbeat(
                worker_id=worker_id,
                hostname=self._hostname,
                pid=self._pid,
                items_processed=metrics["items_processed"],
                items_succeeded=metrics["items_succeeded"],
                items_failed=metrics["items_failed"],
                status=status,
                current_work_item_id=current_work_item_id,
            )
        except Exception as e:
            logger.warning(f"Failed to update heartbeat for {worker_id}: {e}")
    
    def _should_stop(self, worker_processed: int) -> bool:
        """Check if we should stop processing."""
        # Check max_items (global)
        if self.config.max_items:
            with self._metrics_lock:
                if self._run_metrics and self._run_metrics.items_processed >= self.config.max_items:
                    return True
        
        # Check stop_after (per-worker for testing)
        if self.config.stop_after and worker_processed >= self.config.stop_after:
            return True
        
        return False
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        
        # Remove worker heartbeats
        for worker_id in self._workers:
            try:
                self.state_store.remove_worker(worker_id)
            except Exception:
                pass
        
        self._workers.clear()
    
    # =========================================================================
    # Control Methods
    # =========================================================================
    
    def shutdown(self) -> None:
        """
        Initiate graceful shutdown.
        
        Workers will finish their current item and exit.
        """
        logger.info("Initiating shutdown...")
        self._shutdown_event.set()
    
    def pause(self) -> None:
        """
        Pause claiming new work items.
        
        Workers will finish their current item then wait.
        """
        logger.info("Pausing workers...")
        self._pause_event.set()
    
    def resume(self) -> None:
        """Resume from paused state."""
        logger.info("Resuming workers...")
        self._pause_event.clear()
    
    def drain(self) -> None:
        """
        Enter drain mode.
        
        Workers will finish their current item then exit.
        No new items will be claimed.
        """
        logger.info("Entering drain mode...")
        self._drain_mode = True
    
    def get_status(self) -> Dict:
        """
        Get current runner status.
        
        Returns:
            Dictionary with queue stats, worker info, and run metrics
        """
        queue_stats = self.state_store.get_queue_stats()
        workers = self.state_store.get_active_workers()
        
        return {
            "queue": {
                "pending": queue_stats.pending,
                "in_progress": queue_stats.in_progress,
                "completed": queue_stats.completed,
                "failed": queue_stats.failed,
                "total": queue_stats.total,
                "oldest_pending_at": queue_stats.oldest_pending_at.isoformat() 
                    if queue_stats.oldest_pending_at else None,
            },
            "workers": [
                {
                    "worker_id": w.worker_id,
                    "hostname": w.hostname,
                    "pid": w.pid,
                    "status": w.status.value,
                    "items_processed": w.items_processed,
                    "current_item": w.current_work_item_id,
                    "last_heartbeat": w.last_heartbeat_at.isoformat(),
                }
                for w in workers
            ],
            "run_metrics": {
                "run_id": self._run_metrics.run_id if self._run_metrics else None,
                "items_processed": self._run_metrics.items_processed if self._run_metrics else 0,
                "items_succeeded": self._run_metrics.items_succeeded if self._run_metrics else 0,
                "items_failed": self._run_metrics.items_failed if self._run_metrics else 0,
                "items_discovered": self._run_metrics.items_discovered if self._run_metrics else 0,
            } if self._run_metrics else None,
            "state": {
                "paused": self._pause_event.is_set(),
                "draining": self._drain_mode,
                "shutting_down": self._shutdown_event.is_set(),
            },
        }
    
    def close(self) -> None:
        """Close all resources."""
        logger.info("Closing runner resources")
        
        self._cleanup()
        
        # Close connectors
        for connector in self.connectors.values():
            if hasattr(connector, 'close'):
                connector.close()
        
        # Close storage writers
        for writer in self.storage_writers:
            writer.close()
        
        # Close state store
        self.state_store.close()
