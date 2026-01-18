"""
Citation extractor that finds cases citing a given case.
Also attempts to match citation text to actual case IDs in the database.
"""

import logging
from typing import Dict, List, Optional
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase_client

logger = logging.getLogger(__name__)


class CitationExtractor:
    """Extracts and matches citations between cases"""

    def get_citing_cases(self, case_id: int) -> List[Dict]:
        """
        Get all cases that cite the given case.

        Returns:
            List of case dictionaries that cite this case
        """
        client = get_supabase_client()

        # Get all citations that reference this case
        citations = (
            client.table("case_citations")
            .select("citing_case_id, citation_text, citation_context")
            .eq("cited_case_id", case_id)
            .execute()
        )

        if not citations.data:
            return []

        # Get the citing cases
        citing_case_ids = list(set(c["citing_case_id"] for c in citations.data))

        if not citing_case_ids:
            return []

        cases = (
            client.table("court_cases")
            .select("id, case_name, citation, docket_number, decision_date, court_name")
            .in_("id", citing_case_ids)
            .execute()
        )

        # Add citation context to each case
        citation_map = {}
        for citation in citations.data:
            citing_id = citation["citing_case_id"]
            if citing_id not in citation_map:
                citation_map[citing_id] = []
            citation_map[citing_id].append(
                {
                    "text": citation["citation_text"],
                    "context": citation["citation_context"],
                }
            )

        results = []
        for case in cases.data:
            case_id = case["id"]
            case["citation_contexts"] = citation_map.get(case_id, [])
            results.append(case)

        return results

    def match_citation_to_case(self, citation_text: str) -> Optional[int]:
        """
        Try to match a citation text to a case ID in the database.

        Returns:
            Case ID if found, None otherwise
        """
        if not citation_text or len(citation_text.strip()) < 5:
            return None

        client = get_supabase_client()

        # Try exact match on citation field
        try:
            # Clean and sanitize citation text
            clean_citation = citation_text.strip()
            if len(clean_citation) > 200:
                clean_citation = clean_citation[:200]
            
            # Remove problematic characters that might cause SQL issues
            # Keep only alphanumeric, spaces, periods, commas, parentheses, and basic punctuation
            clean_citation = re.sub(r'[^\w\s.,()\-&]', '', clean_citation)
            
            if len(clean_citation) < 5:
                return None

            result = (
                client.table("court_cases")
                .select("id")
                .ilike("citation", f"%{clean_citation}%")
                .limit(1)
                .execute()
            )

            if result.data:
                return result.data[0]["id"]
        except Exception as e:
            logger.debug(f"Error matching citation by citation field: {e}")
            # Don't try case name search if citation search failed with an error
            return None

        # Skip case name search - it's causing too many 500 errors
        # The citation field search is more reliable
        return None
