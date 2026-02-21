CREATE PROCEDURE [llm].[usp_get_job_by_dedupe_key]
    @interrogation_key NVARCHAR(200),
    @dedupe_key NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        job_id,
        created_utc,
        status,
        priority,
        interrogation_key,
        input_json,
        evidence_ref_json,
        model_hint,
        max_attempts,
        attempt_count,
        available_utc,
        locked_by,
        locked_utc,
        last_error,
        dedupe_key
    FROM [llm].[job]
    WHERE interrogation_key = @interrogation_key
      AND dedupe_key = @dedupe_key;
END
