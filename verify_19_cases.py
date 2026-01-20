#!/usr/bin/env python3
"""
Verify that all 19 newly added cases exist in the database and have been analyzed.
"""

from database import get_supabase_client
from typing import List, Dict

def verify_cases():
    """Verify the 19 newly added cases"""
    client = get_supabase_client()
    
    print("=" * 80)
    print("Verifying 19 newly added cases")
    print("=" * 80)
    
    # First, check if we can access the table
    try:
        test_result = client.table("cases").select("id").limit(1).execute()
        print("✓ Successfully connected to cases table\n")
    except Exception as e:
        print(f"✗ Error accessing cases table: {e}")
        return
    
    # Check by source (user_input)
    print("Checking cases with source='user_input'...")
    try:
        result = (
            client.table("cases")
            .select("id, case_name, citation, docket_number, court_name, decision_date, source")
            .eq("source", "user_input")
            .order("id")
            .execute()
        )
        
        cases = result.data or []
        print(f"Found {len(cases)} cases with source='user_input'\n")
        
        if not cases:
            print("No cases found with source='user_input'")
            print("Checking cases by ID range 537-555 instead...")
            
            # Try by ID range
            all_ids = list(range(537, 556))
            result = (
                client.table("cases")
                .select("id, case_name, citation, docket_number, court_name, decision_date, source")
                .in_("id", all_ids)
                .order("id")
                .execute()
            )
            cases = result.data or []
            print(f"Found {len(cases)} cases in ID range 537-555\n")
        
    except Exception as e:
        print(f"✗ Error querying cases: {e}")
        return
    
    if not cases:
        print("No cases found. The cases may not have been inserted yet.")
        return
    
    # For each case, check analysis status
    print("=" * 80)
    print("Case Details and Analysis Status")
    print("=" * 80)
    
    total_factors = 0
    total_holdings = 0
    analyzed_count = 0
    
    for case in cases:
        case_id = case["id"]
        case_name = case.get("case_name", "Unknown")
        
        # Get opinion text length
        try:
            case_detail = (
                client.table("cases")
                .select("opinion_text")
                .eq("id", case_id)
                .single()
                .execute()
            )
            opinion_length = len(case_detail.data.get("opinion_text", "")) if case_detail.data else 0
        except:
            opinion_length = 0
        
        # Check analysis metadata
        try:
            metadata = (
                client.table("cases_analysis_metadata")
                .select("is_analyzed, analyzed_at")
                .eq("case_id", case_id)
                .execute()
            )
            is_analyzed = metadata.data[0]["is_analyzed"] if metadata.data else False
            analyzed_at = metadata.data[0].get("analyzed_at") if metadata.data else None
        except:
            is_analyzed = False
            analyzed_at = None
        
        # Count factors
        try:
            factors = (
                client.table("cases_factors")
                .select("id", count="exact")
                .eq("case_id", case_id)
                .execute()
            )
            factor_count = factors.count if hasattr(factors, "count") else len(factors.data) if factors.data else 0
        except:
            factor_count = 0
        
        # Count holdings
        try:
            holdings = (
                client.table("cases_holdings")
                .select("id")
                .eq("case_id", case_id)
                .execute()
            )
            holding_count = len(holdings.data) if holdings.data else 0
        except:
            holding_count = 0
        
        # Print case info
        status = "✓ Analyzed" if is_analyzed else "✗ Not Analyzed"
        print(f"\nCase ID: {case_id}")
        print(f"  Name: {case_name[:80]}")
        print(f"  Citation: {case.get('citation', 'N/A')}")
        print(f"  Source: {case.get('source', 'N/A')}")
        print(f"  Opinion Text Length: {opinion_length:,} chars")
        print(f"  Status: {status}")
        if analyzed_at:
            print(f"  Analyzed At: {analyzed_at}")
        print(f"  Factors: {factor_count}")
        print(f"  Holdings: {holding_count}")
        
        if is_analyzed:
            analyzed_count += 1
        total_factors += factor_count
        total_holdings += holding_count
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total Cases Found: {len(cases)}")
    print(f"Analyzed: {analyzed_count}")
    print(f"Not Analyzed: {len(cases) - analyzed_count}")
    print(f"Total Factors: {total_factors}")
    print(f"Total Holdings: {total_holdings}")
    print(f"Average Factors per Case: {total_factors / len(cases):.1f}" if cases else "N/A")
    print(f"Average Holdings per Case: {total_holdings / len(cases):.1f}" if cases else "N/A")
    
    if len(cases) < 19:
        print(f"\n⚠ Warning: Expected 19 cases, but found {len(cases)}")
    elif analyzed_count < len(cases):
        print(f"\n⚠ Warning: {len(cases) - analyzed_count} cases have not been analyzed yet.")
        print("   Run: python3 add_new_cases.py")
    else:
        print("\n✓ All cases found and analyzed!")

if __name__ == "__main__":
    verify_cases()
