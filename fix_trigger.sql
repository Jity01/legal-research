-- Fix for the updated_at trigger issue
-- Run this in your Supabase SQL Editor if you're getting the "record 'new' has no field 'updated_at'" error

-- Drop existing triggers
DROP TRIGGER IF EXISTS update_collection_progress_updated_at ON collection_progress;
DROP TRIGGER IF EXISTS update_cases_updated_at ON cases;

-- Recreate the function with better error handling
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Update the appropriate column based on table
        IF TG_TABLE_NAME::text = 'collection_progress' THEN
            NEW.last_updated = NOW();
        ELSIF TG_TABLE_NAME::text = 'cases' THEN
            NEW.updated_at = NOW();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Recreate triggers
CREATE TRIGGER update_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_progress_updated_at
    BEFORE UPDATE ON collection_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
