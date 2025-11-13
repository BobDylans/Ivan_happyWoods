-- Database Migration Script for Voice Agent API
-- P0 Phase: Production Deployment
--
-- This script contains all database migrations for production deployment
-- Run this BEFORE deploying new versions

-- Add migration tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(255),
    installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE
);

-- Migration 001: Add distributed tracing tables (P0 Phase)
-- Status: Pending execution
DO $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version = '001_add_tracing_tables') THEN
        -- Create table for trace spans if not exists
        CREATE TABLE IF NOT EXISTS trace_spans (
            id BIGSERIAL PRIMARY KEY,
            trace_id VARCHAR(32) NOT NULL,
            span_id VARCHAR(16) NOT NULL,
            parent_span_id VARCHAR(16),
            operation_name VARCHAR(255) NOT NULL,
            service_name VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'UNSET',
            error BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            duration_ms INTEGER,
            start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            attributes JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trace_id, span_id)
        );

        -- Create indexes for efficient querying
        CREATE INDEX IF NOT EXISTS idx_trace_spans_trace_id ON trace_spans(trace_id);
        CREATE INDEX IF NOT EXISTS idx_trace_spans_service ON trace_spans(service_name);
        CREATE INDEX IF NOT EXISTS idx_trace_spans_operation ON trace_spans(operation_name);
        CREATE INDEX IF NOT EXISTS idx_trace_spans_start_time ON trace_spans(start_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trace_spans_status ON trace_spans(status);

        -- Record this migration
        INSERT INTO schema_migrations (version, description, execution_time_ms, success)
        VALUES ('001_add_tracing_tables', 'Add distributed tracing span storage tables',
                (SELECT (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CURRENT_TIMESTAMP)) * 1000)::INTEGER),
                TRUE);

        RAISE NOTICE 'Migration 001 executed: Added tracing tables';
    END IF;
END $$;

-- Migration 002: Add performance metrics tables
DO $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version = '002_add_metrics_tables') THEN
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id BIGSERIAL PRIMARY KEY,
            session_id VARCHAR(255),
            endpoint VARCHAR(255),
            method VARCHAR(10),
            response_time_ms INTEGER NOT NULL,
            status_code INTEGER,
            error BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_metrics_endpoint ON performance_metrics(endpoint);
        CREATE INDEX IF NOT EXISTS idx_metrics_session ON performance_metrics(session_id);

        INSERT INTO schema_migrations (version, description, success)
        VALUES ('002_add_metrics_tables', 'Add performance metrics collection tables', TRUE);

        RAISE NOTICE 'Migration 002 executed: Added metrics tables';
    END IF;
END $$;

-- Migration 003: Add backup tracking tables
DO $$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version = '003_add_backup_tables') THEN
        CREATE TABLE IF NOT EXISTS backup_history (
            id BIGSERIAL PRIMARY KEY,
            backup_type VARCHAR(50) NOT NULL, -- 'full', 'incremental'
            status VARCHAR(50) NOT NULL, -- 'pending', 'in_progress', 'completed', 'failed'
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            size_bytes BIGINT,
            location VARCHAR(512),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_backup_status ON backup_history(status);
        CREATE INDEX IF NOT EXISTS idx_backup_created ON backup_history(created_at DESC);

        INSERT INTO schema_migrations (version, description, success)
        VALUES ('003_add_backup_tables', 'Add backup tracking and management tables', TRUE);

        RAISE NOTICE 'Migration 003 executed: Added backup tables';
    END IF;
END $$;

-- Grant appropriate permissions
ALTER TABLE schema_migrations OWNER TO agent_user;
ALTER TABLE trace_spans OWNER TO agent_user;
ALTER TABLE performance_metrics OWNER TO agent_user;
ALTER TABLE backup_history OWNER TO agent_user;

-- Show migration status
SELECT version, description, installed_on, success FROM schema_migrations ORDER BY installed_on;
