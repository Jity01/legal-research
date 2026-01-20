"""
Similarity matcher that finds cases with factors similar to query factors.
Matches based on semantic similarity.
"""

import logging
from typing import Dict, List, Optional, Tuple
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase_client

# Import QueryParser - use relative import if in same package, absolute otherwise
try:
    from .query_parser import QueryParser
except ImportError:
    from strategy.query_parser import QueryParser

logger = logging.getLogger(__name__)

# Rate limiter removed - no retries, fail fast


class SimilarityMatcher:
    """Matches query factors to case factors using semantic similarity"""

    def __init__(
        self,
        use_llm: bool = True,
        max_workers: int = 5,
        cases_per_batch: int = 10,
        db_batch_size: int = 50,
    ):
        # Default to LLM if API key is available, otherwise use text matching
        self.use_llm = use_llm and bool(os.getenv("OPENAI_API_KEY"))
        self.query_parser = QueryParser()
        self.max_workers = max_workers
        self.cases_per_batch = (
            cases_per_batch  # Number of cases to process per LLM call
        )
        self.db_batch_size = db_batch_size  # Number of cases to fetch from DB at once
        # Cache for parsed queries (simple in-memory cache)
        self._query_cache = {}

    def find_similar_cases(
        self,
        query: str,
        limit: Optional[int] = None,
        filter_direction: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find cases similar to the query using optimized two-stage search.

        Args:
            query: User's search query
            limit: Maximum number of cases to return (None = return all matches)
            filter_direction: If 'for_defendant', only return cases favorable to defendant

        Returns:
            List of case dictionaries with similarity scores
        """
        start_time = time.time()
        # Keep limit as-is (None means search all, otherwise use provided limit)
        # Don't default to 20 - let caller decide

        # Parse the query (with caching)
        query_hash = hash(query.lower().strip())
        if query_hash in self._query_cache:
            parsed_query = self._query_cache[query_hash]
            logger.debug("Using cached query parse")
        else:
            parsed_query = self.query_parser.parse_query(query)
            # Cache only if reasonable size (avoid memory bloat)
            if len(self._query_cache) < 100:
                self._query_cache[query_hash] = parsed_query

        query_factors = parsed_query.get("factors", [])
        query_type = parsed_query.get("query_type", "neutral")

        if not query_factors:
            logger.warning("No factors extracted from query")
            return []

        client = get_supabase_client()

        # STAGE 1: Fast text-based pre-filtering using PostgreSQL full-text search
        # This dramatically reduces the number of cases we need to check with LLM
        logger.debug("Stage 1: Fast text-based pre-filtering...")
        prefilter_start = time.time()

        # Extract keywords from query for text search
        query_keywords = self._extract_keywords_for_search(query, query_factors)

        # Use PostgreSQL full-text search to find candidate cases
        # If limit is None, search ALL cases. Otherwise, still get a large pool to find best matches
        if limit is None:
            # No limit - search ALL analyzed cases
            candidate_limit = None
            logger.info("Searching ALL cases in database (no limit specified)")
        else:
            # With limit, still get a large pool (10x limit) to ensure we find the best matches
            candidate_limit = max(limit * 10, 500)
            logger.info(
                f"Searching up to {candidate_limit} candidate cases to find best {limit} matches"
            )

        candidate_case_ids = self._prefilter_cases(
            client, query_keywords, filter_direction, candidate_limit
        )

        logger.info(
            f"Found {len(candidate_case_ids)} candidate cases to process with LLM"
        )

        if not candidate_case_ids:
            if candidate_limit is None:
                # If searching all cases and still got nothing, there are no analyzed cases
                logger.warning("No analyzed cases found in database")
            else:
                logger.warning("No candidate cases found in pre-filtering")
            return []

        logger.debug(
            f"Pre-filtering found {len(candidate_case_ids)} candidates in {time.time() - prefilter_start:.2f}s"
        )

        # Get factors and holdings in parallel (faster)
        # Use batch queries to reduce round trips and handle Supabase .in_() limits
        import concurrent.futures
        import httpx

        def execute_with_retry(query_func, max_retries=3, initial_delay=1):
            """Execute a database query with retry logic for connection errors"""
            for attempt in range(max_retries):
                try:
                    return query_func()
                except (
                    httpx.RemoteProtocolError,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                ) as e:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2**attempt)  # Exponential backoff
                        logger.warning(
                            f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Database connection failed after {max_retries} attempts: {e}"
                        )
                        raise
                except Exception as e:
                    # Don't retry on non-connection errors
                    raise

        def fetch_factors():
            # Supabase .in_() has limits (~100-200 items), so batch the queries
            all_factors_data = []
            batch_size = 100  # Safe batch size for .in_() queries

            for i in range(0, len(candidate_case_ids), batch_size):
                batch_ids = candidate_case_ids[i : i + batch_size]

                def execute_batch():
                    return (
                        client.table("case_factors")
                        .select("case_id, factor_text")
                        .in_("case_id", batch_ids)
                        .execute()
                    )

                batch_result = execute_with_retry(execute_batch)
                if batch_result.data:
                    all_factors_data.extend(batch_result.data)

            # Create a mock response object with .data attribute
            class MockResponse:
                def __init__(self, data):
                    self.data = data

            return MockResponse(all_factors_data)

        def fetch_holdings():
            # Batch holdings fetch as well
            all_holdings_data = []
            batch_size = 100

            for i in range(0, len(candidate_case_ids), batch_size):
                batch_ids = candidate_case_ids[i : i + batch_size]

                def execute_batch():
                    return (
                        client.table("case_holdings")
                        .select("case_id, holding_direction")
                        .in_("case_id", batch_ids)
                        .execute()
                    )

                batch_result = execute_with_retry(execute_batch)
                if batch_result.data:
                    all_holdings_data.extend(batch_result.data)

            class MockResponse:
                def __init__(self, data):
                    self.data = data

            return MockResponse(all_holdings_data)

        # Fetch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            factors_future = executor.submit(fetch_factors)
            holdings_future = executor.submit(fetch_holdings)

            all_factors = factors_future.result()
            holdings = holdings_future.result()

        # Initialize holding_map with all candidate cases (default to "unclear" if no holding)
        holding_map = {case_id: "unclear" for case_id in candidate_case_ids}
        for h in holdings.data:
            holding_map[h["case_id"]] = h["holding_direction"]

        # Initialize case_factors_map with ALL candidate cases (including those without factors)
        case_factors_map = {case_id: [] for case_id in candidate_case_ids}

        # Group factors by case
        for factor in all_factors.data:
            case_id = factor["case_id"]
            if case_id in case_factors_map:
                case_factors_map[case_id].append({"text": factor["factor_text"]})

        # STAGE 2: Batch fetch case details and process in parallel
        logger.debug(f"Stage 2: Processing {len(case_factors_map)} cases in batches...")
        similarity_start = time.time()

        # Get case details in batches from database
        all_case_ids = list(case_factors_map.keys())
        case_details_map = {}

        # Fetch case details in batches of db_batch_size
        for i in range(0, len(all_case_ids), self.db_batch_size):
            batch_ids = all_case_ids[i : i + self.db_batch_size]
            try:
                cases = (
                    client.table("court_cases")
                    .select("id, case_name, court_name, decision_date, citation")
                    .in_("id", batch_ids)
                    .execute()
                )
                for case in cases.data:
                    case_details_map[case["id"]] = case
            except Exception as e:
                logger.debug(f"Error fetching case details for batch: {e}")
                # Continue with empty details for missing cases

        scored_cases = self._calculate_similarities_parallel(
            query_factors,
            case_factors_map,
            holding_map,
            case_details_map,
            filter_direction,
        )

        logger.debug(
            f"Similarity calculation took {time.time() - similarity_start:.2f}s"
        )

        # Sort by similarity score (descending)
        scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Apply limit only if specified
        if limit is not None and len(scored_cases) > limit:
            scored_cases = scored_cases[:limit]

        # Get full case details for matches
        top_case_ids = [c["case_id"] for c in scored_cases]

        if not top_case_ids:
            return []

        def execute_cases_query():
            return (
                client.table("court_cases")
                .select("*")
                .in_("id", top_case_ids)
                .execute()
            )

        cases = execute_with_retry(execute_cases_query)

        # Create a map for quick lookup
        case_map = {c["id"]: c for c in cases.data}

        # Combine with similarity scores
        results = []
        for scored_case in scored_cases:
            case_id = scored_case["case_id"]
            if case_id in case_map:
                case_data = case_map[case_id].copy()
                case_data["similarity_score"] = scored_case["similarity_score"]
                case_data["holding_direction"] = scored_case["holding_direction"]
                # Include justification if available
                if "justification" in scored_case:
                    case_data["justification"] = scored_case["justification"]
                results.append(case_data)

        logger.info(
            f"Search completed in {time.time() - start_time:.2f}s, returned {len(results)} results"
        )
        return results

    def _extract_keywords_for_search(
        self, query: str, query_factors: List[Dict]
    ) -> str:
        """Extract important keywords from query and factors for text search"""
        # Combine query and factor texts
        all_text = query.lower()
        for factor in query_factors:
            all_text += " " + factor.get("text", "").lower()

        # Extract significant words (3+ chars, not common stop words)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
        }
        words = [w for w in all_text.split() if len(w) >= 3 and w not in stop_words]

        # Return top 10 most frequent words
        from collections import Counter

        word_counts = Counter(words)
        top_words = [word for word, count in word_counts.most_common(10)]
        return " ".join(top_words)

    def _prefilter_cases(
        self,
        client,
        query_keywords: str,
        filter_direction: Optional[str],
        candidate_limit: Optional[int],
    ) -> List[int]:
        """
        Use PostgreSQL full-text search to quickly find candidate cases.
        This dramatically reduces the number of cases we need to check with expensive LLM calls.
        """
        # Build a query that searches factor_text using full-text search
        # PostgreSQL has a GIN index on to_tsvector('english', factor_text)

        # Split keywords and create a tsquery
        keywords_list = query_keywords.split()
        if not keywords_list:
            # Fallback: get all analyzed cases if no keywords
            query = (
                client.table("case_analysis_metadata")
                .select("case_id")
                .eq("is_analyzed", True)
            )
            if candidate_limit is not None:
                query = query.limit(candidate_limit)
            analyzed = query.execute()
            return [c["case_id"] for c in analyzed.data] if analyzed.data else []

        # Use plainto_tsquery for better matching
        # This searches for cases where factors contain these keywords
        tsquery = " & ".join(keywords_list[:5])  # Limit to 5 keywords for performance

        # Query using full-text search
        # We'll use a raw SQL query for better performance with tsvector
        try:
            # Get case IDs where factors match the keywords
            # Using the existing GIN index on factor_text
            rpc_params = {"search_query": tsquery, "direction_filter": filter_direction}
            if candidate_limit is not None:
                rpc_params["limit_count"] = candidate_limit
            result = client.rpc("search_cases_by_factors", rpc_params).execute()

            if result.data:
                return [r["case_id"] for r in result.data]
        except Exception as e:
            logger.debug(f"RPC function not available, using fallback: {e}")

        # Fallback: Use optimized text search (much faster than Python)
        # Build a more efficient query using Supabase's query builder
        keyword_set = set(keywords_list)

        # Use a single query with OR conditions for all keywords
        # This is much faster than fetching all factors and filtering in Python
        try:
            # Get factors that contain any of the keywords using ILIKE
            # Supabase query builder doesn't support dynamic OR easily, so we'll use a simpler approach
            # Get factors matching the first (most important) keyword, then filter in Python
            primary_keyword = list(keyword_set)[0] if keyword_set else None

            if primary_keyword:
                try:
                    # Supabase ILIKE requires the pattern without % signs in the method call
                    # The % are added automatically by Supabase
                    def execute_factors_query():
                        query = (
                            client.table("case_factors")
                            .select("case_id, factor_text")
                            .ilike("factor_text", f"%{primary_keyword}%")
                        )
                        # Only apply limit if specified - otherwise get ALL factors
                        if candidate_limit is not None:
                            # If we have a limit, we still want to check a large pool of factors
                            # Use a much larger limit to ensure we don't miss matches
                            query = query.limit(max(candidate_limit * 20, 10000))
                        return query.execute()

                    all_factors = execute_with_retry(execute_factors_query)
                except Exception as query_error:
                    logger.debug(
                        f"ILIKE query failed: {query_error}, using simple text search"
                    )
                    # Fallback: get all factors and filter in Python (slower but works)
                    # This is more reliable than trying to fix the ILIKE syntax
                    query = client.table("case_factors").select("case_id, factor_text")
                    # Only apply limit if specified
                    if candidate_limit is not None:
                        query = query.limit(max(candidate_limit * 20, 10000))
                    all_factors = query.execute()
                    # Filter in Python
                    if all_factors.data:
                        filtered_factors = [
                            f
                            for f in all_factors.data
                            if primary_keyword.lower()
                            in f.get("factor_text", "").lower()
                        ]
                        all_factors.data = filtered_factors
            else:
                # No primary keyword - if limit is None, get ALL analyzed cases
                if candidate_limit is None:
                    logger.info(
                        "No keywords extracted, falling back to ALL analyzed cases"
                    )
                    query = (
                        client.table("case_analysis_metadata")
                        .select("case_id")
                        .eq("is_analyzed", True)
                    )
                    analyzed = query.execute()
                    return (
                        [c["case_id"] for c in analyzed.data] if analyzed.data else []
                    )

                # Return empty result structure
                class EmptyResult:
                    data = []

                all_factors = EmptyResult()

            if not all_factors.data:
                # No factors found - if limit is None, get ALL analyzed cases
                if candidate_limit is None:
                    logger.info(
                        "No factors matched keywords, falling back to ALL analyzed cases"
                    )
                    query = (
                        client.table("case_analysis_metadata")
                        .select("case_id")
                        .eq("is_analyzed", True)
                    )
                    analyzed = query.execute()
                    return (
                        [c["case_id"] for c in analyzed.data] if analyzed.data else []
                    )
                return []

            # Score cases by keyword matches (faster scoring)
            case_scores = {}
            keyword_lower = [kw.lower() for kw in keyword_set]

            for factor in all_factors.data:
                case_id = factor["case_id"]
                factor_text = factor["factor_text"].lower()

                # Count keyword matches (optimized)
                matches = sum(1 for kw in keyword_lower if kw in factor_text)
                if matches > 0:
                    case_scores[case_id] = case_scores.get(case_id, 0) + matches

            # Sort by score and return top candidates
            sorted_cases = sorted(case_scores.items(), key=lambda x: x[1], reverse=True)

            # If candidate_limit is None, we want ALL analyzed cases, not just text matches
            # Text search is only for ranking when we have a limit
            if candidate_limit is None:
                # Get ALL analyzed cases regardless of text matches
                logger.info("Getting ALL analyzed cases (limit=None)")
                query = (
                    client.table("case_analysis_metadata")
                    .select("case_id")
                    .eq("is_analyzed", True)
                )
                analyzed = query.execute()
                candidate_ids = (
                    [c["case_id"] for c in analyzed.data] if analyzed.data else []
                )
            elif sorted_cases:
                # We have a limit and found text matches - use them
                candidate_ids = [
                    case_id for case_id, score in sorted_cases[:candidate_limit]
                ]
            else:
                # No text matches found and we have a limit - return empty
                candidate_ids = []
        except Exception as e:
            logger.debug(f"Optimized query failed, using simple fallback: {e}")
            # Ultra-simple fallback: just get all analyzed cases
            query = (
                client.table("case_analysis_metadata")
                .select("case_id")
                .eq("is_analyzed", True)
                .order("analyzed_at", desc=True)
            )
            if candidate_limit is not None:
                query = query.limit(candidate_limit)
            analyzed = query.execute()
            candidate_ids = (
                [c["case_id"] for c in analyzed.data] if analyzed.data else []
            )

        # Apply direction filter if needed
        if filter_direction and candidate_ids:
            holdings = (
                client.table("case_holdings")
                .select("case_id")
                .in_("case_id", candidate_ids)
                .eq("holding_direction", filter_direction)
                .execute()
            )
            candidate_ids = [h["case_id"] for h in holdings.data]

        return candidate_ids

    def _calculate_similarities_parallel(
        self,
        query_factors: List[Dict],
        case_factors_map: Dict[int, List[Dict]],
        holding_map: Dict[int, str],
        case_details_map: Dict[int, Dict],
        filter_direction: Optional[str],
    ) -> List[Dict]:
        """Calculate similarities in parallel by batching cases"""
        import threading as _threading

        scored_cases = []
        lock = _threading.Lock()

        # Group cases into batches
        all_case_ids = list(case_factors_map.keys())

        # Apply direction filter before batching
        if filter_direction == "for_defendant":
            all_case_ids = [
                case_id
                for case_id in all_case_ids
                if holding_map.get(case_id) == "for_defendant"
            ]

        # Create batches of cases_per_batch
        case_batches = []
        for i in range(0, len(all_case_ids), self.cases_per_batch):
            batch_ids = all_case_ids[i : i + self.cases_per_batch]
            batch_data = []
            for case_id in batch_ids:
                if case_id in case_factors_map:
                    batch_data.append(
                        {
                            "case_id": case_id,
                            "case_factors": case_factors_map[case_id],
                            "case_details": case_details_map.get(case_id, {}),
                            "holding_direction": holding_map.get(case_id, "unclear"),
                        }
                    )
            if batch_data:
                case_batches.append(batch_data)

        total_cases_to_process = sum(len(batch) for batch in case_batches)
        logger.info(
            f"Processing {len(case_batches)} batches ({total_cases_to_process} total cases) with {self.cases_per_batch} cases per batch"
        )

        def calculate_batch(batch_data):
            """Calculate similarity for a batch of cases"""
            try:
                if self.use_llm:
                    return self._calculate_similarity_batch_llm(
                        query_factors, batch_data
                    )
                else:
                    # Fallback: process individually with text matching
                    results = []
                    for case_data in batch_data:
                        score = self._calculate_similarity_text(
                            query_factors, case_data["case_factors"]
                        )
                        if score > 0:
                            results.append(
                                {
                                    "case_id": case_data["case_id"],
                                    "similarity_score": score,
                                    "holding_direction": case_data["holding_direction"],
                                }
                            )
                    return results
            except Exception as e:
                logger.debug(f"Error calculating similarity for batch: {e}")
                return []

        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(calculate_batch, batch): batch for batch in case_batches
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    if batch_results:
                        with lock:
                            scored_cases.extend(batch_results)
                except Exception as e:
                    logger.debug(f"Error in batch similarity calculation: {e}")

        return scored_cases

    def _calculate_similarity(
        self, query_factors: List[Dict], case_factors: List[Dict], use_llm: bool = False
    ) -> float:
        """
        Calculate similarity between query factors and case factors.

        Returns a score from 0.0 to 1.0.
        """
        if use_llm:
            return self._calculate_similarity_llm(query_factors, case_factors)
        else:
            return self._calculate_similarity_text(query_factors, case_factors)

    def _calculate_similarity_batch_llm(
        self, query_factors: List[Dict], batch_data: List[Dict]
    ) -> List[Dict]:
        """Use LLM to calculate semantic similarity for a batch of cases"""
        try:
            from openai import OpenAI
            import json

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Combine all query factors into one string
            query_texts = [f["text"] for f in query_factors]
            combined_query = "\n\n".join(query_texts)

            # Format cases clearly with separators
            cases_text = ""
            for idx, case_data in enumerate(batch_data, 1):
                case_id = case_data["case_id"]
                case_details = case_data.get("case_details", {})
                case_name = case_details.get("case_name", f"Case {case_id}")
                case_citation = case_details.get("citation", "")
                case_factors = case_data["case_factors"]

                case_factors_text = "\n".join([f["text"] for f in case_factors])

                cases_text += f"""
=== CASE {idx} ===
CASE ID: {case_id}
CASE NAME: {case_name}
CITATION: {case_citation}

LEGAL PRINCIPLES FROM THIS CASE:
{case_factors_text}

---
"""

            prompt = f"""You are evaluating whether these cases match the search query based on the legal principles mentioned in the query.

Legal Principles from the Search Query:
{combined_query}

CASES TO EVALUATE:
{cases_text}

CRITICAL INSTRUCTIONS:
- Evaluate EACH case separately - do NOT confuse or mix up cases
- Each case is clearly marked with "=== CASE X ===" and has a unique CASE ID
- Pay close attention to the CASE ID and CASE NAME to keep cases distinct
- For each case, determine if it matches the search query based on the legal principles

CRITICAL SCORING INSTRUCTIONS - SHOW YOUR SELECTIVITY IN THE NUMBERS:
- Be EXTREMELY SELECTIVE - your selectivity must be reflected in the actual score you assign
- If the legal principles are NOT closely related or are fundamentally different: give a VERY LOW score (0.00-0.05)
- If the legal principles are somewhat related but not the same: give a LOW score (0.05-0.20)
- If the legal principles are closely related or very closely related: give a MODERATE score (0.20-0.50)
- If the legal principles are the same or nearly identical: give a HIGH score (0.50-1.0)
- DO NOT give scores like 0.10 or 0.15 to fundamentally different cases - if legal principles are different, give scores like 0.01, 0.02, or 0.05
- Most cases should get VERY LOW scores (0.00-0.05) because most cases won't be closely related
- Your selectivity level MUST be visible in the score - if legal principles are fundamentally different, the score should be VERY LOW (0.01-0.05), not 0.10

Return a JSON object with:
- "case_scores": an array of objects, one for each case, in the same order as presented above
  Each object should have:
    - "case_id": the integer case ID (must match exactly from the case above)
    - "similarity_score": a float between 0.0 and 1.0 that REFLECTS your selectivity level
    - "justification": a brief explanation (2-3 sentences) of why you assigned this score, explaining how the legal principles from the case relate (or don't relate) to the search query. Write directly about the search query - do not refer to "the user", "the lawyer", or any person in third person.

Example format:
{{
  "case_scores": [
    {{"case_id": 123, "similarity_score": 0.85, "justification": "This case directly addresses the same legal principle about asylum eligibility based on past persecution, where the court found that the applicant demonstrated a well-founded fear of future persecution based on the same type of harm."}},
    {{"case_id": 456, "similarity_score": 0.02, "justification": "This case involves completely different legal principles related to criminal procedure and evidence, with no overlap to the asylum-related legal principles mentioned in the search query."}},
    ...
  ]
}}

IMPORTANT: Return scores for ALL cases in the exact order they were presented. Do NOT skip any cases."""

            # Make request without retries - fail fast
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a legal research assistant matching cases to search queries. Be EXTREMELY selective - your selectivity must be visible in the scores you assign. If legal principles are fundamentally different, give VERY LOW scores (0.00-0.05). If they're somewhat related, give LOW scores (0.05-0.20). Only give high scores (0.50+) for closely related legal principles. Show your strict selectivity in the numbers - unrelated cases should get scores like 0.01-0.05, not 0.10. For each case, provide a clear justification (2-3 sentences) explaining your reasoning. Write justifications directly about the search query - do not refer to 'the user', 'the lawyer', or any person in third person. Return only valid JSON. Pay close attention to case IDs to keep cases distinct.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)
                case_scores = result.get("case_scores", [])

                # Convert to our format and add holding direction
                results = []
                case_id_to_data = {
                    case_data["case_id"]: case_data for case_data in batch_data
                }

                # Track the 19 new cases (IDs 537-555) for logging
                NEW_CASE_IDS = set(range(537, 556))

                for score_data in case_scores:
                    case_id = score_data.get("case_id")
                    if case_id and case_id in case_id_to_data:
                        case_data = case_id_to_data[case_id]
                        similarity_score = float(
                            score_data.get("similarity_score", 0.0)
                        )
                        justification = score_data.get(
                            "justification", "No justification provided"
                        )

                        # Log justification for the 19 new cases
                        if case_id in NEW_CASE_IDS:
                            case_name = case_data.get("case_details", {}).get(
                                "case_name", f"Case {case_id}"
                            )
                            logger.info(
                                f"\n{'='*80}\n"
                                f"LLM JUDGE OPINION - Case ID: {case_id}\n"
                                f"Case Name: {case_name}\n"
                                f"Similarity Score: {similarity_score:.3f}\n"
                                f"Justification:\n{justification}\n"
                                f"{'='*80}\n"
                            )

                        if similarity_score > 0:
                            results.append(
                                {
                                    "case_id": case_id,
                                    "similarity_score": similarity_score,
                                    "holding_direction": case_data["holding_direction"],
                                    "justification": justification,
                                }
                            )

                return results

            except Exception as api_error:
                error_str = str(api_error).lower()
                # Check if it's a rate limit or quota error - fall back to text matching
                if (
                    "429" in error_str
                    or "rate limit" in error_str
                    or "quota" in error_str
                ):
                    logger.warning(
                        f"Rate limit hit in batch processing, using text matching fallback: {error_str}"
                    )
                    # Fallback: process individually with text matching
                    results = []
                    for case_data in batch_data:
                        score = self._calculate_similarity_text(
                            query_factors, case_data["case_factors"]
                        )
                        if score > 0:
                            results.append(
                                {
                                    "case_id": case_data["case_id"],
                                    "similarity_score": score,
                                    "holding_direction": case_data["holding_direction"],
                                }
                            )
                    return results
                else:
                    # Non-rate-limit error, re-raise
                    raise

        except Exception as e:
            logger.debug(f"Error calculating batch similarity with LLM: {e}")
            # Fall back to text matching
            results = []
            for case_data in batch_data:
                score = self._calculate_similarity_text(
                    query_factors, case_data["case_factors"]
                )
                if score > 0:
                    results.append(
                        {
                            "case_id": case_data["case_id"],
                            "similarity_score": score,
                            "holding_direction": case_data["holding_direction"],
                        }
                    )
            return results

    def _calculate_similarity_llm(
        self, query_factors: List[Dict], case_factors: List[Dict]
    ) -> float:
        """Use LLM to calculate semantic similarity with rate limit handling"""
        try:
            from openai import OpenAI
            import time

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Combine all query factors into one string
            query_texts = [f["text"] for f in query_factors]
            combined_query = "\n\n".join(query_texts)

            # Combine all case factors into one string
            case_texts = [f["text"] for f in case_factors]
            combined_case = "\n\n".join(case_texts)

            prompt = f"""You are evaluating whether a lawyer conducting legal research would be interested in this case based on the legal principles they are researching.

Legal Principles the Lawyer is Researching:
{combined_query}

Legal Principles from the Case:
{combined_case}

Based on the different legal principles that appear in both the lawyer's research interests and this case, determine if this case would be relevant and useful for the lawyer's research.

CRITICAL SCORING INSTRUCTIONS - SHOW YOUR SELECTIVITY IN THE NUMBERS:
- Be EXTREMELY SELECTIVE - your selectivity must be reflected in the actual score you assign
- If the legal principles are NOT closely related or are fundamentally different: give a VERY LOW score (0.00-0.05)
- If the legal principles are somewhat related but not the same: give a LOW score (0.05-0.20)
- If the legal principles are closely related or very closely related: give a MODERATE score (0.20-0.50)
- If the legal principles are the same or nearly identical: give a HIGH score (0.50-1.0)
- DO NOT give scores like 0.10 or 0.15 to fundamentally different cases - if legal principles are different, give scores like 0.01, 0.02, or 0.05
- Most cases should get VERY LOW scores (0.00-0.05) because most cases won't be closely related
- Your selectivity level MUST be visible in the score - if legal principles are fundamentally different, the score should be VERY LOW (0.01-0.05), not 0.10

Return a JSON object with:
- "similarity_score": a float between 0.0 and 1.0 that REFLECTS your selectivity level

Example: {{"similarity_score": 0.85}}"""

            # Make request without retries - fail fast
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a legal research assistant helping a lawyer find relevant cases. Be EXTREMELY selective - your selectivity must be visible in the scores you assign. If legal principles are fundamentally different, give VERY LOW scores (0.00-0.05). If they're somewhat related, give LOW scores (0.05-0.20). Only give high scores (0.50+) for closely related legal principles. Show your strict selectivity in the numbers - unrelated cases should get scores like 0.01-0.05, not 0.10. Return only valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )

                import json

                result = json.loads(response.choices[0].message.content)
                similarity_score = float(result.get("similarity_score", 0.0))

                return similarity_score

            except Exception as api_error:
                error_str = str(api_error).lower()
                # Check if it's a rate limit or quota error - fall back immediately
                if (
                    "429" in error_str
                    or "rate limit" in error_str
                    or "quota" in error_str
                ):
                    logger.warning(
                        f"Rate limit hit, using text matching fallback immediately: {error_str}"
                    )
                    return self._calculate_similarity_text(query_factors, case_factors)
                else:
                    # Non-rate-limit error, re-raise
                    raise

        except Exception as e:
            logger.debug(f"Error calculating similarity with LLM: {e}")
            # Fall back to text matching
            return self._calculate_similarity_text(query_factors, case_factors)

    def _calculate_similarity_text(
        self, query_factors: List[Dict], case_factors: List[Dict]
    ) -> float:
        """Calculate similarity using text matching"""
        if not query_factors or not case_factors:
            return 0.0

        total_score = 0.0
        match_count = 0

        for query_factor in query_factors:
            query_text = query_factor.get("text", "").lower()

            if not query_text:
                continue

            # Find best matching case factor
            best_match_score = 0.0

            for case_factor in case_factors:
                case_text = case_factor.get("text", "").lower()

                if not case_text:
                    continue

                # Simple word overlap score (Jaccard similarity)
                query_words = set(query_text.split())
                case_words = set(case_text.split())

                if query_words and case_words:
                    overlap = len(query_words & case_words)
                    union = len(query_words | case_words)
                    jaccard = overlap / union if union > 0 else 0
                    best_match_score = max(best_match_score, jaccard)

            if best_match_score > 0:
                total_score += best_match_score
                match_count += 1

        # Average similarity score
        return total_score / match_count if match_count > 0 else 0.0
