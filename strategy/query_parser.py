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

    def validate_query(
        self, query: str, previous_answers: Optional[List[str]] = None
    ) -> Dict:
        """
        Validate a query to determine if it needs clarification.
        If clarification is needed, returns a question to ask the user.
        If previous answers are provided, uses them to generate the next question or proceed.

        Returns:
            {
                'needs_clarification': bool,
                'question': str (if needs_clarification is True),
                'question_number': int (1-3, if needs_clarification is True),
                'enhanced_query': str (if needs_clarification is False, the enhanced query ready for search)
            }
        """
        if self.api_key:
            return self._validate_with_llm(query, previous_answers)
        else:
            # Without API key, assume query is fine
            return {
                "needs_clarification": False,
                "enhanced_query": query,
            }

    def _validate_with_llm(
        self, query: str, previous_answers: Optional[List[str]] = None
    ) -> Dict:
        """Use OpenAI to validate the query and ask clarifying questions if needed"""
        try:
            from openai import OpenAI
            import json

            client = OpenAI(api_key=self.api_key)

            # Build context from previous answers
            context = ""
            if previous_answers:
                context = "\n\nPrevious answers provided by the user:\n"
                for i, answer in enumerate(previous_answers, 1):
                    context += f"{i}. {answer}\n"

            # Calculate current question number based on previous answers
            current_question_num = len(previous_answers) + 1 if previous_answers else 1

            prompt = f"""You are a legal research assistant helping users refine their search queries. Your goal is to ensure the query has:
1. Sufficient context about what's happening in their case (general understanding, doesn't need to be case-specific)
2. Clear legal principles or concepts they're interested in exploring

Current query: "{query}"
{context}

IMPORTANT: Be REASONABLE about asking clarification questions. Ask questions when the query is missing EITHER sufficient context OR legal principles, but don't be overly picky. If the query has reasonable information (even if not perfect), proceed with the search. Only ask if it will genuinely improve the search results.

Analyze this query and determine if it needs clarification. A query needs clarification if:
- It's vague or generic (e.g., "help me", "find cases", "legal issues" with minimal context)
- It lacks context about what's happening in the case (no mention of charges, circumstances, or legal situation)
- It doesn't mention any legal principles, concepts, or legal issues they want to explore
- It's too short (less than 10-15 words) and lacks substance

A query does NOT need clarification if it has BOTH:
- Reasonable context about the case (charges, circumstances, or legal situation mentioned)
- At least one legal principle, concept, or legal issue mentioned

Examples of queries that DO need clarification:
- "help me find cases" (no context, no legal principles)
- "stolen vehicle" (some context but no legal principles mentioned)
- "probable cause" (legal principle but no case context)

Examples of queries that do NOT need clarification:
- "cases about stolen vehicle with lack of probable cause" (has both context and legal principle)
- "defendant charged with knowing possession of stolen motor vehicle" (has context, legal principle implied)
- "lack of evidence for stolen property charges" (has both context and legal principle)

CRITICAL: Question ordering is STRICT and must be followed:
- Question 1 (if needed) MUST ALWAYS be about CONTEXT (what's happening in their case - charges, circumstances, legal situation)
- Question 2 (if needed) MUST ALWAYS be about LEGAL PRINCIPLES (what legal principles or concepts they're interested in exploring)
- DO NOT mix these up - context first, then legal principles

If the query needs clarification AND we haven't asked 2 questions yet:
- If this is question 1: Generate a question about CONTEXT (what charges, circumstances, or legal situation)
- If this is question 2: Generate a question about LEGAL PRINCIPLES (what legal principles or concepts they're interested in exploring)

IMPORTANT: If the question is about legal principles (question 2), you MUST also generate 3-4 suggested legal principles based on the query context and initial query. These should be:
- Relevant to the case context mentioned
- Common legal principles that might apply
- Specific enough to be useful but not overly technical
- Presented as short, clear phrases (e.g., "Lack of probable cause", "Insufficient evidence", "Knowledge requirement")
- CRITICAL: Do NOT suggest legal principles that are already mentioned in the original query or in previous answers
- CRITICAL: Do NOT suggest principles that are essentially the same as ones already mentioned (e.g., don't suggest both "lack of evidence" and "insufficient evidence" if one is already mentioned)
- Only suggest NEW, DISTINCT legal principles that haven't been covered yet

The question should be:
- Simple and concise - ONE sentence only
- Conversational and friendly
- Specific enough to get useful information
- Not too technical or intimidating
- Question 1: Focused ONLY on getting case context (charges, circumstances, legal situation)
- Question 2: Focused ONLY on getting legal principles (what legal concepts they want to explore)
- CRITICAL: Keep it to ONE simple sentence - no compound sentences, no multiple questions, just one clear question

If previous answers were provided, use them to:
- Generate the next clarifying question (if more info is still needed), OR
- Create an enhanced query that combines the original query with the answers (if sufficient info is gathered)

Return your response as JSON in this exact format:
{{
    "needs_clarification": true or false,
    "question": "The question to ask the user" (only if needs_clarification is true),
    "question_type": "context" or "legal_principles" (only if needs_clarification is true),
    "suggested_legal_principles": ["principle 1", "principle 2", ...] (only if question_type is "legal_principles"),
    "question_number": {current_question_num} (only if needs_clarification is true - this should be {current_question_num} based on previous answers),
    "enhanced_query": "The enhanced query ready for search" (only if needs_clarification is false)
}}

Important:
- Current question number is {current_question_num} (based on {len(previous_answers) if previous_answers else 0} previous answer(s))
- Maximum of 2 questions total - if this would be question 3, set needs_clarification to false and provide enhanced_query
- STRICT ORDERING: Question 1 = context, Question 2 = legal principles. DO NOT mix these up.
- Be REASONABLE - ask when genuinely needed (missing context OR legal principles), but proceed if the query has reasonable information
- If the query already has both sufficient context AND legal principles, set needs_clarification to false
- The enhanced_query should combine the original query with all previous answers in a natural way
- When asking about legal principles (question 2), ALWAYS include suggested_legal_principles array with 3-4 relevant suggestions
- When generating suggested_legal_principles, carefully review the original query and all previous answers to identify what legal principles are already mentioned, and ONLY suggest principles that are NOT already covered"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful legal research assistant. Always return valid JSON. Be conversational and friendly when asking questions. Be REASONABLE - ask questions when the query is missing sufficient context OR legal principles, but proceed if it has reasonable information. CRITICAL: Question ordering is STRICT - Question 1 must ALWAYS be about context, Question 2 must ALWAYS be about legal principles. Never mix these up. CRITICAL: Questions must be SIMPLE and ONE sentence only - no compound sentences, no multiple questions. When asking about legal principles (question 2), ALWAYS generate 3-4 relevant suggested legal principles based on the query context. CRITICALLY IMPORTANT: Never suggest legal principles that are already mentioned in the original query or previous answers. Only suggest NEW, DISTINCT principles that haven't been covered yet.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Validate response structure
            if "needs_clarification" not in result:
                result["needs_clarification"] = False
                result["enhanced_query"] = query

            # If needs clarification, ensure question and question_number are present
            if result.get("needs_clarification"):
                if "question" not in result or not result["question"]:
                    result["needs_clarification"] = False
                    result["enhanced_query"] = query
                else:
                    # Calculate expected question number based on previous answers
                    expected_question_num = (
                        len(previous_answers) + 1 if previous_answers else 1
                    )
                    question_num = result.get("question_number", expected_question_num)

                    # Validate question number
                    if question_num > 2:
                        result["needs_clarification"] = False
                        result["enhanced_query"] = query
                    else:
                        # Use the calculated question number to ensure consistency
                        result["question_number"] = expected_question_num

                        # Enforce strict question ordering: Q1 = context, Q2 = legal_principles
                        if expected_question_num == 1:
                            # Question 1 must be about context
                            result["question_type"] = "context"
                        elif expected_question_num == 2:
                            # Question 2 must be about legal principles
                            result["question_type"] = "legal_principles"
                        else:
                            # Fallback to what LLM provided if somehow wrong
                            result["question_type"] = result.get(
                                "question_type", "context"
                            )

                        # If question_type is legal_principles, ensure suggested_legal_principles exists
                        if result.get("question_type") == "legal_principles":
                            if "suggested_legal_principles" not in result:
                                result["suggested_legal_principles"] = []
                            else:
                                # Filter out redundant principles
                                result["suggested_legal_principles"] = (
                                    self._filter_redundant_principles(
                                        result["suggested_legal_principles"],
                                        query,
                                        previous_answers,
                                    )
                                )
                        else:
                            result["question_type"] = result.get(
                                "question_type", "context"
                            )
            else:
                # If no clarification needed, ensure enhanced_query exists
                if "enhanced_query" not in result:
                    result["enhanced_query"] = query

            return result

        except Exception as e:
            logger.warning(
                f"Error validating query with LLM: {e}, proceeding with original query"
            )
            return {
                "needs_clarification": False,
                "enhanced_query": query,
            }

    def _filter_redundant_principles(
        self,
        suggested_principles: List[str],
        query: str,
        previous_answers: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Filter out legal principles that are already mentioned in the query or previous answers.
        Uses simple text matching to identify redundant principles.
        """
        # Combine all existing text to check against
        existing_text = query.lower()
        if previous_answers:
            existing_text += " " + " ".join(previous_answers).lower()

        filtered = []
        for principle in suggested_principles:
            principle_lower = principle.lower().strip()

            # Skip if principle is too short
            if len(principle_lower) < 3:
                continue

            # Check if this principle or very similar wording is already mentioned
            is_redundant = False

            # Direct substring match (principle is mentioned in existing text)
            if principle_lower in existing_text:
                is_redundant = True

            # Check for similar phrases (common variations)
            if not is_redundant:
                # Extract key words from principle
                principle_words = set(principle_lower.split())
                # Remove common stop words
                stop_words = {
                    "the",
                    "a",
                    "an",
                    "of",
                    "in",
                    "on",
                    "at",
                    "to",
                    "for",
                    "with",
                    "by",
                }
                principle_keywords = principle_words - stop_words

                # Check if most keywords appear together in existing text
                if len(principle_keywords) > 0:
                    matches = sum(
                        1 for word in principle_keywords if word in existing_text
                    )
                    # If more than 50% of keywords match, consider it redundant
                    if matches / len(principle_keywords) > 0.5:
                        is_redundant = True

            # Check for common synonyms/variations
            if not is_redundant:
                variations = {
                    "lack of evidence": [
                        "insufficient evidence",
                        "not enough evidence",
                        "absence of evidence",
                    ],
                    "insufficient evidence": [
                        "lack of evidence",
                        "not enough evidence",
                        "absence of evidence",
                    ],
                    "probable cause": ["reasonable suspicion", "reasonable cause"],
                    "knowledge": ["awareness", "knowing", "knowingly"],
                }

                for key, synonyms in variations.items():
                    if key in principle_lower:
                        for synonym in synonyms:
                            if synonym in existing_text:
                                is_redundant = True
                                break
                    if is_redundant:
                        break

            if not is_redundant:
                filtered.append(principle)

        return filtered

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
