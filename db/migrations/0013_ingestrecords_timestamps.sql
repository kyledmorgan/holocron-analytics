-- Migration 0013: Add request/response timestamp columns to ingest.IngestRecords
-- Idempotent: Only adds columns if they don't exist
-- Additive-only (no drops)

USE [Holocron];
GO

-- Add request_timestamp
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]')
    AND name = 'request_timestamp'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords]
    ADD request_timestamp DATETIME2 NULL;
    PRINT 'Column [request_timestamp] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [request_timestamp] already exists on [ingest].[IngestRecords].'
END
GO

-- Add response_timestamp
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]')
    AND name = 'response_timestamp'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords]
    ADD response_timestamp DATETIME2 NULL;
    PRINT 'Column [response_timestamp] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [response_timestamp] already exists on [ingest].[IngestRecords].'
END
GO

PRINT 'Migration 0013 completed: IngestRecords timestamps ensured.'
