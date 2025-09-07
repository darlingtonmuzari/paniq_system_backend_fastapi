-- Initialize PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial database schema
-- This will be managed by Alembic migrations later