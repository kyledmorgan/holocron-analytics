CREATE PROCEDURE dbo.__usp_log_migration_start
    @migration_id NVARCHAR(50),
    @step_name NVARCHAR(200),
    @rows_before BIGINT = NULL,
    @details NVARCHAR(MAX) = NULL,
    @log_id INT OUTPUT
AS
BEGIN
    INSERT INTO dbo.__migration_log (migration_id, step_name, rows_before, details, status)
    VALUES (@migration_id, @step_name, @rows_before, @details, 'started');

    SET @log_id = SCOPE_IDENTITY();

    PRINT '  [START] ' + @step_name + ' (rows_before: ' + ISNULL(CAST(@rows_before AS VARCHAR), 'N/A') + ')';
END;
