-- Create ingest schema for raw ingestion records
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'ingest')
BEGIN
    EXEC('CREATE SCHEMA ingest')
END
GO
