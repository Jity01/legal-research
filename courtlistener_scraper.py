"""
Scraper for CourtListener.com - Massachusetts court cases
"""
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
from scraper_base import BaseScraper
import config
import time

logger = logging.getLogger(__name__)


class CourtListenerScraper(BaseScraper):
    """Scraper for CourtListener.com Massachusetts cases"""

    def __init__(self):
        super().__init__(
            "CourtListener.com",
            "https://www.courtlistener.com",
            use_playwright=True,
        )
        self.base_search_url = "https://www.courtlistener.com/?q&type=o&order_by=dateFiled%20desc&stat_Published=on&court=mass"

    def extract_cases_from_search(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract case information from search results page"""
        cases = []

        # CourtListener uses specific structure - look for result items
        # Try multiple selectors based on common patterns
        case_results = []
        
        # Method 1: Look for result containers with opinion links
        opinion_links = soup.find_all("a", href=re.compile(r"/opinion/\d+/", re.I))
        for link in opinion_links:
            # Get the parent container (usually a div or article)
            parent = link.find_parent(["div", "article", "li"])
            if parent and parent not in case_results:
                case_results.append(parent)
        
        # Method 2: If no results, try finding by class patterns
        if not case_results:
            case_results = soup.find_all(["div", "article", "li"], class_=re.compile(r"result|search-result|opinion-item", re.I))
        
        # Method 3: Look for items containing docket numbers
        if not case_results:
            docket_elements = soup.find_all(string=re.compile(r"SJC-\d+|Docket Number", re.I))
            for elem in docket_elements:
                parent = elem.find_parent(["div", "article", "li"])
                if parent and parent not in case_results:
                    case_results.append(parent)

        logger.info(f"Found {len(case_results)} case result containers")

        for result in case_results:
            try:
                case_info = self._parse_search_result(result)
                if case_info:
                    cases.append(case_info)
            except Exception as e:
                logger.debug(f"Error parsing search result: {e}")
                continue

        return cases

    def _parse_search_result(self, result_element) -> Optional[Dict]:
        """Parse a single search result element"""
        # Find the case name (usually in an <a> tag with opinion URL)
        case_link = result_element.find("a", href=re.compile(r"/opinion/\d+/", re.I))
        if not case_link:
            return None

        case_name = case_link.get_text(strip=True)
        if not case_name or len(case_name) < 5:
            return None
            
        case_url = case_link.get("href", "")
        if not case_url.startswith("http"):
            case_url = f"https://www.courtlistener.com{case_url}"

        # Get all text from the result element
        result_text = result_element.get_text(separator="\n")

        # Extract docket number - look for "Docket Number: SJC-XXXXX" or "SJC-XXXXX"
        docket_match = re.search(r"Docket Number:\s*(SJC-[\d]+|[A-Z0-9-]+)", result_text, re.I)
        if not docket_match:
            # Try finding SJC- pattern directly
            docket_match = re.search(r"(SJC-[\d]+)", result_text, re.I)
        docket_number = docket_match.group(1) if docket_match else None

        # Extract date filed - look for "Date Filed: Month Day, Year"
        date_match = re.search(r"Date Filed:\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4})", result_text, re.I)
        if not date_match:
            # Try alternative format
            date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", result_text)
        date_str = date_match.group(1) if date_match else None
        
        # Extract status
        status_match = re.search(r"Status:\s*(\w+)", result_text, re.I)
        status = status_match.group(1) if status_match else "Published"

        # Determine court type from docket number or case name
        court_type = "APPEALS"
        if docket_number and "SJC" in docket_number:
            court_type = "SJC"
        elif "Appeals" in case_name or "Appeals Court" in result_text:
            court_type = "APPEALS"

        # Parse date
        decision_date = self._parse_date(date_str) if date_str else None

        return {
            "case_name": case_name,
            "docket_number": docket_number,
            "opinion_url": case_url,
            "court_type": court_type,
            "decision_date": decision_date,
            "source": self.source_name,
            "source_url": self.base_search_url,
            "case_type": "Published" if status == "Published" else None,
        }

    def extract_case_details(self, soup: BeautifulSoup, case_url: str) -> Dict:
        """Extract detailed information from an individual case page"""
        details = {}

        # Extract case name (usually in h1 or h2)
        case_name_elem = soup.find("h1") or soup.find("h2")
        if case_name_elem:
            details["case_name"] = case_name_elem.get_text(strip=True)

        # Extract metadata from the page - look for structured data
        page_text = soup.get_text(separator="\n")

        # Extract docket number - look for "Docket Number: SJC-XXXXX"
        docket_match = re.search(r"Docket Number:\s*(SJC-[\d]+|[A-Z0-9-]+)", page_text, re.I)
        if not docket_match:
            # Try finding SJC- pattern directly
            docket_match = re.search(r"(SJC-[\d]+)", page_text, re.I)
        if docket_match:
            details["docket_number"] = docket_match.group(1)

        # Extract date - look for "Dates:" or "Date Filed:"
        date_match = re.search(r"(?:Dates?|Date Filed):\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4})", page_text, re.I)
        if not date_match:
            date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", page_text)
        if date_match:
            details["decision_date"] = self._parse_date(date_match.group(1))

        # Extract judges - look for "Present:" or "County:"
        judges_match = re.search(r"Present:\s*(.+?)(?:\n|County|Keywords)", page_text, re.I | re.DOTALL)
        if not judges_match:
            judges_match = re.search(r"County:\s*(.+?)(?:\n|Keywords)", page_text, re.I | re.DOTALL)
        if judges_match:
            judges_text = judges_match.group(1).strip()
            # Clean up the text
            judges_text = re.sub(r"\s+", " ", judges_text)
            details["judges"] = judges_text

        # Extract keywords - look for "Keywords:"
        keywords_match = re.search(r"Keywords:\s*(.+?)(?:\n\n|\n[A-Z]|$)", page_text, re.I | re.DOTALL)
        if keywords_match:
            keywords_text = keywords_match.group(1).strip()
            # Split by comma or period
            keywords = [k.strip() for k in re.split(r"[,.]", keywords_text) if k.strip()]
            details["topics"] = ", ".join(keywords)

        # Extract full opinion text - look for the opinion content
        # Try to find the main content area
        opinion_elem = (
            soup.find("div", class_=re.compile(r"opinion|text|content|combined", re.I))
            or soup.find("article")
            or soup.find("div", id=re.compile(r"opinion|content", re.I))
        )
        
        if opinion_elem:
            # Remove script, style, and navigation elements
            for script in opinion_elem(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get text content
            opinion_text = opinion_elem.get_text(separator="\n", strip=True)
            
            # Clean up excessive whitespace
            opinion_text = re.sub(r"\n{3,}", "\n\n", opinion_text)
            details["opinion_text"] = opinion_text[:50000]  # Limit to 50k chars for database

        return details

    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Find the URL for the next page of results"""
        # Look for pagination - try multiple methods
        next_link = None
        
        # Method 1: Look for "Next" text
        next_link = soup.find("a", string=re.compile(r"Next", re.I))
        
        # Method 2: Look for next button by class
        if not next_link:
            next_link = soup.find("a", class_=re.compile(r"next|pagination.*next", re.I))
        
        # Method 3: Look for aria-label
        if not next_link:
            next_link = soup.find("a", {"aria-label": re.compile(r"next", re.I)})
        
        # Method 4: Look for pagination with page numbers and find "next" or ">"
        if not next_link:
            pagination = soup.find(["nav", "div"], class_=re.compile(r"pagination", re.I))
            if pagination:
                next_link = pagination.find("a", string=re.compile(r"Next|>|»", re.I))
        
        # Method 5: Look for links with "page=" parameter that's higher than current
        if not next_link:
            # Try to find current page number
            current_page_match = re.search(r"[?&]page=(\d+)", current_url)
            if current_page_match:
                current_page = int(current_page_match.group(1))
                next_page = current_page + 1
                # Look for link with next page number
                page_links = soup.find_all("a", href=re.compile(rf"page={next_page}", re.I))
                if page_links:
                    next_link = page_links[0]

        if next_link:
            next_url = next_link.get("href", "")
            if next_url.startswith("http"):
                return next_url
            elif next_url.startswith("/"):
                return f"https://www.courtlistener.com{next_url}"
            elif next_url.startswith("?"):
                # Relative query string
                base_url = current_url.split("?")[0]
                return f"{base_url}{next_url}"
            else:
                # Might be a query parameter addition
                if "?" in current_url:
                    return f"{current_url}&{next_url}"
                else:
                    return f"{current_url}?{next_url}"

        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None

        # Try various date formats
        formats = [
            "%B %d, %Y",  # "December 16th, 2025"
            "%B %d, %Y",  # "December 16, 2025"
            "%b %d, %Y",  # "Dec 16, 2025"
            "%m/%d/%Y",   # "12/16/2025"
            "%m-%d-%Y",   # "12-16-2025"
            "%Y-%m-%d",   # "2025-12-16"
        ]

        # Remove ordinal suffixes (st, nd, rd, th)
        date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue

        return None

    def collect_cases(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict]:
        """Collect cases from CourtListener with pagination"""
        logger.info(f"Collecting cases from {self.source_name}")

        all_cases = []
        current_url = self.base_search_url
        page_num = 1
        consecutive_empty_pages = 0

        while current_url:
            try:
                logger.info(f"Fetching page {page_num}: {current_url}")

                response = self.fetch_page(current_url, wait_for="main")
                if not response:
                    logger.error(f"Failed to fetch {current_url}")
                    break

                soup = self.parse_html(response.text)
                page_cases = self.extract_cases_from_search(soup)

                logger.info(f"Found {len(page_cases)} cases on page {page_num}")

                if not page_cases:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info("No cases found on 2 consecutive pages, stopping")
                        break
                else:
                    consecutive_empty_pages = 0

                # Fetch detailed information for each case
                for case in page_cases:
                    try:
                        # Fetch individual case page for full details
                        logger.debug(f"Fetching details for: {case.get('case_name')}")
                        case_response = self.fetch_page(case["opinion_url"])
                        if case_response:
                            case_soup = self.parse_html(case_response.text)
                            case_details = self.extract_case_details(case_soup, case["opinion_url"])
                            
                            # Merge details (case_details override basic info)
                            case.update(case_details)
                            
                            # Filter by date if provided
                            if start_date or end_date:
                                if not self.filter_by_date(case, start_date, end_date):
                                    logger.debug(f"Case {case.get('case_name')} filtered out by date")
                                    continue
                            
                            all_cases.append(case)
                            logger.info(f"Extracted case: {case.get('case_name')} ({case.get('docket_number')})")
                    except Exception as e:
                        logger.warning(f"Error fetching case details for {case.get('opinion_url')}: {e}")
                        # Still add the case with basic info if it passes date filter
                        if start_date or end_date:
                            if not self.filter_by_date(case, start_date, end_date):
                                continue
                        all_cases.append(case)
                        continue

                    # Small delay between case fetches to be respectful
                    time.sleep(config.REQUEST_DELAY)

                # Check for next page
                next_url = self.get_next_page_url(soup, current_url)
                if not next_url:
                    logger.info("No next page found, stopping pagination")
                    break
                    
                if max_pages and page_num >= max_pages:
                    logger.info(f"Reached max pages limit ({max_pages}), stopping")
                    break

                current_url = next_url
                page_num += 1

                # Delay between pages
                time.sleep(config.REQUEST_DELAY)

            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                break

        logger.info(f"Found {len(all_cases)} total cases from {self.source_name}")
        return all_cases
