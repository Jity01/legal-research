-- SQL script to create tables in Supabase
-- Run this in your Supabase SQL editor to set up the database schema

-- Create court_cases table
CREATE TABLE IF NOT EXISTS court_cases (
    id BIGSERIAL PRIMARY KEY,
    case_name VARCHAR(500) NOT NULL,
    docket_number VARCHAR(100),
    citation VARCHAR(200),
    court_type VARCHAR(50) NOT NULL,
    court_name VARCHAR(200),
    decision_date DATE NOT NULL,
    published_date DATE,
    opinion_text TEXT,
    opinion_url VARCHAR(1000),
    opinion_file_path VARCHAR(500),
    judges TEXT,
    case_type VARCHAR(100),
    topics TEXT,
    source VARCHAR(200),
    source_url VARCHAR(1000),
    is_published BOOLEAN DEFAULT TRUE,
    is_downloaded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_decision_date ON court_cases(decision_date);
CREATE INDEX IF NOT EXISTS idx_court_type ON court_cases(court_type);
CREATE INDEX IF NOT EXISTS idx_docket_number ON court_cases(docket_number);
CREATE INDEX IF NOT EXISTS idx_case_name ON court_cases(case_name);

-- Create collection_progress table
CREATE TABLE IF NOT EXISTS collection_progress (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(200) UNIQUE NOT NULL,
    last_collected_date DATE,
    total_cases_collected INTEGER DEFAULT 0,
    status VARCHAR(50),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

-- Enable Row Level Security (RLS) - adjust policies as needed
ALTER TABLE court_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_progress ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (adjust based on your security needs)
-- For development, you might want to allow all operations
-- For production, create more restrictive policies

-- Allow all operations on court_cases (adjust as needed)
CREATE POLICY "Allow all operations on court_cases"
    ON court_cases
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Allow all operations on collection_progress (adjust as needed)
CREATE POLICY "Allow all operations on collection_progress"
    ON collection_progress
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Optional: Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        NEW.updated_at = NOW();
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_court_cases_updated_at
    BEFORE UPDATE ON court_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_progress_updated_at
    BEFORE UPDATE ON collection_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
