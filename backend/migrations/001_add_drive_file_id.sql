-- Migration: Add drive_file_id column to learnings table
-- Description: Store Google Drive file ID separately from drive link for better tracking
-- Run this in Supabase SQL Editor

-- Add drive_file_id column to learnings table
ALTER TABLE learnings 
ADD COLUMN IF NOT EXISTS drive_file_id TEXT;

-- Add comment for documentation
COMMENT ON COLUMN learnings.drive_file_id IS 'Google Drive file ID for uploaded files';

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_learnings_drive_file_id ON learnings(drive_file_id);

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'learnings' 
AND column_name = 'drive_file_id';
