-- Initialize PhotoProcessor Database
-- This script creates the initial database structure

-- Create database if not exists (handled by docker-entrypoint)
-- CREATE DATABASE IF NOT EXISTS photoprocessor;

-- Connect to the database
\c photoprocessor;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create processed_images table
CREATE TABLE IF NOT EXISTS processed_images (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    processed_filename VARCHAR(255) NOT NULL,
    processing_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_processed_images_user_id ON processed_images(user_id);
CREATE INDEX IF NOT EXISTS idx_processed_images_created_at ON processed_images(created_at);

-- Insert demo data (optional)
INSERT INTO users (username, email, password_hash) VALUES 
('demo', 'demo@photoprocessor.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj0kOEqN2K1m')
ON CONFLICT (username) DO NOTHING;

-- Show created tables
\dt