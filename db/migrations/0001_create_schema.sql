-- Migration 0001: Create ingest schema
-- Idempotent: Only creates schema if it doesn't exist

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'ingest')
BEGIN
    EXEC('CREATE SCHEMA ingest')
    PRINT 'Schema [ingest] created successfully.'
END
ELSE
BEGIN
    PRINT 'Schema [ingest] already exists.'
END
GO
