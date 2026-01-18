-- Migration to add court_position column to case_factors table
-- Run this in your Supabase SQL editor

ALTER TABLE case_factors 
ADD COLUMN IF NOT EXISTS court_position VARCHAR(50) DEFAULT 'unclear';

-- Add index for filtering by court position
CREATE INDEX IF NOT EXISTS idx_case_factors_court_position 
ON case_factors(court_position);

-- Update comment
COMMENT ON COLUMN case_factors.court_position IS 'Court position on this factor: for_defendant, against_defendant, neutral, mixed, or unclear';
