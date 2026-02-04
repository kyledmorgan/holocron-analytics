-- Migration 0005: Create LLM tables for Phase 1
-- Idempotent: Only creates tables if they don't exist

-- ============================================================================
-- llm.job table: Queue of pending/active LLM derive jobs
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'job' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[job] (
        job_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        status VARCHAR(20) NOT NULL DEFAULT 'NEW',
        priority INT NOT NULL DEFAULT 100,
        interrogation_key NVARCHAR(200) NOT NULL,
        input_json NVARCHAR(MAX) NOT NULL,
        evidence_ref_json NVARCHAR(MAX) NULL,
        model_hint NVARCHAR(100) NULL,
        max_attempts INT NOT NULL DEFAULT 3,
        attempt_count INT NOT NULL DEFAULT 0,
        available_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        locked_by NVARCHAR(200) NULL,
        locked_utc DATETIME2 NULL,
        last_error NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_llm_job PRIMARY KEY CLUSTERED (job_id),
        CONSTRAINT CK_llm_job_status CHECK (status IN ('NEW', 'RUNNING', 'SUCCEEDED', 'FAILED', 'DEADLETTER')),
        CONSTRAINT CK_llm_job_attempt CHECK (attempt_count >= 0),
        CONSTRAINT CK_llm_job_max_attempts CHECK (max_attempts >= 1),
        CONSTRAINT CK_llm_job_priority CHECK (priority >= 0)
    );
    PRINT 'Table [llm].[job] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[job] already exists.'
END
GO

-- ============================================================================
-- llm.run table: Tracks individual LLM run attempts
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'run' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[run] (
        run_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        job_id UNIQUEIDENTIFIER NOT NULL,
        started_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        completed_utc DATETIME2 NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
        worker_id NVARCHAR(200) NOT NULL,
        ollama_base_url NVARCHAR(500) NOT NULL,
        model_name NVARCHAR(100) NOT NULL,
        model_tag NVARCHAR(100) NULL,
        model_digest NVARCHAR(200) NULL,
        options_json NVARCHAR(MAX) NULL,
        metrics_json NVARCHAR(MAX) NULL,
        error NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_llm_run PRIMARY KEY CLUSTERED (run_id),
        CONSTRAINT FK_llm_run_job FOREIGN KEY (job_id) REFERENCES [llm].[job](job_id),
        CONSTRAINT CK_llm_run_status CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED'))
    );
    PRINT 'Table [llm].[run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[run] already exists.'
END
GO

-- ============================================================================
-- llm.artifact table: Tracks artifacts written to the lake
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'artifact' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[artifact] (
        artifact_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        run_id UNIQUEIDENTIFIER NOT NULL,
        artifact_type NVARCHAR(100) NOT NULL,
        content_sha256 NVARCHAR(64) NULL,
        byte_count BIGINT NULL,
        lake_uri NVARCHAR(1000) NOT NULL,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_artifact PRIMARY KEY CLUSTERED (artifact_id),
        CONSTRAINT FK_llm_artifact_run FOREIGN KEY (run_id) REFERENCES [llm].[run](run_id),
        CONSTRAINT CK_llm_artifact_type CHECK (artifact_type IN ('request_json', 'response_json', 'evidence_bundle', 'prompt_text', 'parsed_output', 'raw_response'))
    );
    PRINT 'Table [llm].[artifact] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[artifact] already exists.'
END
GO
