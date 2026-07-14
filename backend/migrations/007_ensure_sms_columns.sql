-- Migration: Ensure SMS columns exist in user_state
-- Description: Add SMS notification columns if they don't exist
-- Created: 2026-07-14

-- Add SMS reminder settings to user_state
ALTER TABLE IF EXISTS public.user_state
  ADD COLUMN IF NOT EXISTS notification_phone text,
  ADD COLUMN IF NOT EXISTS sms_notifications_enabled boolean not null default false,
  ADD COLUMN IF NOT EXISTS notification_timezone text not null default 'UTC',
  ADD COLUMN IF NOT EXISTS notification_hour integer not null default 8,
  ADD COLUMN IF NOT EXISTS last_sms_sent_date text;

-- Add comments for documentation
COMMENT ON COLUMN user_state.notification_phone IS 'Phone number for SMS reminders';
COMMENT ON COLUMN user_state.sms_notifications_enabled IS 'Whether SMS reminders are enabled';
COMMENT ON COLUMN user_state.notification_timezone IS 'Timezone for SMS delivery';
COMMENT ON COLUMN user_state.notification_hour IS 'Preferred hour for SMS delivery (0-23)';
COMMENT ON COLUMN user_state.last_sms_sent_date IS 'Date when last SMS was sent';

-- Verify the columns were added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user_state' 
AND column_name IN ('notification_phone', 'sms_notifications_enabled', 'notification_timezone', 'notification_hour', 'last_sms_sent_date')
ORDER BY column_name;
