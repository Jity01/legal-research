"""
Case analyzer that extracts factors, concepts, and holdings from court opinions.
Uses LLM to identify legal principles and concepts from cases.
"""

import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import re

load_dotenv()

logger = logging.getLogger(__name__)


class CaseAnalyzer:
    """Analyzes court cases to extract factors, holdings, and citations"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning(
                "No OpenAI API key found. Case analysis will use fallback method."
            )

    def analyze_case(self, case: Dict) -> Dict:
        """
        Analyze a case and extract:
        - Factors/concepts (legal principles)
        - Holding text and direction
        - Citations to other cases

        Args:
            case: Dictionary with case data including 'opinion_text'

        Returns:
            {
                'factors': [
                    {'text': str, 'type': str},
                    ...
                ],
                'holding': {
                    'text': str,
                    'direction': str,  # 'for_defendant', 'against_defendant', etc.
                    'confidence': float
                },
                'citations': [
                    {'citation_text': str, 'context': str},
                    ...
                ]
            }
        """
        opinion_text = case.get("opinion_text", "")
        if not opinion_text or len(opinion_text) < 100:
            logger.warning(f"Case {case.get('id')} has insufficient opinion text")
            return self._empty_analysis()

        if self.api_key:
            return self._analyze_with_llm(case, opinion_text)
        else:
            return self._analyze_fallback(case, opinion_text)

    def _analyze_with_llm(self, case: Dict, opinion_text: str) -> Dict:
        """Use OpenAI to analyze the case"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Truncate if too long (keep first 8000 chars for context)
            truncated_text = (
                opinion_text[:8000] if len(opinion_text) > 8000 else opinion_text
            )

            prompt = f"""Analyze the following court opinion and extract:

1. ALL distinct legal principles, concepts, and legal reasoning that influenced the court's decision
2. The holding (the court's final decision/rule)
3. Whether the holding is favorable to the defendant or against the defendant
4. Citations to other cases (legal citations in standard format)

CRITICAL - EXTRACT ALL LEGAL PRINCIPLES: Extract EVERY SINGLE distinct legal issue, principle, doctrine, concept, standard, rule, or legal reasoning that the court addressed or that arose in this case, NO MATTER HOW SMALL OR MINOR IT MAY SEEM. This includes:
- Legal principles that arise from the defendant's actions or conduct
- Legal principles that arise from documents, evidence, or exhibits
- Legal principles that arise from witness testimony or statements
- Legal principles that arise from procedural steps or motions
- Legal principles that arise from constitutional provisions, statutes, or regulations
- Legal principles that arise from case law or precedents cited
- Legal principles that arise from arguments made by either party
- Legal principles that arise from the court's own analysis or reasoning
- Legal principles that arise from any other source mentioned in the opinion
- Even seemingly minor or tangential legal principles - if it's mentioned, extract it

Do NOT miss ANY legal principle, NO MATTER HOW SMALL, MINOR, OR INSIGNIFICANT IT MAY APPEAR. Even if a legal principle is only briefly mentioned, tangentially discussed, or appears to be a minor point, it MUST be extracted as a factor. The number of factors should correspond to the number of distinct legal issues - if the case addresses 3 legal issues, extract 3 factors; if it addresses 15 legal issues, extract 15 factors. If a legal principle is mentioned, discussed, or applied anywhere in the opinion, it MUST be included as a factor. It is better to include all relevant legal principles (even minor ones) than to miss any.

IMPORTANT: Focus ONLY on legal principles and concepts. Do NOT extract bare facts. Instead, weave the specific facts of this case INTO the legal principles to show how the law applies to these particular circumstances.

Case: {case.get('case_name', 'Unknown')}
Court: {case.get('court_name', 'Unknown')}
Date: {case.get('decision_date', 'Unknown')}

Opinion Text:
{truncated_text}

Return your response as JSON in this exact format:
{{
    "factors": [
        {{
            "text": "legal principle with embedded case facts and court reaction",
            "type": "legal_principle" or "concept"
        }},
        ...
    ],
    "holding": {{
        "text": "the court's holding or final decision",
        "direction": "for_defendant" or "against_defendant" or "mixed" or "unclear",
        "confidence": 0.9
    }},
    "citations": [
        {{
            "citation_text": "e.g., Smith v. Jones, 123 Mass. 456 (2020)",
            "context": "brief context of how it was cited"
        }},
        ...
    ]
}}

CRITICAL INSTRUCTIONS FOR FACTORS:
- Focus ONLY on LEGAL PRINCIPLES and CONCEPTS - do NOT extract bare facts
- Weave the specific facts of this case INTO the legal principles to show how the law applies
- Each factor MUST be a legal principle, concept, or legal reasoning with embedded case facts
- Each factor MUST be completely self-contained and readable WITHOUT any prior knowledge of the case
- Each factor MUST include ALL necessary background: WHO is being sued/prosecuted, WHY (what charges/allegations), and the specific facts woven into the legal principle
- Each factor MUST be a complete, contextual sentence or phrase (minimum 20 words, preferably 25-40 words)
- DO NOT use single words or short phrases like "probable cause" or "evidence"
- ALWAYS frame factors as legal principles with embedded facts, and ALWAYS conclude with how the court reacted/applied this principle (e.g., "The legal principle that [legal concept] applies when [specific facts of this case], where [defendant's role/charges] and [what happened], because [legal reasoning], and the court [found/rejected/applied] this principle [in favor of/against] the defendant.")
- Each factor MUST end with a statement about how the court reacted to or applied this legal principle (e.g., "and the court rejected this argument", "and the court found this favored the defendant", "and the court applied this principle against the defendant", "and the court determined this did not prejudice the defendant")
- Examples of GOOD factors (legal principles with embedded facts, including court reaction):
  * "The legal principle that legislative immunity under art. 21 of the Massachusetts Declaration of Rights does not extend to campaign activities applies when a state senator, who was indicted for using his Senate staff to perform campaign work during business hours, argues that directing staff is a fundamental legislative act, because campaign activities are political rather than legislative in nature and fall outside the scope of protected legislative functions, and the court rejected the defendant's immunity claim, finding that he was not immune from prosecution."
  * "The court applied the separation of powers doctrine to determine that a state senator charged with violating the conflict of interest statute by using public resources for his 2018 and 2020 reelection campaigns was not immune from prosecution, because the Legislature's authority to discipline its own members does not displace the executive branch's authority to prosecute violations of criminal statutes, and the court concluded that the separation of powers did not bar the prosecution."
  * "The procedural principle that prosecutors may not exclude grand jurors for bias without judicial involvement applies when a prosecutor, presenting a case against a state senator indicted for misusing Senate staff, excludes a grand juror who expressed political bias without obtaining court approval, and the court found this procedural error was improper but did not prejudice the defendant because the excluded juror's bias would have been harmful to the defendant's interests."
- Examples of BAD factors (DO NOT USE):
  * "The prosecutor excluded a grand juror" (bare fact, not a legal principle)
  * "The defendant was a state senator" (bare fact, no legal principle)
  * "Legislative immunity" (too short, no context, no embedded facts)
  * "The court found procedural error" (missing legal principle and case context)
- Each factor should be a LEGAL PRINCIPLE that:
  1. States the legal concept, doctrine, or principle
  2. Weaves in WHO is involved (defendant's full role/identity, what they're charged with/accused of)
  3. Weaves in WHAT happened (specific facts, events, actions) as part of the legal analysis
  4. Explains WHY it matters (the legal reasoning, how the principle applies to these facts, impact on the case)
  5. Concludes with HOW THE COURT REACTED (e.g., "and the court rejected this argument", "and the court found this favored the defendant", "and the court applied this principle against the defendant")
- Always include the court's reaction/position within the factor text itself - do not leave it implied
- ENSURE UNIQUENESS: Each factor must cover a DISTINCT legal principle or concept - do not repeat similar legal principles
- Capture NUANCES and DETAILS: Include specific legal standards, procedural requirements, constitutional provisions, statutory interpretations, and how they apply to the specific facts
- If a factor is just a fact without a legal principle, rewrite it to frame it as a legal principle with embedded facts

For holding direction:
- "for_defendant" = ruling favors defendant (e.g., charges dismissed, acquittal, reversal in favor)
- "against_defendant" = ruling against defendant (e.g., conviction upheld, motion denied)
- "mixed" = partial victory for both sides
- "unclear" = cannot determine from the text

FACTOR UNIQUENESS AND COMPLETENESS REQUIREMENTS:
- Each factor must cover a DISTINCT and UNIQUE legal principle or concept
- Do NOT create multiple factors that cover the same legal principle or concept
- If two factors would cover similar legal ground, combine them into one comprehensive factor OR focus each on a different legal nuance
- Review all factors before returning to ensure no duplication or excessive overlap
- Each factor should add a new legal principle or concept not covered by other factors
- MOST IMPORTANTLY: Extract ALL distinct legal issues - do not miss ANY legal principles, doctrines, standards, or concepts that the court addressed or that arose from ANY source (actions, documents, witnesses, evidence, motions, arguments, etc.), NO MATTER HOW SMALL OR MINOR
- If the case discusses multiple legal issues (e.g., legislative immunity, separation of powers, grand jury procedures), extract a factor for EACH distinct legal issue
- If a legal principle arises from witness testimony, extract it - even if it seems minor
- If a legal principle arises from documents or evidence, extract it - even if it seems minor
- If a legal principle arises from a motion or procedural step, extract it - even if it seems minor
- If a legal principle arises from an argument made by a party, extract it - even if it seems minor
- If a legal principle is mentioned anywhere in the opinion, extract it - even if it's only briefly mentioned or seems tangential
- If a legal principle appears to be a minor point or footnote, extract it anyway
- The number of factors should match the number of distinct legal issues in the case - be comprehensive, thorough, and do not skip ANY legal principles, no matter how small
- Before finalizing, review the entire opinion again to ensure you haven't missed any legal principles that were discussed, mentioned, or alluded to, regardless of how minor they may seem

REMEMBER: Every factor must be a LEGAL PRINCIPLE with embedded facts, not a bare fact. Frame everything as legal reasoning, legal concepts, or legal doctrines applied to the specific circumstances of this case.

Be thorough, comprehensive, and accurate. Ensure ALL distinct legal issues are captured. Ensure all factors are legal principles with embedded facts, descriptive, contextual, self-contained, and unique."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal research assistant. Always return valid JSON. Be thorough and comprehensive in extracting factors and citations. Extract ALL distinct legal issues - do not miss ANY legal principles, doctrines, or concepts, NO MATTER HOW SMALL OR MINOR, regardless of whether they arise from actions, documents, witnesses, evidence, motions, arguments, or any other source. Even if a legal principle seems minor, tangential, or only briefly mentioned, it MUST be extracted. Each factor must be completely self-contained with full case context, unique from other factors, and capture nuanced details. The number of factors should match the number of distinct legal issues in the case. Review the entire opinion multiple times to ensure no legal principles are missed, including minor ones.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Validate structure
            if "factors" not in result:
                result["factors"] = []
            if "holding" not in result:
                result["holding"] = {
                    "text": "Unable to extract",
                    "direction": "unclear",
                    "confidence": 0.0,
                }
            if "citations" not in result:
                result["citations"] = []

            # Filter and validate factors
            if result["factors"]:
                # Filter out single-word or very short factors
                validated_factors = []
                case_name = case.get("case_name", "").lower()
                # Extract key parties/entities from case name for context checking
                case_context_terms = []
                if case_name:
                    # Try to extract party names from case name (e.g., "DEAN TRAN vs. COMMONWEALTH")
                    parts = case_name.split(" vs. ") or case_name.split(" v. ")
                    if len(parts) > 1:
                        case_context_terms.extend(
                            [p.strip().lower() for p in parts[:2]]
                        )

                for factor in result["factors"]:
                    factor_text = factor.get("text", "").strip()
                    # Must be at least 15 words
                    word_count = len(factor_text.split())

                    # Check if factor includes case context (mentions parties, specific facts, or case details)
                    has_context = False
                    factor_lower = factor_text.lower()

                    # Check for common context indicators and legal principle indicators
                    context_indicators = [
                        "defendant",
                        "plaintiff",
                        "petitioner",
                        "respondent",
                        "court found",
                        "court held",
                        "court concluded",
                        "the case",
                        "this case",
                        "the matter",
                        "charged with",
                        "indicted",
                        "alleged",
                        "claimed",
                        "argued that",
                        "contended that",
                        "asserted that",
                    ]

                    # Check for legal principle indicators (to ensure it's a legal principle, not just a fact)
                    legal_principle_indicators = [
                        "legal principle",
                        "doctrine",
                        "standard",
                        "rule",
                        "statute",
                        "constitutional",
                        "immunity",
                        "jurisdiction",
                        "procedural",
                        "substantive",
                        "applies when",
                        "applies to",
                        "requires",
                        "provides that",
                        "establishes",
                        "determines",
                        "analysis",
                        "reasoning",
                        "interpretation",
                        "construction",
                    ]

                    # Check if factor mentions case parties or has contextual language
                    if any(
                        indicator in factor_lower for indicator in context_indicators
                    ):
                        has_context = True

                    # Check if factor is a legal principle (not just a bare fact)
                    has_legal_principle = any(
                        indicator in factor_lower
                        for indicator in legal_principle_indicators
                    )

                    # If it doesn't have explicit legal principle language, check if it's framed as legal reasoning
                    if not has_legal_principle:
                        # Check for implicit legal principle framing (mentions of law, court analysis, etc.)
                        implicit_legal_terms = [
                            "court",
                            "law",
                            "legal",
                            "principle",
                            "applies",
                            "because",
                            "therefore",
                            "thus",
                            "conclusion",
                            "determination",
                            "finding",
                        ]
                        if any(term in factor_lower for term in implicit_legal_terms):
                            has_legal_principle = True

                    # Check if factor mentions parties from case name
                    if case_context_terms:
                        for term in case_context_terms:
                            if term and len(term) > 3 and term in factor_lower:
                                has_context = True
                                break

                    # Must be at least 20 words, have context, be a legal principle, and not be just a concept name
                    if (
                        word_count >= 20
                        and has_context
                        and has_legal_principle
                        and not factor_text.lower()
                        in [
                            "probable cause",
                            "evidence",
                            "reasonable",
                            "standard",
                            "burden",
                            "motion",
                            "dismiss",
                            "conviction",
                            "acquittal",
                            "reversal",
                        ]
                    ):
                        validated_factors.append(factor)
                    else:
                        logger.debug(
                            f"Filtered out factor (words: {word_count}, has_context: {has_context}, has_legal_principle: {has_legal_principle}): {factor_text[:80]}"
                        )

                # Remove duplicate or highly similar factors
                unique_factors = []
                seen_concepts = set()
                for factor in validated_factors:
                    factor_text = factor.get("text", "").strip()
                    factor_lower = factor_text.lower()

                    # Extract key concepts/words (first 5-7 significant words) to detect duplicates
                    words = [
                        w for w in factor_lower.split() if len(w) > 4
                    ]  # Words longer than 4 chars
                    if len(words) >= 3:
                        key_concept = " ".join(
                            sorted(words[:5])
                        )  # Use first 5 significant words
                    else:
                        key_concept = factor_lower[:50]  # Fallback to first 50 chars

                    # Check if this factor is too similar to an existing one
                    is_duplicate = False
                    for seen in seen_concepts:
                        # Check for high overlap in key words
                        seen_words = set(seen.split())
                        current_words = set(key_concept.split())
                        overlap = len(seen_words & current_words)
                        if overlap >= 3 and len(seen_words) > 0:
                            overlap_ratio = overlap / len(seen_words)
                            if overlap_ratio > 0.6:  # More than 60% overlap
                                is_duplicate = True
                                logger.debug(
                                    f"Filtered out duplicate factor: {factor_text[:80]}"
                                )
                                break

                    if not is_duplicate:
                        unique_factors.append(factor)
                        seen_concepts.add(key_concept)

                result["factors"] = unique_factors

            return result

        except Exception as e:
            logger.error(f"Error analyzing case with LLM: {e}")
            return self._analyze_fallback(case, opinion_text)

    def _analyze_fallback(self, case: Dict, opinion_text: str) -> Dict:
        """Fallback analysis using heuristics and regex"""
        factors = []
        holding = {
            "text": "Unable to extract",
            "direction": "unclear",
            "confidence": 0.0,
        }
        citations = []

        # Extract citations using regex patterns
        citation_patterns = [
            r"\d+\s+[A-Z][a-z]+\s+\d+\s*\([0-9]{4}\)",  # e.g., "123 Mass. 456 (2020)"
            r"[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+",  # e.g., "Smith v. Jones"
        ]

        for pattern in citation_patterns:
            matches = re.finditer(pattern, opinion_text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(opinion_text), match.end() + 50)
                context = opinion_text[start:end].strip()
                citations.append({"citation_text": match.group(), "context": context})

        # Try to find holding section
        holding_keywords = [
            "holding",
            "we hold",
            "we conclude",
            "we find",
            "decision",
            "ruling",
        ]
        for keyword in holding_keywords:
            idx = opinion_text.lower().find(keyword)
            if idx != -1:
                holding_text = opinion_text[idx : idx + 500].strip()
                holding["text"] = holding_text
                break

        # Extract contextual factors (better approach)
        # Look for sentences that contain legal concepts and extract them with context
        sentences = re.split(r"[.!?]+", opinion_text)

        legal_concepts = {
            "probable cause": "probable cause",
            "reasonable suspicion": "reasonable suspicion",
            "evidence": "evidence",
            "burden of proof": "burden",
            "motion to dismiss": "motion",
            "standard of review": "standard",
        }

        for concept_key, concept_term in legal_concepts.items():
            # Find sentences that mention this concept
            relevant_sentences = [
                s.strip()
                for s in sentences
                if concept_term.lower() in s.lower() and len(s.split()) >= 10
            ]

            if relevant_sentences:
                # Take the first relevant sentence and create a contextual factor
                context_sentence = relevant_sentences[0]
                # Limit to reasonable length
                if len(context_sentence) > 200:
                    context_sentence = context_sentence[:200] + "..."

                # Check if concept appears multiple times (indicates importance)
                count = opinion_text.lower().count(concept_term.lower())

                if count > 0 and len(context_sentence.split()) >= 10:
                    factors.append(
                        {
                            "text": context_sentence,
                            "type": "legal_principle",
                        }
                    )

        # Try to determine holding direction
        text_lower = opinion_text.lower()
        if any(
            word in text_lower
            for word in ["dismissed", "reversed", "acquitted", "granted", "favor"]
        ):
            holding["direction"] = "for_defendant"
            holding["confidence"] = 0.6
        elif any(
            word in text_lower
            for word in ["affirmed", "denied", "conviction", "upheld"]
        ):
            holding["direction"] = "against_defendant"
            holding["confidence"] = 0.6

        return {
            "factors": factors[:10],  # Limit to 10
            "holding": holding,
            "citations": citations[:20],  # Limit to 20
        }

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "factors": [],
            "holding": {
                "text": "No opinion text available",
                "direction": "unclear",
                "confidence": 0.0,
            },
            "citations": [],
        }
