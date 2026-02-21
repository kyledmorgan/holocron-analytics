"""
Relationship Extraction Handler.

Handles relationship_extraction jobs:
1. Reads source content from job input
2. Assembles LLM input context
3. Calls the model (or model abstraction)
4. Parses output and validates against contract
5. Writes artifacts to lake
6. Persists relationships via stored procedure (unless dry-run)
7. Updates job/run status

Phase 2: Focused on entity-entity relationships with temporal bounds.
Foundation for: Phase 3 multi-output families, Phase 4 governance queue.
"""

import hashlib
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
from ..interrogations.definitions.relationship_extraction import validate_relationship_extraction_output


logger = logging.getLogger(__name__)


class RelationshipExtractionHandler:
    """
    Handler for relationship extraction jobs.
    
    This handler:
    - Extracts relationships from source text using LLM
    - Validates output against relationship extraction contract
    - Writes artifacts for debugging and audit
    - Persists relationships to BridgeEntityRelation (in live mode)
    
    Example:
        >>> handler = RelationshipExtractionHandler(
        ...     ollama_client=client,
        ...     lake_writer=writer,
        ...     relationship_store=store,
        ... )
        >>> result = handler.handle(job, ctx)
    """
    
    def __init__(
        self,
        ollama_client=None,
        lake_writer=None,
        relationship_store=None,
        queue=None,
    ):
        """
        Initialize the handler.
        
        Args:
            ollama_client: Client for LLM calls (optional, for testing)
            lake_writer: Lake writer for artifacts (optional, for testing)
            relationship_store: Store for relationship persistence (optional, for testing)
            queue: SQL job queue for SQL-first artifact storage (optional)
        """
        self.ollama_client = ollama_client
        self.lake_writer = lake_writer
        self.relationship_store = relationship_store
        self.queue = queue
        self._interrogation = None
    
    @property
    def interrogation(self):
        """Lazy load interrogation definition."""
        if self._interrogation is None:
            self._interrogation = get_interrogation("relationship_extraction_v1")
        return self._interrogation
    
    def handle(self, job: Job, ctx: RunContext) -> HandlerResult:
        """
        Handle a relationship extraction job.
        
        Args:
            job: The job to process
            ctx: Run context with execution metadata
            
        Returns:
            HandlerResult with status, artifacts, and output
        """
        timestamp = datetime.now(timezone.utc)
        artifacts: List[ArtifactReference] = []
        metrics: Dict[str, Any] = {
            "handler": "relationship_extraction",
            "execution_mode": ctx.execution_mode.value,
            "schema_key": self.interrogation.key,
            "schema_version": self.interrogation.version,
        }
        
        log_ctx = ctx.get_log_context()
        logger.info(f"Starting relationship extraction for job {job.job_id}", extra=log_ctx)
        
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
            if self.lake_writer or self.queue:
                prompt_artifact = self._write_artifact(
                    ctx.run_id, "prompt", prompt, timestamp
                )
                if prompt_artifact:
                    artifacts.append(prompt_artifact)
            
            # 4. Write input artifact for debugging
            if self.lake_writer or self.queue:
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
                    "relationships": [],
                    "entities_referenced": [],
                    "extraction_metadata": {
                        "source_page_title": source_title,
                        "total_relationships_found": 0,
                        "relationship_types_found": [],
                        "extraction_notes": "DRY-RUN: LLM call skipped"
                    }
                }
                
                if self.lake_writer or self.queue:
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
            validation_errors = validate_relationship_extraction_output(parsed_output)
            
            if validation_errors:
                logger.warning(
                    f"Validation errors for job {job.job_id}: {validation_errors}",
                    extra=log_ctx,
                )
                
                # Write invalid output for debugging
                if self.lake_writer or self.queue:
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
            if self.lake_writer or self.queue:
                output_artifact = self._write_artifact(
                    ctx.run_id, "output", json.dumps(parsed_output, indent=2), timestamp
                )
                if output_artifact:
                    artifacts.append(output_artifact)
            
            # 9. Persist relationships to database (live mode only)
            domain_writes = []
            if self.relationship_store and parsed_output.get("relationships"):
                try:
                    writes = self._persist_relationships(parsed_output["relationships"], ctx)
                    domain_writes.extend(writes)
                    metrics["relationships_persisted"] = len(writes)
                except Exception as e:
                    logger.error(f"Relationship persistence failed: {e}", extra=log_ctx)
                    # Don't fail the job for persistence errors
                    # but record the error
                    metrics["persistence_error"] = str(e)
            
            # 10. Return success
            metrics["relationships_extracted"] = len(parsed_output.get("relationships", []))
            metrics["entities_referenced"] = len(parsed_output.get("entities_referenced", []))
            
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
        Call the LLM with the rendered prompt using structured output.
        
        Uses chat_with_structured_output to enforce schema at the API
        level via the Ollama ``format`` parameter.  The complete request
        and response payloads are persisted as SQL-first artifacts when
        a queue is configured.
        
        Returns the raw LLM output string.
        """
        if not self.ollama_client:
            raise RuntimeError("Ollama client not configured")
        
        timestamp = datetime.now(timezone.utc)
        
        # Build chat messages
        messages = []
        if self.interrogation.system_prompt:
            messages.append({"role": "system", "content": self.interrogation.system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Get schema for Ollama structured output enforcement
        output_schema = self.interrogation.get_schema_for_ollama()
        
        # Build the full request payload for artifact capture
        request_payload = self.ollama_client.get_full_request_payload(
            messages=messages,
            output_schema=output_schema,
        )
        
        # Persist request artifact (SQL-first, lake additive)
        request_content = json.dumps(request_payload, indent=2, ensure_ascii=False, default=str)
        self._persist_artifact(
            ctx.run_id, "request_json", request_content,
            "application/json", timestamp,
        )
        
        # Call Ollama with schema-enforced structured output
        response = self.ollama_client.chat_with_structured_output(
            messages=messages,
            output_schema=output_schema,
        )
        
        # Persist response artifact (SQL-first, lake additive)
        response_content = json.dumps(
            response.raw_response or {}, indent=2,
            ensure_ascii=False, default=str,
        )
        self._persist_artifact(
            ctx.run_id, "response_json", response_content,
            "application/json", timestamp,
        )
        
        return response.content or ""
    
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
        """Write an artifact to the lake and optionally to SQL."""
        lake_uri = None
        content_bytes = content.encode("utf-8")
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        byte_count = len(content_bytes)
        
        # Write to lake if available
        if self.lake_writer:
            try:
                result = self.lake_writer.write_text(
                    run_id, artifact_type, content, timestamp=timestamp
                )
                lake_uri = result.lake_uri
                content_sha256 = result.content_sha256
                byte_count = result.byte_count
            except Exception as e:
                logger.warning(f"Failed to write artifact {artifact_type} to lake: {e}")
        
        # Write to SQL if queue is available (SQL-first)
        if self.queue:
            try:
                mime_type = "application/json" if artifact_type.endswith("_json") else "text/plain"
                self.queue.create_artifact(
                    run_id=run_id,
                    artifact_type=artifact_type,
                    lake_uri=lake_uri,
                    content_sha256=content_sha256,
                    byte_count=byte_count,
                    content=content,
                    content_mime_type=mime_type,
                    stored_in_sql=True,
                    mirrored_to_lake=lake_uri is not None,
                )
            except Exception as e:
                logger.warning(f"Failed to write artifact {artifact_type} to SQL: {e}")
        
        return ArtifactReference(
            artifact_type=artifact_type,
            lake_uri=lake_uri or "",
            content_sha256=content_sha256,
            byte_count=byte_count,
        )
    
    def _persist_artifact(
        self,
        run_id: str,
        artifact_type: str,
        content: str,
        content_mime_type: str,
        timestamp: datetime,
    ) -> Optional[ArtifactReference]:
        """
        Persist an artifact using SQL-first storage with optional lake mirroring.
        
        SQL is the system of record.  When a lake_writer is configured the
        content is also mirrored to the data lake for portability.
        """
        content_bytes = content.encode("utf-8")
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        byte_count = len(content_bytes)
        lake_uri = None
        
        # Mirror to lake if available
        if self.lake_writer:
            try:
                if content_mime_type == "application/json":
                    result = self.lake_writer.write_json(
                        run_id, artifact_type, json.loads(content), timestamp=timestamp
                    )
                else:
                    result = self.lake_writer.write_text(
                        run_id, artifact_type, content, timestamp=timestamp
                    )
                lake_uri = result.lake_uri
            except Exception as e:
                logger.warning(f"Failed to mirror artifact {artifact_type} to lake: {e}")
        
        # Store in SQL (system of record)
        if self.queue:
            try:
                self.queue.create_artifact(
                    run_id=run_id,
                    artifact_type=artifact_type,
                    lake_uri=lake_uri,
                    content_sha256=content_sha256,
                    byte_count=byte_count,
                    content=content,
                    content_mime_type=content_mime_type,
                    stored_in_sql=True,
                    mirrored_to_lake=lake_uri is not None,
                )
            except Exception as e:
                logger.warning(f"Failed to persist artifact {artifact_type} to SQL: {e}")
        
        return ArtifactReference(
            artifact_type=artifact_type,
            lake_uri=lake_uri or "",
            content_sha256=content_sha256,
            byte_count=byte_count,
        )
    
    def _persist_relationships(
        self,
        relationships: List[Dict[str, Any]],
        ctx: RunContext,
    ) -> List[Dict[str, Any]]:
        """
        Persist extracted relationships to the database.
        
        Returns list of domain write records for tracking.
        """
        writes = []
        
        for rel in relationships:
            try:
                write_record = self.relationship_store.upsert_relationship(
                    from_entity=rel["from_entity"],
                    to_entity=rel["to_entity"],
                    relation_type=rel["relation_type"],
                    confidence=rel.get("confidence", 1.0),
                    start_date=rel.get("start_date"),
                    end_date=rel.get("end_date"),
                    work_context=rel.get("work_context"),
                    run_id=ctx.run_id,
                    job_id=ctx.job_id,
                )
                writes.append(write_record)
            except Exception as e:
                logger.warning(
                    f"Failed to persist relationship {rel.get('from_entity')} -> {rel.get('to_entity')}: {e}"
                )
        
        return writes


def handle(job: Job, ctx: RunContext) -> HandlerResult:
    """
    Module-level handle function for dispatcher integration.
    
    This function creates a handler instance and delegates to it.
    In production, dependencies would be injected from configuration.
    """
    # Create handler with no dependencies (will use defaults or skip)
    # In production, these would be injected from dispatcher config
    handler = RelationshipExtractionHandler()
    return handler.handle(job, ctx)
