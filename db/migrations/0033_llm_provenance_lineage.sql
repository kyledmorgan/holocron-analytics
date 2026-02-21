-- Migration 0033: LLM Provenance and Lineage Extensions
-- Idempotent: Only adds columns/constraints if they don't exist
--
-- Purpose: Extends LLM schema tables to support end-to-end lineage from
-- evidence sources through LLM runs to DVO merges. Treats Ollama as the
-- extraction source while preserving true evidence origins via bundles.
--
-- Tables Modified:
--   - llm.run: First-class artifact pointers, prompt metadata, run chaining
--   - llm.artifact: Content type metadata, expanded artifact type vocabulary
--   - llm.evidence_item: Source identifiers, selectors, roles, ordering
--   - llm.evidence_bundle: Deterministic fingerprint, bundle semantics
--   - llm.run_evidence: Bundle attachment purpose and attribution
--   - llm.job: Normalized evidence + prompt intent at enqueue time
--
-- Design Principle: Ollama is a source of extraction (extractor provenance),
-- while evidence bundles represent curated, multi-source inputs (evidence provenance).

-- ============================================================================
-- 1. llm.run — Add first-class artifact pointers + run chaining
-- ============================================================================

-- 1a. request_artifact_id: Exact request body sent to Ollama
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'request_artifact_id'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD request_artifact_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [request_artifact_id] added to [llm].[run].'
END
GO

-- 1b. response_artifact_id: Raw HTTP response from Ollama
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'response_artifact_id'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD response_artifact_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [response_artifact_id] added to [llm].[run].'
END
GO

-- 1c. output_artifact_id: Validated JSON output used for DVO merge
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'output_artifact_id'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD output_artifact_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [output_artifact_id] added to [llm].[run].'
END
GO

-- 1d. prompt_rendered_artifact_id: Final rendered prompt text
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'prompt_rendered_artifact_id'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD prompt_rendered_artifact_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [prompt_rendered_artifact_id] added to [llm].[run].'
END
GO

-- 1e. prompt_template_ref: Stable identifier of the prompt template
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'prompt_template_ref'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD prompt_template_ref NVARCHAR(200) NULL;
    PRINT 'Column [prompt_template_ref] added to [llm].[run].'
END
GO

-- 1f. prompt_template_version: Version of the prompt template
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'prompt_template_version'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD prompt_template_version NVARCHAR(50) NULL;
    PRINT 'Column [prompt_template_version] added to [llm].[run].'
END
GO

-- 1g. prompt_hash: Deterministic hash of the rendered prompt text
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'prompt_hash'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD prompt_hash NVARCHAR(64) NULL;
    PRINT 'Column [prompt_hash] added to [llm].[run].'
END
GO

-- 1h. parent_run_id: Links chained runs (classification → extraction → adjudication)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'parent_run_id'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD parent_run_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [parent_run_id] added to [llm].[run].'
END
GO

-- 1i. run_fingerprint: Deterministic hash for deduping identical reruns
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run]')
    AND name = 'run_fingerprint'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD run_fingerprint NVARCHAR(64) NULL;
    PRINT 'Column [run_fingerprint] added to [llm].[run].'
END
GO

-- 1j. Foreign keys for artifact pointers
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_run_request_artifact'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD CONSTRAINT FK_llm_run_request_artifact
        FOREIGN KEY (request_artifact_id)
        REFERENCES [llm].[artifact](artifact_id);
    PRINT 'FK [FK_llm_run_request_artifact] added.'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_run_response_artifact'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD CONSTRAINT FK_llm_run_response_artifact
        FOREIGN KEY (response_artifact_id)
        REFERENCES [llm].[artifact](artifact_id);
    PRINT 'FK [FK_llm_run_response_artifact] added.'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_run_output_artifact'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD CONSTRAINT FK_llm_run_output_artifact
        FOREIGN KEY (output_artifact_id)
        REFERENCES [llm].[artifact](artifact_id);
    PRINT 'FK [FK_llm_run_output_artifact] added.'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_run_prompt_rendered_artifact'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD CONSTRAINT FK_llm_run_prompt_rendered_artifact
        FOREIGN KEY (prompt_rendered_artifact_id)
        REFERENCES [llm].[artifact](artifact_id);
    PRINT 'FK [FK_llm_run_prompt_rendered_artifact] added.'
END
GO

-- 1k. Self-referencing FK for parent_run_id
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_run_parent_run'
)
BEGIN
    ALTER TABLE [llm].[run]
    ADD CONSTRAINT FK_llm_run_parent_run
        FOREIGN KEY (parent_run_id)
        REFERENCES [llm].[run](run_id);
    PRINT 'FK [FK_llm_run_parent_run] added.'
END
GO

-- 1l. Index on parent_run_id for chained run queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_run_parent_run'
    AND object_id = OBJECT_ID('[llm].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_parent_run
    ON [llm].[run] (parent_run_id)
    WHERE parent_run_id IS NOT NULL;
    PRINT 'Index [IX_llm_run_parent_run] created.'
END
GO

-- 1m. Index on run_fingerprint for dedupe lookups
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_run_fingerprint'
    AND object_id = OBJECT_ID('[llm].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_fingerprint
    ON [llm].[run] (run_fingerprint)
    WHERE run_fingerprint IS NOT NULL;
    PRINT 'Index [IX_llm_run_fingerprint] created.'
END
GO

-- ============================================================================
-- 2. llm.artifact — Content type metadata + expanded artifact types
-- ============================================================================

-- 2a. content_mime_type: Helps interpret artifact payloads
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'content_mime_type'
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD content_mime_type NVARCHAR(100) NULL;
    PRINT 'Column [content_mime_type] added to [llm].[artifact].'
END
GO

-- 2b. schema_version: Version of output contract if applicable
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'schema_version'
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD schema_version NVARCHAR(50) NULL;
    PRINT 'Column [schema_version] added to [llm].[artifact].'
END
GO

-- 2c. Drop old CHECK constraint and add expanded one
IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_llm_artifact_type'
    AND parent_object_id = OBJECT_ID('[llm].[artifact]')
)
BEGIN
    ALTER TABLE [llm].[artifact]
    DROP CONSTRAINT CK_llm_artifact_type;
    PRINT 'Old CHECK constraint [CK_llm_artifact_type] dropped.'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_llm_artifact_type'
    AND parent_object_id = OBJECT_ID('[llm].[artifact]')
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD CONSTRAINT CK_llm_artifact_type CHECK (
        artifact_type IN (
            -- Original types
            'request_json',
            'response_json',
            'evidence_bundle',
            'prompt_text',
            'parsed_output',
            'raw_response',
            -- Expanded types for provenance/lineage
            'prompt_template',
            'prompt_rendered',
            'llm_request',
            'llm_response_raw',
            'llm_output_json',
            'llm_output_validation_report',
            'merge_payload',
            'merge_result_report'
        )
    );
    PRINT 'Expanded CHECK constraint [CK_llm_artifact_type] added.'
END
GO

-- ============================================================================
-- 3. llm.evidence_item — Source identifiers, selectors, roles, ordering
-- ============================================================================

-- 3a. source_system: Normalized origin (wikipedia, youtube, pdf, sql, etc.)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'source_system'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD source_system NVARCHAR(100) NULL;
    PRINT 'Column [source_system] added to [llm].[evidence_item].'
END
GO

-- 3b. source_uri: Canonical URL for external sources
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'source_uri'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD source_uri NVARCHAR(2000) NULL;
    PRINT 'Column [source_uri] added to [llm].[evidence_item].'
END
GO

-- 3c. source_ref: Source-native identifier (page_id, revision_id, etc.)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'source_ref'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD source_ref NVARCHAR(400) NULL;
    PRINT 'Column [source_ref] added to [llm].[evidence_item].'
END
GO

-- 3d. selector_json: Structured selection details (offsets, page ranges, etc.)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'selector_json'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD selector_json NVARCHAR(MAX) NULL;
    PRINT 'Column [selector_json] added to [llm].[evidence_item].'
END
GO

-- 3e. ordinal: Ordering within the bundle for deterministic assembly
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'ordinal'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD ordinal INT NULL;
    PRINT 'Column [ordinal] added to [llm].[evidence_item].'
END
GO

-- 3f. role: How the evidence is used (primary, supporting, counter, context)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'role'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD role NVARCHAR(50) NULL;
    PRINT 'Column [role] added to [llm].[evidence_item].'
END
GO

-- 3g. excerpt_hash: Hash of the excerpt used (if different from full content)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'excerpt_hash'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD excerpt_hash NVARCHAR(64) NULL;
    PRINT 'Column [excerpt_hash] added to [llm].[evidence_item].'
END
GO

-- 3h. created_utc: Audit timestamp for evidence item creation
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'created_utc'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD created_utc DATETIME2(3) NOT NULL
        CONSTRAINT DF_llm_evidence_item_created_utc DEFAULT SYSUTCDATETIME();
    PRINT 'Column [created_utc] added to [llm].[evidence_item].'
END
GO

-- 3i. Index on source_system for provenance queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_evidence_item_source_system'
    AND object_id = OBJECT_ID('[llm].[evidence_item]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_item_source_system
    ON [llm].[evidence_item] (source_system)
    WHERE source_system IS NOT NULL;
    PRINT 'Index [IX_llm_evidence_item_source_system] created.'
END
GO

-- 3j. Index on ordinal within bundle for deterministic assembly
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_evidence_item_bundle_ordinal'
    AND object_id = OBJECT_ID('[llm].[evidence_item]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_item_bundle_ordinal
    ON [llm].[evidence_item] (bundle_id, ordinal);
    PRINT 'Index [IX_llm_evidence_item_bundle_ordinal] created.'
END
GO

-- ============================================================================
-- 4. llm.evidence_bundle — Deterministic fingerprint + bundle semantics
-- ============================================================================

-- 4a. bundle_sha256: Deterministic hash of bundle composition
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'bundle_sha256'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD bundle_sha256 NVARCHAR(64) NULL;
    PRINT 'Column [bundle_sha256] added to [llm].[evidence_bundle].'
END
GO

-- 4b. bundle_kind: Categorizes bundles (llm_input, human_review_packet, etc.)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'bundle_kind'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD bundle_kind NVARCHAR(50) NULL;
    PRINT 'Column [bundle_kind] added to [llm].[evidence_bundle].'
END
GO

-- 4c. created_by: Worker/user identifier that assembled the bundle
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'created_by'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD created_by NVARCHAR(200) NULL;
    PRINT 'Column [created_by] added to [llm].[evidence_bundle].'
END
GO

-- 4d. notes: Optional human commentary about the bundle
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'notes'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD notes NVARCHAR(2000) NULL;
    PRINT 'Column [notes] added to [llm].[evidence_bundle].'
END
GO

-- 4e. assembly_artifact_id: Pointer to assembled input text artifact
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'assembly_artifact_id'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD assembly_artifact_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [assembly_artifact_id] added to [llm].[evidence_bundle].'
END
GO

-- 4f. Index on bundle_sha256 for dedupe/reuse lookups
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_evidence_bundle_sha256'
    AND object_id = OBJECT_ID('[llm].[evidence_bundle]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_bundle_sha256
    ON [llm].[evidence_bundle] (bundle_sha256)
    WHERE bundle_sha256 IS NOT NULL;
    PRINT 'Index [IX_llm_evidence_bundle_sha256] created.'
END
GO

-- 4g. Index on bundle_kind for category-based queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_evidence_bundle_kind'
    AND object_id = OBJECT_ID('[llm].[evidence_bundle]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_bundle_kind
    ON [llm].[evidence_bundle] (bundle_kind)
    WHERE bundle_kind IS NOT NULL;
    PRINT 'Index [IX_llm_evidence_bundle_kind] created.'
END
GO

-- ============================================================================
-- 5. llm.run_evidence — Bundle attachment purpose and attribution
-- ============================================================================

-- 5a. role: Why the bundle is attached (input, output_support, human_override, comparison)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run_evidence]')
    AND name = 'role'
)
BEGIN
    ALTER TABLE [llm].[run_evidence]
    ADD role NVARCHAR(50) NULL;
    PRINT 'Column [role] added to [llm].[run_evidence].'
END
GO

-- 5b. attached_by: Worker/user identifier that attached the bundle
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run_evidence]')
    AND name = 'attached_by'
)
BEGIN
    ALTER TABLE [llm].[run_evidence]
    ADD attached_by NVARCHAR(200) NULL;
    PRINT 'Column [attached_by] added to [llm].[run_evidence].'
END
GO

-- 5c. attached_reason: Optional short text explaining the linkage
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[run_evidence]')
    AND name = 'attached_reason'
)
BEGIN
    ALTER TABLE [llm].[run_evidence]
    ADD attached_reason NVARCHAR(500) NULL;
    PRINT 'Column [attached_reason] added to [llm].[run_evidence].'
END
GO

-- ============================================================================
-- 6. llm.job — Normalize evidence + prompt intent at enqueue time
-- ============================================================================

-- 6a. input_bundle_id: Primary evidence bundle intended as input context
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'input_bundle_id'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD input_bundle_id UNIQUEIDENTIFIER NULL;
    PRINT 'Column [input_bundle_id] added to [llm].[job].'
END
GO

-- 6b. prompt_template_ref: Intended prompt contract for the job
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'prompt_template_ref'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD prompt_template_ref NVARCHAR(200) NULL;
    PRINT 'Column [prompt_template_ref] added to [llm].[job].'
END
GO

-- 6c. prompt_template_version: Version of the intended prompt contract
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'prompt_template_version'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD prompt_template_version NVARCHAR(50) NULL;
    PRINT 'Column [prompt_template_version] added to [llm].[job].'
END
GO

-- 6d. contract_version: Version of JSON schema expected from the LLM
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'contract_version'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD contract_version NVARCHAR(50) NULL;
    PRINT 'Column [contract_version] added to [llm].[job].'
END
GO

-- 6e. requested_output_types: Which DVO object families are expected
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'requested_output_types'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD requested_output_types NVARCHAR(500) NULL;
    PRINT 'Column [requested_output_types] added to [llm].[job].'
END
GO

-- 6f. job_fingerprint: Deterministic hash for dedupe standardization
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[job]')
    AND name = 'job_fingerprint'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD job_fingerprint NVARCHAR(64) NULL;
    PRINT 'Column [job_fingerprint] added to [llm].[job].'
END
GO

-- 6g. FK for input_bundle_id
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_llm_job_input_bundle'
)
BEGIN
    ALTER TABLE [llm].[job]
    ADD CONSTRAINT FK_llm_job_input_bundle
        FOREIGN KEY (input_bundle_id)
        REFERENCES [llm].[evidence_bundle](bundle_id);
    PRINT 'FK [FK_llm_job_input_bundle] added.'
END
GO

-- 6h. Index on job_fingerprint for dedupe lookups
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_job_fingerprint'
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_fingerprint
    ON [llm].[job] (job_fingerprint)
    WHERE job_fingerprint IS NOT NULL;
    PRINT 'Index [IX_llm_job_fingerprint] created.'
END
GO

-- 6i. Index on input_bundle_id for bundle-based job queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_job_input_bundle'
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_input_bundle
    ON [llm].[job] (input_bundle_id)
    WHERE input_bundle_id IS NOT NULL;
    PRINT 'Index [IX_llm_job_input_bundle] created.'
END
GO

PRINT '=== Migration 0033 complete: LLM provenance and lineage extensions applied. ==='
GO
