-- Create the Holocron database if it does not already exist
-- This script is run by the initdb container before seeding

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'$(DATABASE_NAME)')
BEGIN
    CREATE DATABASE [$(DATABASE_NAME)];
    PRINT 'Database $(DATABASE_NAME) created successfully.';
END
ELSE
BEGIN
    PRINT 'Database $(DATABASE_NAME) already exists.';
END
GO
