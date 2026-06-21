CREATE PROCEDURE dbo.__usp_log_migration_end
    @log_id INT,
    @status NVARCHAR(20),
    @rows_after BIGINT = NULL,
    @error_message NVARCHAR(MAX) = NULL,
    @details NVARCHAR(MAX) = NULL
AS
BEGIN
    UPDATE dbo.__migration_log
    SET completed_utc = SYSUTCDATETIME(),
        status = @status,
        rows_after = @rows_after,
        error_message = @error_message,
        details = ISNULL(@details, details)
    WHERE log_id = @log_id;

    IF @status = 'completed'
        PRINT '  [DONE] Completed (rows_after: ' + ISNULL(CAST(@rows_after AS VARCHAR), 'N/A') + ')';
    ELSE IF @status = 'failed'
        PRINT '  [FAIL] ' + ISNULL(@error_message, 'Unknown error');
    ELSE IF @status = 'skipped'
        PRINT '  [SKIP] ' + ISNULL(@details, 'No changes needed');
END;
