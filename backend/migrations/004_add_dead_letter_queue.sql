-- Migration: Add Dead-Letter Queue Table
-- Description: Store permanently failed jobs for manual review and retry
-- Created: 2026-07-14

-- Create dead_letter_queue table
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    job_id TEXT,
    user_id UUID,
    payload JSONB,
    error_message TEXT,
    error_stack TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    status TEXT DEFAULT 'failed', -- failed, retrying, resolved
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by TEXT
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_dlq_job_type ON dead_letter_queue(job_type);
CREATE INDEX IF NOT EXISTS idx_dlq_user_id ON dead_letter_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX IF NOT EXISTS idx_dlq_created_at ON dead_letter_queue(created_at);

-- Add comments for documentation
COMMENT ON TABLE dead_letter_queue IS 'Stores permanently failed jobs for manual review and retry';
COMMENT ON COLUMN dead_letter_queue.job_type IS 'Type of job (e.g., sms_notification, ai_generation, drive_upload)';
COMMENT ON COLUMN dead_letter_queue.job_id IS 'Unique identifier for the job';
COMMENT ON COLUMN dead_letter_queue.user_id IS 'User ID associated with the job';
COMMENT ON COLUMN dead_letter_queue.payload IS 'Job payload/data';
COMMENT ON COLUMN dead_letter_queue.error_message IS 'Human-readable error message';
COMMENT ON COLUMN dead_letter_queue.error_stack IS 'Full error stack trace';
COMMENT ON COLUMN dead_letter_queue.retry_count IS 'Number of retry attempts';
COMMENT ON COLUMN dead_letter_queue.max_retries IS 'Maximum allowed retries';
COMMENT ON COLUMN dead_letter_queue.status IS 'Job status: failed, retrying, resolved';
COMMENT ON COLUMN dead_letter_queue.resolved_at IS 'Timestamp when job was resolved';
COMMENT ON COLUMN dead_letter_queue.resolved_by IS 'Who resolved the job (system or admin)';

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_dlq_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
CREATE TRIGGER trigger_update_dlq_updated_at
    BEFORE UPDATE ON dead_letter_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_dlq_updated_at();

-- Verify the table was created
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'dead_letter_queue' 
ORDER BY ordinal_position;
