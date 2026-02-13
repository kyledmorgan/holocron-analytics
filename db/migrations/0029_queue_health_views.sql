-- Migration: 0029_queue_health_views.sql
-- Phase 3: Queue Health Monitoring Views
--
-- Creates views for monitoring LLM job queue health:
-- - llm.vw_queue_health: Summary by status
-- - llm.vw_queue_health_by_type: Summary by job type
-- - llm.vw_queue_aged_jobs: Jobs exceeding age thresholds
-- - llm.vw_queue_summary_by_priority: Priority band distribution
--
-- Foundation for: Phase 4 UI; ops dashboards; Phase 7 automation

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

PRINT 'Creating queue health monitoring views...';

-- =============================================================================
-- View: llm.vw_queue_health
-- Summary of queue health by status
-- =============================================================================

IF OBJECT_ID('llm.vw_queue_health', 'V') IS NOT NULL
    DROP VIEW llm.vw_queue_health;
GO

CREATE VIEW llm.vw_queue_health AS
SELECT 
    status,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes,
    MIN(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS min_age_minutes,
    MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS max_age_minutes,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 60 THEN 1 ELSE 0 END) AS jobs_over_1h,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 240 THEN 1 ELSE 0 END) AS jobs_over_4h,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 1440 THEN 1 ELSE 0 END) AS jobs_over_24h
FROM llm.job
GROUP BY status;
GO

PRINT 'Created view: llm.vw_queue_health';

-- =============================================================================
-- View: llm.vw_queue_health_by_type
-- Summary of queue health by interrogation type (job type)
-- =============================================================================

IF OBJECT_ID('llm.vw_queue_health_by_type', 'V') IS NOT NULL
    DROP VIEW llm.vw_queue_health_by_type;
GO

CREATE VIEW llm.vw_queue_health_by_type AS
SELECT 
    interrogation_key,
    status,
    COUNT(*) AS job_count,
    AVG(priority) AS avg_priority,
    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes,
    MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS max_age_minutes,
    AVG(attempt_count) AS avg_attempts,
    SUM(CASE WHEN attempt_count >= max_attempts THEN 1 ELSE 0 END) AS exhausted_retries
FROM llm.job
GROUP BY interrogation_key, status;
GO

PRINT 'Created view: llm.vw_queue_health_by_type';

-- =============================================================================
-- View: llm.vw_queue_aged_jobs
-- Jobs exceeding age thresholds for monitoring/escalation
-- =============================================================================

IF OBJECT_ID('llm.vw_queue_aged_jobs', 'V') IS NOT NULL
    DROP VIEW llm.vw_queue_aged_jobs;
GO

CREATE VIEW llm.vw_queue_aged_jobs AS
SELECT 
    job_id,
    interrogation_key,
    status,
    priority,
    attempt_count,
    max_attempts,
    created_at,
    DATEDIFF(MINUTE, created_at, GETUTCDATE()) AS age_minutes,
    CASE 
        WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 1440 THEN 'critical'
        WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 240 THEN 'warning'
        WHEN DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 60 THEN 'elevated'
        ELSE 'normal'
    END AS age_severity,
    backoff_until,
    last_error
FROM llm.job
WHERE status IN ('NEW', 'RUNNING')
  AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 60;
GO

PRINT 'Created view: llm.vw_queue_aged_jobs';

-- =============================================================================
-- View: llm.vw_queue_summary_by_priority
-- Distribution of jobs across priority bands
-- =============================================================================

IF OBJECT_ID('llm.vw_queue_summary_by_priority', 'V') IS NOT NULL
    DROP VIEW llm.vw_queue_summary_by_priority;
GO

CREATE VIEW llm.vw_queue_summary_by_priority AS
SELECT 
    CASE 
        WHEN priority >= 200 THEN 'urgent (200+)'
        WHEN priority >= 100 THEN 'normal (100-199)'
        WHEN priority >= 50 THEN 'backfill (50-99)'
        ELSE 'low (<50)'
    END AS priority_band,
    status,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes
FROM llm.job
GROUP BY 
    CASE 
        WHEN priority >= 200 THEN 'urgent (200+)'
        WHEN priority >= 100 THEN 'normal (100-199)'
        WHEN priority >= 50 THEN 'backfill (50-99)'
        ELSE 'low (<50)'
    END,
    status;
GO

PRINT 'Created view: llm.vw_queue_summary_by_priority';

-- =============================================================================
-- Stored Procedure: llm.usp_escalate_aged_jobs
-- Auto-escalate jobs exceeding age thresholds
-- =============================================================================

IF OBJECT_ID('llm.usp_escalate_aged_jobs', 'P') IS NOT NULL
    DROP PROCEDURE llm.usp_escalate_aged_jobs;
GO

CREATE PROCEDURE llm.usp_escalate_aged_jobs
    @age_threshold_minutes INT = 60,
    @priority_boost INT = 50,
    @max_priority INT = 300,
    @max_jobs_per_run INT = 100
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @affected_count INT = 0;
    
    -- Escalate aged jobs that are still pending
    UPDATE TOP (@max_jobs_per_run) llm.job
    SET 
        priority = CASE 
            WHEN priority + @priority_boost > @max_priority THEN @max_priority
            ELSE priority + @priority_boost
        END,
        updated_at = GETUTCDATE()
    WHERE status = 'NEW'
      AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > @age_threshold_minutes
      AND priority < @max_priority;
    
    SET @affected_count = @@ROWCOUNT;
    
    -- Return summary
    SELECT 
        @affected_count AS jobs_escalated,
        @age_threshold_minutes AS age_threshold_minutes,
        @priority_boost AS priority_boost,
        @max_priority AS max_priority;
END;
GO

PRINT 'Created stored procedure: llm.usp_escalate_aged_jobs';

-- =============================================================================
-- Stored Procedure: llm.usp_get_queue_health_summary
-- Returns comprehensive queue health summary
-- =============================================================================

IF OBJECT_ID('llm.usp_get_queue_health_summary', 'P') IS NOT NULL
    DROP PROCEDURE llm.usp_get_queue_health_summary;
GO

CREATE PROCEDURE llm.usp_get_queue_health_summary
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Overall queue metrics
    SELECT 
        (SELECT COUNT(*) FROM llm.job WHERE status = 'NEW') AS pending_jobs,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'RUNNING') AS running_jobs,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'SUCCEEDED' AND created_at > DATEADD(HOUR, -24, GETUTCDATE())) AS succeeded_24h,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'FAILED' AND created_at > DATEADD(HOUR, -24, GETUTCDATE())) AS failed_24h,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'DEADLETTER') AS deadletter_total,
        (SELECT AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) FROM llm.job WHERE status = 'NEW') AS avg_pending_age_minutes,
        (SELECT MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) FROM llm.job WHERE status = 'NEW') AS max_pending_age_minutes,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'NEW' AND DATEDIFF(MINUTE, created_at, GETUTCDATE()) > 60) AS stale_job_count;
    
    -- Queue health by status
    SELECT * FROM llm.vw_queue_health;
    
    -- Aged jobs requiring attention
    SELECT TOP 20 * FROM llm.vw_queue_aged_jobs ORDER BY age_minutes DESC;
END;
GO

PRINT 'Created stored procedure: llm.usp_get_queue_health_summary';

PRINT 'Queue health monitoring views created successfully.';
GO
