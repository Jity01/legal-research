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

    def __init__(self, source_name: str, base_url: str, use_playwright: bool = False):
        self.source_name = source_name
        self.base_url = base_url
        self.use_playwright = use_playwright
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        self.playwright_browser = None
        self.playwright_page = None

    def _init_playwright(self):
        """Initialize Playwright browser if not already initialized"""
        if self.playwright_browser is None:
            try:
                from playwright.sync_api import sync_playwright

                self.playwright = sync_playwright().start()
                self.playwright_browser = self.playwright.chromium.launch(headless=True)
                self.playwright_context = self.playwright_browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                )
                # Don't create a page here - create one per request
                logger.info("Playwright browser initialized")
            except ImportError:
                logger.error(
                    "Playwright not installed. Run: pip install playwright && playwright install"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {e}")
                raise

    def _close_playwright(self):
        """Close Playwright browser"""
        try:
            if hasattr(self, "playwright_context") and self.playwright_context:
                self.playwright_context.close()
            if self.playwright_browser:
                self.playwright_browser.close()
            if hasattr(self, "playwright") and self.playwright:
                self.playwright.stop()
            self.playwright_browser = None
            self.playwright_page = None
            self.playwright_context = None
            logger.info("Playwright browser closed")
        except Exception as e:
            logger.warning(f"Error closing Playwright: {e}")

    def fetch_page(
        self,
        url: str,
        retries: int = config.MAX_RETRIES,
        wait_for: Optional[str] = None,
    ) -> Optional[requests.Response]:
        """Fetch a page with retry logic"""
        if self.use_playwright:
            return self._fetch_with_playwright(url, wait_for)

        # Fallback to requests
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

    def _fetch_with_playwright(
        self, url: str, wait_for: Optional[str] = None
    ) -> Optional[requests.Response]:
        """Fetch page using Playwright to render JavaScript"""
        page = None
        try:
            self._init_playwright()

            # Create a new page for each request to avoid async conflicts
            page = self.playwright_context.new_page()
            logger.info(f"Loading {url} with Playwright...")

            page.goto(url, wait_until="networkidle", timeout=60000)

            # Wait for specific selector if provided
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except Exception as e:
                    logger.warning(
                        f"Selector {wait_for} not found, continuing anyway: {e}"
                    )

            # Additional wait for content to load
            time.sleep(2)

            # Get the rendered HTML
            html_content = page.content()

            # Create a mock response object
            class MockResponse:
                def __init__(self, text):
                    self.text = text
                    self.status_code = 200
                    self.url = url

                def raise_for_status(self):
                    pass

            return MockResponse(html_content)

        except Exception as e:
            logger.error(f"Error fetching {url} with Playwright: {e}")
            return None
        finally:
            # Always close the page after use
            if page:
                try:
                    page.close()
                except Exception as e:
                    logger.debug(f"Error closing page: {e}")

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
        # If no date filters provided, include all cases
        if not start_date and not end_date:
            return True

        # If case has no date, include it (we can't filter it out)
        if not case.get("decision_date"):
            logger.debug(f"Case {case.get('case_name')} has no date, including it")
            return True

        case_date = case["decision_date"]
        if isinstance(case_date, str):
            try:
                case_date = datetime.strptime(case_date, "%Y-%m-%d").date()
            except:
                # If we can't parse the date, include the case
                logger.debug(f"Could not parse date {case_date}, including case")
                return True

        if isinstance(case_date, datetime):
            case_date = case_date.date()

        if start_date and case_date < start_date.date():
            return False
        if end_date and case_date > end_date.date():
            return False

        return True

    def __del__(self):
        """Cleanup Playwright on deletion"""
        if self.use_playwright:
            self._close_playwright()
