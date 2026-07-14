-- Migration: Create ai_artifacts table for storing AI-generated content
-- Description: Store all AI outputs (summary, keywords, quiz, flashcards, mindmap, revision notes)
-- Run this in Supabase SQL Editor

-- Create ai_artifacts table
CREATE TABLE IF NOT EXISTS ai_artifacts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    learning_id UUID NOT NULL REFERENCES learnings(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL, -- 'summary', 'keywords', 'quiz', 'flashcards', 'mindmap', 'revision_notes'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE ai_artifacts IS 'Stores AI-generated content for learning materials';
COMMENT ON COLUMN ai_artifacts.learning_id IS 'Foreign key to learnings table (UUID)';
COMMENT ON COLUMN ai_artifacts.artifact_type IS 'Type of AI content (summary, keywords, quiz, flashcards, mindmap, revision_notes)';
COMMENT ON COLUMN ai_artifacts.content IS 'The AI-generated content';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_artifacts_learning_id ON ai_artifacts(learning_id);
CREATE INDEX IF NOT EXISTS idx_ai_artifacts_type ON ai_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_ai_artifacts_created_at ON ai_artifacts(created_at);

-- Add unique constraint to prevent duplicate artifacts of same type per learning
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_artifacts_unique 
ON ai_artifacts(learning_id, artifact_type);

-- Verify the table was created
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'ai_artifacts' 
ORDER BY ordinal_position;
