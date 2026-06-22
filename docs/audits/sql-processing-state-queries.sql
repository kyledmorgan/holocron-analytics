/*
Read-only SQL Processing State Diagnostics
Target database: Holocron
This script uses SELECT statements only.
*/
SET NOCOUNT ON;

PRINT '01_database_identity';
SELECT @@SERVERNAME AS server_name, @@VERSION AS server_version, DB_NAME() AS current_database,
       d.name AS database_name, d.compatibility_level, d.create_date, d.collation_name
FROM sys.databases d
WHERE d.name = DB_NAME();

PRINT '02_schemas';
SELECT name AS schema_name, schema_id
FROM sys.schemas
WHERE name IN ('dbo','ingest','llm','sem','vector','lake')
ORDER BY name;

PRINT '03_tables_row_estimates';
SELECT s.name AS schema_name, t.name AS table_name, SUM(p.rows) AS approx_rows,
       CAST(SUM(a.total_pages) * 8.0 / 1024 AS DECIMAL(18,2)) AS allocated_mb,
       CAST(SUM(a.used_pages) * 8.0 / 1024 AS DECIMAL(18,2)) AS used_mb
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.indexes i ON i.object_id = t.object_id AND i.index_id IN (0,1)
JOIN sys.partitions p ON p.object_id = i.object_id AND p.index_id = i.index_id
JOIN sys.allocation_units a ON a.container_id = p.partition_id
WHERE s.name IN ('dbo','ingest','llm','sem','vector','lake')
GROUP BY s.name, t.name
ORDER BY approx_rows DESC, s.name, t.name;

PRINT '04_core_object_presence';
SELECT v.schema_name, v.object_name, o.type_desc
FROM (VALUES
 ('ingest','work_items'),('ingest','IngestRecords'),('ingest','ingest_runs'),('ingest','worker_heartbeats'),
 ('sem','SourcePage'),('sem','PageSignals'),('sem','PageClassification'),
 ('dbo','DimEntity'),('dbo','DimTag'),('dbo','BridgeTagAssignment'),('dbo','BridgeEntityRelation'),('dbo','BridgeEntityEvent'),('dbo','BridgeEntityWork'),
 ('llm','job'),('llm','run'),('llm','artifact'),('llm','evidence_bundle'),('llm','run_evidence'),('llm','evidence_item')
) v(schema_name, object_name)
LEFT JOIN sys.objects o ON o.object_id = OBJECT_ID(QUOTENAME(v.schema_name) + '.' + QUOTENAME(v.object_name))
ORDER BY v.schema_name, v.object_name;

PRINT '05_indexes_processing_objects';
SELECT s.name AS schema_name, t.name AS table_name, i.name AS index_name, i.is_unique, i.type_desc, i.filter_definition,
       STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS key_columns
FROM sys.indexes i
JOIN sys.tables t ON t.object_id = i.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
LEFT JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
LEFT JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE s.name IN ('ingest','llm','sem','dbo')
  AND t.name IN ('work_items','IngestRecords','ingest_runs','SourcePage','PageClassification','DimEntity','BridgeEntityRelation','job','run','artifact','evidence_bundle','evidence_item')
  AND i.name IS NOT NULL
GROUP BY s.name, t.name, i.name, i.is_unique, i.type_desc, i.filter_definition
ORDER BY s.name, t.name, i.is_unique DESC, i.name;

PRINT '06_foreign_keys_processing_objects';
SELECT sch_parent.name AS parent_schema, tab_parent.name AS parent_table, fk.name AS foreign_key_name,
       sch_ref.name AS referenced_schema, tab_ref.name AS referenced_table, fk.is_disabled, fk.is_not_trusted
FROM sys.foreign_keys fk
JOIN sys.tables tab_parent ON tab_parent.object_id = fk.parent_object_id
JOIN sys.schemas sch_parent ON sch_parent.schema_id = tab_parent.schema_id
JOIN sys.tables tab_ref ON tab_ref.object_id = fk.referenced_object_id
JOIN sys.schemas sch_ref ON sch_ref.schema_id = tab_ref.schema_id
WHERE sch_parent.name IN ('ingest','llm','sem','dbo')
ORDER BY sch_parent.name, tab_parent.name, fk.name;

PRINT '07_ingest_status_counts';
IF OBJECT_ID('ingest.work_items','U') IS NOT NULL
SELECT status, COUNT(*) AS cnt, MIN(created_at) AS earliest_created_at, MAX(updated_at) AS latest_updated_at
FROM ingest.work_items
GROUP BY status
ORDER BY cnt DESC;

PRINT '08_ingest_stuck_or_expired';
IF OBJECT_ID('ingest.work_items','U') IS NOT NULL AND COL_LENGTH('ingest.work_items','lease_expires_at') IS NOT NULL
SELECT COUNT(*) AS in_progress_total,
       SUM(CASE WHEN lease_expires_at < SYSUTCDATETIME() THEN 1 ELSE 0 END) AS expired_lease_count,
       MIN(lease_expires_at) AS earliest_lease_expires_at,
       MAX(updated_at) AS latest_updated_at
FROM ingest.work_items
WHERE status = 'in_progress';

PRINT '09_ingest_records_counts';
IF OBJECT_ID('ingest.IngestRecords','U') IS NOT NULL
SELECT COUNT(*) AS ingest_records_total,
       SUM(CASE WHEN work_item_id IS NULL THEN 1 ELSE 0 END) AS without_work_item_id,
       COUNT(DISTINCT resource_id) AS distinct_resource_id,
       MIN(fetched_at_utc) AS earliest_fetched_at_utc,
       MAX(fetched_at_utc) AS latest_fetched_at_utc
FROM ingest.IngestRecords;

PRINT '10_dim_entity_completion';
IF OBJECT_ID('dbo.DimEntity','U') IS NOT NULL
SELECT COUNT(*) AS total_active_latest,
       SUM(CASE WHEN EntityType IS NULL THEN 1 ELSE 0 END) AS missing_entity_type,
       SUM(CASE WHEN EntityType IS NOT NULL THEN 1 ELSE 0 END) AS has_entity_type,
       SUM(CASE WHEN DisplayNameNormalized IS NULL THEN 1 ELSE 0 END) AS missing_display_name_normalized,
       SUM(CASE WHEN SortName IS NULL THEN 1 ELSE 0 END) AS missing_sort_name,
       SUM(CASE WHEN AliasCsv IS NULL THEN 1 ELSE 0 END) AS missing_aliascsv,
       SUM(CASE WHEN SourcePageId IS NULL THEN 1 ELSE 0 END) AS missing_source_page_id,
       SUM(CASE WHEN ExternalKey IS NULL THEN 1 ELSE 0 END) AS missing_external_key
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1;

PRINT '11_dim_entity_by_type';
IF OBJECT_ID('dbo.DimEntity','U') IS NOT NULL
SELECT TOP (100) EntityType, COUNT(*) AS cnt,
       SUM(CASE WHEN AliasCsv IS NULL THEN 1 ELSE 0 END) AS missing_aliascsv
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1
GROUP BY EntityType
ORDER BY cnt DESC;

PRINT '12_classify_default_resume_candidates';
IF OBJECT_ID('dbo.DimEntity','U') IS NOT NULL
SELECT COUNT(*) AS classify_default_resume_candidates
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1 AND EntityType IS NULL;

PRINT '13_classify_strict_resume_candidates';
IF OBJECT_ID('dbo.DimEntity','U') IS NOT NULL
SELECT COUNT(*) AS classify_strict_missing_any_candidates
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1
  AND (EntityType IS NULL OR DisplayNameNormalized IS NULL OR SortName IS NULL OR AliasCsv IS NULL);

PRINT '14_llm_job_status_by_interrogation';
IF OBJECT_ID('llm.job','U') IS NOT NULL
SELECT interrogation_key, status, COUNT(*) AS cnt, MIN(created_utc) AS earliest_created_utc,
       MAX(created_utc) AS latest_created_utc, MIN(available_utc) AS earliest_available_utc,
       MAX(available_utc) AS latest_available_utc
FROM llm.job
GROUP BY interrogation_key, status
ORDER BY interrogation_key, status;

PRINT '15_llm_failed_jobs_latest_errors';
IF OBJECT_ID('llm.job','U') IS NOT NULL
SELECT TOP (50) job_id, interrogation_key, status, attempt_count, max_attempts,
       LEFT(last_error, 500) AS last_error_prefix, created_utc, updated_utc, locked_by, available_utc
FROM llm.job
WHERE status IN ('FAILED','DEADLETTER','RUNNING')
ORDER BY updated_utc DESC;

PRINT '16_llm_run_status_model';
IF OBJECT_ID('llm.run','U') IS NOT NULL
SELECT status, model_name, model_tag, model_digest, COUNT(*) AS cnt,
       MIN(started_utc) AS earliest_started_utc, MAX(completed_utc) AS latest_completed_utc
FROM llm.run
GROUP BY status, model_name, model_tag, model_digest
ORDER BY cnt DESC;

PRINT '17_llm_recent_runs';
IF OBJECT_ID('llm.run','U') IS NOT NULL
SELECT TOP (100) run_id, job_id, status, model_name, model_tag, model_digest, started_utc, completed_utc,
       LEFT(error, 500) AS error_prefix
FROM llm.run
ORDER BY started_utc DESC;

PRINT '18_llm_artifact_counts';
IF OBJECT_ID('llm.artifact','U') IS NOT NULL
SELECT artifact_type, COUNT(*) AS cnt, COUNT(DISTINCT content_sha256) AS distinct_content_sha256,
       MIN(created_utc) AS earliest_created_utc, MAX(created_utc) AS latest_created_utc
FROM llm.artifact
GROUP BY artifact_type
ORDER BY cnt DESC;

PRINT '19_duplicate_llm_jobs_by_dedupe';
IF OBJECT_ID('llm.job','U') IS NOT NULL
SELECT interrogation_key, dedupe_key, COUNT(*) AS duplicate_rows,
       MIN(created_utc) AS first_created_utc, MAX(created_utc) AS last_created_utc
FROM llm.job
WHERE dedupe_key IS NOT NULL
GROUP BY interrogation_key, dedupe_key
HAVING COUNT(*) > 1
ORDER BY duplicate_rows DESC, last_created_utc DESC;

PRINT '20_duplicate_llm_artifacts_by_run_type_hash';
IF OBJECT_ID('llm.artifact','U') IS NOT NULL
SELECT run_id, artifact_type, content_sha256, COUNT(*) AS duplicate_rows
FROM llm.artifact
WHERE content_sha256 IS NOT NULL
GROUP BY run_id, artifact_type, content_sha256
HAVING COUNT(*) > 1
ORDER BY duplicate_rows DESC;

PRINT '21_duplicate_dim_entities_current';
IF OBJECT_ID('dbo.DimEntity','U') IS NOT NULL
SELECT TOP (100) DisplayNameNormalized, EntityType, COUNT(*) AS duplicate_current_rows
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1
GROUP BY DisplayNameNormalized, EntityType
HAVING COUNT(*) > 1
ORDER BY duplicate_current_rows DESC;

PRINT '22_duplicate_bridge_entity_relation';
IF OBJECT_ID('dbo.BridgeEntityRelation','U') IS NOT NULL
SELECT TOP (100) FromEntityId, ToEntityId, RelationType, StartDateText, EndDateText, SourcePageId,
       COUNT(*) AS duplicate_rows
FROM dbo.BridgeEntityRelation
GROUP BY FromEntityId, ToEntityId, RelationType, StartDateText, EndDateText, SourcePageId
HAVING COUNT(*) > 1
ORDER BY duplicate_rows DESC;

PRINT '23_sem_page_classification_coverage';
IF OBJECT_ID('sem.SourcePage','U') IS NOT NULL
SELECT COUNT(*) AS source_pages_total,
       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS source_pages_active
FROM sem.SourcePage;

IF OBJECT_ID('sem.PageClassification','U') IS NOT NULL
SELECT primary_type, method, taxonomy_version, COUNT(*) AS cnt,
       SUM(CASE WHEN is_current = 1 THEN 1 ELSE 0 END) AS current_cnt,
       SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) AS needs_review_cnt,
       MIN(created_utc) AS earliest_created_utc, MAX(created_utc) AS latest_created_utc
FROM sem.PageClassification
GROUP BY primary_type, method, taxonomy_version
ORDER BY cnt DESC;

PRINT '24_backfill_relationship_candidate_count_equivalent';
IF OBJECT_ID('sem.SourcePage','U') IS NOT NULL AND OBJECT_ID('sem.PageClassification','U') IS NOT NULL
SELECT COUNT(*) AS relationship_backfill_candidate_count_current_code_predicate
FROM sem.SourcePage sp
LEFT JOIN sem.PageClassification pc ON sp.source_page_id = pc.source_page_id AND pc.is_current = 1
WHERE sp.source_system = 'wookieepedia'
  AND sp.is_active = 1
  AND pc.primary_type NOT IN ('TechnicalSitePage', 'ReferenceMeta', 'Unknown');

PRINT '25_queue_health_views_if_present';
IF OBJECT_ID('llm.vw_queue_health','V') IS NOT NULL SELECT * FROM llm.vw_queue_health;
IF OBJECT_ID('llm.vw_queue_health_by_type','V') IS NOT NULL SELECT * FROM llm.vw_queue_health_by_type;
IF OBJECT_ID('llm.vw_queue_aged_jobs','V') IS NOT NULL SELECT TOP (100) * FROM llm.vw_queue_aged_jobs ORDER BY created_utc ASC;
