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

# Suppress verbose HTTP logs from httpx and openai
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

# Rate limiter removed - no retries, fail fast


def execute_with_retry(query_func, max_retries=3, initial_delay=1):
    """Execute a database query with retry logic for connection errors"""
    import httpx

    for attempt in range(max_retries):
        try:
            return query_func()
        except (
            httpx.RemoteProtocolError,
            httpx.ConnectError,
            httpx.ReadTimeout,
        ) as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2**attempt)
                logger.debug(
                    f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.debug(
                    f"Database connection failed after {max_retries} attempts: {e}"
                )
                raise
        except Exception as e:
            raise


class SimilarityMatcher:
    """Matches query factors to case factors using semantic similarity"""

    def __init__(
        self,
        use_llm: bool = True,
        max_workers: int = 40,  # xAI: 480 RPM supports 40+ workers
        cases_per_batch: int = 40,  # Keep same batch size
        db_batch_size: int = 50,
        text_prefilter_size: int = 20000,  # Use fts_vector similarity to prefilter to top 20k cases
        max_rpm: int = 480,  # xAI: 480 RPM
        max_tpm: int = 30000,  # Keep same TPM limit (adjust if needed)
    ):
        # Default to LLM if API key is available, otherwise use text matching
        self.use_llm = use_llm and bool(os.getenv("XAI_API_KEY"))
        self.query_parser = QueryParser()
        self.max_workers = max_workers
        self.cases_per_batch = (
            cases_per_batch  # Number of cases to process per LLM call
        )
        self.db_batch_size = db_batch_size  # Number of cases to fetch from DB at once
        self.text_prefilter_size = (
            text_prefilter_size  # Top N cases to keep after embedding prefilter
        )
        self.max_rpm = max_rpm  # Maximum requests per minute (for rate limiting)
        self.max_tpm = max_tpm  # Maximum tokens per minute (for rate limiting)
        # Cache for parsed queries (simple in-memory cache)
        self._query_cache = {}
        # Cache for query embeddings
        self._query_embedding_cache = {}

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
            f"✓ Found {len(candidate_case_ids):,} candidate cases to process with LLM"
        )

        # Log a warning if we expected more cases but got fewer
        if candidate_limit is None and len(candidate_case_ids) < 50000:
            logger.warning(
                f"⚠️  Expected to find ~99k analyzed cases but only found {len(candidate_case_ids):,}. "
                f"This might indicate a pagination issue or that fewer cases are analyzed than expected."
            )

        if not candidate_case_ids:
            if candidate_limit is None:
                # If searching all cases and still got nothing, there are no analyzed cases
                logger.warning("No analyzed cases found in database")
            else:
                logger.warning("No candidate cases found in pre-filtering")
            return []

        prefilter_elapsed = time.time() - prefilter_start
        prefilter_min = int(prefilter_elapsed // 60)
        prefilter_sec = int(prefilter_elapsed % 60)
        logger.info(
            f"✓ Pre-filtering completed in {prefilter_elapsed:.1f}s ({prefilter_min}m {prefilter_sec}s): "
            f"found {len(candidate_case_ids):,} candidates"
        )

        # STAGE 2: Fast fts_vector-based prefiltering (if we have many cases)
        # Use PostgreSQL full-text search vector to reduce from 99k → 20k candidates before expensive LLM calls
        fts_prefilter_start = time.time()

        # If we have more cases than text_prefilter_size, use fts_vector similarity to prefilter
        if len(candidate_case_ids) > self.text_prefilter_size:
            logger.info(
                f"Stage 2a: Fast fts_vector-based prefiltering {len(candidate_case_ids):,} cases down to top {self.text_prefilter_size:,} candidates..."
            )
            top_candidates = self._fast_fts_vector_prefilter(
                client,
                query_factors,
                candidate_case_ids,
                filter_direction,
                self.text_prefilter_size,
            )
            fts_prefilter_elapsed = time.time() - fts_prefilter_start
            fts_prefilter_min = int(fts_prefilter_elapsed // 60)
            fts_prefilter_sec = int(fts_prefilter_elapsed % 60)
            logger.info(
                f"✓ FTS vector prefiltering completed in {fts_prefilter_elapsed:.1f}s "
                f"({fts_prefilter_min}m {fts_prefilter_sec}s): "
                f"reduced {len(candidate_case_ids):,} → {len(top_candidates):,} candidates"
            )
            candidate_case_ids = top_candidates
        else:
            logger.info(
                f"Skipping fts_vector prefilter (only {len(candidate_case_ids):,} cases, below threshold of {self.text_prefilter_size:,})"
            )

        # STAGE 3: LLM-based similarity calculation on prefiltered candidates
        similarity_start = time.time()

        # Process in chunks to manage memory
        # Keep top results from each chunk, then merge at the end
        # Use smaller chunks (5k) for faster processing and better parallelism
        chunk_size = 5000  # Process 5k cases at a time for faster processing
        all_scored_cases = []

        # Determine how many top results to keep per chunk
        # If we have a limit, keep more per chunk to ensure we get the best overall results
        results_per_chunk = (
            (limit * 2) if limit else 1000
        )  # Keep top 2x limit per chunk, or top 1000 if no limit

        total_chunks = (len(candidate_case_ids) + chunk_size - 1) // chunk_size
        total_cases_to_process = len(candidate_case_ids)
        logger.info(
            f"Stage 3: Processing {total_cases_to_process:,} prefiltered cases in {total_chunks} chunks of {chunk_size:,} cases each with LLM"
        )

        overall_start_time = time.time()
        for chunk_idx, chunk_start in enumerate(
            range(0, len(candidate_case_ids), chunk_size), 1
        ):
            chunk_end = min(chunk_start + chunk_size, len(candidate_case_ids))
            chunk_case_ids = candidate_case_ids[chunk_start:chunk_end]

            processed_so_far = chunk_start
            elapsed = time.time() - overall_start_time
            rate = processed_so_far / elapsed if elapsed > 0 else 0
            remaining = total_cases_to_process - processed_so_far
            eta = remaining / rate if rate > 0 else 0

            elapsed_sec = time.time() - overall_start_time
            elapsed_min = int(elapsed_sec // 60)
            elapsed_sec_remainder = int(elapsed_sec % 60)
            logger.info(
                f"[Chunk {chunk_idx}/{total_chunks}] Processing cases {chunk_start + 1:,}-{chunk_end:,} "
                f"({len(chunk_case_ids):,} cases) | Overall: {processed_so_far:,}/{total_cases_to_process:,} "
                f"({rate:.0f} cases/sec, ~{eta:.0f}s remaining) | Elapsed: {elapsed_min}m {elapsed_sec_remainder}s"
            )

            # Process this chunk
            chunk_start_time = time.time()
            chunk_scored = self._process_case_chunk(
                client,
                query_factors,
                chunk_case_ids,
                filter_direction,
            )

            # Keep only top results from this chunk
            chunk_scored.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_from_chunk = chunk_scored[:results_per_chunk]
            all_scored_cases.extend(top_from_chunk)

            chunk_time = time.time() - chunk_start_time
            processed_so_far = chunk_end
            elapsed = time.time() - overall_start_time
            rate = processed_so_far / elapsed if elapsed > 0 else 0
            remaining = total_cases_to_process - processed_so_far
            eta = remaining / rate if rate > 0 else 0
            elapsed_min = int(elapsed // 60)
            elapsed_sec_remainder = int(elapsed % 60)
            logger.info(
                f"[Chunk {chunk_idx}/{total_chunks}] ✓ Processed {len(chunk_case_ids):,} cases in {chunk_time:.1f}s, "
                f"kept top {len(top_from_chunk)} results (total results so far: {len(all_scored_cases):,}) | "
                f"Overall: {processed_so_far:,}/{total_cases_to_process:,} ({rate:.0f} cases/sec, ~{eta:.0f}s remaining) | "
                f"Elapsed: {elapsed_min}m {elapsed_sec_remainder}s"
            )

            # Early termination: If we have a limit and already have enough high-scoring results, we can stop
            if limit and len(all_scored_cases) >= limit:
                # Check if we have enough high-quality results (score > 0.5)
                high_quality = [
                    c for c in all_scored_cases if c.get("similarity_score", 0) > 0.5
                ]
                if len(high_quality) >= limit:
                    logger.info(
                        f"Early termination: Found {len(high_quality)} high-quality results (score > 0.5), "
                        f"which exceeds limit of {limit}. Stopping chunk processing."
                    )
                    break

            # Clear chunk data from memory
            del chunk_scored, chunk_case_ids

        total_similarity_time = time.time() - similarity_start
        similarity_min = int(total_similarity_time // 60)
        similarity_sec = int(total_similarity_time % 60)
        logger.info(
            f"✓ Completed similarity calculation for all chunks in {total_similarity_time:.1f}s "
            f"({similarity_min}m {similarity_sec}s) | {len(all_scored_cases):,} total results before final sorting"
        )

        # Sort all results by similarity score (descending)
        all_scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Apply limit only if specified
        if limit is not None and len(all_scored_cases) > limit:
            all_scored_cases = all_scored_cases[:limit]

        # Get full case details for matches
        top_case_ids = [c["case_id"] for c in all_scored_cases]

        if not top_case_ids:
            return []

        def execute_cases_query():
            return client.table("cases").select("*").in_("id", top_case_ids).execute()

        cases = execute_with_retry(execute_cases_query)

        # Create a map for quick lookup
        case_map = {c["id"]: c for c in cases.data}

        # Combine with similarity scores
        results = []
        for scored_case in all_scored_cases:
            case_id = scored_case["case_id"]
            if case_id in case_map:
                case_data = case_map[case_id].copy()
                case_data["similarity_score"] = scored_case["similarity_score"]
                case_data["holding_direction"] = scored_case["holding_direction"]
                # Include justification if available
                if "justification" in scored_case:
                    case_data["justification"] = scored_case["justification"]
                results.append(case_data)

        total_time = time.time() - start_time
        total_min = int(total_time // 60)
        total_sec = int(total_time % 60)
        logger.info(
            f"✓ Search completed in {total_time:.1f}s ({total_min}m {total_sec}s): "
            f"processed {len(candidate_case_ids):,} cases, returned {len(results):,} results"
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
            if candidate_limit is not None:
                query = (
                    client.table("cases_analysis_metadata")
                    .select("case_id")
                    .eq("is_analyzed", True)
                    .limit(candidate_limit)
                )
                analyzed = query.execute()
                return [c["case_id"] for c in analyzed.data] if analyzed.data else []
            else:
                # Get ALL cases using pagination (Supabase has a default limit per request)
                return self._fetch_all_analyzed_case_ids(client)

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
                            client.table("cases_factors")
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
                    query = client.table("cases_factors").select("case_id, factor_text")
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
                    return self._fetch_all_analyzed_case_ids(client)

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
                    return self._fetch_all_analyzed_case_ids(client)
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
                candidate_ids = self._fetch_all_analyzed_case_ids(client)
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
            if candidate_limit is not None:
                query = (
                    client.table("cases_analysis_metadata")
                    .select("case_id")
                    .eq("is_analyzed", True)
                    .order("analyzed_at", desc=True)
                    .limit(candidate_limit)
                )
                analyzed = query.execute()
                candidate_ids = (
                    [c["case_id"] for c in analyzed.data] if analyzed.data else []
                )
            else:
                candidate_ids = self._fetch_all_analyzed_case_ids(client)

        # Apply direction filter if needed
        if filter_direction and candidate_ids:
            original_count = len(candidate_ids)
            logger.debug(
                f"Applying direction filter '{filter_direction}' to {original_count:,} cases..."
            )
            holdings = (
                client.table("cases_holdings")
                .select("case_id")
                .in_("case_id", candidate_ids)
                .eq("holding_direction", filter_direction)
                .execute()
            )
            candidate_ids = (
                [h["case_id"] for h in holdings.data] if holdings.data else []
            )
            filtered_count = len(candidate_ids)
            logger.debug(
                f"Direction filter reduced cases from {original_count:,} to {filtered_count:,}"
            )

        logger.debug(
            f"Returning {len(candidate_ids):,} candidate case IDs from prefilter"
        )
        return candidate_ids

    def _fast_fts_vector_prefilter(
        self,
        client,
        query_factors: List[Dict],
        candidate_case_ids: List[str],
        filter_direction: Optional[str],
        top_n: int,
    ) -> List[str]:
        """
        Fast fts_vector-based prefiltering to reduce candidate set before expensive LLM calls.
        Uses PostgreSQL full-text search vector (fts_vector) field in the cases table for ranking.

        This is MUCH faster than LLM (no API calls) and can process 99k cases in seconds using database-side ranking.
        """
        logger.info(
            f"Starting fast fts_vector prefilter on {len(candidate_case_ids):,} cases..."
        )
        prefilter_start = time.time()

        # Step 1: Extract search terms from query factors
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

        search_terms = []
        for factor in query_factors:
            factor_text = factor.get("text", "")
            # Extract important words (skip stop words)
            words = [
                w.lower()
                for w in factor_text.split()
                if len(w) >= 3 and w.lower() not in stop_words
            ]
            search_terms.extend(words[:10])  # Limit per factor

        # Remove duplicates and limit total terms
        search_terms = list(set(search_terms))[:20]

        if not search_terms:
            logger.warning("No search terms extracted, returning all candidates")
            return candidate_case_ids[:top_n]

        # Step 2: Use PostgreSQL RPC function for fast fts_vector ranking
        # This is the fastest approach - database does the ranking
        try:
            logger.info("Using PostgreSQL fts_vector for fast ranking...")

            # Create a tsquery from search terms (use plainto_tsquery for better matching)
            query_text = " ".join(search_terms[:10])

            # Try to use an RPC function if available (most efficient)
            try:
                result = client.rpc(
                    "search_cases_by_fts_vector",
                    {
                        "search_query": query_text,
                        "case_ids": candidate_case_ids,
                        "limit_count": top_n,
                        "direction_filter": filter_direction,
                    },
                ).execute()

                if result.data:
                    top_candidates = [r["case_id"] for r in result.data]
                    logger.info(
                        f"✓ FTS vector RPC completed in {time.time() - prefilter_start:.1f}s: "
                        f"found {len(top_candidates):,} candidates"
                    )
                    return top_candidates
            except Exception as rpc_error:
                logger.debug(
                    f"FTS vector RPC not available: {rpc_error}, using direct query"
                )

            # Fallback: Use direct query with text search on full_text field
            # Since we can't easily use ts_rank without an RPC, we'll use a simpler approach:
            # Search for cases where full_text contains the search terms and rank by relevance
            logger.info("Using text search on full_text field as fallback...")

            # Build a search query using ILIKE for each term (simple but works)
            # Process in chunks to avoid query size limits
            chunk_size = 10000
            all_scored = []

            total_chunks = (len(candidate_case_ids) + chunk_size - 1) // chunk_size
            logger.info(
                f"Processing {total_chunks} chunks of {chunk_size:,} cases each with text search..."
            )

            for chunk_idx, chunk_start in enumerate(
                range(0, len(candidate_case_ids), chunk_size), 1
            ):
                chunk_end = min(chunk_start + chunk_size, len(candidate_case_ids))
                chunk_case_ids = candidate_case_ids[chunk_start:chunk_end]

                if chunk_idx % 5 == 0 or chunk_idx == total_chunks:
                    processed = min(chunk_end, len(candidate_case_ids))
                    elapsed = time.time() - prefilter_start
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = len(candidate_case_ids) - processed
                    eta = remaining / rate if rate > 0 else 0
                    elapsed_min = int(elapsed // 60)
                    elapsed_sec_remainder = int(elapsed % 60)
                    logger.info(
                        f"  FTS vector prefilter progress: {processed:,}/{len(candidate_case_ids):,} cases "
                        f"({chunk_idx}/{total_chunks} chunks, {rate:.0f} cases/sec, ~{eta:.0f}s remaining) | "
                        f"Elapsed: {elapsed_min}m {elapsed_sec_remainder}s"
                    )

                # Fetch cases and score by text matching
                try:
                    cases = (
                        client.table("cases")
                        .select("id, full_text")
                        .in_("id", chunk_case_ids)
                        .execute()
                    )

                    if cases.data:
                        # Score each case by counting search term matches in full_text
                        for case in cases.data:
                            case_id = case["id"]
                            full_text = (case.get("full_text") or "").lower()

                            if full_text:
                                # Count how many search terms appear in the text
                                matches = sum(
                                    1 for term in search_terms if term in full_text
                                )
                                if matches > 0:
                                    # Score = number of matches / total terms (normalized)
                                    score = matches / len(search_terms)
                                    all_scored.append((case_id, score))
                except Exception as e:
                    logger.debug(f"Error scoring chunk: {e}")
                    # Fallback: just return cases in order
                    all_scored.extend([(cid, 1.0) for cid in chunk_case_ids])

            # Sort by score and get top N
            all_scored.sort(key=lambda x: x[1], reverse=True)
            top_candidates = [case_id for case_id, score in all_scored[:top_n]]

        except Exception as e:
            logger.warning(
                f"Error in fts_vector prefilter: {e}, falling back to simple limit"
            )
            return candidate_case_ids[:top_n]

        prefilter_elapsed = time.time() - prefilter_start
        prefilter_min = int(prefilter_elapsed // 60)
        prefilter_sec = int(prefilter_elapsed % 60)
        logger.info(
            f"✓ FTS vector prefilter completed in {prefilter_elapsed:.1f}s ({prefilter_min}m {prefilter_sec}s): "
            f"scored {len(all_scored):,} cases, returning top {len(top_candidates):,} candidates"
        )

        # Apply direction filter if needed
        if filter_direction and top_candidates:
            logger.debug(
                f"Applying direction filter to {len(top_candidates):,} prefiltered candidates..."
            )
            holdings = (
                client.table("cases_holdings")
                .select("case_id")
                .in_("case_id", top_candidates)
                .eq("holding_direction", filter_direction)
                .execute()
            )
            top_candidates = (
                [h["case_id"] for h in holdings.data] if holdings.data else []
            )
            logger.debug(f"Direction filter: {len(top_candidates):,} candidates remain")

        return top_candidates

    def _vector_search_rpc(
        self,
        client,
        query_embedding: List[float],
        candidate_case_ids: List[str],
        filter_direction: Optional[str],
        top_n: int,
    ) -> List[str]:
        """
        Try to use Supabase pgvector RPC function for fast database-side vector search.
        This is the fastest approach if pgvector is set up in the database.
        """
        try:
            # Try calling an RPC function that does vector similarity search
            # The function signature would be something like:
            # search_cases_by_embedding(query_embedding vector, limit_count int, direction_filter text)
            result = client.rpc(
                "search_cases_by_embedding",
                {
                    "query_embedding": query_embedding,
                    "limit_count": top_n,
                    "direction_filter": filter_direction,
                },
            ).execute()

            if result.data:
                return [r["case_id"] for r in result.data]
        except Exception as e:
            # RPC function doesn't exist or failed, return empty to trigger fallback
            raise ValueError(f"Vector search RPC not available: {e}")

        return []

    def _check_embeddings_exist(self, client, sample_case_ids: List[str]) -> bool:
        """
        Quick check to see if embeddings exist in the database.
        Samples a few cases to determine if embeddings are available.
        """
        if not sample_case_ids:
            return False

        try:
            # Check a small sample of cases for embeddings
            factors = (
                client.table("cases_factors")
                .select("case_id, embedding")
                .in_("case_id", sample_case_ids[:10])
                .limit(50)
                .execute()
            )

            if factors.data:
                # Check if any factors have embeddings
                has_embeddings = any(
                    f.get("embedding") is not None and f.get("embedding") != ""
                    for f in factors.data
                )
                if has_embeddings:
                    logger.info(
                        "✓ Found embeddings in database, will use for prefiltering"
                    )
                else:
                    logger.info(
                        "✗ No embeddings found in database, skipping embedding prefilter"
                    )
                return has_embeddings
            return False
        except Exception as e:
            logger.debug(f"Error checking for embeddings: {e}")
            return False

    def _get_query_embedding(self, query_factors: List[Dict]) -> Optional[List[float]]:
        """
        Generate embedding for query factors using OpenAI.
        Uses caching to avoid regenerating embeddings for the same query.
        """
        # Create a cache key from query factors
        query_text = " ".join([f.get("text", "") for f in query_factors])
        query_hash = hash(query_text.lower().strip())

        if query_hash in self._query_embedding_cache:
            logger.debug("Using cached query embedding")
            return self._query_embedding_cache[query_hash]

        try:
            from openai import OpenAI

            # Use xAI's OpenAI-compatible API for embeddings (if xAI supports embeddings)
            # Note: xAI may not support embeddings - this might need to fall back to OpenAI or skip
            client = OpenAI(
                api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"
            )

            # Combine all query factors into one text
            combined_query = "\n\n".join([f.get("text", "") for f in query_factors])

            # Generate embedding
            # Note: xAI may not support embeddings endpoint - if this fails, embeddings will be None
            # and the code will fall back to text-based matching
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=combined_query,  # xAI may not support this
                )
            except Exception as embed_error:
                logger.warning(
                    f"xAI embeddings not available (or different model name): {embed_error}. Skipping embeddings."
                )
                return None

            embedding = response.data[0].embedding

            # Cache it
            if len(self._query_embedding_cache) < 100:
                self._query_embedding_cache[query_hash] = embedding

            return embedding

        except Exception as e:
            logger.warning(f"Failed to generate query embedding: {e}")
            return None

    def _score_chunk_with_embeddings(
        self, client, query_embedding: List[float], chunk_case_ids: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Score a chunk of cases using embedding similarity.
        First tries to use stored embeddings from database, falls back to generating on the fly.
        """
        chunk_scores = []
        batch_size = 100
        case_embeddings_map = {}  # case_id -> list of embeddings
        case_factors_map = {}  # case_id -> list of factor texts (fallback)

        # Try to fetch embeddings from database
        for i in range(0, len(chunk_case_ids), batch_size):
            batch_ids = chunk_case_ids[i : i + batch_size]
            try:
                # Try to fetch with embedding column
                factors = (
                    client.table("cases_factors")
                    .select("case_id, factor_text, embedding")
                    .in_("case_id", batch_ids)
                    .execute()
                )

                if factors.data:
                    for factor in factors.data:
                        case_id = factor["case_id"]
                        # Check if embedding exists
                        if "embedding" in factor and factor["embedding"] is not None:
                            if case_id not in case_embeddings_map:
                                case_embeddings_map[case_id] = []
                            # Handle both list and JSON string formats
                            embedding = factor["embedding"]
                            if isinstance(embedding, str):
                                try:
                                    import json

                                    embedding = json.loads(embedding)
                                except:
                                    continue
                            if isinstance(embedding, list) and len(embedding) > 0:
                                case_embeddings_map[case_id].append(embedding)

                        # Also store factor text for fallback
                        if case_id not in case_factors_map:
                            case_factors_map[case_id] = []
                        case_factors_map[case_id].append(factor.get("factor_text", ""))
            except Exception as e:
                logger.debug(f"Error fetching embeddings: {e}")
                # Fallback: fetch just factors
                try:
                    factors = (
                        client.table("cases_factors")
                        .select("case_id, factor_text")
                        .in_("case_id", batch_ids)
                        .execute()
                    )
                    if factors.data:
                        for factor in factors.data:
                            case_id = factor["case_id"]
                            if case_id not in case_factors_map:
                                case_factors_map[case_id] = []
                            case_factors_map[case_id].append(
                                factor.get("factor_text", "")
                            )
                except:
                    pass

        # Use stored embeddings if available, otherwise skip (don't generate on the fly - too slow)
        if case_embeddings_map and any(case_embeddings_map.values()):
            # We have stored embeddings - use them
            logger.info(
                f"Using stored embeddings for {len(case_embeddings_map)} cases in chunk"
            )

            # Process in parallel for speed
            def score_case_embedding(case_id):
                case_embeddings = case_embeddings_map.get(case_id, [])
                if case_embeddings:
                    avg_embedding = self._average_embeddings(case_embeddings)
                    similarity = self._cosine_similarity(query_embedding, avg_embedding)
                    if similarity > 0:
                        return (case_id, similarity)
                return None

            with ThreadPoolExecutor(
                max_workers=min(20, len(chunk_case_ids))
            ) as executor:
                results = executor.map(score_case_embedding, chunk_case_ids)
                chunk_scores = [r for r in results if r is not None]
        else:
            # No stored embeddings - return empty (shouldn't happen if we checked first)
            logger.warning(
                f"No stored embeddings found for chunk. This should have been detected earlier. "
                f"Skipping this chunk to avoid slow on-the-fly generation."
            )
            return []

        return chunk_scores

    def _score_chunk_with_generated_embeddings(
        self,
        client,
        query_embedding: List[float],
        chunk_case_ids: List[str],
        case_factors_map: Optional[Dict] = None,
    ) -> List[Tuple[str, float]]:
        """
        Generate embeddings on the fly for factors and calculate similarity.
        This is slower but works if embeddings aren't pre-computed in the database.
        """
        chunk_scores = []

        # If case_factors_map not provided, fetch it
        if case_factors_map is None:
            case_factors_map = {}
            batch_size = 100
            for i in range(0, len(chunk_case_ids), batch_size):
                batch_ids = chunk_case_ids[i : i + batch_size]
                try:
                    factors = (
                        client.table("cases_factors")
                        .select("case_id, factor_text")
                        .in_("case_id", batch_ids)
                        .execute()
                    )
                    if factors.data:
                        for factor in factors.data:
                            case_id = factor["case_id"]
                            if case_id not in case_factors_map:
                                case_factors_map[case_id] = []
                            case_factors_map[case_id].append(factor["factor_text"])
                except Exception as e:
                    logger.debug(f"Error fetching factors: {e}")

        # Generate embeddings for all factors in parallel
        try:
            from openai import OpenAI

            # Use xAI's OpenAI-compatible API for embeddings (if xAI supports embeddings)
            embedding_client = OpenAI(
                api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"
            )

            # Collect all unique factor texts (deduplicate to save API calls)
            all_factor_texts = []
            factor_to_cases = {}  # Map factor text to list of case IDs
            seen_factors = set()

            for case_id, factors in case_factors_map.items():
                for factor_text in factors:
                    if factor_text and factor_text not in seen_factors:
                        all_factor_texts.append(factor_text)
                        factor_to_cases[factor_text] = []
                        seen_factors.add(factor_text)
                    if factor_text in factor_to_cases:
                        factor_to_cases[factor_text].append(case_id)

            # Generate embeddings in batches (OpenAI allows up to 2048 inputs per request)
            # Use larger batches for efficiency - OpenAI API is very fast for embeddings
            embedding_batch_size = 1000  # Large batches = fewer API calls = faster
            factor_embeddings = {}

            logger.debug(
                f"Generating embeddings for {len(all_factor_texts):,} unique factors in batches of {embedding_batch_size}..."
            )

            # Process embedding batches in parallel for even more speed
            def generate_embedding_batch(batch_texts, batch_idx):
                try:
                    # Note: xAI may not support embeddings - if this fails, will fall back to text matching
                    response = embedding_client.embeddings.create(
                        model="text-embedding-3-small", input=batch_texts
                    )
                    batch_embeddings = {}
                    for idx, embedding_data in enumerate(response.data):
                        factor_text = batch_texts[idx]
                        batch_embeddings[factor_text] = embedding_data.embedding
                    return batch_embeddings, batch_idx
                except Exception as e:
                    logger.debug(
                        f"Error generating embeddings for batch {batch_idx}: {e}"
                    )
                    return {}, batch_idx

            # Create batches
            embedding_batches = []
            for i in range(0, len(all_factor_texts), embedding_batch_size):
                batch_texts = all_factor_texts[i : i + embedding_batch_size]
                embedding_batches.append((batch_texts, i // embedding_batch_size))

            # Generate embeddings in parallel (up to 10 concurrent batches for speed)
            completed_batches = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(generate_embedding_batch, batch_texts, idx): (
                        batch_texts,
                        idx,
                    )
                    for batch_texts, idx in embedding_batches
                }

                for future in as_completed(futures):
                    batch_embeddings, batch_idx = future.result()
                    factor_embeddings.update(batch_embeddings)
                    completed_batches += 1

                    if completed_batches % 5 == 0 or completed_batches == len(
                        embedding_batches
                    ):
                        logger.info(
                            f"  Generated embeddings for {len(factor_embeddings):,}/{len(all_factor_texts):,} factors "
                            f"({completed_batches}/{len(embedding_batches)} batches)..."
                        )

            # Calculate similarity for each case in parallel
            def score_case_with_embeddings(case_id):
                case_factors = case_factors_map.get(case_id, [])
                if case_factors:
                    # Get embeddings for this case's factors
                    case_factor_embeddings = [
                        factor_embeddings.get(ft)
                        for ft in case_factors
                        if ft in factor_embeddings
                    ]

                    if case_factor_embeddings:
                        # Average the embeddings
                        avg_embedding = self._average_embeddings(case_factor_embeddings)
                        similarity = self._cosine_similarity(
                            query_embedding, avg_embedding
                        )
                        if similarity > 0:
                            return (case_id, similarity)
                return None

            # Process in parallel for speed
            with ThreadPoolExecutor(
                max_workers=min(20, len(chunk_case_ids))
            ) as executor:
                results = executor.map(score_case_with_embeddings, chunk_case_ids)
                chunk_scores = [r for r in results if r is not None]

        except Exception as e:
            logger.warning(
                f"Error in embedding generation: {e}, falling back to text matching"
            )
            # Fallback to text matching - need query_factors, but we don't have them here
            # Return empty and let the caller handle fallback
            logger.warning(
                "Cannot fallback to text matching without query_factors in this context"
            )
            return []

        return chunk_scores

    def _score_chunk_with_text_matching(
        self, client, query_factors: List[Dict], chunk_case_ids: List[str]
    ) -> List[Tuple[str, float]]:
        """Fallback: score using text matching if embeddings fail"""
        chunk_scores = []
        batch_size = 100

        # Fetch factors
        case_factors_map = {}
        for i in range(0, len(chunk_case_ids), batch_size):
            batch_ids = chunk_case_ids[i : i + batch_size]
            try:
                factors = (
                    client.table("cases_factors")
                    .select("case_id, factor_text")
                    .in_("case_id", batch_ids)
                    .execute()
                )
                if factors.data:
                    for factor in factors.data:
                        case_id = factor["case_id"]
                        if case_id not in case_factors_map:
                            case_factors_map[case_id] = []
                        case_factors_map[case_id].append(
                            {"text": factor["factor_text"]}
                        )
            except Exception as e:
                logger.debug(f"Error fetching factors: {e}")

        # Score with text matching in parallel
        def score_case_text(case_id):
            case_factors = case_factors_map.get(case_id, [])
            if case_factors:
                score = self._calculate_similarity_text(query_factors, case_factors)
                if score > 0:
                    return (case_id, score)
            return None

        # Process in parallel for speed
        with ThreadPoolExecutor(max_workers=min(20, len(chunk_case_ids))) as executor:
            results = executor.map(score_case_text, chunk_case_ids)
            chunk_scores = [r for r in results if r is not None]

        return chunk_scores

    def _fast_text_prefilter_fallback(
        self,
        client,
        query_factors: List[Dict],
        candidate_case_ids: List[str],
        filter_direction: Optional[str],
        top_n: int,
    ) -> List[str]:
        """Fallback to text matching if embedding generation fails"""
        logger.info("Falling back to text-based prefiltering...")
        chunk_size = 5000
        all_scored = []

        total_chunks = (len(candidate_case_ids) + chunk_size - 1) // chunk_size
        logger.info(f"Processing {total_chunks} chunks with text matching...")

        for chunk_idx, chunk_start in enumerate(
            range(0, len(candidate_case_ids), chunk_size), 1
        ):
            chunk_end = min(chunk_start + chunk_size, len(candidate_case_ids))
            chunk_case_ids = candidate_case_ids[chunk_start:chunk_end]

            if chunk_idx % 5 == 0 or chunk_idx == total_chunks:
                processed = min(chunk_end, len(candidate_case_ids))
                elapsed = time.time() - prefilter_start
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = len(candidate_case_ids) - processed
                eta = remaining / rate if rate > 0 else 0
                elapsed_min = int(elapsed // 60)
                elapsed_sec_remainder = int(elapsed % 60)
                logger.info(
                    f"  Text prefilter progress: {processed:,}/{len(candidate_case_ids):,} cases "
                    f"({chunk_idx}/{total_chunks} chunks, {rate:.0f} cases/sec, ~{eta:.0f}s remaining) | "
                    f"Elapsed: {elapsed_min}m {elapsed_sec_remainder}s"
                )

            chunk_scores = self._score_chunk_with_text_matching(
                client, query_factors, chunk_case_ids
            )
            all_scored.extend(chunk_scores)

        all_scored.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [case_id for case_id, score in all_scored[:top_n]]

        if filter_direction and top_candidates:
            holdings = (
                client.table("cases_holdings")
                .select("case_id")
                .in_("case_id", top_candidates)
                .eq("holding_direction", filter_direction)
                .execute()
            )
            top_candidates = (
                [h["case_id"] for h in holdings.data] if holdings.data else []
            )

        return top_candidates

    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Average multiple embeddings into a single embedding vector"""
        if not embeddings:
            return None

        dimension = len(embeddings[0])
        avg = [0.0] * dimension

        for embedding in embeddings:
            for i in range(dimension):
                avg[i] += embedding[i]

        return [x / len(embeddings) for x in avg]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _fetch_all_analyzed_case_ids(self, client) -> List[str]:
        """
        Fetch ALL analyzed case IDs using pagination.
        Supabase has a default limit per request, so we need to paginate.
        """
        all_case_ids = []
        page_size = 1000  # Supabase's default/max per request
        offset = 0

        logger.info(
            "Fetching all analyzed case IDs (this may take a moment for large datasets)..."
        )

        while True:
            query = (
                client.table("cases_analysis_metadata")
                .select("case_id")
                .eq("is_analyzed", True)
                .order("case_id")  # Order is required for consistent pagination
                .range(offset, offset + page_size - 1)
            )

            result = query.execute()

            if not result.data:
                logger.debug(f"  No more data at offset {offset}, stopping pagination")
                break

            batch_ids = [c["case_id"] for c in result.data]
            all_case_ids.extend(batch_ids)

            # Log progress every 10k cases or on the last page
            if len(all_case_ids) % 10000 < page_size or len(result.data) < page_size:
                logger.info(
                    f"  Fetched {len(all_case_ids):,} case IDs so far (page at offset {offset})..."
                )

            # If we got fewer results than page_size, we've reached the end
            if len(result.data) < page_size:
                logger.debug(
                    f"  Got {len(result.data)} results (less than page_size {page_size}), reached end"
                )
                break

            offset += page_size

            # Safety check: if we've fetched an unreasonably large number, something might be wrong
            if len(all_case_ids) > 200000:
                logger.warning(
                    f"  ⚠️  Fetched {len(all_case_ids):,} cases, which seems unusually high. Stopping pagination."
                )
                break

        logger.info(f"✓ Total analyzed cases found: {len(all_case_ids):,}")
        return all_case_ids

    def _process_case_chunk(
        self,
        client,
        query_factors: List[Dict],
        chunk_case_ids: List[str],
        filter_direction: Optional[str],
    ) -> List[Dict]:
        """
        Process a chunk of cases: fetch their data and calculate similarities.
        This keeps memory usage manageable for large datasets.
        """
        import concurrent.futures
        import httpx

        logger.debug(f"Fetching data for {len(chunk_case_ids):,} cases in chunk...")

        # Fetch factors and holdings for this chunk in parallel
        def fetch_factors():
            all_factors_data = []
            batch_size = 100  # Safe batch size for .in_() queries
            total_factor_batches = (len(chunk_case_ids) + batch_size - 1) // batch_size

            for batch_idx, i in enumerate(range(0, len(chunk_case_ids), batch_size), 1):
                batch_ids = chunk_case_ids[i : i + batch_size]

                def execute_batch():
                    return (
                        client.table("cases_factors")
                        .select("case_id, factor_text")
                        .in_("case_id", batch_ids)
                        .execute()
                    )

                batch_result = execute_with_retry(execute_batch)
                if batch_result.data:
                    all_factors_data.extend(batch_result.data)

                if batch_idx % 5 == 0 or batch_idx == total_factor_batches:
                    processed = min(i + batch_size, len(chunk_case_ids))
                    logger.info(
                        f"  Fetched factors for {processed:,}/{len(chunk_case_ids):,} cases "
                        f"({batch_idx}/{total_factor_batches} batches)..."
                    )

            class MockResponse:
                def __init__(self, data):
                    self.data = data

            return MockResponse(all_factors_data)

        def fetch_holdings():
            all_holdings_data = []
            batch_size = 100
            total_holding_batches = (len(chunk_case_ids) + batch_size - 1) // batch_size

            for batch_idx, i in enumerate(range(0, len(chunk_case_ids), batch_size), 1):
                batch_ids = chunk_case_ids[i : i + batch_size]

                def execute_batch():
                    return (
                        client.table("cases_holdings")
                        .select("case_id, holding_direction")
                        .in_("case_id", batch_ids)
                        .execute()
                    )

                batch_result = execute_with_retry(execute_batch)
                if batch_result.data:
                    all_holdings_data.extend(batch_result.data)

                if batch_idx % 5 == 0 or batch_idx == total_holding_batches:
                    processed = min(i + batch_size, len(chunk_case_ids))
                    logger.info(
                        f"  Fetched holdings for {processed:,}/{len(chunk_case_ids):,} cases "
                        f"({batch_idx}/{total_holding_batches} batches)..."
                    )

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

        logger.debug(
            f"  ✓ Fetched {len(all_factors.data):,} factors and {len(holdings.data):,} holdings"
        )

        # Build maps for this chunk
        holding_map = {case_id: "unclear" for case_id in chunk_case_ids}
        for h in holdings.data:
            holding_map[h["case_id"]] = h["holding_direction"]

        case_factors_map = {case_id: [] for case_id in chunk_case_ids}
        cases_with_factors = 0
        for factor in all_factors.data:
            case_id = factor["case_id"]
            if case_id in case_factors_map:
                if not case_factors_map[case_id]:  # First factor for this case
                    cases_with_factors += 1
                case_factors_map[case_id].append({"text": factor["factor_text"]})

        logger.debug(
            f"  ✓ Mapped data: {cases_with_factors:,}/{len(chunk_case_ids):,} cases have factors"
        )

        # Fetch case details for this chunk
        case_details_map = {}
        for i in range(0, len(chunk_case_ids), self.db_batch_size):
            batch_ids = chunk_case_ids[i : i + self.db_batch_size]
            try:
                cases = (
                    client.table("cases")
                    .select("id, case_name, court, date_filed, citation")
                    .in_("id", batch_ids)
                    .execute()
                )
                for case in cases.data:
                    case_details_map[case["id"]] = case
            except Exception as e:
                logger.debug(f"Error fetching case details for batch: {e}")

        # Calculate similarities for this chunk
        return self._calculate_similarities_parallel(
            query_factors,
            case_factors_map,
            holding_map,
            case_details_map,
            filter_direction,
        )

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
            f"Processing {len(case_batches):,} LLM batches ({total_cases_to_process:,} total cases) "
            f"with {self.cases_per_batch} cases per batch using {self.max_workers} workers. "
            f"Tracking actual time - will show progress as batches complete."
        )

        # Process batches in parallel with rate limiting
        # Paid accounts: Tier 1 = 500 RPM / 30k TPM, Tier 2+ = 5000-10000 RPM / higher TPM
        completed_batches = 0
        processed_cases = 0
        llm_start_time = time.time()

        # Rate limiter: track requests and tokens per minute
        rate_limiter_lock = _threading.Lock()
        request_times = []  # Track request timestamps
        token_usage = []  # Track (timestamp, tokens) for TPM tracking
        api_request_counter = {
            "count": 0
        }  # Track total API requests made (use dict for nonlocal access)

        # Performance tracking
        batch_times = []  # Track actual batch processing times
        rate_limit_wait_times = []  # Track time spent waiting for rate limits
        api_call_times = []  # Track actual API call durations

        # Dynamic limits: start with configured values, adjust based on API errors
        actual_rpm_limit = {"value": self.max_rpm}  # Use dict for nonlocal access
        actual_tpm_limit = {"value": self.max_tpm}  # Use dict for nonlocal access

        def wait_for_rate_limit(estimated_tokens: int = 0):
            """Wait if we've hit the rate limit (RPM or TPM)"""
            wait_start = time.time()
            total_wait_time = 0

            with rate_limiter_lock:
                now = time.time()
                # Remove requests/tokens older than 1 minute
                request_times[:] = [t for t in request_times if now - t < 60]
                token_usage[:] = [
                    (ts, tokens) for ts, tokens in token_usage if now - ts < 60
                ]

                # Check RPM limit (use actual limit detected from API, or configured limit)
                current_rpm_limit = actual_rpm_limit["value"]
                if len(request_times) >= current_rpm_limit:
                    # Wait until the oldest request is 60 seconds old
                    oldest = min(request_times)
                    wait_time = 60 - (now - oldest) + 0.1  # Small buffer
                    if wait_time > 0:
                        logger.debug(
                            f"Rate limit: waiting {wait_time:.1f}s before next request ({current_rpm_limit} RPM limit)..."
                        )
                        time.sleep(wait_time)
                        total_wait_time += wait_time
                        # Clean up again after waiting
                        now = time.time()
                        request_times[:] = [t for t in request_times if now - t < 60]
                        token_usage[:] = [
                            (ts, tokens) for ts, tokens in token_usage if now - ts < 60
                        ]

                # Check TPM limit (use actual limit detected from API, or configured limit)
                current_tpm_limit = actual_tpm_limit["value"]
                current_tpm = sum(tokens for _, tokens in token_usage)
                if (
                    estimated_tokens > 0
                    and current_tpm + estimated_tokens > current_tpm_limit
                ):
                    # Need to wait until tokens free up
                    if token_usage:
                        oldest_token_time = min(ts for ts, _ in token_usage)
                        wait_time = 60 - (now - oldest_token_time) + 0.1
                        if wait_time > 0:
                            logger.debug(
                                f"TPM limit: waiting {wait_time:.1f}s before next request "
                                f"({current_tpm:,}/{current_tpm_limit:,} tokens used, need {estimated_tokens:,} more)..."
                            )
                            time.sleep(wait_time)
                            total_wait_time += wait_time
                            # Clean up again after waiting
                            now = time.time()
                            token_usage[:] = [
                                (ts, tokens)
                                for ts, tokens in token_usage
                                if now - ts < 60
                            ]

                # Record this request
                request_times.append(time.time())
                if estimated_tokens > 0:
                    token_usage.append((time.time(), estimated_tokens))
                api_request_counter["count"] += 1

                # Track wait time
                if total_wait_time > 0:
                    rate_limit_wait_times.append(total_wait_time)

            return total_wait_time

        def calculate_batch(batch_data):
            """Calculate similarity for a batch of cases with rate limiting"""
            batch_start = time.time()

            # Estimate tokens for this batch
            estimated_tokens = self._estimate_tokens_for_batch(
                query_factors, batch_data
            )

            # Wait for rate limit before making request (check both RPM and TPM)
            wait_time = wait_for_rate_limit(estimated_tokens)

            try:
                api_call_start = time.time()
                if self.use_llm:
                    result = self._calculate_similarity_batch_llm(
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
                    result = results

                # Track API call time
                api_call_duration = time.time() - api_call_start
                with rate_limiter_lock:
                    api_call_times.append(api_call_duration)
                    # Keep only last 100 measurements to avoid memory bloat
                    if len(api_call_times) > 100:
                        api_call_times.pop(0)

                return result
            except Exception as e:
                # If LLM failed, try text matching as fallback
                logger.debug(
                    f"Error calculating similarity for batch: {e}, using text matching"
                )
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
            finally:
                # Track total batch time
                batch_duration = time.time() - batch_start
                with rate_limiter_lock:
                    batch_times.append(batch_duration)
                    # Keep only last 100 measurements
                    if len(batch_times) > 100:
                        batch_times.pop(0)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(calculate_batch, batch): batch for batch in case_batches
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    batch = futures[future]
                    batch_size = len(batch)
                    if batch_results:
                        with lock:
                            scored_cases.extend(batch_results)
                    with lock:
                        processed_cases += batch_size
                        completed_batches += 1

                    # Log progress every 5 batches or every 200 cases, whichever comes first
                    if (
                        completed_batches % 5 == 0
                        or processed_cases % 200 == 0
                        or completed_batches == len(case_batches)
                    ):
                        elapsed = time.time() - llm_start_time
                        rate = processed_cases / elapsed if elapsed > 0 else 0
                        remaining_batches = len(case_batches) - completed_batches
                        remaining_cases = total_cases_to_process - processed_cases

                        # Calculate ETA based on actual measured performance
                        eta_seconds = 0
                        if rate > 0 and remaining_cases > 0:
                            eta_seconds = remaining_cases / rate

                        # Also calculate ETA based on actual batch times if we have enough data
                        with rate_limiter_lock:
                            if (
                                len(batch_times) >= 5
                            ):  # Need at least 5 samples for reliable average
                                avg_batch_time = sum(batch_times) / len(batch_times)
                                # Account for parallelization: with max_workers, batches complete in parallel
                                # So time is roughly: remaining_batches / max_workers * avg_batch_time
                                eta_from_batches = (
                                    remaining_batches / self.max_workers
                                ) * avg_batch_time
                                # Use the more conservative (longer) estimate
                                if eta_from_batches > eta_seconds:
                                    eta_seconds = eta_from_batches

                        elapsed_min = int(elapsed // 60)
                        elapsed_sec_remainder = int(elapsed % 60)
                        eta_min = int(eta_seconds // 60)
                        eta_sec = int(eta_seconds % 60)

                        # Calculate API request stats
                        with rate_limiter_lock:
                            total_requests = api_request_counter["count"]
                            requests_in_last_min = len(
                                [t for t in request_times if time.time() - t < 60]
                            )
                            requests_per_min = (
                                (total_requests / elapsed * 60) if elapsed > 0 else 0
                            )

                            # Show actual performance metrics
                            avg_batch_time_str = ""
                            avg_api_time_str = ""
                            if len(batch_times) > 0:
                                avg_batch = sum(batch_times) / len(batch_times)
                                avg_batch_time_str = f"avg {avg_batch:.1f}s/batch"
                            if len(api_call_times) > 0:
                                avg_api = sum(api_call_times) / len(api_call_times)
                                avg_api_time_str = f"avg {avg_api:.1f}s/API call"

                            total_wait_time = (
                                sum(rate_limit_wait_times)
                                if rate_limit_wait_times
                                else 0
                            )
                            wait_time_str = ""
                            if total_wait_time > 0:
                                wait_pct = (
                                    (total_wait_time / elapsed) * 100
                                    if elapsed > 0
                                    else 0
                                )
                                wait_time_str = f", {total_wait_time:.1f}s waiting ({wait_pct:.1f}%)"

                        logger.info(
                            f"  LLM progress: {processed_cases:,}/{total_cases_to_process:,} cases processed "
                            f"({completed_batches:,}/{len(case_batches):,} batches, "
                            f"{rate:.1f} cases/sec) | "
                            f"ETA: {eta_min}m {eta_sec}s | "
                            f"Elapsed: {elapsed_min}m {elapsed_sec_remainder}s | "
                            f"API: {total_requests:,} requests ({requests_per_min:.1f}/min avg, {requests_in_last_min}/min current)"
                        )

                        if avg_batch_time_str or avg_api_time_str or wait_time_str:
                            logger.info(
                                f"    Performance: {avg_batch_time_str}{', ' + avg_api_time_str if avg_api_time_str else ''}{wait_time_str}"
                            )
                except Exception as e:
                    batch = futures[future]
                    batch_size = len(batch)
                    with lock:
                        processed_cases += batch_size
                        completed_batches += 1
                    logger.warning(f"Error in batch similarity calculation: {e}")

        llm_total_elapsed = time.time() - llm_start_time
        llm_total_min = int(llm_total_elapsed // 60)
        llm_total_sec = int(llm_total_elapsed % 60)

        with rate_limiter_lock:
            total_requests = api_request_counter["count"]
            avg_requests_per_min = (
                (total_requests / llm_total_elapsed * 60)
                if llm_total_elapsed > 0
                else 0
            )

            # Calculate actual performance metrics
            avg_batch_time = sum(batch_times) / len(batch_times) if batch_times else 0
            avg_api_time = (
                sum(api_call_times) / len(api_call_times) if api_call_times else 0
            )
            total_wait_time = sum(rate_limit_wait_times) if rate_limit_wait_times else 0
            wait_pct = (
                (total_wait_time / llm_total_elapsed * 100)
                if llm_total_elapsed > 0
                else 0
            )

            cases_per_second = (
                processed_cases / llm_total_elapsed if llm_total_elapsed > 0 else 0
            )

        logger.info(
            f"✓ Completed LLM similarity calculation for {len(scored_cases):,} cases in "
            f"{llm_total_elapsed:.1f}s ({llm_total_min}m {llm_total_sec}s)"
        )
        logger.info(
            f"  Performance: {cases_per_second:.2f} cases/sec | "
            f"{total_requests:,} API requests ({avg_requests_per_min:.1f}/min) | "
            f"Avg batch time: {avg_batch_time:.2f}s | "
            f"Avg API call: {avg_api_time:.2f}s | "
            f"Rate limit waits: {total_wait_time:.1f}s ({wait_pct:.1f}% of total time)"
        )
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

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 characters per token"""
        return len(text) // 4

    def _estimate_tokens_for_batch(
        self, query_factors: List[Dict], batch_data: List[Dict]
    ) -> int:
        """Estimate tokens needed for a batch of cases"""
        # Base prompt overhead
        base_tokens = 500

        # Query factors
        query_text = "\n\n".join([f["text"] for f in query_factors])
        query_tokens = self._estimate_tokens(query_text)

        # Cases in batch
        case_tokens = 0
        for case_data in batch_data:
            case_factors = case_data.get("case_factors", [])
            case_text = "\n".join([f["text"] for f in case_factors])
            case_tokens += (
                self._estimate_tokens(case_text) + 100
            )  # +100 for case metadata

        # Response tokens (rough estimate: ~100 tokens per case)
        response_tokens = len(batch_data) * 100

        total = base_tokens + query_tokens + case_tokens + response_tokens
        return total

    def _calculate_similarity_batch_llm(
        self,
        query_factors: List[Dict],
        batch_data: List[Dict],
    ) -> List[Dict]:
        """Use LLM to calculate semantic similarity for a batch of cases with token limit checking"""
        remaining_results = []  # Track results from split batches

        try:
            from openai import OpenAI
            import json

            # Use xAI's OpenAI-compatible API
            client = OpenAI(
                api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"
            )

            # Combine all query factors into one string
            query_texts = [f["text"] for f in query_factors]
            combined_query = "\n\n".join(query_texts)

            # Format cases clearly with separators, but limit batch size if tokens get too large
            cases_text = ""
            estimated_tokens = (
                self._estimate_tokens(combined_query) + 500
            )  # Base prompt overhead
            max_tokens_per_request = 8000  # Stay well under 10k TPM limit

            # Build cases text, but stop if we're getting too large
            actual_batch = []
            for idx, case_data in enumerate(batch_data, 1):
                case_id = case_data["case_id"]
                case_details = case_data.get("case_details", {})
                case_name = case_details.get("case_name", f"Case {case_id}")
                case_citation = case_details.get("citation", "")
                case_factors = case_data["case_factors"]

                case_factors_text = "\n".join([f["text"] for f in case_factors])
                case_text = f"""
=== CASE {idx} ===
CASE ID: {case_id}
CASE NAME: {case_name}
CITATION: {case_citation}

LEGAL PRINCIPLES FROM THIS CASE:
{case_factors_text}

---
"""
                case_tokens = self._estimate_tokens(case_text)

                # Check if adding this case would exceed token limit
                if estimated_tokens + case_tokens > max_tokens_per_request:
                    logger.debug(
                        f"Batch token limit reached at {idx-1}/{len(batch_data)} cases "
                        f"({estimated_tokens} tokens). Splitting batch."
                    )
                    break

                cases_text += case_text
                estimated_tokens += case_tokens
                actual_batch.append(case_data)

            # If we had to truncate, process remaining cases separately
            if len(actual_batch) < len(batch_data):
                remaining_batch = batch_data[len(actual_batch) :]
                logger.debug(
                    f"Processing {len(remaining_batch)} remaining cases in separate batch"
                )
                remaining_results = self._calculate_similarity_batch_llm(
                    query_factors, remaining_batch
                )

            # Use the actual batch we built (may be smaller than original)
            if not actual_batch:
                # If batch is empty, just return remaining results
                return remaining_results

            batch_data = actual_batch

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

CRITICAL SCORING INSTRUCTIONS - USE THE MOST SIMILAR PRINCIPLE:
- IMPORTANT: Base the score on the MOST SIMILAR legal principle between the query and the case, NOT the average similarity of all principles
- Find the single legal principle from the case that is MOST similar to any legal principle in the query
- If that most similar principle is highly correlated with the query, give a HIGH score even if other principles in the case don't match well
- This ensures cases with one highly relevant principle will still appear in results, even if they also contain unrelated principles
- Be EXTREMELY SELECTIVE - your selectivity must be reflected in the actual score you assign
- If the MOST SIMILAR legal principle is NOT closely related or is fundamentally different: give a VERY LOW score (0.00-0.05)
- If the MOST SIMILAR legal principle is somewhat related but not the same: give a LOW score (0.05-0.20)
- If the MOST SIMILAR legal principle is closely related or very closely related: give a MODERATE score (0.20-0.50)
- If the MOST SIMILAR legal principle is the same or nearly identical: give a HIGH score (0.50-1.0)
- DO NOT give scores like 0.10 or 0.15 to fundamentally different cases - if the most similar legal principle is different, give scores like 0.01, 0.02, or 0.05
- Most cases should get VERY LOW scores (0.00-0.05) because most cases won't be closely related
- Your selectivity level MUST be visible in the score - if the most similar legal principle is fundamentally different, the score should be VERY LOW (0.01-0.05), not 0.10

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
                    model="grok-4",  # xAI Grok model
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a legal research assistant matching cases to search queries. CRITICAL: Base scores on the MOST SIMILAR legal principle between the query and each case, NOT the average similarity. If one principle matches very well, give a high score even if other principles don't match. Be EXTREMELY selective - your selectivity must be visible in the scores you assign. If the most similar legal principle is fundamentally different, give VERY LOW scores (0.00-0.05). If it's somewhat related, give LOW scores (0.05-0.20). Only give high scores (0.50+) for closely related legal principles. Show your strict selectivity in the numbers - unrelated cases should get scores like 0.01-0.05, not 0.10. For each case, provide a clear justification (2-3 sentences) explaining your reasoning. Write justifications directly about the search query - do not refer to 'the user', 'the lawyer', or any person in third person. Return only valid JSON. Pay close attention to case IDs to keep cases distinct.",
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

                # Combine with any remaining results
                results.extend(remaining_results)
                return results

            except Exception as api_error:
                error_str = str(api_error).lower()
                error_full = str(api_error)

                # Try to extract actual limits from error message
                import re

                # Look for "limit X" patterns in the error
                rpm_match = re.search(
                    r"requests per min.*?limit\s+(\d+)", error_full, re.IGNORECASE
                )
                tpm_match = re.search(
                    r"tokens per min.*?limit\s+(\d+)", error_full, re.IGNORECASE
                )

                if rpm_match:
                    detected_rpm = int(rpm_match.group(1))
                    with rate_limiter_lock:
                        if detected_rpm < actual_rpm_limit["value"]:
                            actual_rpm_limit["value"] = detected_rpm
                            logger.warning(
                                f"⚠️  API reports RPM limit of {detected_rpm} (lower than configured {self.max_rpm}). "
                                f"Adjusting rate limiter to match API limits."
                            )

                if tpm_match:
                    detected_tpm = int(tpm_match.group(1))
                    with rate_limiter_lock:
                        if detected_tpm < actual_tpm_limit["value"]:
                            actual_tpm_limit["value"] = detected_tpm
                            logger.warning(
                                f"⚠️  API reports TPM limit of {detected_tpm:,} (lower than configured {self.max_tpm:,}). "
                                f"Adjusting rate limiter to match API limits."
                            )

                # Check if it's a rate limit or quota error - fall back to text matching
                if (
                    "429" in error_str
                    or "rate limit" in error_str
                    or "quota" in error_str
                    or "requests per day" in error_str
                ):
                    # Check if it's a daily limit (for free tier accounts)
                    if "requests per day" in error_str or "rpd" in error_str:
                        logger.warning(
                            f"⚠️  Daily request limit reached! "
                            f"Using text matching fallback for this batch. "
                            f"Note: Paid accounts don't have daily limits. "
                            f"Error: {error_str[:200]}"
                        )
                    else:
                        logger.warning(
                            f"Rate limit hit in batch processing, using text matching fallback: {error_str[:200]}"
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
            # Note: remaining_results would be empty here since error happened before split
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

CRITICAL SCORING INSTRUCTIONS - USE THE MOST SIMILAR PRINCIPLE:
- IMPORTANT: Base the score on the MOST SIMILAR legal principle between the query and the case, NOT the average similarity of all principles
- Find the single legal principle from the case that is MOST similar to any legal principle in the query
- If that most similar principle is highly correlated with the query, give a HIGH score even if other principles in the case don't match well
- This ensures cases with one highly relevant principle will still appear in results, even if they also contain unrelated principles
- Be EXTREMELY SELECTIVE - your selectivity must be reflected in the actual score you assign
- If the MOST SIMILAR legal principle is NOT closely related or is fundamentally different: give a VERY LOW score (0.00-0.05)
- If the MOST SIMILAR legal principle is somewhat related but not the same: give a LOW score (0.05-0.20)
- If the MOST SIMILAR legal principle is closely related or very closely related: give a MODERATE score (0.20-0.50)
- If the MOST SIMILAR legal principle is the same or nearly identical: give a HIGH score (0.50-1.0)
- DO NOT give scores like 0.10 or 0.15 to fundamentally different cases - if the most similar legal principle is different, give scores like 0.01, 0.02, or 0.05
- Most cases should get VERY LOW scores (0.00-0.05) because most cases won't be closely related
- Your selectivity level MUST be visible in the score - if the most similar legal principle is fundamentally different, the score should be VERY LOW (0.01-0.05), not 0.10

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
                            "content": "You are a legal research assistant helping a lawyer find relevant cases. CRITICAL: Base scores on the MOST SIMILAR legal principle between the query and the case, NOT the average similarity. If one principle matches very well, give a high score even if other principles don't match. Be EXTREMELY selective - your selectivity must be visible in the scores you assign. If the most similar legal principle is fundamentally different, give VERY LOW scores (0.00-0.05). If it's somewhat related, give LOW scores (0.05-0.20). Only give high scores (0.50+) for closely related legal principles. Show your strict selectivity in the numbers - unrelated cases should get scores like 0.01-0.05, not 0.10. Return only valid JSON.",
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
