CREATE PROCEDURE [llm].[usp_enqueue_job_idempotent]
    @interrogation_key NVARCHAR(200),
    @dedupe_key NVARCHAR(500),
    @input_json NVARCHAR(MAX),
    @evidence_ref_json NVARCHAR(MAX) = NULL,
    @model_hint NVARCHAR(100) = NULL,
    @priority INT = 100,
    @max_attempts INT = 3
AS
BEGIN
    SET NOCOUNT ON;

    -- Validate dedupe_key is provided
    IF @dedupe_key IS NULL OR LEN(LTRIM(RTRIM(@dedupe_key))) = 0
    BEGIN
        RAISERROR('dedupe_key is required for idempotent job enqueue', 16, 1);
        RETURN;
    END

    -- Call the standard enqueue with dedupe_key
    EXEC [llm].[usp_enqueue_job]
        @priority = @priority,
        @interrogation_key = @interrogation_key,
        @input_json = @input_json,
        @evidence_ref_json = @evidence_ref_json,
        @model_hint = @model_hint,
        @max_attempts = @max_attempts,
        @dedupe_key = @dedupe_key;
END
