-- Migration: Fix revisions table schema
-- Description: Ensure all required columns exist for proper revision tracking
-- Run this in Supabase SQL Editor

-- Add drive_link column if it doesn't exist
ALTER TABLE revisions 
ADD COLUMN IF NOT EXISTS drive_link TEXT;

-- Add material_id column if it doesn't exist (links to learnings table)
ALTER TABLE revisions 
ADD COLUMN IF NOT EXISTS material_id INTEGER;

-- Add completed_date column if it doesn't exist (tracks when revision was completed)
ALTER TABLE revisions 
ADD COLUMN IF NOT EXISTS completed_date TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN revisions.drive_link IS 'Google Drive link for the revision material';
COMMENT ON COLUMN revisions.material_id IS 'Foreign key reference to learnings table';
COMMENT ON COLUMN revisions.completed_date IS 'Timestamp when revision was marked as completed';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_revisions_material_id ON revisions(material_id);
CREATE INDEX IF NOT EXISTS idx_revisions_completed_date ON revisions(completed_date);
CREATE INDEX IF NOT EXISTS idx_revisions_scheduled_date ON revisions(scheduled_date);

-- Verify the columns were added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'revisions' 
AND column_name IN ('drive_link', 'material_id', 'completed_date')
ORDER BY column_name;
