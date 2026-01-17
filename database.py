"""
Database models and utilities for storing court case data in Supabase
"""

from supabase import create_client, Client
from datetime import datetime
from typing import List, Dict, Optional
import logging
import config

logger = logging.getLogger(__name__)

# Initialize Supabase client
_supabase: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global _supabase
    if _supabase is None:
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase


def init_database():
    """Initialize the database - create tables if they don't exist"""
    # Note: Tables should be created in Supabase dashboard or via migrations
    # This function verifies connection
    try:
        client = get_supabase_client()
        # Test connection by checking if tables exist
        result = client.table("court_cases").select("id").limit(1).execute()
        logger.info("Successfully connected to Supabase")
        return client
    except Exception as e:
        logger.warning(
            f"Could not verify tables exist. Please create them in Supabase: {e}"
        )
        logger.info("Creating tables via SQL...")
        # Return client anyway - tables might need to be created manually
        return get_supabase_client()


class CourtCase:
    """Model for storing court case information"""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.case_name = kwargs.get("case_name", "")
        self.docket_number = kwargs.get("docket_number")
        self.citation = kwargs.get("citation")
        self.court_type = kwargs.get("court_type", "")
        self.court_name = kwargs.get("court_name")
        self.decision_date = kwargs.get("decision_date")
        self.published_date = kwargs.get("published_date")
        self.opinion_text = kwargs.get("opinion_text")
        self.opinion_url = kwargs.get("opinion_url")
        self.opinion_file_path = kwargs.get("opinion_file_path")
        self.judges = kwargs.get("judges")
        self.case_type = kwargs.get("case_type")
        self.topics = kwargs.get("topics")
        self.source = kwargs.get("source")
        self.source_url = kwargs.get("source_url")
        self.is_published = kwargs.get("is_published", True)
        self.is_downloaded = kwargs.get("is_downloaded", False)
        self.created_at = kwargs.get("created_at")
        self.updated_at = kwargs.get("updated_at")

    def to_dict(self) -> Dict:
        """Convert to dictionary for Supabase insertion"""
        data = {
            "case_name": self.case_name,
            "docket_number": self.docket_number,
            "citation": self.citation,
            "court_type": self.court_type,
            "court_name": self.court_name,
            "decision_date": (
                self.decision_date.isoformat() if self.decision_date else None
            ),
            "published_date": (
                self.published_date.isoformat() if self.published_date else None
            ),
            "opinion_text": self.opinion_text,
            "opinion_url": self.opinion_url,
            "opinion_file_path": self.opinion_file_path,
            "judges": self.judges,
            "case_type": self.case_type,
            "topics": self.topics,
            "source": self.source,
            "source_url": self.source_url,
            "is_published": self.is_published,
            "is_downloaded": self.is_downloaded,
        }
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> "CourtCase":
        """Create CourtCase from dictionary"""
        # Convert date strings to date objects if needed
        if isinstance(data.get("decision_date"), str):
            data["decision_date"] = datetime.fromisoformat(data["decision_date"]).date()
        if isinstance(data.get("published_date"), str):
            data["published_date"] = datetime.fromisoformat(
                data["published_date"]
            ).date()
        return cls(**data)


class CollectionProgress:
    """Track collection progress for different sources"""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.source = kwargs.get("source", "")
        self.last_collected_date = kwargs.get("last_collected_date")
        self.total_cases_collected = kwargs.get("total_cases_collected", 0)
        self.status = kwargs.get("status")
        self.last_updated = kwargs.get("last_updated")
        self.notes = kwargs.get("notes")

    def to_dict(self) -> Dict:
        """Convert to dictionary for Supabase insertion"""
        data = {
            "source": self.source,
            "last_collected_date": (
                self.last_collected_date.isoformat()
                if self.last_collected_date
                else None
            ),
            "total_cases_collected": self.total_cases_collected,
            "status": self.status,
            "notes": self.notes,
        }
        return {k: v for k, v in data.items() if v is not None}


def get_session():
    """Get a database session (Supabase client)"""
    return get_supabase_client()


# Database operation functions
def save_case(case_data: Dict) -> bool:
    """Save a case to Supabase"""
    try:
        client = get_supabase_client()

        # Check if case already exists
        if case_data.get("docket_number") and case_data.get("decision_date"):
            existing = (
                client.table("court_cases")
                .select("id")
                .eq("docket_number", case_data["docket_number"])
                .eq(
                    "decision_date",
                    (
                        case_data["decision_date"].isoformat()
                        if hasattr(case_data["decision_date"], "isoformat")
                        else case_data["decision_date"]
                    ),
                )
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.debug(f"Case already exists: {case_data.get('case_name')}")
                return False

        # Prepare data for insertion
        case = CourtCase(**case_data)
        insert_data = case.to_dict()

        # Ensure decision_date is set - use a default if missing
        if not insert_data.get("decision_date"):
            # Use today's date as default if no date found
            from datetime import date

            insert_data["decision_date"] = date.today().isoformat()
            logger.debug(
                f"Case {case_data.get('case_name')} has no date, using today as default"
            )

        # Insert into Supabase
        result = client.table("court_cases").insert(insert_data).execute()

        if result.data:
            logger.info(f"Saved case: {case_data.get('case_name')}")
            return True
        else:
            logger.warning(f"Failed to save case: {case_data.get('case_name')}")
            return False

    except Exception as e:
        logger.error(f"Error saving case: {e}")
        return False


def get_case_by_id(case_id: int) -> Optional[Dict]:
    """Get a case by ID"""
    try:
        client = get_supabase_client()
        result = client.table("court_cases").select("*").eq("id", case_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        return None


def get_cases_by_court(court_type: str, limit: int = 100) -> List[Dict]:
    """Get cases by court type"""
    try:
        client = get_supabase_client()
        result = (
            client.table("court_cases")
            .select("*")
            .eq("court_type", court_type)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Error getting cases: {e}")
        return []


def update_progress(
    source: str,
    last_date: datetime = None,
    total_cases: int = 0,
    status: str = "active",
):
    """Update collection progress for a source"""
    try:
        client = get_supabase_client()

        # Check if progress record exists
        existing = (
            client.table("collection_progress")
            .select("id")
            .eq("source", source)
            .limit(1)
            .execute()
        )

        progress_data = {
            "source": source,
            "last_collected_date": (
                last_date.date().isoformat() if last_date else None
            ),
            "total_cases_collected": total_cases,
            "status": status,
            # Don't include updated_at - it's handled by the database trigger
        }

        if existing.data:
            # Update existing - don't include updated_at
            result = (
                client.table("collection_progress")
                .update(progress_data)
                .eq("source", source)
                .execute()
            )
        else:
            # Insert new
            result = client.table("collection_progress").insert(progress_data).execute()

        return result.data is not None
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        return False


def get_statistics() -> Dict:
    """Get collection statistics"""
    try:
        client = get_supabase_client()

        # Get total count
        total_result = client.table("court_cases").select("id", count="exact").execute()
        total_cases = (
            total_result.count
            if hasattr(total_result, "count")
            else len(total_result.data) if total_result.data else 0
        )

        # Get counts by court type
        by_court = {}
        for court_type in config.COURT_TYPES.keys():
            result = (
                client.table("court_cases")
                .select("id", count="exact")
                .eq("court_type", court_type)
                .execute()
            )
            count = (
                result.count
                if hasattr(result, "count")
                else len(result.data) if result.data else 0
            )
            if count > 0:
                by_court[court_type] = count

        # Get counts by year (simplified - would need more complex query for full year breakdown)
        by_year = {}
        # This would require a more complex query or fetching all cases
        # For now, return basic stats

        return {
            "total_cases": total_cases,
            "by_court": by_court,
            "by_year": by_year,  # Would need to implement year grouping
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"total_cases": 0, "by_court": {}, "by_year": {}}
