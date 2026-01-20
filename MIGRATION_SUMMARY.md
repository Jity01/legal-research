# Migration to Partner's Schema

This document summarizes the migration from your schema to your partner's schema.

## Schema Changes

### Table Name Changes
- `court_cases` → `cases`
- `case_factors` → `cases_factors`
- `case_holdings` → `cases_holdings`
- `case_citations` → `cases_citations`
- `case_analysis_metadata` → `cases_analysis_metadata`

### Data Type Changes
- `case_id` changed from `BIGINT` to `TEXT` (to match partner's `cases.id` which is TEXT)

## Migration Script

**File:** `migrate_to_partner_schema.sql`

This SQL script:
1. Migrates all data from `court_cases` to `cases` (converting BIGINT id to TEXT)
2. Migrates all analysis tables with converted case_id values
3. Uses `ON CONFLICT DO NOTHING` to avoid duplicates
4. Includes verification queries (commented out) to check migration results

**To run:**
1. Ensure partner's schema tables exist in Supabase
2. Run `migrate_to_partner_schema.sql` in Supabase SQL Editor
3. Uncomment and run verification queries at the end to verify migration

## Code Updates

All Python files have been updated to use the new schema:

### Updated Files:
- `database.py` - All `court_cases` → `cases` references
- `process_cases_table.py` - Schema references and function return types
- `preprocess_cases.py` - All table references updated
- `strategy/similarity_matcher.py` - All table references updated
- `strategy/citation_extractor.py` - All table references updated
- `verify_19_cases.py` - All table references updated
- `keep_only_two_cases.py` - All table references updated
- `reprocess_19_cases.py` - All table references updated
- `web/app.py` - Updated route to accept TEXT case_id instead of int

### SQL Files Updated:
- `verify_19_cases.sql` - Updated table names and id comparisons (now TEXT)
- `insert_dean_tran_case.sql` - Updated table names
- `fix_trigger.sql` - Updated trigger references

## Important Notes

1. **Case IDs are now TEXT**: All code that previously expected integer case IDs now handles TEXT. The web API route `/api/case/<case_id>` now accepts string IDs.

2. **Function Return Types**: `get_or_create_court_case()` in `process_cases_table.py` now returns `Optional[str]` instead of `Optional[int]`.

3. **ID Comparisons**: In SQL queries, numeric ID comparisons have been updated to string comparisons (e.g., `WHERE id BETWEEN '537' AND '555'`).

4. **Migration Safety**: The migration script uses `ON CONFLICT DO NOTHING` to prevent duplicate entries if run multiple times.

## Next Steps

1. **Run the migration script** in Supabase SQL Editor
2. **Verify the migration** by running the verification queries in the migration script
3. **Test your application** to ensure everything works with the new schema
4. **Update any external documentation** that references the old schema

## Rollback

If you need to rollback, you would need to:
1. Keep your old tables (`court_cases`, `case_*`) intact
2. Revert the code changes using git
3. The old tables should still contain your original data
