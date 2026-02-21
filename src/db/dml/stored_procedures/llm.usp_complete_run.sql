CREATE PROCEDURE [llm].[usp_complete_run]
    @run_id UNIQUEIDENTIFIER,
    @status VARCHAR(20),
    @metrics_json NVARCHAR(MAX) = NULL,
    @error NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE [llm].[run]
    SET completed_utc = SYSUTCDATETIME(),
        status = @status,
        metrics_json = @metrics_json,
        error = @error
    WHERE run_id = @run_id;
END
