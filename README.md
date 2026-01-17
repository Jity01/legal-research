# Massachusetts Court Cases Collection System

This project collects and organizes all published Massachusetts court cases since 1900, including:

- Supreme Judicial Court (SJC)
- Massachusetts Appeals Court
- Trial Courts (Superior, District, Probate & Family, Housing, Juvenile)
- Federal Courts (U.S. District Court for Massachusetts, First Circuit Court of Appeals)

## Features

- **Comprehensive Collection**: Gathers cases from multiple public sources
- **Structured Storage**: Supabase (PostgreSQL) database with proper indexing for fast queries
- **Metadata Tracking**: Stores case names, docket numbers, dates, citations, and more
- **Progress Tracking**: Monitors collection progress and can resume interrupted collections
- **Date Filtering**: Collect cases from specific date ranges
- **Statistics**: View collection statistics by court type and year

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Install Playwright browsers (required for JavaScript-rendered pages):

```bash
playwright install chromium
```

See `PLAYWRIGHT_SETUP.md` for detailed setup instructions.

2. Set up Supabase database:

   - Go to your Supabase project dashboard
   - Navigate to the SQL Editor
   - Run the SQL script from `supabase_setup.sql` to create the necessary tables
   - The tables `court_cases` and `collection_progress` will be created with proper indexes

3. Configure Supabase credentials:
   - Create a `.env` file in the project root (copy from `.env.example`)
   - Add your Supabase credentials:
     ```
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_KEY=your_publishable_key_here
     ```
   - Alternatively, set them as environment variables:
     ```bash
     export SUPABASE_URL="https://your-project.supabase.co"
     export SUPABASE_KEY="your_publishable_key_here"
     ```

## Usage

### Basic Collection

Collect all cases from 1900 to present:

```bash
python main.py
```

### Custom Date Range

Collect cases from a specific year range:

```bash
python main.py --start-year 2000 --end-year 2020
```

### View Statistics

View current collection statistics:

```bash
python main.py --stats
```

## Data Sources

The system collects from:

- **Mass.gov Appellate Opinion Portal**: SJC and Appeals Court published opinions
- **Mass.gov Published Trial Court Opinions**: Trial court published decisions
- Additional sources can be added by extending the scraper classes

## Database Schema

Cases are stored in Supabase (PostgreSQL) with the following key fields:

- Case identification (name, docket number, citation)
- Court information (type, name)
- Dates (decision date, published date)
- Opinion content (text, URL, file path)
- Metadata (judges, case type, topics)
- Source information

## Project Structure

- `main.py`: Entry point for the collection system
- `case_collector.py`: Main orchestrator for collection
- `scraper_base.py`: Base class for all scrapers
- `mass_gov_scraper.py`: Scrapers for Mass.gov portals
- `database.py`: Database models and utilities
- `config.py`: Configuration settings
- `data/`: Directory for collected data (PDFs, etc.)
- `supabase_setup.sql`: SQL script to create tables in Supabase

## Notes

- **Published vs. Unpublished**: This system focuses on _published_ court opinions. Many trial court decisions are not published and would require different collection methods.
- **Historical Coverage**: Older cases (pre-2000) may require additional sources like law library archives or commercial databases.
- **Rate Limiting**: The system includes delays between requests to be respectful of server resources.
- **Resume Capability**: The system tracks progress and can resume interrupted collections.

## Future Enhancements

- Add support for federal court cases (PACER integration)
- Integrate with law library digital archives
- Add OCR capabilities for scanned historical documents
- Implement case text extraction from PDFs
- Add web interface for searching collected cases

## Legal Notice

Court opinions are generally in the public domain. However, be aware of:

- Copyright on annotations and headnotes in official reporters
- Terms of service for data sources
- Fair use considerations when republishing content
