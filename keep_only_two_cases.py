"""
Script to delete all cases except for two test cases.
Useful for testing preprocessing on a small dataset.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client


def keep_only_two_cases(case_id_1: int, case_id_2: int):
    """
    Delete all cases except the two specified case IDs.

    Args:
        case_id_1: First case ID to keep
        case_id_2: Second case ID to keep
    """
    client = get_supabase_client()

    # Get all case IDs
    all_cases = client.table("cases").select("id").execute()

    if not all_cases.data:
        print("No cases found in database.")
        return

    case_ids_to_delete = [
        c["id"] for c in all_cases.data if c["id"] not in [case_id_1, case_id_2]
    ]

    if not case_ids_to_delete:
        print(f"Only cases {case_id_1} and {case_id_2} exist. Nothing to delete.")
        return

    print(f"Found {len(all_cases.data)} total cases.")
    print(f"Keeping cases {case_id_1} and {case_id_2}.")
    print(f"Deleting {len(case_ids_to_delete)} cases...")

    # Delete in batches to avoid timeout
    batch_size = 50
    deleted_count = 0

    for i in range(0, len(case_ids_to_delete), batch_size):
        batch = case_ids_to_delete[i : i + batch_size]
        try:
            # Delete related data first (cascade should handle this, but be explicit)
            client.table("cases_factors").delete().in_("case_id", batch).execute()
            client.table("cases_holdings").delete().in_("case_id", batch).execute()
            client.table("cases_citations").delete().in_(
                "citing_case_id", batch
            ).execute()
            client.table("cases_citations").delete().in_(
                "cited_case_id", batch
            ).execute()
            client.table("cases_analysis_metadata").delete().in_(
                "case_id", batch
            ).execute()

            # Delete the cases themselves
            client.table("cases").delete().in_("id", batch).execute()
            deleted_count += len(batch)
            print(f"Deleted {deleted_count}/{len(case_ids_to_delete)} cases...")
        except Exception as e:
            print(f"Error deleting batch: {e}")
            continue

    print(f"\nDone! Deleted {deleted_count} cases.")
    print(f"Remaining cases: {case_id_1} and {case_id_2}")

    # Verify
    remaining = client.table("cases").select("id, case_name").execute()

    print("\nRemaining cases:")
    for case in remaining.data:
        print(f"  - ID {case['id']}: {case.get('case_name', 'Unknown')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Keep only two cases for testing")
    parser.add_argument("case_id_1", type=int, help="First case ID to keep")
    parser.add_argument("case_id_2", type=int, help="Second case ID to keep")
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm deletion (required for safety)"
    )

    args = parser.parse_args()

    if not args.confirm:
        print("ERROR: This will delete most of your cases!")
        print(f"Only cases {args.case_id_1} and {args.case_id_2} will be kept.")
        print("Run with --confirm to proceed.")
        sys.exit(1)

    keep_only_two_cases(args.case_id_1, args.case_id_2)
