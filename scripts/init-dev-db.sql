-- Initialize development database
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases if needed
-- CREATE DATABASE fastapi_template_staging;

-- Create any initial extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";

-- You can add initial seed data here if needed
-- INSERT INTO initial_data...

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE fastapi_template_dev TO dev_user;