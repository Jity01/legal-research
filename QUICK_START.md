# Quick Start Guide

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

## Initial Setup

1. **Set up Supabase database:**
   - Go to your Supabase project dashboard
   - Navigate to SQL Editor
   - Run the SQL script from `supabase_setup.sql` to create tables
   - See `SUPABASE_SETUP.md` for detailed instructions

2. **Inspect data sources** (optional but recommended):
```bash
python inspect_sources.py
```
This will help you understand the structure of the Mass.gov pages and can guide scraper improvements.

3. **Test database connection:**
```python
python -c "from database import init_database, get_statistics; init_database(); stats = get_statistics(); print(f'Database connected. Total cases: {stats[\"total_cases\"]}')"
```

## Running the Collection

### Basic Collection
Start collecting cases from all sources:
```bash
python main.py
```

### Custom Date Range
Collect cases from a specific period:
```bash
python main.py --start-year 2000 --end-year 2020
```

### View Statistics
Check what's been collected:
```bash
python main.py --stats
```

## Next Steps

1. **Inspect the actual page structures:**
   - Run `inspect_sources.py` to see how Mass.gov pages are structured
   - This will help refine the scrapers in `mass_gov_scraper.py`

2. **Enhance the scrapers:**
   - The current scrapers are templates that need to be adapted to the actual page structure
   - Use the inspection results to implement proper parsing

3. **Add additional sources:**
   - Federal court scrapers
   - Historical source integrations
   - Commercial database APIs (if available)

4. **Extract case text:**
   - Add PDF parsing for opinion text
   - Implement OCR for scanned documents
   - Store full text in the database

## Database Access

The database is stored in Supabase. You can query it using the database functions:

```python
from database import get_statistics, get_cases_by_court

# Get statistics
stats = get_statistics()
print(f"Total cases: {stats['total_cases']}")
print(f"By court: {stats['by_court']}")

# Get cases by court type
sjc_cases = get_cases_by_court('SJC', limit=100)
print(f"SJC cases: {len(sjc_cases)}")
```

Or query directly in Supabase dashboard using SQL:
```sql
SELECT COUNT(*) FROM court_cases;
SELECT * FROM court_cases WHERE court_type = 'SJC' LIMIT 10;
```

## Troubleshooting

- **No cases found**: The scrapers may need to be updated based on actual page structure. Run `inspect_sources.py` first.
- **Connection errors**: Check your internet connection and verify the URLs in `config.py` are still valid.
- **Database errors**: 
  - Ensure you've run the `supabase_setup.sql` script
  - Check that your Supabase URL and key are correct in `config.py`
  - Verify Row Level Security policies allow your operations

## Important Notes

- The current implementation provides a framework that needs to be adapted to actual page structures
- Mass.gov pages may use JavaScript rendering, which would require Selenium or similar tools
- Some sources may require authentication or have rate limits
- Historical cases (pre-2000) may require different collection methods
