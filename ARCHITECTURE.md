# Legal Case Search System - Architecture

## Overview

This system implements a sophisticated legal case search engine that matches user queries to court cases based on semantic similarity of legal factors and concepts.

## Directory Structure

```
legal_search/
├── scraping/          # Scrapers for collecting court cases
│   └── __init__.py
├── strategy/          # Core search and analysis logic
│   ├── __init__.py
│   ├── query_parser.py          # Breaks queries into factors
│   ├── case_analyzer.py         # Analyzes cases to extract factors
│   ├── similarity_matcher.py   # Matches query to cases
│   ├── citation_extractor.py    # Finds citing cases
│   └── database_schema.sql      # Extended database schema
├── web/                # Web interface
│   ├── __init__.py
│   ├── app.py          # Flask application
│   ├── templates/
│   │   └── index.html  # Search interface
│   └── static/         # Static assets (CSS, JS, etc.)
├── preprocess_cases.py # Script to analyze all cases
├── start_search_server.py  # Quick start script
└── [existing files]    # Original scraping infrastructure
```

## Core Components

### 1. Query Parser (`strategy/query_parser.py`)

**Purpose**: Breaks down natural language queries into structured factors.

**Process**:
1. Takes a user query (e.g., "cases where defendant was charged with knowing stolen motor vehicle but had lack of probable cause")
2. Extracts:
   - **Premise**: The main question/issue
   - **3 Factors**: Key concepts/facts/legal principles
   - **Weights**: Importance of each factor (0.0-1.0, sum to 1.0)
   - **Query Type**: Whether looking for defendant_favor, plaintiff_favor, or neutral

**Implementation**:
- Primary: Uses OpenAI GPT-4o-mini for semantic understanding
- Fallback: Heuristic-based extraction if no API key

### 2. Case Analyzer (`strategy/case_analyzer.py`)

**Purpose**: Analyzes court opinions to extract factors, holdings, and citations.

**Process**:
1. Takes a court case with opinion text
2. Extracts:
   - **Factors**: Concepts/facts/legal principles that influenced the decision
   - **Factor Weights**: How much each factor mattered to the holding (0.0-1.0)
   - **Holding**: The court's final decision/rule
   - **Holding Direction**: for_defendant, against_defendant, mixed, or unclear
   - **Citations**: References to other cases

**Implementation**:
- Primary: Uses OpenAI GPT-4o-mini for comprehensive analysis
- Fallback: Regex and keyword-based extraction

### 3. Similarity Matcher (`strategy/similarity_matcher.py`)

**Purpose**: Finds cases with factors similar to query factors.

**Process**:
1. Gets query factors (from QueryParser)
2. Gets all case factors (from database)
3. Calculates similarity between:
   - Query factors ↔ Case factors
   - Weighted by importance to holding
4. Returns top N most similar cases

**Similarity Calculation**:
- Primary: LLM-based semantic similarity
- Fallback: Jaccard similarity (word overlap) weighted by factor importance

**Formula** (simplified):
```
similarity = Σ (query_factor_weight × best_case_factor_match × case_factor_weight)
```

### 4. Citation Extractor (`strategy/citation_extractor.py`)

**Purpose**: Finds cases that cite a given case.

**Process**:
1. Searches `case_citations` table for cases citing the target case
2. Returns list of citing cases with citation context

## Database Schema Extensions

### New Tables

1. **`case_factors`**: Stores extracted factors from each case
   - `case_id`, `factor_text`, `factor_type`, `weight_to_holding`

2. **`case_holdings`**: Stores holdings and their direction
   - `case_id`, `holding_text`, `holding_direction`, `confidence`

3. **`case_citations`**: Stores citations between cases
   - `citing_case_id`, `cited_case_id`, `citation_text`, `citation_context`

4. **`case_analysis_metadata`**: Tracks analysis status
   - `case_id`, `is_analyzed`, `analyzed_at`, `error_message`

## Workflow

### Preprocessing Phase

1. Run `preprocess_cases.py`:
   ```bash
   python preprocess_cases.py
   ```

2. For each case:
   - Analyze opinion text → extract factors, holding, citations
   - Store in database tables
   - Mark as analyzed

### Search Phase

1. User enters query in web interface
2. Query Parser breaks down query into factors
3. Similarity Matcher finds matching cases
4. Citation Extractor finds cases citing each result
5. Results displayed with:
   - Similarity score
   - Holding direction indicator
   - Citing cases (expandable)

## Key Design Decisions

### Factor-Based Matching

Instead of simple keyword matching, the system:
- Extracts **semantic factors** from both queries and cases
- Weights factors by **importance to the holding**
- Matches based on **conceptual similarity**, not just text

This allows finding cases that address the same legal issues even with different wording.

### Weighted Importance

Factors are weighted by:
- **Query side**: How important each factor is to answering the premise
- **Case side**: How much each factor influenced the final holding

This ensures that:
- Cases decided on factors important to the query rank higher
- Query factors that are central to the question get more weight

### Holding Direction

Each case is classified as:
- **for_defendant**: Ruling favors defendant
- **against_defendant**: Ruling against defendant
- **mixed**: Partial victory for both
- **unclear**: Cannot determine

This allows filtering and visual indication of case outcomes.

## Performance Considerations

1. **Preprocessing**: Done once, stored in database
2. **Indexing**: Database indexes on `case_id`, `weight_to_holding`, etc.
3. **Caching**: Query results could be cached (future enhancement)
4. **Batch Processing**: Preprocessing supports batching and resuming

## Future Enhancements

1. **Embeddings**: Use vector embeddings for better semantic matching
2. **Caching**: Cache query results and factor extractions
3. **Pagination**: Support for large result sets
4. **Advanced Filters**: Date range, court type, etc.
5. **Export**: Export search results to PDF/CSV
6. **Analytics**: Track search patterns and popular queries
