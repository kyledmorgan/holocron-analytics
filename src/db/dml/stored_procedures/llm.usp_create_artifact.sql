CREATE PROCEDURE [llm].[usp_create_artifact]
    @run_id UNIQUEIDENTIFIER,
    @artifact_type NVARCHAR(100),
    @lake_uri NVARCHAR(1000) = NULL,
    @content_sha256 NVARCHAR(64) = NULL,
    @byte_count BIGINT = NULL,
    @content NVARCHAR(MAX) = NULL,
    @content_mime_type NVARCHAR(100) = NULL,
    @stored_in_sql BIT = 0,
    @mirrored_to_lake BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @artifact_id UNIQUEIDENTIFIER = NEWID();

    INSERT INTO [llm].[artifact] (
        artifact_id,
        run_id,
        artifact_type,
        content_sha256,
        byte_count,
        lake_uri,
        content,
        content_mime_type,
        stored_in_sql,
        mirrored_to_lake,
        created_utc
    )
    VALUES (
        @artifact_id,
        @run_id,
        @artifact_type,
        @content_sha256,
        @byte_count,
        @lake_uri,
        @content,
        @content_mime_type,
        @stored_in_sql,
        @mirrored_to_lake,
        SYSUTCDATETIME()
    );

    SELECT @artifact_id AS artifact_id;
END
