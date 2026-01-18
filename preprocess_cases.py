"""
Preprocessing script to analyze all cases in the database.
Extracts factors, holdings, and citations from each case.
"""

import logging
import sys
import os
from typing import Dict, List
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client, get_case_by_id
from strategy.case_analyzer import CaseAnalyzer
from strategy.citation_extractor import CitationExtractor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def preprocess_all_cases(batch_size: int = 10, start_from: int = 0, force: bool = False):
    """
    Preprocess all cases in the database.
    
    Args:
        batch_size: Number of cases to process in each batch
        start_from: Case ID to start from (for resuming)
        force: If True, re-analyze cases even if already analyzed
    """
    client = get_supabase_client()
    analyzer = CaseAnalyzer()
    citation_extractor = CitationExtractor()

    # Get all cases that haven't been analyzed
    logger.info("Fetching cases to analyze...")

    # Get all cases
    all_cases = (
        client.table("court_cases")
        .select("id, opinion_text")
        .gte("id", start_from)
        .order("id")
        .execute()
    )

    if not all_cases.data:
        logger.info("No cases found to analyze")
        return

    total_cases = len(all_cases.data)
    logger.info(f"Found {total_cases} cases to analyze")

    # Process in batches
    for i in tqdm(range(0, total_cases, batch_size), desc="Processing batches"):
        batch = all_cases.data[i : i + batch_size]

        for case_data in batch:
            case_id = case_data["id"]

            try:
                # Check if already analyzed (unless force is True)
                if not force:
                    existing = (
                        client.table("case_analysis_metadata")
                        .select("id")
                        .eq("case_id", case_id)
                        .eq("is_analyzed", True)
                        .execute()
                    )

                    if existing.data:
                        logger.debug(f"Case {case_id} already analyzed, skipping")
                        continue

                # Get full case data
                full_case = get_case_by_id(case_id)
                if not full_case:
                    logger.warning(f"Case {case_id} not found")
                    continue

                # Analyze the case
                logger.debug(
                    f"Analyzing case {case_id}: {full_case.get('case_name', 'Unknown')}"
                )
                analysis = analyzer.analyze_case(full_case)

                # Save factors (delete existing first to avoid duplicates)
                if analysis.get("factors"):
                    try:
                        # Delete existing factors for this case to avoid duplicates
                        client.table("case_factors").delete().eq(
                            "case_id", case_id
                        ).execute()
                    except Exception as e:
                        logger.debug(
                            f"Error deleting existing factors for case {case_id}: {e}"
                        )

                    factors_data = []
                    for factor in analysis["factors"]:
                        factor_text = factor.get("text", "").strip()
                        
                        # Validate factor: must be at least 10 words and not just a keyword
                        if factor_text:
                            word_count = len(factor_text.split())
                            # Reject single words or very short phrases
                            if word_count < 10:
                                logger.debug(
                                    f"Filtered out short factor for case {case_id}: {factor_text[:50]}"
                                )
                                continue
                            
                            # Reject common single-word legal terms without context
                            single_word_terms = [
                                "probable cause", "evidence", "reasonable", "standard",
                                "burden", "motion", "dismiss", "conviction", "acquittal", "reversal"
                            ]
                            if factor_text.lower().strip() in single_word_terms:
                                logger.debug(
                                    f"Filtered out non-contextual factor for case {case_id}: {factor_text}"
                                )
                                continue
                            
                            factors_data.append(
                                {
                                    "case_id": case_id,
                                    "factor_text": factor_text,
                                    "factor_type": factor.get("type", "concept"),
                                }
                            )

                    if factors_data:
                        try:
                            client.table("case_factors").insert(factors_data).execute()
                        except Exception as e:
                            logger.error(
                                f"Error inserting factors for case {case_id}: {e}"
                            )

                # Save holding (check if exists first, then update or insert)
                holding = analysis.get("holding", {})
                if holding.get("text"):
                    try:
                        # Check if holding already exists
                        existing_holding = (
                            client.table("case_holdings")
                            .select("id")
                            .eq("case_id", case_id)
                            .execute()
                        )

                        holding_data = {
                            "case_id": case_id,
                            "holding_text": holding.get("text", ""),
                            "holding_direction": holding.get("direction", "unclear"),
                            "confidence": holding.get("confidence", 0.0),
                        }

                        if existing_holding.data:
                            # Update existing
                            client.table("case_holdings").update(holding_data).eq(
                                "case_id", case_id
                            ).execute()
                        else:
                            # Insert new
                            client.table("case_holdings").insert(holding_data).execute()
                    except Exception as e:
                        logger.debug(f"Error saving holding for case {case_id}: {e}")

                # Save citations (with better error handling)
                citations = analysis.get("citations", [])
                if citations:
                    citations_data = []
                    for citation in citations:
                        citation_text = citation.get("citation_text", "").strip()
                        if citation_text and len(citation_text) > 5:
                            try:
                                # Try to match to a case ID (silently fail if it doesn't work)
                                cited_case_id = citation_extractor.match_citation_to_case(
                                    citation_text
                                )
                            except Exception:
                                # Silently fail - citation matching is best-effort
                                cited_case_id = None

                            if citation_text:  # Only add if we have valid text
                                citations_data.append(
                                    {
                                        "citing_case_id": case_id,
                                        "cited_case_id": cited_case_id,
                                        "citation_text": citation_text[:500],  # Limit length
                                        "citation_context": citation.get("context", "")[:1000] if citation.get("context") else None,
                                    }
                                )

                    if citations_data:
                        # Insert citations one at a time to handle duplicates gracefully
                        for cit_data in citations_data:
                            try:
                                client.table("case_citations").insert(cit_data).execute()
                            except Exception:
                                # Silently skip duplicates or other errors
                                # Citations are best-effort, don't spam logs
                                pass

                # Mark as analyzed (check if exists first, then update or insert)
                try:
                    existing_metadata = (
                        client.table("case_analysis_metadata")
                        .select("id")
                        .eq("case_id", case_id)
                        .execute()
                    )

                    metadata_data = {
                        "case_id": case_id,
                        "is_analyzed": True,
                        "analyzed_at": "now()",
                    }

                    if existing_metadata.data:
                        # Update existing
                        client.table("case_analysis_metadata").update(metadata_data).eq(
                            "case_id", case_id
                        ).execute()
                    else:
                        # Insert new
                        client.table("case_analysis_metadata").insert(
                            metadata_data
                        ).execute()
                except Exception as e:
                    logger.debug(f"Error saving metadata for case {case_id}: {e}")

                logger.debug(f"Successfully analyzed case {case_id}")

            except Exception as e:
                # Only log error if it's not a known/expected issue
                error_msg = str(e)
                if "duplicate key" not in error_msg.lower() and "timeout" not in error_msg.lower():
                    logger.warning(f"Error analyzing case {case_id}: {error_msg[:200]}")
                else:
                    logger.debug(f"Expected error for case {case_id}: {error_msg[:100]}")

                # Mark as error (use same check-then-update/insert pattern)
                try:
                    existing_metadata = (
                        client.table("case_analysis_metadata")
                        .select("id")
                        .eq("case_id", case_id)
                        .execute()
                    )
                    
                    error_data = {
                        "case_id": case_id,
                        "is_analyzed": False,
                        "error_message": error_msg[:500],
                    }
                    
                    if existing_metadata.data:
                        client.table("case_analysis_metadata").update(error_data).eq(
                            "case_id", case_id
                        ).execute()
                    else:
                        client.table("case_analysis_metadata").insert(error_data).execute()
                except Exception as meta_error:
                    logger.debug(f"Could not save error metadata for case {case_id}: {meta_error}")

    logger.info("Preprocessing complete!")


def get_preprocessing_stats():
    """Get statistics about preprocessing progress"""
    client = get_supabase_client()

    total_cases = client.table("court_cases").select("id", count="exact").execute()
    total_count = (
        total_cases.count
        if hasattr(total_cases, "count")
        else len(total_cases.data) if total_cases.data else 0
    )

    analyzed = (
        client.table("case_analysis_metadata")
        .select("id", count="exact")
        .eq("is_analyzed", True)
        .execute()
    )
    analyzed_count = (
        analyzed.count
        if hasattr(analyzed, "count")
        else len(analyzed.data) if analyzed.data else 0
    )

    total_factors = client.table("case_factors").select("id", count="exact").execute()
    factors_count = (
        total_factors.count
        if hasattr(total_factors, "count")
        else len(total_factors.data) if total_factors.data else 0
    )

    total_citations = (
        client.table("case_citations").select("id", count="exact").execute()
    )
    citations_count = (
        total_citations.count
        if hasattr(total_citations, "count")
        else len(total_citations.data) if total_citations.data else 0
    )

    print(f"\n=== Preprocessing Statistics ===")
    print(f"Total cases: {total_count}")
    print(
        f"Analyzed cases: {analyzed_count} ({analyzed_count/total_count*100:.1f}%)"
        if total_count > 0
        else "Analyzed cases: 0"
    )
    print(f"Total factors extracted: {factors_count}")
    print(f"Total citations found: {citations_count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preprocess cases in the database")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of cases to process in each batch",
    )
    parser.add_argument(
        "--start-from", type=int, default=0, help="Case ID to start from (for resuming)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-analyze cases even if already analyzed (useful after updating analysis logic)"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show preprocessing statistics"
    )

    args = parser.parse_args()

    if args.stats:
        get_preprocessing_stats()
    else:
        preprocess_all_cases(batch_size=args.batch_size, start_from=args.start_from, force=args.force)
