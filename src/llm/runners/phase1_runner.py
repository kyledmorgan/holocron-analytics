"""
Phase 1 Runner - End-to-end LLM derive runner.

This runner implements the Phase 1 flow:
1. Claim a job from the SQL Server queue
2. Build evidence bundle from job input
3. Render prompt from interrogation definition
4. Call Ollama with structured output
5. Validate response against contract
6. Write artifacts to lake
7. Update job status in SQL Server

Usage:
    # Run once (process single job)
    python -m src.llm.runners.phase1_runner --once --worker-id worker-1

    # Run in loop mode
    python -m src.llm.runners.phase1_runner --loop --poll-seconds 10 --worker-id worker-1
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..contracts.phase1_contracts import (
    EvidenceBundleV1,
    EvidenceSnippet,
    Job,
    JobInputEnvelope,
    validate_entity_facts_output,
)
from ..contracts.evidence_contracts import (
    EvidenceBundle,
    EvidencePolicy,
)
from ..core.exceptions import LLMProviderError, LLMValidationError, LLMStorageError
from ..core.types import LLMConfig
from ..evidence.builder import build_evidence_bundle
from ..interrogations.registry import get_interrogation, InterrogationDefinition
from ..providers.ollama_client import OllamaClient, OllamaResponse
from ..storage.sql_job_queue import SqlJobQueue, QueueConfig
from ..storage.lake_writer import LakeWriter, LakeWriterConfig


logger = logging.getLogger(__name__)


@dataclass
class RunnerConfig:
    """Configuration for the Phase 1 runner."""
    worker_id: str
    ollama_base_url: str = "http://ollama:11434"
    default_model: str = "llama3.2"
    poll_seconds: int = 10
    lake_root: str = "lake/llm_runs"
    temperature: float = 0.0
    timeout_seconds: int = 120
    
    @classmethod
    def from_env(cls, worker_id: Optional[str] = None) -> "RunnerConfig":
        """Create config from environment variables."""
        return cls(
            worker_id=worker_id or os.environ.get("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            default_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            poll_seconds=int(os.environ.get("POLL_SECONDS", "10")),
            lake_root=os.environ.get("LAKE_ROOT", "lake/llm_runs"),
            temperature=float(os.environ.get("OLLAMA_TEMPERATURE", "0.0")),
            timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")),
        )


class Phase1Runner:
    """
    End-to-end LLM derive runner for Phase 1.
    
    Orchestrates the full derive pipeline:
    1. Claim job from queue
    2. Build evidence bundle
    3. Render prompt
    4. Call Ollama with structured output
    5. Validate response
    6. Write artifacts
    7. Update job status
    
    Example:
        >>> config = RunnerConfig.from_env()
        >>> runner = Phase1Runner(config)
        >>> processed = runner.run_once()
    """
    
    def __init__(
        self,
        config: RunnerConfig,
        queue: Optional[SqlJobQueue] = None,
        lake_writer: Optional[LakeWriter] = None,
    ):
        """
        Initialize the Phase 1 runner.
        
        Args:
            config: Runner configuration
            queue: SQL job queue (created from env if None)
            lake_writer: Lake writer (created from env if None)
        """
        self.config = config
        self.queue = queue or SqlJobQueue(QueueConfig.from_env())
        self.lake_writer = lake_writer or LakeWriter(LakeWriterConfig(base_dir=config.lake_root))
        self._shutdown_requested = False
        
        logger.info(
            f"Phase1Runner initialized: worker_id={config.worker_id}, "
            f"ollama_base_url={config.ollama_base_url}, model={config.default_model}"
        )
    
    def _get_ollama_client(self, model: str) -> OllamaClient:
        """Create an Ollama client for the specified model."""
        llm_config = LLMConfig(
            provider="ollama",
            model=model,
            base_url=self.config.ollama_base_url,
            temperature=self.config.temperature,
            timeout_seconds=self.config.timeout_seconds,
            stream=False,
        )
        return OllamaClient(llm_config)
    
    def run_once(self) -> bool:
        """
        Process a single job.
        
        Returns:
            True if a job was processed, False if no jobs available
        """
        # Claim next job
        job = self.queue.claim_next_job(self.config.worker_id)
        if job is None:
            logger.debug("No jobs available")
            return False
        
        logger.info(f"Processing job {job.job_id} (interrogation: {job.interrogation_key})")
        
        try:
            self._process_job(job)
            return True
        except Exception as e:
            logger.error(f"Job {job.job_id} failed with unexpected error: {e}")
            try:
                self.queue.mark_failed(job.job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
            return True
    
    def run_loop(self, poll_seconds: Optional[int] = None) -> None:
        """
        Run in loop mode, continuously processing jobs.
        
        Args:
            poll_seconds: Seconds to wait between poll attempts
        """
        poll_interval = poll_seconds or self.config.poll_seconds
        
        logger.info(f"Starting loop mode with {poll_interval}s poll interval")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        while not self._shutdown_requested:
            try:
                processed = self.run_once()
                if not processed:
                    # No jobs, wait before polling again
                    time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in run loop: {e}")
                time.sleep(poll_interval)
        
        logger.info("Shutdown complete")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_requested = True
    
    def _process_job(self, job: Job) -> None:
        """
        Process a single job end-to-end.
        
        Args:
            job: The job to process
        """
        timestamp = datetime.now(timezone.utc)
        
        # 1. Get interrogation definition
        interrogation = get_interrogation(job.interrogation_key)
        if interrogation is None:
            error = f"Unknown interrogation key: {job.interrogation_key}"
            logger.error(error)
            self.queue.mark_failed(job.job_id, error)
            return
        
        # 2. Determine model to use
        model = job.model_hint or interrogation.recommended_model or self.config.default_model
        
        # 3. Create Ollama client
        client = self._get_ollama_client(model)
        
        # 4. Get model info for tracking
        model_info = client.get_model_info()
        model_digest = model_info.get("digest") if model_info else None
        model_tag = model.split(":")[-1] if ":" in model else None
        model_name = model.split(":")[0] if ":" in model else model
        
        # 5. Create run record
        run_id = self.queue.create_run(
            job_id=job.job_id,
            worker_id=self.config.worker_id,
            ollama_base_url=self.config.ollama_base_url,
            model_name=model_name,
            model_tag=model_tag,
            model_digest=model_digest,
            options_json=json.dumps({"temperature": self.config.temperature}),
        )
        
        try:
            # 6. Build evidence bundle
            evidence_bundle = self._build_evidence_bundle(job)
            
            # 7. Render prompt
            job_input = job.get_input()
            prompt = self._render_prompt(interrogation, job_input, evidence_bundle)
            
            # 8. Build messages
            messages = []
            if interrogation.system_prompt:
                messages.append({"role": "system", "content": interrogation.system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 9. Get request payload for artifact
            request_payload = client.get_full_request_payload(
                messages=messages,
                output_schema=interrogation.output_schema,
            )
            
            # 10. Write request artifact
            request_artifact = self.lake_writer.write_request(run_id, request_payload, timestamp)
            self.queue.create_artifact(
                run_id=run_id,
                artifact_type="request_json",
                lake_uri=request_artifact.lake_uri,
                content_sha256=request_artifact.content_sha256,
                byte_count=request_artifact.byte_count,
            )
            
            # 11. Write evidence artifact
            evidence_artifact = self.lake_writer.write_evidence(run_id, evidence_bundle.to_dict(), timestamp)
            self.queue.create_artifact(
                run_id=run_id,
                artifact_type="evidence_bundle",
                lake_uri=evidence_artifact.lake_uri,
                content_sha256=evidence_artifact.content_sha256,
                byte_count=evidence_artifact.byte_count,
            )
            
            # 11b. Record evidence bundle metadata to SQL Server
            self.queue.create_evidence_bundle(
                bundle_id=evidence_bundle.bundle_id,
                build_version=evidence_bundle.build_version,
                policy_json=json.dumps(evidence_bundle.policy.to_dict()),
                summary_json=json.dumps(evidence_bundle.summary),
                lake_uri=evidence_artifact.lake_uri,
            )
            
            # 11c. Link run to evidence bundle
            self.queue.link_run_to_evidence_bundle(
                run_id=run_id,
                bundle_id=evidence_bundle.bundle_id,
            )
            
            # 12. Write prompt artifact
            prompt_artifact = self.lake_writer.write_prompt(run_id, prompt, timestamp)
            self.queue.create_artifact(
                run_id=run_id,
                artifact_type="prompt_text",
                lake_uri=prompt_artifact.lake_uri,
                content_sha256=prompt_artifact.content_sha256,
                byte_count=prompt_artifact.byte_count,
            )
            
            # 13. Call Ollama with structured output
            logger.info(f"Calling Ollama ({model}) for job {job.job_id}")
            response = client.chat_with_structured_output(
                messages=messages,
                output_schema=interrogation.output_schema,
            )
            
            # 14. Write response artifact (always, even if parsing fails)
            response_artifact = self.lake_writer.write_response(
                run_id, response.raw_response or {}, timestamp
            )
            self.queue.create_artifact(
                run_id=run_id,
                artifact_type="response_json",
                lake_uri=response_artifact.lake_uri,
                content_sha256=response_artifact.content_sha256,
                byte_count=response_artifact.byte_count,
            )
            
            # 15. Extract metrics
            metrics = client.extract_metrics(response.raw_response or {})
            
            # 16. Parse and validate output
            parsed_output = self._parse_and_validate(response, interrogation)
            
            # 17. Write parsed output artifact
            output_artifact = self.lake_writer.write_output(run_id, parsed_output, timestamp)
            self.queue.create_artifact(
                run_id=run_id,
                artifact_type="parsed_output",
                lake_uri=output_artifact.lake_uri,
                content_sha256=output_artifact.content_sha256,
                byte_count=output_artifact.byte_count,
            )
            
            # 18. Complete run as succeeded
            self.queue.complete_run(
                run_id=run_id,
                status="SUCCEEDED",
                metrics_json=json.dumps(metrics),
            )
            
            # 19. Mark job as succeeded
            self.queue.mark_succeeded(job.job_id, run_id)
            
            logger.info(f"Job {job.job_id} completed successfully")
            
        except LLMValidationError as e:
            # Validation failed - artifacts are already written
            logger.error(f"Validation error for job {job.job_id}: {e}")
            self.queue.complete_run(run_id=run_id, status="FAILED", error=str(e))
            self.queue.mark_failed(job.job_id, str(e), run_id)
            
        except LLMProviderError as e:
            # Provider error (Ollama not available, etc.)
            logger.error(f"Provider error for job {job.job_id}: {e}")
            self.queue.complete_run(run_id=run_id, status="FAILED", error=str(e))
            self.queue.mark_failed(job.job_id, str(e), run_id)
            
        except Exception as e:
            # Unexpected error
            logger.exception(f"Unexpected error processing job {job.job_id}")
            self.queue.complete_run(run_id=run_id, status="FAILED", error=str(e))
            self.queue.mark_failed(job.job_id, str(e), run_id)
    
    def _build_evidence_bundle(self, job: Job) -> EvidenceBundle:
        """
        Build evidence bundle from job input using Phase 2 builder.
        
        Phase 2 supports multiple modes:
        1. Evidence provided directly in input_json (inline)
        2. Evidence references in evidence_ref_json pointing to lake artifacts
        3. SQL result sets (existing artifacts or executed queries)
        4. HTTP response artifacts
        
        Args:
            job: The job to build evidence for
            
        Returns:
            EvidenceBundle with bounded evidence items
        """
        job_input_dict = json.loads(job.input_json)
        
        # Parse evidence references if present
        evidence_refs = None
        if job.evidence_ref_json:
            try:
                evidence_refs = json.loads(job.evidence_ref_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse evidence_ref_json: {e}")
        
        # Use default policy or customize as needed
        policy = EvidencePolicy(
            max_items=50,
            max_total_bytes=100000,
            max_item_bytes=10000,
            max_sql_rows=100,
            enable_redaction=False,
        )
        
        # Build evidence bundle using Phase 2 builder
        bundle = build_evidence_bundle(
            job_input=job_input_dict,
            evidence_refs=evidence_refs,
            policy=policy,
            lake_root=self.config.lake_root,
        )
        
        logger.info(
            f"Built evidence bundle {bundle.bundle_id} with {len(bundle.items)} items "
            f"({bundle.summary.get('total_bytes', 0)} bytes)"
        )
        
        return bundle
    
    def _render_prompt(
        self,
        interrogation: InterrogationDefinition,
        job_input: JobInputEnvelope,
        evidence_bundle: EvidenceBundle,
    ) -> str:
        """
        Render the prompt from template and inputs.
        
        Args:
            interrogation: The interrogation definition
            job_input: Job input envelope
            evidence_bundle: Evidence bundle (Phase 2)
            
        Returns:
            Rendered prompt string
        """
        # Format evidence content from Phase 2 evidence items
        evidence_parts = []
        for item in evidence_bundle.items:
            evidence_parts.append(
                f"--- Evidence [{item.evidence_id}] (type: {item.evidence_type}) ---\n"
                f"{item.content}\n"
            )
        evidence_content = "\n".join(evidence_parts) if evidence_parts else "[No evidence provided]"
        
        # Render template
        prompt = interrogation.prompt_template.format(
            entity_type=job_input.entity_type,
            entity_id=job_input.entity_id,
            evidence_content=evidence_content,
        )
        
        return prompt
    
    def _parse_and_validate(
        self,
        response: OllamaResponse,
        interrogation: InterrogationDefinition,
    ) -> Dict[str, Any]:
        """
        Parse and validate the LLM response.
        
        Args:
            response: Ollama response
            interrogation: Interrogation definition with validator
            
        Returns:
            Parsed and validated output dict
            
        Raises:
            LLMValidationError: If parsing or validation fails
        """
        if not response.success:
            raise LLMValidationError(
                f"LLM request failed: {response.error_message}",
                validation_errors=["Request failed"]
            )
        
        if not response.content:
            raise LLMValidationError(
                "LLM returned empty content",
                validation_errors=["Empty content"]
            )
        
        # Parse JSON
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise LLMValidationError(
                f"LLM returned invalid JSON: {e}",
                validation_errors=[str(e)]
            )
        
        # Validate against contract
        validation_errors = interrogation.validate_output(parsed)
        if validation_errors:
            raise LLMValidationError(
                f"Output validation failed: {validation_errors}",
                validation_errors=validation_errors
            )
        
        return parsed


def main():
    """CLI entry point for Phase 1 runner."""
    parser = argparse.ArgumentParser(
        description="Phase 1 LLM Derive Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Process a single job and exit"
    )
    mode_group.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, polling for jobs"
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
        "--model",
        type=str,
        default=None,
        help="Override model (default: use job model_hint or config)"
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=None,
        help="Ollama base URL (default: from OLLAMA_BASE_URL env)"
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
    
    # Build config
    config = RunnerConfig.from_env(args.worker_id)
    
    if args.ollama_url:
        config.ollama_base_url = args.ollama_url
    if args.model:
        config.default_model = args.model
    if args.lake_root:
        config.lake_root = args.lake_root
    
    # Create and run
    runner = Phase1Runner(config)
    
    if args.once:
        processed = runner.run_once()
        sys.exit(0 if processed else 1)
    else:
        runner.run_loop(args.poll_seconds)


if __name__ == "__main__":
    main()
