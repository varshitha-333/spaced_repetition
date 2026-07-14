-- Migration: Add Execution Locks Table
-- Description: Database-based locks to prevent concurrent cron executions
-- Created: 2026-07-14

-- Create execution_locks table
CREATE TABLE IF NOT EXISTS execution_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lock_key TEXT UNIQUE NOT NULL,
    locked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_execution_locks_key ON execution_locks(lock_key);
CREATE INDEX IF NOT EXISTS idx_execution_locks_expires_at ON execution_locks(expires_at);

-- Add comments for documentation
COMMENT ON TABLE execution_locks IS 'Database-based locks to prevent concurrent cron executions';
COMMENT ON COLUMN execution_locks.lock_key IS 'Unique identifier for the lock (e.g., daily_notifications)';
COMMENT ON COLUMN execution_locks.locked_at IS 'When the lock was acquired';
COMMENT ON COLUMN execution_locks.expires_at IS 'When the lock expires (auto-releases)';

-- Create function to clean up expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM execution_locks WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create idempotency_keys table for duplicate prevention
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for idempotency_keys
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_key ON idempotency_keys(key);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_job_type ON idempotency_keys(job_type);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_executed_at ON idempotency_keys(executed_at);

-- Add comments for idempotency_keys
COMMENT ON TABLE idempotency_keys IS 'Tracks executed jobs to prevent duplicate executions';
COMMENT ON COLUMN idempotency_keys.key IS 'Unique idempotency key for the job';
COMMENT ON COLUMN idempotency_keys.job_type IS 'Type of job (e.g., sms_notification)';
COMMENT ON COLUMN idempotency_keys.executed_at IS 'When the job was executed';

-- Create function to clean up old idempotency keys (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_idempotency_keys()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM idempotency_keys WHERE executed_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Verify the tables were created
-- Note: Run these separately if needed
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'execution_locks' ORDER BY ordinal_position;
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'idempotency_keys' ORDER BY ordinal_position;
