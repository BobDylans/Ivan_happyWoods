-- Database Rollback Script for Voice Agent API
-- P0 Phase: Production Deployment
--
-- CAUTION: This script reverts migrations in reverse order
-- Use only in case of critical failures
-- Always take a backup before executing rollback

-- Rollback Migration 003: Remove backup tracking tables
DO $$
BEGIN
    IF EXISTS(SELECT 1 FROM schema_migrations WHERE version = '003_add_backup_tables' AND success = TRUE) THEN
        -- Backup the data before deletion
        CREATE TABLE IF NOT EXISTS backup_history_archive AS
        SELECT * FROM backup_history;

        DROP TABLE IF EXISTS backup_history CASCADE;
        DELETE FROM schema_migrations WHERE version = '003_add_backup_tables';

        RAISE NOTICE 'Rollback 003 completed: Backup tables removed (archived to backup_history_archive)';
    END IF;
END $$;

-- Rollback Migration 002: Remove performance metrics tables
DO $$
BEGIN
    IF EXISTS(SELECT 1 FROM schema_migrations WHERE version = '002_add_metrics_tables' AND success = TRUE) THEN
        -- Backup the data before deletion
        CREATE TABLE IF NOT EXISTS performance_metrics_archive AS
        SELECT * FROM performance_metrics;

        DROP TABLE IF EXISTS performance_metrics CASCADE;
        DELETE FROM schema_migrations WHERE version = '002_add_metrics_tables';

        RAISE NOTICE 'Rollback 002 completed: Metrics tables removed (archived to performance_metrics_archive)';
    END IF;
END $$;

-- Rollback Migration 001: Remove distributed tracing tables
DO $$
BEGIN
    IF EXISTS(SELECT 1 FROM schema_migrations WHERE version = '001_add_tracing_tables' AND success = TRUE) THEN
        -- Backup the data before deletion
        CREATE TABLE IF NOT EXISTS trace_spans_archive AS
        SELECT * FROM trace_spans;

        DROP TABLE IF EXISTS trace_spans CASCADE;
        DELETE FROM schema_migrations WHERE version = '001_add_tracing_tables';

        RAISE NOTICE 'Rollback 001 completed: Tracing tables removed (archived to trace_spans_archive)';
    END IF;
END $$;

-- Show final migration status
SELECT version, description, installed_on, success FROM schema_migrations ORDER BY installed_on DESC;
SELECT COUNT(*) as archived_trace_spans FROM trace_spans_archive;
SELECT COUNT(*) as archived_metrics FROM performance_metrics_archive;
SELECT COUNT(*) as archived_backups FROM backup_history_archive;
