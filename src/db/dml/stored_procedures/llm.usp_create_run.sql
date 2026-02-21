CREATE PROCEDURE [llm].[usp_create_run]
    @job_id UNIQUEIDENTIFIER,
    @worker_id NVARCHAR(200),
    @ollama_base_url NVARCHAR(500),
    @model_name NVARCHAR(100),
    @model_tag NVARCHAR(100) = NULL,
    @model_digest NVARCHAR(200) = NULL,
    @options_json NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @run_id UNIQUEIDENTIFIER = NEWID();

    INSERT INTO [llm].[run] (
        run_id,
        job_id,
        started_utc,
        status,
        worker_id,
        ollama_base_url,
        model_name,
        model_tag,
        model_digest,
        options_json
    )
    VALUES (
        @run_id,
        @job_id,
        SYSUTCDATETIME(),
        'RUNNING',
        @worker_id,
        @ollama_base_url,
        @model_name,
        @model_tag,
        @model_digest,
        @options_json
    );

    SELECT @run_id AS run_id;
END
