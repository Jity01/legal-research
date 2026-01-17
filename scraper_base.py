"""
Base scraper class for court case collection
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all court case scrapers"""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

    def fetch_page(
        self, url: str, retries: int = config.MAX_RETRIES
    ) -> Optional[requests.Response]:
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                time.sleep(config.REQUEST_DELAY)
                response = self.session.get(url, timeout=config.TIMEOUT)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
        return None

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content"""
        return BeautifulSoup(html_content, "lxml")

    def extract_cases(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract case information from parsed HTML - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement extract_cases")

    def collect_cases(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Main method to collect cases - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement collect_cases")

    def filter_by_date(
        self, case: Dict, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> bool:
        """Filter cases by date range"""
        if not case.get("decision_date"):
            return False

        case_date = case["decision_date"]
        if isinstance(case_date, str):
            try:
                case_date = datetime.strptime(case_date, "%Y-%m-%d").date()
            except:
                return False

        if start_date and case_date < start_date.date():
            return False
        if end_date and case_date > end_date.date():
            return False

        return True
