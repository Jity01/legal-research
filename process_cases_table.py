"""
Optimized script to process cases from the 'cases' table and extract factors.
Designed to handle large-scale processing (800k+ cases) efficiently.
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client
from strategy.case_analyzer import CaseAnalyzer
from strategy.citation_extractor import CitationExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("case_processing.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Thread-safe counters and failed cases tracking
processed_count = 0
error_count = 0
failed_cases = []  # List of tuples: (case_id, case_name, error_message)
lock = threading.Lock()


def map_case_schema(source_case: Dict) -> Dict:
    """
    Map from 'cases' table schema to 'court_cases' table schema.

    Source schema (cases):
    - id (text)
    - case_name (text)
    - full_text (text)
    - citation (text)
    - court (text)
    - date_filed (timestamp)
    - judges (text)
    - url (text)
    - summary (text)

    Target schema (court_cases):
    - case_name (required)
    - opinion_text (from full_text)
    - citation
    - court_name (from court)
    - court_type (extracted from court or inferred)
    - decision_date (from date_filed)
    - judges
    - opinion_url (from url)
    - source
    """
    # Extract court type from court name (handle both 'court' and 'court_name')
    court_name = source_case.get("court") or source_case.get("court_name") or ""
    court_type = source_case.get("court_type") or infer_court_type(court_name)

    # Parse date (handle both 'date_filed' and 'decision_date')
    date_filed = source_case.get("date_filed") or source_case.get("decision_date")
    decision_date = None
    if date_filed:
        if isinstance(date_filed, str):
            try:
                decision_date = datetime.fromisoformat(
                    date_filed.replace("Z", "+00:00")
                ).date()
            except:
                try:
                    decision_date = datetime.strptime(
                        date_filed.split()[0], "%Y-%m-%d"
                    ).date()
                except:
                    pass
        elif hasattr(date_filed, "date") and not hasattr(date_filed, "isoformat"):
            # datetime object
            decision_date = date_filed.date()
        elif hasattr(date_filed, "isoformat"):
            # Already a date object
            decision_date = date_filed

    # Use case id as docket_number if no citation
    docket_number = (
        source_case.get("docket_number")
        or source_case.get("citation")
        or source_case.get("id")
    )

    mapped_case = {
        "case_name": source_case.get("case_name", "Unknown Case"),
        "opinion_text": source_case.get("full_text")
        or source_case.get("opinion_text")
        or source_case.get("summary")
        or "",
        "citation": source_case.get("citation"),
        "docket_number": docket_number,
        "court_name": court_name,
        "court_type": court_type,
        "decision_date": decision_date.isoformat() if decision_date else None,
        "judges": source_case.get("judges"),
        "opinion_url": source_case.get("url") or source_case.get("source_url"),
        "source": source_case.get("source") or "cases_table_migration",
        "is_published": source_case.get("is_published", True),
        "is_downloaded": source_case.get("is_downloaded", True),
    }

    # Remove None values
    return {k: v for k, v in mapped_case.items() if v is not None}


def infer_court_type(court_name: str) -> str:
    """Infer court_type from court name"""
    if not court_name:
        return "UNKNOWN"

    court_upper = court_name.upper()
    if "SUPREME JUDICIAL" in court_upper or "SJC" in court_upper:
        return "SJC"
    elif "APPEALS" in court_upper:
        return "APPEALS"
    elif "SUPERIOR" in court_upper:
        return "SUPERIOR"
    elif "DISTRICT" in court_upper:
        return "DISTRICT"
    elif "PROBATE" in court_upper:
        return "PROBATE"
    elif "HOUSING" in court_upper:
        return "HOUSING"
    elif "JUVENILE" in court_upper:
        return "JUVENILE"
    elif "FEDERAL" in court_upper or "U.S." in court_upper or "US" in court_upper:
        if "DISTRICT" in court_upper:
            return "FEDERAL_DISTRICT"
        elif "APPEALS" in court_upper or "CIRCUIT" in court_upper:
            return "FEDERAL_APPEALS"
    return "UNKNOWN"


def get_or_create_court_case(client, mapped_case: Dict) -> Optional[int]:
    """
    Check if case exists in court_cases, if not create it.
    Returns the court_cases.id (bigint) or None if creation failed.
    """
    try:
        # Try to find existing case by case_name + decision_date or citation
        case_name = mapped_case.get("case_name")
        decision_date = mapped_case.get("decision_date")
        citation = mapped_case.get("citation")
        docket_number = mapped_case.get("docket_number")

        # Check by citation first (most reliable)
        if citation:
            existing = (
                client.table("court_cases")
                .select("id, opinion_text")
                .eq("citation", citation)
                .limit(1)
                .execute()
            )
            if existing.data:
                case_id = existing.data[0]["id"]
                # Update opinion_text if it's empty and we have new text
                if not existing.data[0].get("opinion_text") and mapped_case.get(
                    "opinion_text"
                ):
                    try:
                        client.table("court_cases").update(
                            {"opinion_text": mapped_case["opinion_text"]}
                        ).eq("id", case_id).execute()
                        logger.debug(f"Updated opinion_text for case {case_id}")
                    except Exception as e:
                        logger.debug(
                            f"Error updating opinion_text for case {case_id}: {e}"
                        )
                return case_id

        # Check by docket_number + decision_date
        if docket_number and decision_date:
            existing = (
                client.table("court_cases")
                .select("id, opinion_text")
                .eq("docket_number", docket_number)
                .eq("decision_date", decision_date)
                .limit(1)
                .execute()
            )
            if existing.data:
                case_id = existing.data[0]["id"]
                # Update opinion_text if it's empty and we have new text
                if not existing.data[0].get("opinion_text") and mapped_case.get(
                    "opinion_text"
                ):
                    try:
                        client.table("court_cases").update(
                            {"opinion_text": mapped_case["opinion_text"]}
                        ).eq("id", case_id).execute()
                        logger.debug(f"Updated opinion_text for case {case_id}")
                    except Exception as e:
                        logger.debug(
                            f"Error updating opinion_text for case {case_id}: {e}"
                        )
                return case_id

        # Check by case_name + decision_date
        if case_name and decision_date:
            existing = (
                client.table("court_cases")
                .select("id, opinion_text")
                .eq("case_name", case_name)
                .eq("decision_date", decision_date)
                .limit(1)
                .execute()
            )
            if existing.data:
                case_id = existing.data[0]["id"]
                # Update opinion_text if it's empty and we have new text
                if not existing.data[0].get("opinion_text") and mapped_case.get(
                    "opinion_text"
                ):
                    try:
                        client.table("court_cases").update(
                            {"opinion_text": mapped_case["opinion_text"]}
                        ).eq("id", case_id).execute()
                        logger.debug(f"Updated opinion_text for case {case_id}")
                    except Exception as e:
                        logger.debug(
                            f"Error updating opinion_text for case {case_id}: {e}"
                        )
                return case_id

        # Case doesn't exist, create it
        # Ensure decision_date is set (required field)
        if not mapped_case.get("decision_date"):
            from datetime import date

            mapped_case["decision_date"] = date.today().isoformat()

        result = client.table("court_cases").insert(mapped_case).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return None

    except Exception as e:
        logger.error(f"Error getting/creating court case: {e}")
        return None


def process_single_case(
    source_case: Dict,
    analyzer: CaseAnalyzer,
    citation_extractor: CitationExtractor,
    client,
    force: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Process a single case: map schema, create court_case, analyze, save results.

    Returns:
        (success: bool, error_message: Optional[str])
    """
    global processed_count, error_count

    source_case_id = source_case.get("id")
    source_case_name = source_case.get("case_name", "Unknown")
    court_case_id = None

    try:
        # Map schema
        mapped_case = map_case_schema(source_case)

        # Get or create court_case
        court_case_id = get_or_create_court_case(client, mapped_case)
        if not court_case_id:
            error_msg = "Failed to create/get court_case"
            with lock:
                error_count += 1
                failed_cases.append((source_case_id, source_case_name, error_msg))
            return False, error_msg

        # Check if already analyzed (unless force)
        if not force:
            existing = (
                client.table("case_analysis_metadata")
                .select("id")
                .eq("case_id", court_case_id)
                .eq("is_analyzed", True)
                .execute()
            )
            if existing.data:
                with lock:
                    processed_count += 1
                return True, None

        # Prepare case dict for analyzer (needs opinion_text, case_name, court_name)
        case_for_analysis = {
            "id": court_case_id,
            "case_name": mapped_case.get("case_name"),
            "opinion_text": mapped_case.get("opinion_text", ""),
            "court_name": mapped_case.get("court_name"),
        }

        # Analyze the case
        analysis = analyzer.analyze_case(case_for_analysis)

        # Save factors (bulk insert)
        if analysis.get("factors"):
            # Delete existing factors first
            try:
                client.table("case_factors").delete().eq(
                    "case_id", court_case_id
                ).execute()
            except:
                pass

            factors_data = []
            for factor in analysis["factors"]:
                factor_text = factor.get("text", "").strip()

                # Validate factor (same validation as preprocess_cases.py)
                if factor_text:
                    word_count = len(factor_text.split())
                    if word_count < 20:  # Updated minimum from case_analyzer
                        continue

                    factors_data.append(
                        {
                            "case_id": court_case_id,
                            "factor_text": factor_text,
                            "factor_type": factor.get("type", "legal_principle"),
                        }
                    )

            if factors_data:
                try:
                    # Bulk insert
                    client.table("case_factors").insert(factors_data).execute()
                except Exception as e:
                    logger.debug(
                        f"Error inserting factors for case {court_case_id}: {e}"
                    )

        # Save holding
        holding = analysis.get("holding", {})
        if holding.get("text"):
            holding_data = {
                "case_id": court_case_id,
                "holding_text": holding.get("text", ""),
                "holding_direction": holding.get("direction", "unclear"),
                "confidence": holding.get("confidence", 0.0),
            }

            try:
                existing_holding = (
                    client.table("case_holdings")
                    .select("id")
                    .eq("case_id", court_case_id)
                    .execute()
                )

                if existing_holding.data:
                    client.table("case_holdings").update(holding_data).eq(
                        "case_id", court_case_id
                    ).execute()
                else:
                    client.table("case_holdings").insert(holding_data).execute()
            except Exception as e:
                logger.debug(f"Error saving holding for case {court_case_id}: {e}")

        # Save citations (bulk insert with error handling)
        citations = analysis.get("citations", [])
        if citations:
            citations_data = []
            for citation in citations:
                citation_text = citation.get("citation_text", "").strip()
                if citation_text and len(citation_text) > 5:
                    try:
                        cited_case_id = citation_extractor.match_citation_to_case(
                            citation_text
                        )
                    except:
                        cited_case_id = None

                    citations_data.append(
                        {
                            "citing_case_id": court_case_id,
                            "cited_case_id": cited_case_id,
                            "citation_text": citation_text[:500],
                            "citation_context": (
                                citation.get("context", "")[:1000]
                                if citation.get("context")
                                else None
                            ),
                        }
                    )

            if citations_data:
                # Insert one at a time to handle duplicates gracefully
                for cit_data in citations_data:
                    try:
                        client.table("case_citations").insert(cit_data).execute()
                    except:
                        pass  # Skip duplicates

        # Mark as analyzed
        try:
            existing_metadata = (
                client.table("case_analysis_metadata")
                .select("id")
                .eq("case_id", court_case_id)
                .execute()
            )

            metadata_data = {
                "case_id": court_case_id,
                "is_analyzed": True,
                "analyzed_at": datetime.now().isoformat(),
            }

            if existing_metadata.data:
                client.table("case_analysis_metadata").update(metadata_data).eq(
                    "case_id", court_case_id
                ).execute()
            else:
                client.table("case_analysis_metadata").insert(metadata_data).execute()
        except Exception as e:
            logger.debug(f"Error saving metadata for case {court_case_id}: {e}")

        with lock:
            processed_count += 1

        return True, None

    except Exception as e:
        error_msg = str(e)
        with lock:
            error_count += 1
            failed_cases.append((source_case_id, source_case_name, error_msg))

        # Mark as error
        try:
            if court_case_id:
                existing_metadata = (
                    client.table("case_analysis_metadata")
                    .select("id")
                    .eq("case_id", court_case_id)
                    .execute()
                )

                error_data = {
                    "case_id": court_case_id,
                    "is_analyzed": False,
                    "error_message": error_msg[:500],
                }

                if existing_metadata.data:
                    client.table("case_analysis_metadata").update(error_data).eq(
                        "case_id", court_case_id
                    ).execute()
                else:
                    client.table("case_analysis_metadata").insert(error_data).execute()
        except:
            pass

        return False, error_msg


def process_cases_batch(
    cases_batch: List[Dict],
    analyzer: CaseAnalyzer,
    citation_extractor: CitationExtractor,
    client,
    force: bool = False,
    max_workers: int = 5,
) -> Tuple[int, int]:
    """
    Process a batch of cases in parallel.

    Returns:
        (success_count, error_count)
    """
    success_count = 0
    batch_error_count = 0

    # Use ThreadPoolExecutor for parallel processing
    # Note: OpenAI API has rate limits, so we limit concurrency
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_single_case, case, analyzer, citation_extractor, client, force
            ): case
            for case in cases_batch
        }

        for future in as_completed(futures):
            case = futures[future]
            try:
                success, error = future.result()
                if success:
                    success_count += 1
                else:
                    batch_error_count += 1
                    if error:
                        logger.debug(
                            f"Error processing case {case.get('id')}: {error[:100]}"
                        )
            except Exception as e:
                batch_error_count += 1
                logger.debug(f"Exception processing case {case.get('id')}: {e}")

    return success_count, batch_error_count


def process_all_cases(
    batch_size: int = 50,
    analysis_batch_size: int = 5,
    max_workers: int = 5,
    force: bool = False,
    limit: Optional[int] = None,
    resume_from: Optional[str] = None,
):
    """
    Process all cases from the 'cases' table.

    Args:
        batch_size: Number of cases to fetch from DB at once
        analysis_batch_size: Number of cases to analyze in parallel
        max_workers: Max concurrent workers for analysis (respects API rate limits)
        force: Re-analyze cases even if already analyzed
        limit: Limit total number of cases to process (for testing)
        resume_from: Case ID to resume from (for resuming interrupted runs)
    """
    global processed_count, error_count, failed_cases
    processed_count = 0
    error_count = 0
    failed_cases = []

    client = get_supabase_client()
    analyzer = CaseAnalyzer()
    citation_extractor = CitationExtractor()

    logger.info("Starting case processing...")
    logger.info(
        f"Batch size: {batch_size}, Analysis workers: {max_workers}, Force: {force}"
    )

    # Get total count
    count_result = client.table("cases").select("id", count="exact").execute()
    total_cases = count_result.count if hasattr(count_result, "count") else 0

    if limit:
        total_cases = min(total_cases, limit)
        logger.info(f"Processing limited to {limit} cases")
    else:
        logger.info(f"Found {total_cases} total cases to process")

    # Build query
    query = client.table("cases").select("*")

    if resume_from:
        query = query.gt("id", resume_from)
        logger.info(f"Resuming from case ID: {resume_from}")

    query = query.order("id")

    # Process in batches
    offset = 0
    start_time = time.time()

    with tqdm(total=total_cases, desc="Processing cases") as pbar:
        while offset < total_cases:
            # Fetch batch
            batch_query = query.range(offset, offset + batch_size - 1)
            cases_batch = batch_query.execute()

            if not cases_batch.data:
                break

            # Process this batch
            success, errors = process_cases_batch(
                cases_batch.data,
                analyzer,
                citation_extractor,
                client,
                force=force,
                max_workers=max_workers,
            )

            offset += len(cases_batch.data)
            pbar.update(len(cases_batch.data))

            # Log progress
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            remaining = (total_cases - offset) / rate if rate > 0 else 0

            logger.info(
                f"Progress: {offset}/{total_cases} cases processed. "
                f"Success: {success}, Errors: {errors}. "
                f"Rate: {rate:.2f} cases/sec, ETA: {remaining/60:.1f} min"
            )

            # Small delay to avoid overwhelming the database
            time.sleep(0.1)

    total_time = time.time() - start_time
    logger.info(f"\n=== Processing Complete ===")
    logger.info(f"Total processed: {processed_count}")
    logger.info(f"Total errors: {error_count}")
    logger.info(f"Total time: {total_time/60:.1f} minutes")
    logger.info(f"Average rate: {processed_count/total_time:.2f} cases/sec")

    # Log all failed cases
    if failed_cases:
        logger.info(f"\n=== Failed Cases ({len(failed_cases)}) ===")
        for case_id, case_name, error_msg in failed_cases:
            logger.error(
                f"Case ID: {case_id}, Name: {case_name[:100]}, Error: {error_msg[:200]}"
            )

        # Also write to a separate file for easy reference
        failed_cases_file = "failed_cases.log"
        with open(failed_cases_file, "w") as f:
            f.write(f"Failed Cases Report - {datetime.now().isoformat()}\n")
            f.write(f"Total failed: {len(failed_cases)}\n")
            f.write("=" * 80 + "\n\n")
            for case_id, case_name, error_msg in failed_cases:
                f.write(f"Case ID: {case_id}\n")
                f.write(f"Case Name: {case_name}\n")
                f.write(f"Error: {error_msg}\n")
                f.write("-" * 80 + "\n")
        logger.info(f"\nFailed cases details written to: {failed_cases_file}")
    else:
        logger.info("\n=== No Failed Cases ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process cases from 'cases' table")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of cases to fetch from DB at once (default: 50)",
    )
    parser.add_argument(
        "--analysis-workers",
        type=int,
        default=5,
        help="Max concurrent workers for analysis (default: 5, adjust based on API limits)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-analyze cases even if already analyzed"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit total number of cases to process (for testing)"
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        help="Case ID to resume from (for resuming interrupted runs)",
    )

    args = parser.parse_args()

    process_all_cases(
        batch_size=args.batch_size,
        analysis_batch_size=args.analysis_workers,
        max_workers=args.analysis_workers,
        force=args.force,
        limit=args.limit,
        resume_from=args.resume_from,
    )
