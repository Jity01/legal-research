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

    def __init__(self, use_llm: bool = True, max_workers: int = 5):
        # Default to LLM if API key is available, otherwise use text matching
        self.use_llm = use_llm and bool(os.getenv("OPENAI_API_KEY"))
        self.query_parser = QueryParser()
        # Reduced default workers to avoid rate limits
        # Increase only if you have higher tier OpenAI API access
        # NOTE: Even with 5 workers, if all hit rate limits simultaneously,
        # each retries 3 times = 15+ requests. Consider reducing to 2-3.
        self.max_workers = max_workers
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
        limit = limit or 20  # Default to 20 for performance
        
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
        # Get fewer candidates initially - we'll expand if needed
        initial_candidates = max(limit * 3, 50)  # Start with 3x limit, min 50
        candidate_case_ids = self._prefilter_cases(
            client, query_keywords, filter_direction, initial_candidates
        )
        
        if not candidate_case_ids:
            logger.warning("No candidate cases found in pre-filtering")
            return []
        
        logger.debug(f"Pre-filtering found {len(candidate_case_ids)} candidates in {time.time() - prefilter_start:.2f}s")
        
        # Get factors and holdings in parallel (faster)
        # Use batch queries to reduce round trips
        import concurrent.futures
        
        def fetch_factors():
            return (
                client.table("case_factors")
                .select("case_id, factor_text")
                .in_("case_id", candidate_case_ids)
                .execute()
            )
        
        def fetch_holdings():
            return (
                client.table("case_holdings")
                .select("case_id, holding_direction")
                .in_("case_id", candidate_case_ids)
                .execute()
            )
        
        # Fetch in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            factors_future = executor.submit(fetch_factors)
            holdings_future = executor.submit(fetch_holdings)
            
            all_factors = factors_future.result()
            holdings = holdings_future.result()
        
        holding_map = {h["case_id"]: h["holding_direction"] for h in holdings.data}
        
        # Group factors by case
        case_factors_map = {}
        for factor in all_factors.data:
            case_id = factor["case_id"]
            if case_id not in case_factors_map:
                case_factors_map[case_id] = []
            case_factors_map[case_id].append({"text": factor["factor_text"]})
        
        # STAGE 2: Parallel LLM similarity calculation on candidates
        logger.debug(f"Stage 2: Calculating similarity for {len(case_factors_map)} cases in parallel...")
        similarity_start = time.time()
        
        scored_cases = self._calculate_similarities_parallel(
            query_factors, case_factors_map, holding_map, filter_direction, limit
        )
        
        logger.debug(f"Similarity calculation took {time.time() - similarity_start:.2f}s")
        
        # Sort by similarity score (descending)
        scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Apply limit
        if len(scored_cases) > limit:
            scored_cases = scored_cases[:limit]
        
        # Get full case details for matches
        top_case_ids = [c["case_id"] for c in scored_cases]
        
        if not top_case_ids:
            return []
        
        cases = (
            client.table("court_cases").select("*").in_("id", top_case_ids).execute()
        )
        
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
                results.append(case_data)
        
        logger.info(f"Search completed in {time.time() - start_time:.2f}s, returned {len(results)} results")
        return results
    
    def _extract_keywords_for_search(self, query: str, query_factors: List[Dict]) -> str:
        """Extract important keywords from query and factors for text search"""
        # Combine query and factor texts
        all_text = query.lower()
        for factor in query_factors:
            all_text += " " + factor.get("text", "").lower()
        
        # Extract significant words (3+ chars, not common stop words)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was", "are", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can"}
        words = [w for w in all_text.split() if len(w) >= 3 and w not in stop_words]
        
        # Return top 10 most frequent words
        from collections import Counter
        word_counts = Counter(words)
        top_words = [word for word, count in word_counts.most_common(10)]
        return " ".join(top_words)
    
    def _prefilter_cases(
        self, client, query_keywords: str, filter_direction: Optional[str], candidate_limit: int
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
            analyzed = (
                client.table("case_analysis_metadata")
                .select("case_id")
                .eq("is_analyzed", True)
                .limit(candidate_limit)
                .execute()
            )
            return [c["case_id"] for c in analyzed.data] if analyzed.data else []
        
        # Use plainto_tsquery for better matching
        # This searches for cases where factors contain these keywords
        tsquery = " & ".join(keywords_list[:5])  # Limit to 5 keywords for performance
        
        # Query using full-text search
        # We'll use a raw SQL query for better performance with tsvector
        try:
            # Get case IDs where factors match the keywords
            # Using the existing GIN index on factor_text
            result = client.rpc(
                "search_cases_by_factors",
                {
                    "search_query": tsquery,
                    "limit_count": candidate_limit,
                    "direction_filter": filter_direction
                }
            ).execute()
            
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
                    all_factors = (
                        client.table("case_factors")
                        .select("case_id, factor_text")
                        .ilike("factor_text", f"%{primary_keyword}%")
                        .limit(5000)  # Reduced limit for speed
                        .execute()
                    )
                except Exception as query_error:
                    logger.debug(f"ILIKE query failed: {query_error}, using simple text search")
                    # Fallback: get all factors and filter in Python (slower but works)
                    # This is more reliable than trying to fix the ILIKE syntax
                    all_factors = (
                        client.table("case_factors")
                        .select("case_id, factor_text")
                        .limit(5000)
                        .execute()
                    )
                    # Filter in Python
                    if all_factors.data:
                        filtered_factors = [
                            f for f in all_factors.data 
                            if primary_keyword.lower() in f.get("factor_text", "").lower()
                        ]
                        all_factors.data = filtered_factors
            else:
                # Return empty result structure
                class EmptyResult:
                    data = []
                all_factors = EmptyResult()
            
            if not all_factors.data:
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
            candidate_ids = [case_id for case_id, score in sorted_cases[:candidate_limit]]
        except Exception as e:
            logger.debug(f"Optimized query failed, using simple fallback: {e}")
            # Ultra-simple fallback: just get recent analyzed cases
            analyzed = (
                client.table("case_analysis_metadata")
                .select("case_id")
                .eq("is_analyzed", True)
                .limit(candidate_limit)
                .order("analyzed_at", desc=True)
                .execute()
            )
            candidate_ids = [c["case_id"] for c in analyzed.data] if analyzed.data else []
        
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
        filter_direction: Optional[str],
        limit: int = 20
    ) -> List[Dict]:
        """Calculate similarities in parallel with early termination"""
        scored_cases = []
        lock = threading.Lock()
        
        def calculate_one(case_id, case_factors):
            """Calculate similarity for one case"""
            # Skip if direction filter doesn't match
            if filter_direction == "for_defendant":
                if holding_map.get(case_id) != "for_defendant":
                    return None
            
            try:
                similarity_score = self._calculate_similarity(
                    query_factors, case_factors, use_llm=self.use_llm
                )
                
                if similarity_score > 0:
                    return {
                        "case_id": case_id,
                        "similarity_score": similarity_score,
                        "holding_direction": holding_map.get(case_id, "unclear"),
                    }
            except Exception as e:
                logger.debug(f"Error calculating similarity for case {case_id}: {e}")
            return None
        
        # Process in parallel with rate limit protection
        # Add a semaphore to limit concurrent API calls and avoid overwhelming the API
        semaphore = threading.Semaphore(self.max_workers)
        
        def calculate_with_semaphore(case_id, case_factors):
            """Calculate similarity with semaphore protection"""
            with semaphore:
                return calculate_one(case_id, case_factors)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(calculate_with_semaphore, case_id, case_factors): case_id
                for case_id, case_factors in case_factors_map.items()
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        with lock:
                            scored_cases.append(result)
                except Exception as e:
                    logger.debug(f"Error in similarity calculation: {e}")
        
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
                if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
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
