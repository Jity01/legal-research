# Supabase Setup Guide

## Quick Setup

1. **Create Tables in Supabase**
   - Log into your Supabase dashboard: https://supabase.com/dashboard
   - Select your project
   - Go to the SQL Editor
   - Copy and paste the contents of `supabase_setup.sql`
   - Click "Run" to execute the SQL script

2. **Verify Tables Created**
   - Go to Table Editor in Supabase
   - You should see two tables:
     - `court_cases` - Main table for storing case information
     - `collection_progress` - Tracks collection progress

3. **Configure Row Level Security (RLS)**
   - The setup script includes basic RLS policies that allow all operations
   - For production, you may want to create more restrictive policies
   - Adjust the policies in the Supabase dashboard under Authentication > Policies

## Database Schema

### court_cases Table
Stores all court case information with the following key fields:
- `id` - Primary key (auto-increment)
- `case_name` - Name of the case (required)
- `docket_number` - Court docket number
- `citation` - Legal citation
- `court_type` - Type of court (SJC, APPEALS, etc.)
- `decision_date` - Date case was decided (required)
- `opinion_text` - Full text of the opinion
- `opinion_url` - URL to the opinion
- And more... (see `supabase_setup.sql` for full schema)

### collection_progress Table
Tracks collection progress:
- `source` - Data source name (unique)
- `last_collected_date` - Most recent case date collected
- `total_cases_collected` - Count of cases
- `status` - Collection status

## Indexes

The following indexes are created for performance:
- `idx_decision_date` - Fast queries by date
- `idx_court_type` - Fast queries by court type
- `idx_docket_number` - Fast lookups by docket number
- `idx_case_name` - Fast searches by case name

## Testing Connection

After setup, test the connection:

```python
from database import init_database, get_statistics

# Initialize connection
client = init_database()

# Get statistics
stats = get_statistics()
print(f"Total cases: {stats['total_cases']}")
```

## Troubleshooting

### "Table does not exist" error
- Make sure you ran the `supabase_setup.sql` script
- Check that you're connected to the correct Supabase project

### "Permission denied" error
- Check Row Level Security policies
- Ensure your API key has the correct permissions
- Verify the publishable key is correct in `config.py`

### Connection timeout
- Check your internet connection
- Verify the Supabase URL is correct
- Check Supabase project status in dashboard
