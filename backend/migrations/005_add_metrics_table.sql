-- Migration: Add Metrics Table
-- Description: Store system metrics for monitoring and alerting
-- Created: 2026-07-14

-- Create metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp);

-- Add comments for documentation
COMMENT ON TABLE metrics IS 'Stores system metrics for monitoring and alerting';
COMMENT ON COLUMN metrics.metric_name IS 'Name of the metric (e.g., cron_executions, sms_sent, sms_failed)';
COMMENT ON COLUMN metrics.metric_value IS 'Numeric value of the metric';
COMMENT ON COLUMN metrics.metric_unit IS 'Unit of measurement (e.g., count, milliseconds, percent)';
COMMENT ON COLUMN metrics.tags IS 'Additional context as JSON (e.g., {job_type: sms, user_id: xxx})';
COMMENT ON COLUMN metrics.timestamp IS 'When the metric was recorded';

-- Create cron_executions table for detailed cron job tracking
CREATE TABLE IF NOT EXISTS cron_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL, -- started, completed, failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    processed_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    error_message TEXT,
    error_stack TEXT,
    idempotency_key TEXT
);

-- Create indexes for cron_executions
CREATE INDEX IF NOT EXISTS idx_cron_executions_execution_id ON cron_executions(execution_id);
CREATE INDEX IF NOT EXISTS idx_cron_executions_job_type ON cron_executions(job_type);
CREATE INDEX IF NOT EXISTS idx_cron_executions_status ON cron_executions(status);
CREATE INDEX IF NOT EXISTS idx_cron_executions_started_at ON cron_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_cron_executions_idempotency_key ON cron_executions(idempotency_key);

-- Add comments for cron_executions
COMMENT ON TABLE cron_executions IS 'Tracks cron job executions for monitoring and debugging';
COMMENT ON COLUMN cron_executions.execution_id IS 'Unique identifier for this execution';
COMMENT ON COLUMN cron_executions.job_type IS 'Type of cron job (e.g., daily_notifications)';
COMMENT ON COLUMN cron_executions.status IS 'Execution status: started, completed, failed';
COMMENT ON COLUMN cron_executions.started_at IS 'When the job started';
COMMENT ON COLUMN cron_executions.completed_at IS 'When the job completed';
COMMENT ON COLUMN cron_executions.duration_ms IS 'Job duration in milliseconds';
COMMENT ON COLUMN cron_executions.processed_count IS 'Number of items processed';
COMMENT ON COLUMN cron_executions.skipped_count IS 'Number of items skipped';
COMMENT ON COLUMN cron_executions.failed_count IS 'Number of items that failed';
COMMENT ON COLUMN cron_executions.idempotency_key IS 'Key to prevent duplicate executions';

-- Verify the tables were created
-- Note: Run these separately if needed
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'metrics' ORDER BY ordinal_position;
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cron_executions' ORDER BY ordinal_position;
