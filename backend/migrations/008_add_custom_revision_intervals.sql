-- Migration: Add custom revision intervals to user_state
-- Description: Allow users to set custom revision intervals in days
-- Created: 2026-09-08

-- Add custom_revision_intervals column (JSON array of integers)
ALTER TABLE IF EXISTS public.user_state
  ADD COLUMN IF NOT EXISTS custom_revision_intervals jsonb;

-- Set default to NULL (means use system default)
ALTER TABLE IF EXISTS public.user_state
  ALTER COLUMN custom_revision_intervals SET DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN user_state.custom_revision_intervals IS 'Custom revision intervals in days (JSON array of integers). NULL means use system default [1,4,7,30,180]';

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'user_state'
AND column_name = 'custom_revision_intervals';
