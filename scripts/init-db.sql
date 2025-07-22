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

-- Set up database configuration for better performance
ALTER DATABASE digital_store_bot SET log_statement = 'none';
ALTER DATABASE digital_store_bot SET log_min_duration_statement = 1000;
ALTER DATABASE digital_store_bot SET shared_preload_libraries = '';

-- Create initial schemas if needed (Alembic will handle table creation)
-- These are just for reference and will be managed by Alembic migrations

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE digital_store_bot TO botuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO botuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO botuser;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO botuser;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO botuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO botuser;

-- Optimization settings for the database user
ALTER USER botuser SET synchronous_commit = 'off';
ALTER USER botuser SET wal_writer_delay = '200ms';
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