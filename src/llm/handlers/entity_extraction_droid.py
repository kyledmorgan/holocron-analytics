"""
Droid Entity Extraction Handler.

Handles entity_extraction_droid jobs:
1. Reads source content from job input
2. Assembles LLM input context
3. Calls the model (or model abstraction)
4. Parses output and validates against contract
5. Writes artifacts to lake
6. Persists entities via stored procedure (unless dry-run)
7. Updates job/run status
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..contracts.phase1_contracts import Job
from ..jobs.handlers import (
    RunContext,
    HandlerResult,
    HandlerStatus,
    ArtifactReference,
)
from ..interrogations.registry import get_interrogation
from ..interrogations.definitions.entity_extraction_droid import validate_entity_extraction_output


logger = logging.getLogger(__name__)


class EntityExtractionDroidHandler:
    """
    Handler for droid entity extraction jobs.
    
    This handler:
    - Extracts droids from source text using LLM
    - Validates output against entity extraction contract
    - Writes artifacts for debugging and audit
    - Persists entities to DimEntity (in live mode)
    
    Example:
        >>> handler = EntityExtractionDroidHandler(
        ...     ollama_client=client,
        ...     lake_writer=writer,
        ...     entity_store=store,
        ... )
        >>> result = handler.handle(job, ctx)
    """
    
    def __init__(
        self,
        ollama_client=None,
        lake_writer=None,
        entity_store=None,
    ):
        """
        Initialize the handler.
        
        Args:
            ollama_client: Client for LLM calls (optional, for testing)
            lake_writer: Lake writer for artifacts (optional, for testing)
            entity_store: Store for entity persistence (optional, for testing)
        """
        self.ollama_client = ollama_client
        self.lake_writer = lake_writer
        self.entity_store = entity_store
        self._interrogation = None
    
    @property
    def interrogation(self):
        """Lazy load interrogation definition."""
        if self._interrogation is None:
            self._interrogation = get_interrogation("entity_extraction_droid_v1")
        return self._interrogation
    
    def handle(self, job: Job, ctx: RunContext) -> HandlerResult:
        """
        Handle a droid entity extraction job.
        
        Args:
            job: The job to process
            ctx: Run context with execution metadata
            
        Returns:
            HandlerResult with status, artifacts, and output
        """
        timestamp = datetime.now(timezone.utc)
        artifacts: List[ArtifactReference] = []
        metrics: Dict[str, Any] = {
            "handler": "entity_extraction_droid",
            "execution_mode": ctx.execution_mode.value,
        }
        
        log_ctx = ctx.get_log_context()
        logger.info(f"Starting droid entity extraction for job {job.job_id}", extra=log_ctx)
        
        try:
            # 1. Parse job input
            job_input = self._parse_job_input(job)
            
            source_id = job_input.get("source_id", job_input.get("entity_id", "unknown"))
            source_title = job_input.get("source_page_title", job_input.get("title", None))
            content = job_input.get("content", "")
            
            metrics["source_id"] = source_id
            metrics["content_length"] = len(content)
            
            if not content:
                logger.warning(f"No content provided for job {job.job_id}", extra=log_ctx)
                return HandlerResult.skipped(
                    reason="No content provided",
                    artifacts=artifacts,
                )
            
            # 2. Render prompt
            prompt = self._render_prompt(source_id, source_title, content)
            metrics["prompt_length"] = len(prompt)
            
            # 3. Write prompt artifact (always, even in dry-run)
            if self.lake_writer:
                prompt_artifact = self._write_artifact(
                    ctx.run_id, "prompt", prompt, timestamp
                )
                if prompt_artifact:
                    artifacts.append(prompt_artifact)
            
            # 4. Write input artifact for debugging
            if self.lake_writer:
                input_artifact = self._write_artifact(
                    ctx.run_id, "input", json.dumps(job_input, indent=2), timestamp
                )
                if input_artifact:
                    artifacts.append(input_artifact)
            
            # 5. In dry-run mode, skip LLM call and domain writes
            if ctx.is_dry_run:
                logger.info(
                    f"DRY-RUN: Skipping LLM call and domain writes for job {job.job_id}",
                    extra=log_ctx,
                )
                
                # Write a mock output for dry-run testing
                dry_run_output = {
                    "entities": [],
                    "relationships": [],
                    "extraction_metadata": {
                        "source_page_title": source_title,
                        "total_entities_found": 0,
                        "primary_type_focus": "Droid",
                        "extraction_notes": "DRY-RUN: LLM call skipped"
                    }
                }
                
                if self.lake_writer:
                    output_artifact = self._write_artifact(
                        ctx.run_id, "output", json.dumps(dry_run_output, indent=2), timestamp
                    )
                    if output_artifact:
                        artifacts.append(output_artifact)
                
                return HandlerResult.success(
                    output=dry_run_output,
                    artifacts=artifacts,
                    metrics=metrics,
                )
            
            # 6. Call LLM (live mode)
            llm_output = self._call_llm(prompt, ctx)
            metrics["llm_call_completed"] = True
            
            # 7. Parse and validate output
            parsed_output = self._parse_llm_output(llm_output)
            validation_errors = validate_entity_extraction_output(parsed_output)
            
            if validation_errors:
                logger.warning(
                    f"Validation errors for job {job.job_id}: {validation_errors}",
                    extra=log_ctx,
                )
                
                # Write invalid output for debugging
                if self.lake_writer:
                    error_artifact = self._write_artifact(
                        ctx.run_id, "validation_errors",
                        json.dumps({"errors": validation_errors, "raw_output": llm_output}, indent=2),
                        timestamp
                    )
                    if error_artifact:
                        artifacts.append(error_artifact)
                
                return HandlerResult.failure(
                    error_message=f"Validation failed: {validation_errors[0]}",
                    artifacts=artifacts,
                    validation_errors=validation_errors,
                    metrics=metrics,
                )
            
            # 8. Write validated output artifact
            if self.lake_writer:
                output_artifact = self._write_artifact(
                    ctx.run_id, "output", json.dumps(parsed_output, indent=2), timestamp
                )
                if output_artifact:
                    artifacts.append(output_artifact)
            
            # 9. Persist entities to database (live mode only)
            domain_writes = []
            if self.entity_store and parsed_output.get("entities"):
                try:
                    writes = self._persist_entities(parsed_output["entities"], ctx)
                    domain_writes.extend(writes)
                    metrics["entities_persisted"] = len(writes)
                except Exception as e:
                    logger.error(f"Entity persistence failed: {e}", extra=log_ctx)
                    # Don't fail the job for persistence errors
                    # but record the error
                    metrics["persistence_error"] = str(e)
            
            # 10. Return success
            metrics["entities_extracted"] = len(parsed_output.get("entities", []))
            metrics["relationships_extracted"] = len(parsed_output.get("relationships", []))
            
            return HandlerResult.success(
                output=parsed_output,
                artifacts=artifacts,
                metrics=metrics,
                domain_writes=domain_writes,
            )
            
        except Exception as e:
            logger.exception(f"Handler error for job {job.job_id}: {e}", extra=log_ctx)
            return HandlerResult.failure(
                error_message=str(e),
                artifacts=artifacts,
                metrics=metrics,
            )
    
    def _parse_job_input(self, job: Job) -> Dict[str, Any]:
        """Parse job input JSON into dictionary."""
        try:
            return json.loads(job.input_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid job input JSON: {e}")
    
    def _render_prompt(
        self,
        source_id: str,
        source_title: Optional[str],
        content: str,
    ) -> str:
        """Render the prompt from template and inputs."""
        if not self.interrogation:
            raise RuntimeError("Interrogation definition not found")
        
        return self.interrogation.prompt_template.format(
            source_id=source_id,
            source_page_title=source_title or "Unknown",
            content=content,
        )
    
    def _call_llm(self, prompt: str, ctx: RunContext) -> str:
        """
        Call the LLM with the rendered prompt.
        
        Returns the raw LLM output string.
        """
        if not self.ollama_client:
            raise RuntimeError("Ollama client not configured")
        
        response = self.ollama_client.generate(
            prompt=prompt,
            system=self.interrogation.system_prompt,
            model=self.interrogation.recommended_model,
            temperature=self.interrogation.recommended_temperature,
            format="json",
        )
        
        return response.get("response", "")
    
    def _parse_llm_output(self, llm_output: str) -> Dict[str, Any]:
        """Parse LLM output string into dictionary."""
        try:
            return json.loads(llm_output)
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', llm_output)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse LLM output as JSON: {e}")
    
    def _write_artifact(
        self,
        run_id: str,
        artifact_type: str,
        content: str,
        timestamp: datetime,
    ) -> Optional[ArtifactReference]:
        """Write an artifact to the lake."""
        try:
            result = self.lake_writer.write_text(run_id, artifact_type, content, timestamp)
            return ArtifactReference(
                artifact_type=artifact_type,
                lake_uri=result.lake_uri,
                content_sha256=result.content_sha256,
                byte_count=result.byte_count,
            )
        except Exception as e:
            logger.warning(f"Failed to write artifact {artifact_type}: {e}")
            return None
    
    def _persist_entities(
        self,
        entities: List[Dict[str, Any]],
        ctx: RunContext,
    ) -> List[Dict[str, Any]]:
        """
        Persist extracted entities to the database.
        
        Returns list of domain write records for tracking.
        """
        writes = []
        
        for entity in entities:
            try:
                write_record = self.entity_store.upsert_entity(
                    name=entity["name"],
                    entity_type=entity["type"],
                    confidence=entity.get("confidence", 1.0),
                    attributes=entity.get("attributes"),
                    run_id=ctx.run_id,
                    job_id=ctx.job_id,
                )
                writes.append(write_record)
            except Exception as e:
                logger.warning(f"Failed to persist entity {entity.get('name')}: {e}")
        
        return writes


def handle(job: Job, ctx: RunContext) -> HandlerResult:
    """
    Module-level handle function for dispatcher integration.
    
    This function creates a handler instance and delegates to it.
    In production, dependencies would be injected from configuration.
    """
    # Create handler with no dependencies (will use defaults or skip)
    # In production, these would be injected from dispatcher config
    handler = EntityExtractionDroidHandler()
    return handler.handle(job, ctx)
