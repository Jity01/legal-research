"""
Main collector that orchestrates all scrapers and saves to database
"""

import logging
from datetime import datetime
from typing import List, Dict
import sys
import os

# Add parent directory to path for config and database imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import init_database, save_case, update_progress, get_statistics
from .mass_gov_scraper import MassGovAppellateScraper, MassGovTrialScraper
from .courtlistener_scraper import CourtListenerScraper
import config

logger = logging.getLogger(__name__)


class CaseCollector:
    """Main class to collect and store court cases"""

    def __init__(self):
        self.db_client = init_database()
        self.scrapers = [
            CourtListenerScraper(),  # Primary source - CourtListener
            # MassGovAppellateScraper(),  # Disabled for now
            # MassGovTrialScraper(),  # Disabled for now
        ]

    def save_case(self, case_data: Dict) -> bool:
        """Save a single case to the database"""
        return save_case(case_data)

    def update_progress(
        self,
        source: str,
        last_date: datetime = None,
        total_cases: int = 0,
        status: str = "active",
    ):
        """Update collection progress for a source"""
        update_progress(source, last_date, total_cases, status)

    def collect_all(
        self,
        start_year: int = config.START_YEAR,
        end_year: int = config.END_YEAR,
        max_pages: int = None,
    ):
        """Collect cases from all sources"""
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)

        logger.info(f"Starting collection for years {start_year}-{end_year}")

        total_cases = 0

        for scraper in self.scrapers:
            try:
                logger.info(f"Collecting from {scraper.source_name}")
                # Pass max_pages if scraper supports it
                if hasattr(scraper, "collect_cases"):
                    if "max_pages" in scraper.collect_cases.__code__.co_varnames:
                        cases = scraper.collect_cases(
                            start_date=start_date,
                            end_date=end_date,
                            max_pages=max_pages,
                        )
                    else:
                        cases = scraper.collect_cases(
                            start_date=start_date, end_date=end_date
                        )
                else:
                    cases = []

                saved_count = 0
                for case in cases:
                    if self.save_case(case):
                        saved_count += 1

                total_cases += saved_count
                self.update_progress(
                    scraper.source_name,
                    last_date=end_date,
                    total_cases=saved_count,
                    status="completed" if saved_count > 0 else "error",
                )

                logger.info(f"Saved {saved_count} new cases from {scraper.source_name}")

            except Exception as e:
                logger.error(f"Error collecting from {scraper.source_name}: {e}")
                self.update_progress(scraper.source_name, status="error")
                continue
            finally:
                # Clean up Playwright browser after each scraper
                if hasattr(scraper, "use_playwright") and scraper.use_playwright:
                    try:
                        scraper._close_playwright()
                    except Exception as e:
                        logger.debug(
                            f"Error closing Playwright for {scraper.source_name}: {e}"
                        )

        logger.info(f"Collection complete. Total new cases saved: {total_cases}")
        return total_cases

    def get_statistics(self) -> Dict:
        """Get collection statistics"""
        return get_statistics()
