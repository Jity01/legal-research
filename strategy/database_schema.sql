-- Database schema extensions for case analysis and search
-- Run this in Supabase SQL editor after the base schema

-- Table to store extracted factors from cases
CREATE TABLE IF NOT EXISTS case_factors (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    factor_text TEXT NOT NULL,
    factor_type VARCHAR(50), -- 'concept', 'fact', 'legal_principle', etc.
    weight_to_holding FLOAT NOT NULL DEFAULT 0.0, -- 0.0 to 1.0, how important to final holding
    court_position VARCHAR(50) DEFAULT 'unclear', -- 'for_defendant', 'against_defendant', 'neutral', 'mixed', 'unclear'
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(case_id, factor_text)
);

CREATE INDEX IF NOT EXISTS idx_case_factors_case_id ON case_factors(case_id);
CREATE INDEX IF NOT EXISTS idx_case_factors_weight ON case_factors(weight_to_holding);
CREATE INDEX IF NOT EXISTS idx_case_factors_text ON case_factors USING gin(to_tsvector('english', factor_text));
CREATE INDEX IF NOT EXISTS idx_case_factors_court_position ON case_factors(court_position);

-- Table to store case holdings and their direction
CREATE TABLE IF NOT EXISTS case_holdings (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE UNIQUE,
    holding_text TEXT NOT NULL,
    holding_direction VARCHAR(20), -- 'for_defendant', 'against_defendant', 'mixed', 'unclear'
    confidence FLOAT DEFAULT 0.0, -- 0.0 to 1.0
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_holdings_case_id ON case_holdings(case_id);
CREATE INDEX IF NOT EXISTS idx_case_holdings_direction ON case_holdings(holding_direction);

-- Table to store citations between cases
CREATE TABLE IF NOT EXISTS case_citations (
    id BIGSERIAL PRIMARY KEY,
    citing_case_id BIGINT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE,
    cited_case_id BIGINT REFERENCES court_cases(id) ON DELETE SET NULL,
    citation_text VARCHAR(500), -- The actual citation text found
    citation_context TEXT, -- Surrounding context
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(citing_case_id, cited_case_id, citation_text)
);

CREATE INDEX IF NOT EXISTS idx_case_citations_citing ON case_citations(citing_case_id);
CREATE INDEX IF NOT EXISTS idx_case_citations_cited ON case_citations(cited_case_id);

-- Table to store case analysis metadata
CREATE TABLE IF NOT EXISTS case_analysis_metadata (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES court_cases(id) ON DELETE CASCADE UNIQUE,
    is_analyzed BOOLEAN DEFAULT FALSE,
    analysis_version INTEGER DEFAULT 1,
    analyzed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_analysis_metadata_case_id ON case_analysis_metadata(case_id);
CREATE INDEX IF NOT EXISTS idx_case_analysis_metadata_analyzed ON case_analysis_metadata(is_analyzed);

-- Enable RLS
ALTER TABLE case_factors ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_analysis_metadata ENABLE ROW LEVEL SECURITY;

-- RLS Policies (allow all for now - adjust for production)
CREATE POLICY "Allow all operations on case_factors"
    ON case_factors FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on case_holdings"
    ON case_holdings FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on case_citations"
    ON case_citations FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on case_analysis_metadata"
    ON case_analysis_metadata FOR ALL USING (true) WITH CHECK (true);
