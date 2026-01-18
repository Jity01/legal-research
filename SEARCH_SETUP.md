# Legal Case Search System Setup Guide

This guide explains how to set up and use the legal case search system.

## Architecture

The system is organized into three main modules:

- **`scraping/`**: Contains scrapers for collecting court cases (existing scrapers)
- **`strategy/`**: Contains the search and analysis logic
  - `query_parser.py`: Breaks down user queries into factors
  - `case_analyzer.py`: Analyzes cases to extract factors and holdings
  - `similarity_matcher.py`: Matches query factors to case factors
  - `citation_extractor.py`: Finds cases that cite other cases
- **`web/`**: Contains the Flask web application
  - `app.py`: Main Flask application
  - `templates/index.html`: Search interface

## Prerequisites

1. **Database Setup**: Ensure your Supabase database is set up with the base schema (`supabase_setup.sql`)

2. **Extended Schema**: Run the extended schema for case analysis:
   ```sql
   -- Run strategy/database_schema.sql in Supabase SQL editor
   ```

3. **Environment Variables**: Create a `.env` file with:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_api_key  # Optional but recommended
   ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 1: Preprocess Cases

Before you can search cases, you need to analyze all cases in your database. This extracts factors, holdings, and citations from each case.

```bash
python preprocess_cases.py
```

This will:
- Analyze all cases in the database
- Extract factors/concepts and weight them by importance to the holding
- Extract the holding and determine if it's for/against defendant
- Extract citations to other cases
- Store everything in the database

**Options**:
- `--batch-size N`: Process N cases at a time (default: 10)
- `--start-from ID`: Resume from a specific case ID
- `--stats`: Show preprocessing statistics

**Example**:
```bash
# Process all cases
python preprocess_cases.py

# Check progress
python preprocess_cases.py --stats

# Resume from case ID 1000
python preprocess_cases.py --start-from 1000
```

**Note**: This process can take a while depending on:
- Number of cases in your database
- Whether you're using OpenAI API (faster and more accurate) or fallback methods
- Your API rate limits

## Step 2: Start the Web Server

Once cases are preprocessed, start the web interface:

```bash
python web/app.py
```

Or:

```bash
cd web
python app.py
```

The server will start on `http://localhost:5000`

## Step 3: Search Cases

1. Open your browser to `http://localhost:5000`
2. Enter a legal query, for example:
   - "cases where a defendant was charged with knowing stolen motor vehicle but had lack of probable cause or lack of sufficient evidence"
3. Optionally check "Only show cases favorable to defendant" to filter results
4. Click "Search"

## How It Works

### Query Processing

1. **Query Parsing**: The system breaks down your query into:
   - A premise (the main question)
   - 3 key factors (concepts/facts/legal principles)
   - Weights for each factor (how important to the premise)
   - Query type (defendant_favor, plaintiff_favor, or neutral)

### Case Matching

1. **Factor Extraction**: Each case has been analyzed to extract:
   - Factors/concepts that influenced the decision
   - Weight of each factor to the holding (how much it mattered)
   - The holding and its direction (for/against defendant)

2. **Similarity Calculation**: The system matches:
   - Query factors → Case factors
   - Considers semantic similarity
   - Weights by importance to the holding
   - Returns top 20 most similar cases

### Display Features

- **Similarity Score**: Shows how well the case matches your query (0-100%)
- **Holding Indicator**: 
  - ✓ For Defendant (green)
  - ✗ Against Defendant (red)
  - ± Mixed (yellow)
  - ? Unclear (yellow)
- **Citing Cases**: Click to expand and see all cases that cite this case (like folder sublinks)
- **Case Metadata**: Date, court, citation, etc.

## API Endpoints

### POST /api/search

Search for cases.

**Request**:
```json
{
  "query": "your search query",
  "filter_direction": "for_defendant",  // optional
  "limit": 20  // optional, default 20
}
```

**Response**:
```json
{
  "results": [
    {
      "id": 123,
      "case_name": "Case Name",
      "similarity_score": 0.85,
      "holding_direction": "for_defendant",
      "citing_cases": [...],
      ...
    }
  ],
  "count": 20
}
```

### GET /api/case/<case_id>

Get full details of a specific case.

## Troubleshooting

### "No analyzed cases found"

Run the preprocessing script first:
```bash
python preprocess_cases.py
```

### "No OpenAI API key found"

The system will use fallback methods, but they're less accurate. For best results, add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=sk-...
```

### Cases not showing citations

Citations are extracted during preprocessing. Make sure preprocessing completed successfully and check:
```bash
python preprocess_cases.py --stats
```

### Search returns no results

1. Check that cases have been preprocessed
2. Try a broader query
3. Check the similarity threshold (currently any score > 0 is included)

## Performance Tips

1. **Use OpenAI API**: Much faster and more accurate than fallback methods
2. **Batch Processing**: Adjust `--batch-size` based on your API rate limits
3. **Resume Capability**: Use `--start-from` to resume if preprocessing is interrupted
4. **Indexing**: The database schema includes indexes for fast queries

## Future Enhancements

- Add more sophisticated semantic search using embeddings
- Cache query results
- Add pagination for results
- Export search results
- Advanced filters (date range, court type, etc.)
