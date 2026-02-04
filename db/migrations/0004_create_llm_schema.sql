-- Migration 0004: Create llm schema
-- Idempotent: Only creates schema if it doesn't exist

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'llm')
BEGIN
    EXEC('CREATE SCHEMA llm')
    PRINT 'Schema [llm] created successfully.'
END
ELSE
BEGIN
    PRINT 'Schema [llm] already exists.'
END
GO
