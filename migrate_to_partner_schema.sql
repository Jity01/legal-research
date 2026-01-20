-- Migration script to move data from your schema to partner's schema
-- This script migrates:
--   court_cases (BIGINT id) → cases (TEXT id)
--   case_factors → cases_factors
--   case_holdings → cases_holdings
--   case_citations → cases_citations
--   case_analysis_metadata → cases_analysis_metadata
--
-- IMPORTANT: Run this in Supabase SQL Editor
-- Make sure partner's schema tables exist first!

BEGIN;

-- Step 1: Migrate court_cases to cases table
-- Convert BIGINT id to TEXT id
-- Note: Partner's cases table only has: id, case_name, full_text, citation, court, date_filed, judges, url, summary
INSERT INTO cases (
    id,
    case_name,
    full_text,
    citation,
    court,
    date_filed,
    judges,
    url,
    summary
)
SELECT 
    cc.id::TEXT AS id,  -- Convert BIGINT to TEXT
    cc.case_name,
    COALESCE(cc.opinion_text, '') AS full_text,  -- Map opinion_text to full_text
    cc.citation,
    COALESCE(cc.court_name, cc.court_type, 'Unknown') AS court,  -- Map court_name/court_type to court
    cc.decision_date AS date_filed,  -- Map decision_date to date_filed (DATE to TIMESTAMP)
    cc.judges,
    cc.opinion_url AS url,  -- Map opinion_url to url
    COALESCE(cc.topics, cc.case_type, '') AS summary  -- Use topics or case_type as summary
FROM court_cases cc
WHERE cc.case_name IS NOT NULL  -- Only migrate cases with a name
ON CONFLICT (id) DO NOTHING;  -- Skip if already exists

-- Step 2: Migrate case_factors to cases_factors
-- Convert case_id from BIGINT to TEXT
INSERT INTO cases_factors (
    case_id,
    factor_text,
    factor_type,
    weight_to_holding,
    extracted_at,
    court_position
)
SELECT 
    cf.case_id::TEXT AS case_id,  -- Convert BIGINT to TEXT
    cf.factor_text,
    COALESCE(cf.factor_type, 'concept') AS factor_type,
    cf.weight_to_holding,
    cf.extracted_at,
    cf.court_position
FROM case_factors cf
WHERE EXISTS (SELECT 1 FROM cases c WHERE c.id = cf.case_id::TEXT)  -- Only migrate if case exists
ON CONFLICT (case_id, factor_text) DO NOTHING;

-- Step 3: Migrate case_holdings to cases_holdings
INSERT INTO cases_holdings (
    case_id,
    holding_text,
    holding_direction,
    confidence,
    extracted_at
)
SELECT 
    ch.case_id::TEXT AS case_id,  -- Convert BIGINT to TEXT
    ch.holding_text,
    COALESCE(ch.holding_direction, 'unclear') AS holding_direction,
    COALESCE(ch.confidence, 0.0) AS confidence,
    ch.extracted_at
FROM case_holdings ch
WHERE EXISTS (SELECT 1 FROM cases c WHERE c.id = ch.case_id::TEXT)
ON CONFLICT (case_id) DO NOTHING;

-- Step 4: Migrate case_citations to cases_citations
INSERT INTO cases_citations (
    citing_case_id,
    cited_case_id,
    citation_text,
    citation_context,
    extracted_at
)
SELECT 
    cc.citing_case_id::TEXT AS citing_case_id,  -- Convert BIGINT to TEXT
    CASE 
        WHEN cc.cited_case_id IS NOT NULL THEN cc.cited_case_id::TEXT
        ELSE NULL
    END AS cited_case_id,
    cc.citation_text,
    cc.citation_context,
    cc.extracted_at
FROM case_citations cc
WHERE EXISTS (SELECT 1 FROM cases c WHERE c.id = cc.citing_case_id::TEXT)  -- Only if citing case exists
ON CONFLICT DO NOTHING;

-- Step 5: Migrate case_analysis_metadata to cases_analysis_metadata
INSERT INTO cases_analysis_metadata (
    case_id,
    is_analyzed,
    analysis_version,
    analyzed_at,
    error_message,
    created_at
)
SELECT 
    cam.case_id::TEXT AS case_id,  -- Convert BIGINT to TEXT
    COALESCE(cam.is_analyzed, FALSE) AS is_analyzed,
    cam.analysis_version::VARCHAR(50) AS analysis_version,  -- Convert INTEGER to VARCHAR
    cam.analyzed_at,
    cam.error_message,
    cam.created_at
FROM case_analysis_metadata cam
WHERE EXISTS (SELECT 1 FROM cases c WHERE c.id = cam.case_id::TEXT)
ON CONFLICT (case_id) DO NOTHING;

-- Verification queries (run these after migration to check results)
-- Uncomment to run:

/*
-- Check record counts
SELECT 'cases' AS table_name, COUNT(*) AS count FROM cases
UNION ALL
SELECT 'cases_factors', COUNT(*) FROM cases_factors
UNION ALL
SELECT 'cases_holdings', COUNT(*) FROM cases_holdings
UNION ALL
SELECT 'cases_citations', COUNT(*) FROM cases_citations
UNION ALL
SELECT 'cases_analysis_metadata', COUNT(*) FROM cases_analysis_metadata
ORDER BY table_name;

-- Check for any orphaned records (case_ids that don't exist in cases table)
SELECT 'cases_factors' AS table_name, COUNT(*) AS orphaned_count
FROM cases_factors cf
WHERE NOT EXISTS (SELECT 1 FROM cases c WHERE c.id = cf.case_id)
UNION ALL
SELECT 'cases_holdings', COUNT(*)
FROM cases_holdings ch
WHERE NOT EXISTS (SELECT 1 FROM cases c WHERE c.id = ch.case_id)
UNION ALL
SELECT 'cases_citations', COUNT(*)
FROM cases_citations cc
WHERE NOT EXISTS (SELECT 1 FROM cases c WHERE c.id = cc.citing_case_id)
UNION ALL
SELECT 'cases_analysis_metadata', COUNT(*)
FROM cases_analysis_metadata cam
WHERE NOT EXISTS (SELECT 1 FROM cases c WHERE c.id = cam.case_id);
*/

COMMIT;
