-- Verify all 19 newly added cases exist and have been analyzed

-- First, check if tables exist (run this first to diagnose)
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('cases', 'cases_factors', 'cases_holdings', 'cases_analysis_metadata')
ORDER BY table_name;

-- If tables exist, run the verification queries below:

-- Check by case IDs (537-555 based on logs) and source
SELECT 
    cc.id,
    cc.case_name,
    cc.citation,
    cc.docket_number,
    cc.court_name,
    cc.decision_date,
    cc.source,
    LENGTH(cc.opinion_text) as opinion_text_length,
    cam.is_analyzed,
    (SELECT COUNT(*) FROM public.cases_factors WHERE case_id = cc.id) AS factor_count,
    (SELECT COUNT(*) FROM public.cases_holdings WHERE case_id = cc.id) AS holding_count
FROM public.cases cc
LEFT JOIN public.cases_analysis_metadata cam ON cam.case_id = cc.id
WHERE cc.id BETWEEN '537' AND '555'
   OR (cc.source = 'user_input' AND cc.id >= '537')
ORDER BY cc.id;

-- Summary
SELECT 
    COUNT(*) AS total_cases,
    COUNT(CAM.is_analyzed) FILTER (WHERE CAM.is_analyzed = true) AS analyzed_count,
    SUM((SELECT COUNT(*) FROM public.cases_factors WHERE case_id = CC.id)) AS total_factors,
    SUM((SELECT COUNT(*) FROM public.cases_holdings WHERE case_id = CC.id)) AS total_holdings
FROM public.cases CC
LEFT JOIN public.cases_analysis_metadata CAM ON CAM.case_id = CC.id
WHERE CC.id BETWEEN '537' AND '555'
   OR (CC.source = 'user_input' AND CC.id >= '537');

-- Alternative: Check by source only (if ID range doesn't work)
SELECT 
    cc.id,
    cc.case_name,
    cc.citation,
    cc.source,
    LENGTH(cc.opinion_text) as opinion_text_length,
    cam.is_analyzed,
    (SELECT COUNT(*) FROM public.cases_factors WHERE case_id = cc.id) AS factor_count,
    (SELECT COUNT(*) FROM public.cases_holdings WHERE case_id = cc.id) AS holding_count
FROM public.cases cc
LEFT JOIN public.cases_analysis_metadata cam ON cam.case_id = cc.id
WHERE cc.source = 'user_input'
ORDER BY cc.id DESC
LIMIT 20;
