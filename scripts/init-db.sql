-- =============================================================================
-- Digital Store Bot v2 - Database Initialization Script
-- =============================================================================

-- Create database if not exists (this is handled by Docker environment)
-- But we can set up initial configurations here

-- Set timezone
SET timezone = 'UTC';

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Database configuration will be set after creation
-- Grant necessary permissions (database name comes from POSTGRES_DB env var)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO botuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO botuser;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO botuser;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO botuser;

-- Optimization settings for the database user
ALTER USER botuser SET synchronous_commit = 'off';
-- wal_writer_delay cannot be set per user, skip it
ALTER USER botuser SET commit_delay = 100000;
ALTER USER botuser SET commit_siblings = 5;

-- Create a function to update the updated_at column automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log initialization
DO $$ 
BEGIN
    RAISE NOTICE 'Digital Store Bot v2 database initialization completed successfully';
END $$;