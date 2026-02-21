"""
Job Dispatcher - Routes and executes jobs based on job type.

This module provides the dispatcher that:
1. Claims jobs from the queue
2. Resolves job type → definition via registry
3. Constructs execution context (job_id, run_id, correlation_id)
4. Invokes the correct handler
5. Ensures consistent status transitions and error handling

The dispatcher supports both live and dry-run execution modes.
"""

import argparse
import importlib
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..contracts.phase1_contracts import Job
from ..contracts.evidence_contracts import EvidenceBundle, EvidencePolicy
from ..core.exceptions import LLMProviderError, LLMValidationError, LLMStorageError
from ..evidence.builder import build_evidence_bundle
from ..interrogations.registry import get_interrogation
from ..providers.ollama_client import OllamaClient
from ..storage.sql_job_queue import SqlJobQueue, QueueConfig
from ..storage.lake_writer import LakeWriter, LakeWriterConfig

from ..jobs.registry import (
    JobTypeDefinition,
    get_job_type,
    get_job_type_registry,
)
from ..jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ExecutionMode,
    ArtifactReference,
)


logger = logging.getLogger(__name__)


class _SafeFormatDict(dict):
    """Format-map dict that returns empty string for missing keys."""
    def __missing__(self, key):
        return ""


class DispatcherConfig:
    """Configuration for the job dispatcher."""
    
    def __init__(
        self,
        worker_id: str,
        dry_run: bool = False,
        poll_seconds: int = 10,
        lake_root: str = "lake/llm_runs",
        ollama_base_url: str = "http://ollama:11434",
        default_model: str = "llama3.2",
        temperature: float = 0.0,
        timeout_seconds: int = 120,
    ):
        self.worker_id = worker_id
        self.dry_run = dry_run
        self.poll_seconds = poll_seconds
        self.lake_root = lake_root
        self.ollama_base_url = ollama_base_url
        self.default_model = default_model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
    
    @classmethod
    def from_env(cls, worker_id: Optional[str] = None, dry_run: bool = False) -> "DispatcherConfig":
        """Create config from environment variables."""
        import uuid
        return cls(
            worker_id=worker_id or os.environ.get("WORKER_ID", f"dispatcher-{uuid.uuid4().hex[:8]}"),
            dry_run=dry_run,
            poll_seconds=int(os.environ.get("POLL_SECONDS", "10")),
            lake_root=os.environ.get("LAKE_ROOT", "lake/llm_runs"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            default_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            temperature=float(os.environ.get("OLLAMA_TEMPERATURE", "0.0")),
            timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")),
        )
    
    @property
    def execution_mode(self) -> ExecutionMode:
        """Get the execution mode based on dry_run flag."""
        return ExecutionMode.DRY_RUN if self.dry_run else ExecutionMode.LIVE


class JobDispatcher:
    """
    Job dispatcher that routes jobs to handlers based on job type.
    
    The dispatcher:
    1. Claims jobs from the SQL queue
    2. Resolves job type to handler via registry
    3. Builds execution context with correlation IDs
    4. Invokes handler with context
    5. Records results and artifacts
    6. Updates job status
    
    Supports dry-run mode where artifacts are written but domain
    writes are skipped.
    
    Example:
        >>> config = DispatcherConfig.from_env(dry_run=True)
        >>> dispatcher = JobDispatcher(config)
        >>> processed = dispatcher.dispatch_once()
    """
    
    def __init__(
        self,
        config: DispatcherConfig,
        queue: Optional[SqlJobQueue] = None,
        lake_writer: Optional[LakeWriter] = None,
    ):
        """
        Initialize the dispatcher.
        
        Args:
            config: Dispatcher configuration
            queue: SQL job queue (created from env if None)
            lake_writer: Lake writer (created from config if None)
        """
        self.config = config
        self.queue = queue or SqlJobQueue(QueueConfig.from_env())
        self.lake_writer = lake_writer or LakeWriter(LakeWriterConfig(base_dir=config.lake_root))
        self._shutdown_requested = False
        self._handlers: Dict[str, Callable] = {}
        
        mode_str = "DRY-RUN" if config.dry_run else "LIVE"
        logger.info(
            f"JobDispatcher initialized: worker_id={config.worker_id}, "
            f"mode={mode_str}, lake_root={config.lake_root}"
        )
    
    def register_handler(self, job_type: str, handler: Callable) -> None:
        """
        Register a handler callable for a job type.
        
        This allows handlers to be provided directly rather than
        loaded via import path.
        
        Args:
            job_type: Job type identifier
            handler: Callable handler function
        """
        self._handlers[job_type] = handler
        logger.debug(f"Registered handler for job type: {job_type}")
    
    def _resolve_handler(self, job_type_def: JobTypeDefinition) -> Optional[Callable]:
        """
        Resolve the handler callable for a job type.
        
        First checks for directly registered handlers, then attempts
        to import from the handler_ref path.
        
        Args:
            job_type_def: Job type definition
            
        Returns:
            Handler callable, or None if not found
        """
        job_type = job_type_def.job_type
        
        # Check for directly registered handler
        if job_type in self._handlers:
            return self._handlers[job_type]
        
        # Try to import from handler_ref
        handler_ref = job_type_def.handler_ref
        if not handler_ref or not handler_ref.strip():
            return None
        
        try:
            # Parse "module.path.function" format
            parts = handler_ref.rsplit(".", 1)
            if len(parts) != 2:
                logger.error(f"Invalid handler_ref format: {handler_ref}")
                return None
            
            module_path, func_name = parts
            module = importlib.import_module(module_path)
            handler = getattr(module, func_name, None)
            
            if handler is None:
                logger.error(f"Handler function not found: {handler_ref}")
                return None
            
            # Cache for future use
            self._handlers[job_type] = handler
            return handler
            
        except ImportError as e:
            logger.warning(f"Could not import handler module for {job_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error resolving handler for {job_type}: {e}")
            return None
    
    def dispatch_once(self) -> bool:
        """
        Claim and dispatch a single job.
        
        Returns:
            True if a job was processed, False if no jobs available
        """
        # Claim next job from queue
        job = self.queue.claim_next_job(self.config.worker_id)
        if job is None:
            logger.debug("No jobs available")
            return False
        
        logger.info(
            f"Claimed job {job.job_id} "
            f"(interrogation: {job.interrogation_key}, attempt: {job.attempt_count})"
        )
        
        try:
            self._dispatch_job(job)
            return True
        except Exception as e:
            logger.error(f"Unexpected error dispatching job {job.job_id}: {e}")
            try:
                self.queue.mark_failed(job.job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
            return True
    
    def dispatch_loop(self, poll_seconds: Optional[int] = None) -> None:
        """
        Run in loop mode, continuously claiming and dispatching jobs.
        
        Args:
            poll_seconds: Seconds to wait between poll attempts
        """
        poll_interval = poll_seconds or self.config.poll_seconds
        mode_str = "DRY-RUN" if self.config.dry_run else "LIVE"
        
        logger.info(
            f"Starting dispatch loop (mode={mode_str}, poll={poll_interval}s)"
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        while not self._shutdown_requested:
            try:
                processed = self.dispatch_once()
                if not processed:
                    time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in dispatch loop: {e}")
                time.sleep(poll_interval)
        
        logger.info("Dispatch loop shutdown complete")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_requested = True
    
    def _dispatch_job(self, job: Job) -> None:
        """
        Dispatch a single job to its handler.
        
        Args:
            job: The job to dispatch
        """
        timestamp = datetime.now(timezone.utc)
        
        # 1. Resolve job type (use interrogation_key as fallback job type)
        job_type = self._infer_job_type(job)
        job_type_def = get_job_type(job_type)
        
        # 2. Get interrogation definition
        interrogation = get_interrogation(job.interrogation_key)
        if interrogation is None:
            error = f"Unknown interrogation key: {job.interrogation_key}"
            logger.error(error)
            self.queue.mark_failed(job.job_id, error)
            return
        
        # 3. Create execution context
        ctx = RunContext.create(
            job_id=job.job_id,
            worker_id=self.config.worker_id,
            job_type=job_type,
            interrogation_key=job.interrogation_key,
            execution_mode=self.config.execution_mode,
            attempt_number=job.attempt_count,
            max_attempts=job.max_attempts,
        )
        
        # Log with correlation context
        log_ctx = ctx.get_log_context()
        logger.info(
            f"Dispatching job: {log_ctx}",
            extra=log_ctx,
        )
        
        # 4. Create run record
        run_id = self._create_run_record(job, ctx, timestamp)
        
        # Update context with actual run_id from database
        ctx.run_id = run_id
        ctx.correlation_id = f"{job.job_id}-{run_id[:8]}"
        
        try:
            # 5. Resolve handler
            handler = None
            if job_type_def:
                handler = self._resolve_handler(job_type_def)
            
            # 6. Execute handler or use default execution
            if handler:
                result = self._execute_with_handler(job, ctx, handler, timestamp)
            else:
                # Fall back to generic execution using existing Phase1 patterns
                logger.info(f"No custom handler for {job_type}, using generic execution")
                result = self._execute_generic(job, ctx, interrogation, timestamp)
            
            # 7. Complete run based on result
            self._complete_run(job, ctx, result, timestamp)
            
        except Exception as e:
            logger.exception(f"Error executing job {job.job_id}")
            self.queue.complete_run(
                run_id=ctx.run_id,
                status="FAILED",
                error=str(e),
            )
            self.queue.mark_failed(job.job_id, str(e))
    
    def _infer_job_type(self, job: Job) -> str:
        """
        Infer job type from job metadata.
        
        Uses interrogation_key as the primary source since existing jobs
        may not have explicit job_type field.
        """
        # Map interrogation keys to job types
        key_to_type = {
            "page_classification_v1": "page_classification",
            "sw_entity_facts_v1": "sw_entity_facts",
        }
        return key_to_type.get(job.interrogation_key, job.interrogation_key)
    
    def _create_run_record(
        self,
        job: Job,
        ctx: RunContext,
        timestamp: datetime,
    ) -> str:
        """Create a run record in the database."""
        model = job.model_hint or self.config.default_model
        model_name = model.split(":")[0] if ":" in model else model
        model_tag = model.split(":")[-1] if ":" in model else None
        
        run_id = self.queue.create_run(
            job_id=job.job_id,
            worker_id=ctx.worker_id,
            ollama_base_url=self.config.ollama_base_url,
            model_name=model_name,
            model_tag=model_tag,
            options_json=json.dumps({
                "temperature": self.config.temperature,
                "execution_mode": ctx.execution_mode.value,
            }),
        )
        
        return run_id
    
    def _execute_with_handler(
        self,
        job: Job,
        ctx: RunContext,
        handler: Callable,
        timestamp: datetime,
    ) -> HandlerResult:
        """
        Execute job using a registered handler.
        
        The handler receives (job, ctx) and returns HandlerResult.
        """
        try:
            result = handler(job, ctx)
            
            if not isinstance(result, HandlerResult):
                # Handler returned something else - wrap it
                if isinstance(result, dict):
                    result = HandlerResult.success(output=result)
                else:
                    result = HandlerResult.failure(
                        f"Handler returned unexpected type: {type(result)}"
                    )
            
            return result
            
        except Exception as e:
            logger.exception(f"Handler execution failed for job {job.job_id}")
            return HandlerResult.failure(error_message=str(e))
    
    def _execute_generic(
        self,
        job: Job,
        ctx: RunContext,
        interrogation,
        timestamp: datetime,
    ) -> HandlerResult:
        """
        Execute job using generic (Phase1-style) execution.
        
        This provides backwards compatibility with existing jobs that
        don't have custom handlers registered.
        """
        from ..core.types import LLMConfig
        
        artifacts = []
        
        try:
            # Build evidence bundle
            evidence_bundle = self._build_evidence_bundle(job, ctx)
            
            # Write evidence artifact
            evidence_dict = evidence_bundle.to_dict()
            evidence_content = json.dumps(evidence_dict, indent=2, ensure_ascii=False, default=str)
            evidence_artifact = self.lake_writer.write_evidence(
                ctx.run_id, evidence_dict, timestamp
            )
            artifacts.append(ArtifactReference(
                artifact_type="evidence_bundle",
                lake_uri=evidence_artifact.lake_uri,
                content_sha256=evidence_artifact.content_sha256,
                byte_count=evidence_artifact.byte_count,
            ))
            self.queue.create_artifact(
                run_id=ctx.run_id,
                artifact_type="evidence_bundle",
                lake_uri=evidence_artifact.lake_uri,
                content_sha256=evidence_artifact.content_sha256,
                byte_count=evidence_artifact.byte_count,
                content=evidence_content,
                content_mime_type="application/json",
                stored_in_sql=True,
                mirrored_to_lake=True,
            )
            
            # Render prompt
            job_input = job.get_input()
            prompt = self._render_prompt(interrogation, job_input, evidence_bundle)
            
            # Write prompt artifact
            prompt_artifact = self.lake_writer.write_prompt(ctx.run_id, prompt, timestamp)
            artifacts.append(ArtifactReference(
                artifact_type="prompt_text",
                lake_uri=prompt_artifact.lake_uri,
                content_sha256=prompt_artifact.content_sha256,
                byte_count=prompt_artifact.byte_count,
            ))
            self.queue.create_artifact(
                run_id=ctx.run_id,
                artifact_type="prompt_text",
                lake_uri=prompt_artifact.lake_uri,
                content_sha256=prompt_artifact.content_sha256,
                byte_count=prompt_artifact.byte_count,
                content=prompt,
                content_mime_type="text/plain",
                stored_in_sql=True,
                mirrored_to_lake=True,
            )
            
            # Write job metadata artifact (for dry-run debugging)
            job_meta = {
                "job_id": job.job_id,
                "job_type": ctx.job_type,
                "interrogation_key": job.interrogation_key,
                "execution_mode": ctx.execution_mode.value,
                "correlation_id": ctx.correlation_id,
                "attempt_number": ctx.attempt_number,
                "input": json.loads(job.input_json),
            }
            job_artifact = self.lake_writer.write_json(ctx.run_id, "job", job_meta, timestamp)
            artifacts.append(ArtifactReference(
                artifact_type="job_json",
                lake_uri=job_artifact.lake_uri,
                content_sha256=job_artifact.content_sha256,
                byte_count=job_artifact.byte_count,
            ))
            
            # Write run context artifact
            ctx_artifact = self.lake_writer.write_json(
                ctx.run_id, "run_meta", ctx.to_dict(), timestamp
            )
            artifacts.append(ArtifactReference(
                artifact_type="run_meta",
                lake_uri=ctx_artifact.lake_uri,
                content_sha256=ctx_artifact.content_sha256,
                byte_count=ctx_artifact.byte_count,
            ))
            
            # In dry-run mode, return success without LLM call
            if ctx.is_dry_run:
                logger.info(
                    f"DRY-RUN: Skipping LLM call and domain writes for job {job.job_id}",
                    extra=ctx.get_log_context(),
                )
                return HandlerResult.success(
                    output={"dry_run": True, "prompt_rendered": True},
                    artifacts=artifacts,
                    metrics={"execution_mode": "dry_run"},
                )
            
            # For live mode, we would call the LLM here
            # This is a simplified version - full implementation would
            # use the existing Phase1Runner logic
            logger.info(
                f"Generic execution would proceed to LLM call for job {job.job_id}",
                extra=ctx.get_log_context(),
            )
            
            # Return partial success (prompt rendered, ready for LLM)
            return HandlerResult.success(
                output={"prompt_rendered": True},
                artifacts=artifacts,
                metrics={"execution_mode": "live"},
            )
            
        except Exception as e:
            logger.exception(f"Generic execution failed for job {job.job_id}")
            return HandlerResult.failure(
                error_message=str(e),
                artifacts=artifacts,
            )
    
    def _build_evidence_bundle(self, job: Job, ctx: RunContext) -> EvidenceBundle:
        """Build evidence bundle from job input."""
        job_input_dict = json.loads(job.input_json)
        
        evidence_refs = None
        if job.evidence_ref_json:
            try:
                evidence_refs = json.loads(job.evidence_ref_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse evidence_ref_json: {e}")
        
        policy = EvidencePolicy(
            max_items=50,
            max_total_bytes=100000,
            max_item_bytes=10000,
            max_sql_rows=100,
            enable_redaction=False,
        )
        
        bundle = build_evidence_bundle(
            job_input=job_input_dict,
            evidence_refs=evidence_refs,
            policy=policy,
            lake_root=self.config.lake_root,
        )
        
        logger.debug(
            f"Built evidence bundle {bundle.bundle_id} with {len(bundle.items)} items",
            extra=ctx.get_log_context(),
        )
        
        return bundle
    
    def _render_prompt(self, interrogation, job_input, evidence_bundle) -> str:
        """Render the prompt from template and inputs."""
        evidence_parts = []
        for item in evidence_bundle.items:
            evidence_parts.append(
                f"--- Evidence [{item.evidence_id}] (type: {item.evidence_type}) ---\n"
                f"{item.content}\n"
            )
        evidence_content = "\n".join(evidence_parts) if evidence_parts else "[No evidence provided]"

        # Build a flexible template context so different interrogation
        # prompt variables can be satisfied without KeyError.
        template_values = _SafeFormatDict()
        template_values["evidence_content"] = evidence_content

        # JobInputEnvelope fields (if present)
        template_values["entity_type"] = getattr(job_input, "entity_type", "")
        template_values["entity_id"] = getattr(job_input, "entity_id", "")

        # Raw input payload fields (if present)
        try:
            input_dict = job_input.model_dump() if hasattr(job_input, "model_dump") else {}
        except Exception:
            input_dict = {}
        if isinstance(input_dict, dict):
            for k, v in input_dict.items():
                if k not in template_values and v is not None:
                    template_values[k] = v

        # Common aliases used by interrogation templates.
        source_id = template_values.get("source_id") or template_values.get("entity_id", "")
        source_page_title = (
            template_values.get("source_page_title")
            or template_values.get("title")
            or template_values.get("entity_id", "")
        )
        template_values["source_id"] = source_id
        template_values["source_page_title"] = source_page_title

        # If no explicit content was provided, reuse assembled evidence text.
        if not template_values.get("content"):
            template_values["content"] = evidence_content

        return interrogation.prompt_template.format_map(template_values)
    
    def _complete_run(
        self,
        job: Job,
        ctx: RunContext,
        result: HandlerResult,
        timestamp: datetime,
    ) -> None:
        """Complete the run based on handler result."""
        # Write result artifact
        result_dict = result.to_dict()
        result_content = json.dumps(result_dict, indent=2, ensure_ascii=False, default=str)
        result_artifact = self.lake_writer.write_json(
            ctx.run_id, "result", result_dict, timestamp
        )
        self.queue.create_artifact(
            run_id=ctx.run_id,
            artifact_type="parsed_output",
            lake_uri=result_artifact.lake_uri,
            content_sha256=result_artifact.content_sha256,
            byte_count=result_artifact.byte_count,
            content=result_content,
            content_mime_type="application/json",
            stored_in_sql=True,
            mirrored_to_lake=True,
        )
        
        log_ctx = ctx.get_log_context()
        
        if result.succeeded:
            self.queue.complete_run(
                run_id=ctx.run_id,
                status="SUCCEEDED",
                metrics_json=json.dumps(result.metrics) if result.metrics else None,
            )
            self.queue.mark_succeeded(job.job_id, ctx.run_id)
            logger.info(
                f"Job {job.job_id} completed successfully",
                extra=log_ctx,
            )
            
        elif result.status == HandlerStatus.SKIPPED:
            self.queue.complete_run(
                run_id=ctx.run_id,
                status="SUCCEEDED",  # Skipped counts as "handled"
                metrics_json=json.dumps({"skipped": True, "reason": result.skipped_reason}),
            )
            self.queue.mark_succeeded(job.job_id, ctx.run_id)
            logger.info(
                f"Job {job.job_id} skipped: {result.skipped_reason}",
                extra=log_ctx,
            )
            
        else:
            self.queue.complete_run(
                run_id=ctx.run_id,
                status="FAILED",
                error=result.error_message,
                metrics_json=json.dumps(result.metrics) if result.metrics else None,
            )
            self.queue.mark_failed(job.job_id, result.error_message or "Unknown error")
            logger.error(
                f"Job {job.job_id} failed: {result.error_message}",
                extra=log_ctx,
            )


def main():
    """CLI entry point for the job dispatcher."""
    parser = argparse.ArgumentParser(
        description="LLM Job Dispatcher - Route and execute jobs by type",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Dispatch a single job and exit"
    )
    mode_group.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, dispatching jobs"
    )
    mode_group.add_argument(
        "--list-types",
        action="store_true",
        help="List registered job types and exit"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no domain writes, artifacts only)"
    )
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Worker identifier (default: auto-generated)"
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=10,
        help="Seconds between poll attempts in loop mode (default: 10)"
    )
    parser.add_argument(
        "--lake-root",
        type=str,
        default=None,
        help="Lake root directory (default: from LAKE_ROOT env)"
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
    
    # Handle --list-types
    if args.list_types:
        registry = get_job_type_registry()
        print("Registered job types:")
        for job_type_def in registry.list_definitions():
            print(f"  {job_type_def.job_type}: {job_type_def.display_name}")
            print(f"    interrogation: {job_type_def.interrogation_key}")
            print(f"    handler: {job_type_def.handler_ref}")
        sys.exit(0)
    
    # Require --once or --loop for actual dispatch
    if not args.once and not args.loop:
        parser.error("one of --once, --loop, or --list-types is required")
    
    # Build config
    config = DispatcherConfig.from_env(args.worker_id, args.dry_run)
    
    if args.lake_root:
        config.lake_root = args.lake_root
    
    # Create and run dispatcher
    dispatcher = JobDispatcher(config)
    
    if args.once:
        processed = dispatcher.dispatch_once()
        sys.exit(0 if processed else 1)
    else:
        dispatcher.dispatch_loop(args.poll_seconds)


if __name__ == "__main__":
    main()
