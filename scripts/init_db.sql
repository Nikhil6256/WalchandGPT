-- WalchandGPT Database Initialization
-- Enable required PostgreSQL extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for full-text search

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE walchandgpt TO walchand;
