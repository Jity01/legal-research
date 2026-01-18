"""
Scraper for Mass.gov opinion portals using Playwright
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
import sys
import os

# Add parent directory to path for config imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .scraper_base import BaseScraper
import config

logger = logging.getLogger(__name__)


class MassGovAppellateScraper(BaseScraper):
    """Scraper for Mass.gov Appellate Opinion Portal"""

    def __init__(self):
        super().__init__(
            "Mass.gov Appellate Portal",
            config.DATA_SOURCES["MASS_GOV_APPELLATE"],
            use_playwright=True,
        )

    def extract_cases(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract cases from the opinion portal page"""
        cases = []

        # Look for various patterns that might indicate case listings
        # Try multiple selectors to find case information

        # Look for links with opinion/case/docket keywords
        case_links = soup.find_all(
            "a", href=re.compile(r"opinion|case|docket|decision", re.I)
        )

        # Also look for table rows or list items that might contain case info
        tables = soup.find_all("table")
        lists = soup.find_all(["ul", "ol"])

        logger.info(
            f"Found {len(case_links)} links, {len(tables)} tables, {len(lists)} lists"
        )

        # Process links
        for link in case_links:
            try:
                case_info = self._parse_case_link(link)
                if case_info:
                    cases.append(case_info)
            except Exception as e:
                logger.debug(f"Error parsing case link: {e}")
                continue

        # Process table rows
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                try:
                    case_info = self._parse_table_row(row)
                    if case_info:
                        cases.append(case_info)
                except Exception as e:
                    logger.debug(f"Error parsing table row: {e}")
                    continue

        # Process list items
        for lst in lists:
            items = lst.find_all("li")
            for item in items:
                try:
                    case_info = self._parse_list_item(item)
                    if case_info:
                        cases.append(case_info)
                except Exception as e:
                    logger.debug(f"Error parsing list item: {e}")
                    continue

        # Remove duplicates based on case name and URL
        seen = set()
        unique_cases = []
        for case in cases:
            key = (case.get("case_name"), case.get("opinion_url"))
            if key not in seen and key[0] and key[1]:
                seen.add(key)
                unique_cases.append(case)

        logger.info(
            f"Extracted {len(unique_cases)} unique cases from {len(cases)} total matches"
        )
        return unique_cases

    def _parse_case_link(self, link) -> Optional[Dict]:
        """Parse a single case link to extract information"""
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # Skip if too short or doesn't look like a case
        if not text or len(text) < 5:
            return None

        # Skip navigation/header links - expanded list
        skip_keywords = [
            "home",
            "about",
            "contact",
            "search",
            "menu",
            "skip",
            "navigation",
            "massachusetts court cases",
            "published court opinions",
            "office of the reporter",
            "find the newest",
            "opinion revisions",
            "sign up",
            "follow us",
            "twitter",
            "email",
            "notification",
            "official website",
            "secure website",
            "state organizations",
            "show the sub topics",
            "health & social",
            "families & children",
            "housing & property",
            "transportation",
            "living",
            "topics",
        ]
        text_lower = text.lower()
        if any(skip in text_lower for skip in skip_keywords):
            return None

        # Must look like a case - should have "v." or "vs." or be a case number pattern
        if not any(
            indicator in text_lower
            for indicator in ["v.", "vs.", "v ", "case", "docket", "no.", "number"]
        ):
            # Check if URL suggests it's a case
            if not any(
                case_indicator in href.lower()
                for case_indicator in ["opinion", "case", "docket", "decision", ".pdf"]
            ):
                return None

        # Try to extract date from text or nearby elements
        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        date_str = date_match.group(1) if date_match else None

        # Try to determine court type from URL or text
        court_type = "APPEALS"
        if "sjc" in href.lower() or "supreme" in text.lower():
            court_type = "SJC"

        # Build full URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"https://www.mass.gov{href}"
        else:
            full_url = f"{self.base_url}/{href.lstrip('/')}"

        return {
            "case_name": text[:500],  # Limit length
            "opinion_url": full_url,
            "court_type": court_type,
            "source": self.source_name,
            "source_url": self.base_url,
            "decision_date": self._parse_date(date_str) if date_str else None,
        }

    def _parse_table_row(self, row) -> Optional[Dict]:
        """Parse a table row for case information"""
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            return None

        # Look for links in cells
        links = row.find_all("a", href=True)
        if not links:
            return None

        text = " ".join([cell.get_text(strip=True) for cell in cells])
        if len(text) < 10:
            return None

        # Try to find date
        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        date_str = date_match.group(1) if date_match else None

        # Get the first link
        link = links[0]
        href = link.get("href", "")
        link_text = link.get_text(strip=True)

        court_type = "APPEALS"
        if "sjc" in href.lower() or "supreme" in text.lower():
            court_type = "SJC"

        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"https://www.mass.gov{href}"
        else:
            full_url = f"{self.base_url}/{href.lstrip('/')}"

        return {
            "case_name": link_text[:500] if link_text else text[:500],
            "opinion_url": full_url,
            "court_type": court_type,
            "source": self.source_name,
            "source_url": self.base_url,
            "decision_date": self._parse_date(date_str) if date_str else None,
        }

    def _parse_list_item(self, item) -> Optional[Dict]:
        """Parse a list item for case information"""
        links = item.find_all("a", href=True)
        if not links:
            return None

        text = item.get_text(strip=True)
        if len(text) < 10:
            return None

        link = links[0]
        href = link.get("href", "")
        link_text = link.get_text(strip=True)

        # Skip if doesn't look like a case
        if not any(
            keyword in text.lower() for keyword in ["v.", "vs.", "case", "opinion"]
        ):
            return None

        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        date_str = date_match.group(1) if date_match else None

        court_type = "APPEALS"
        if "sjc" in href.lower() or "supreme" in text.lower():
            court_type = "SJC"

        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"https://www.mass.gov{href}"
        else:
            full_url = f"{self.base_url}/{href.lstrip('/')}"

        return {
            "case_name": link_text[:500] if link_text else text[:500],
            "opinion_url": full_url,
            "court_type": court_type,
            "source": self.source_name,
            "source_url": self.base_url,
            "decision_date": self._parse_date(date_str) if date_str else None,
        }

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None

        formats = ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return None

    def collect_cases(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Collect cases from the appellate portal"""
        logger.info(f"Collecting cases from {self.source_name}")

        # Wait for content to load - try common selectors
        wait_selectors = [
            "table",
            "ul",
            ".opinion",
            ".case",
            "[data-opinion]",
            "main",
            "article",
        ]

        response = self.fetch_page(self.base_url, wait_for="main")
        if not response:
            logger.error(f"Failed to fetch {self.base_url}")
            return []

        soup = self.parse_html(response.text)
        cases = self.extract_cases(soup)

        # Filter by date if provided
        if start_date or end_date:
            cases = [c for c in cases if self.filter_by_date(c, start_date, end_date)]

        logger.info(f"Found {len(cases)} cases from {self.source_name}")
        return cases


class MassGovTrialScraper(BaseScraper):
    """Scraper for Mass.gov Published Trial Court Opinions"""

    def __init__(self):
        super().__init__(
            "Mass.gov Trial Court Opinions",
            config.DATA_SOURCES["MASS_GOV_TRIAL"],
            use_playwright=True,
        )

    def extract_cases(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract trial court cases"""
        cases = []

        # Similar approach to appellate scraper
        case_links = soup.find_all(
            "a", href=re.compile(r"opinion|case|docket|decision", re.I)
        )
        tables = soup.find_all("table")
        lists = soup.find_all(["ul", "ol"])

        logger.info(
            f"Found {len(case_links)} links, {len(tables)} tables, {len(lists)} lists"
        )

        for link in case_links:
            try:
                case_info = self._parse_trial_case_link(link)
                if case_info:
                    cases.append(case_info)
            except Exception as e:
                logger.debug(f"Error parsing trial case link: {e}")
                continue

        # Remove duplicates
        seen = set()
        unique_cases = []
        for case in cases:
            key = (case.get("case_name"), case.get("opinion_url"))
            if key not in seen and key[0] and key[1]:
                seen.add(key)
                unique_cases.append(case)

        logger.info(
            f"Extracted {len(unique_cases)} unique cases from {len(cases)} total matches"
        )
        return unique_cases

    def _parse_trial_case_link(self, link) -> Optional[Dict]:
        """Parse a trial court case link"""
        href = link.get("href", "")
        text = link.get_text(strip=True)

        if not text or len(text) < 5:
            return None

        # Skip navigation links
        if any(
            skip in text.lower()
            for skip in ["home", "about", "contact", "search", "menu", "skip"]
        ):
            return None

        # Determine court type from text or URL
        court_type = "SUPERIOR"
        if "district" in href.lower() or "district" in text.lower():
            court_type = "DISTRICT"
        elif "probate" in href.lower() or "probate" in text.lower():
            court_type = "PROBATE"
        elif "housing" in href.lower() or "housing" in text.lower():
            court_type = "HOUSING"
        elif "juvenile" in href.lower() or "juvenile" in text.lower():
            court_type = "JUVENILE"

        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"https://www.mass.gov{href}"
        else:
            full_url = f"{self.base_url}/{href.lstrip('/')}"

        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        date_str = date_match.group(1) if date_match else None

        return {
            "case_name": text[:500],
            "opinion_url": full_url,
            "court_type": court_type,
            "source": self.source_name,
            "source_url": self.base_url,
            "decision_date": self._parse_date(date_str) if date_str else None,
        }

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None

        formats = ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return None

    def collect_cases(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Collect trial court cases"""
        logger.info(f"Collecting cases from {self.source_name}")

        response = self.fetch_page(self.base_url, wait_for="main")
        if not response:
            logger.error(f"Failed to fetch {self.base_url}")
            return []

        soup = self.parse_html(response.text)
        cases = self.extract_cases(soup)

        if start_date or end_date:
            cases = [c for c in cases if self.filter_by_date(c, start_date, end_date)]

        logger.info(f"Found {len(cases)} cases from {self.source_name}")
        return cases
