"""
Similarity matcher that finds cases with factors similar to query factors.
Matches based on semantic similarity.
"""

import logging
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase_client

# Import QueryParser - use relative import if in same package, absolute otherwise
try:
    from .query_parser import QueryParser
except ImportError:
    from strategy.query_parser import QueryParser

logger = logging.getLogger(__name__)


class SimilarityMatcher:
    """Matches query factors to case factors using semantic similarity"""

    def __init__(self, use_llm: bool = True):
        # Default to LLM if API key is available, otherwise use text matching
        self.use_llm = use_llm and bool(os.getenv("OPENAI_API_KEY"))
        self.query_parser = QueryParser()

    def find_similar_cases(
        self,
        query: str,
        limit: Optional[int] = None,
        filter_direction: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find cases similar to the query.

        Args:
            query: User's search query
            limit: Maximum number of cases to return (None = return all matches)
            filter_direction: If 'for_defendant', only return cases favorable to defendant

        Returns:
            List of case dictionaries with similarity scores
        """
        # Parse the query
        parsed_query = self.query_parser.parse_query(query)
        query_factors = parsed_query.get("factors", [])
        query_type = parsed_query.get("query_type", "neutral")

        if not query_factors:
            logger.warning("No factors extracted from query")
            return []

        # Get all analyzed cases with their factors
        client = get_supabase_client()

        # Build query to get cases with factors
        # First, get all case IDs that have been analyzed
        analyzed_cases = (
            client.table("case_analysis_metadata")
            .select("case_id")
            .eq("is_analyzed", True)
            .execute()
        )

        if not analyzed_cases.data:
            logger.warning("No analyzed cases found. Run preprocessing first.")
            return []

        case_ids = [c["case_id"] for c in analyzed_cases.data]

        # Get factors for all cases
        all_factors = (
            client.table("case_factors")
            .select("case_id, factor_text")
            .in_("case_id", case_ids)
            .execute()
        )

        # Get holdings for direction filtering
        holdings = (
            client.table("case_holdings")
            .select("case_id, holding_direction")
            .in_("case_id", case_ids)
            .execute()
        )

        holding_map = {h["case_id"]: h["holding_direction"] for h in holdings.data}

        # Group factors by case
        case_factors_map = {}
        for factor in all_factors.data:
            case_id = factor["case_id"]
            if case_id not in case_factors_map:
                case_factors_map[case_id] = []
            case_factors_map[case_id].append({"text": factor["factor_text"]})

        # Calculate similarity scores
        scored_cases = []

        for case_id, case_factors in case_factors_map.items():
            # Skip if direction filter doesn't match
            if filter_direction == "for_defendant":
                if holding_map.get(case_id) != "for_defendant":
                    continue

            similarity_score = self._calculate_similarity(
                query_factors, case_factors, use_llm=self.use_llm
            )

            if similarity_score > 0:  # Only include cases with some similarity
                scored_cases.append(
                    {
                        "case_id": case_id,
                        "similarity_score": similarity_score,
                        "holding_direction": holding_map.get(case_id, "unclear"),
                    }
                )

        # Sort by similarity score (descending)
        scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Apply limit only if specified and if we have more results than the limit
        if limit is not None and len(scored_cases) > limit:
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

        return results

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
        """Use LLM to calculate semantic similarity"""
        try:
            from openai import OpenAI

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

        except Exception as e:
            logger.error(f"Error calculating similarity with LLM: {e}")
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
