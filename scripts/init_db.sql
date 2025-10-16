-- Database Initialization Script
-- This script is automatically executed when PostgreSQL container starts

-- Enable pgvector extension (for Phase 3B)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database user (if not exists)
-- Note: User is already created via environment variables in docker-compose

-- Grant necessary privileges
GRANT ALL PRIVILEGES ON DATABASE voice_agent TO agent_user;

-- Create schema (optional, using public by default)
-- CREATE SCHEMA IF NOT EXISTS voice_agent;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Voice Agent database initialized successfully';
END $$;

