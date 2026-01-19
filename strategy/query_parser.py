"""
Query parser that breaks down user queries into legal principles/factors.
Extracts all distinct legal principles from the query with full context.
"""

import logging
from typing import Dict, List, Optional
import os
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Rate limiter removed - no retries, fail fast


class QueryParser:
    """Parses user queries into legal principles/factors with full query context"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning(
                "No OpenAI API key found. Query parsing will use fallback method."
            )

    def parse_query(self, query: str) -> Dict:
        """
        Parse a query into legal principles/factors with full context.

        Returns:
            {
                'factors': [
                    {'text': str, 'type': str},
                    ...
                ],
                'query_type': str  # e.g., 'defendant_favor', 'plaintiff_favor'
            }
        """
        if self.api_key:
            return self._parse_with_llm(query)
        else:
            return self._parse_fallback(query)

    def _parse_with_llm(self, query: str) -> Dict:
        """Use OpenAI to parse the query with rate limit handling"""
        try:
            from openai import OpenAI
            import time

            client = OpenAI(api_key=self.api_key)

            prompt = f"""You are a legal research assistant. Extract ALL distinct legal principles, concepts, and legal reasoning from the following user query. Each factor must be a legal principle with embedded query context.

Query: "{query}"

CRITICAL INSTRUCTIONS:
- Extract ALL distinct legal principles, concepts, or legal reasoning mentioned in the query
- Each factor MUST be completely self-contained and readable WITHOUT the original query
- Each factor MUST state the legal principle and the context from the query (what charges, what circumstances, what legal issues are mentioned)
- DO NOT assume what the user is asking for or searching for - just state the legal principles in the context mentioned in the query
- USE THE EXACT VERBIAGE FROM THE QUERY - do not rephrase or assume specifics that aren't explicitly stated
- If the query says "lack of sufficient evidence", use that exact phrase - do not assume which specific element (knowledge, possession, etc.) it refers to
- If the query says "lack of probable cause", use that exact phrase - do not elaborate on what specific aspect of probable cause
- Each factor MUST be a legal principle (not just a bare fact or keyword)
- Each factor should be a complete sentence (minimum 20 words, preferably 25-40 words)
- Frame factors as legal principles with embedded context from the query, using the query's exact wording

Examples of GOOD factors (using exact query verbiage):
- Query: "give me cases where a defendant was charged with knowing stolen motor vehicle but had lack of probable cause"
  Factor: "The legal principle that lack of probable cause can be a defense applies in the context of a defendant charged with knowing possession of a stolen motor vehicle, where there was lack of probable cause."
- Query: "give me cases where a defendant was charged with knowing stolen motor vehicle but had lack of sufficient evidence"
  Factor: "The legal principle that lack of sufficient evidence can be a defense applies in the context of a defendant charged with knowing possession of a stolen motor vehicle, where there was lack of sufficient evidence."

Examples of BAD factors (DO NOT USE):
- "where the prosecution may have failed to present sufficient evidence to establish the defendant's knowledge that the vehicle was stolen" (assumes it's about knowledge - use exact query wording instead)
- "where the prosecution may have lacked sufficient probable cause to support the charge" (assumes specifics - use exact query wording instead)
- "The user is searching for cases where..." (don't assume what user is searching for)
- "knowing stolen motor vehicle" (too short, no context, not a legal principle)

Also identify:
- The query type (whether the user is looking for cases favorable to defendant, plaintiff, or neutral)

Return your response as JSON in this exact format:
{{
    "query_type": "defendant_favor" or "plaintiff_favor" or "neutral",
    "factors": [
        {{
            "text": "legal principle with full query context",
            "type": "legal_principle" or "concept"
        }},
        ...
    ]
}}

Extract ALL distinct legal principles from the query - do not miss any, no matter how small."""

            # Make request without retries - fail fast
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a legal research assistant. Always return valid JSON. Extract ALL distinct legal principles from the query with full context. Each factor must be self-contained and state the legal principle in the context mentioned in the query. Use the EXACT verbiage from the query - do not rephrase or assume specifics that aren't explicitly stated. Do not assume what the user is searching for - just state the legal principles in the context provided using the query's exact wording.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                import json

                result = json.loads(response.choices[0].message.content)

                # Validate
                if "factors" not in result or len(result["factors"]) == 0:
                    logger.warning("LLM didn't return any factors, using fallback")
                    return self._parse_fallback(query)

                # Ensure query_type exists
                if "query_type" not in result:
                    result["query_type"] = "neutral"

                return result

            except Exception as api_error:
                error_str = str(api_error).lower()
                # Check if it's a rate limit or quota error - fall back immediately
                if (
                    "429" in error_str
                    or "rate limit" in error_str
                    or "quota" in error_str
                    or "insufficient_quota" in error_str
                ):
                    logger.warning(
                        f"Rate limit/quota hit in query parser, using fallback immediately: {error_str}"
                    )
                    return self._parse_fallback(query)
                else:
                    # Non-rate-limit error, re-raise
                    raise

        except Exception as e:
            logger.warning(f"Error parsing query with LLM: {e}, using fallback")
            return self._parse_fallback(query)

    def _parse_fallback(self, query: str) -> Dict:
        """Fallback parsing method using simple heuristics"""
        query_lower = query.lower()

        # Try to identify query type
        if any(word in query_lower for word in ["defendant", "accused", "charged"]):
            query_type = "defendant_favor"
        elif any(word in query_lower for word in ["plaintiff", "prosecution"]):
            query_type = "plaintiff_favor"
        else:
            query_type = "neutral"

        # Extract key legal concepts and create contextual factors
        import re

        # Common legal terms to look for
        legal_terms = {
            "probable cause": "The legal principle that probable cause is required for searches and seizures applies when the user is searching for cases where defendants were charged but the prosecution lacked probable cause to support the charge.",
            "lack of evidence": "The legal principle that sufficient evidence is required for conviction applies when the user is searching for cases where defendants were charged but the prosecution lacked sufficient evidence to establish the elements of the crime.",
            "stolen": "The legal principle that knowledge of stolen property is required for conviction applies when the user is searching for cases involving stolen property where the defendant's knowledge of the property's stolen status is at issue.",
            "motor vehicle": "The legal principle that knowing possession of a stolen motor vehicle requires proof of the defendant's knowledge applies when the user is searching for cases involving stolen motor vehicles.",
        }

        factors = []
        for term, factor_text in legal_terms.items():
            if term in query_lower:
                # Enhance with query context
                enhanced_factor = f"{factor_text} The user's query asks: '{query}'"
                factors.append({"text": enhanced_factor, "type": "legal_principle"})

        # If no specific legal terms found, create a general factor with query context
        if not factors:
            factors.append(
                {
                    "text": f"The query mentions: {query}. This involves legal principles related to the charges, circumstances, and legal issues mentioned in the query.",
                    "type": "legal_principle",
                }
            )

        return {"query_type": query_type, "factors": factors}
