"""
Scraper for Mass.gov opinion portals
"""
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
from scraper_base import BaseScraper
import config

logger = logging.getLogger(__name__)


class MassGovAppellateScraper(BaseScraper):
    """Scraper for Mass.gov Appellate Opinion Portal"""
    
    def __init__(self):
        super().__init__("Mass.gov Appellate Portal", config.DATA_SOURCES["MASS_GOV_APPELLATE"])
    
    def extract_cases(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract cases from the opinion portal page"""
        cases = []
        
        # The structure of Mass.gov pages can vary, so we'll need to adapt
        # Look for case listings - common patterns include:
        # - Links to opinion PDFs
        # - Case name and date information
        # - Docket numbers
        
        # Try to find case listings (this will need to be adjusted based on actual page structure)
        case_links = soup.find_all('a', href=re.compile(r'opinion|case|docket', re.I))
        
        for link in case_links:
            try:
                case_info = self._parse_case_link(link)
                if case_info:
                    cases.append(case_info)
            except Exception as e:
                logger.warning(f"Error parsing case link: {e}")
                continue
        
        return cases
    
    def _parse_case_link(self, link) -> Optional[Dict]:
        """Parse a single case link to extract information"""
        # This is a placeholder - actual implementation depends on page structure
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Try to extract date from text or nearby elements
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        date_str = date_match.group(1) if date_match else None
        
        # Try to determine court type from URL or text
        court_type = "APPEALS"
        if "sjc" in href.lower() or "supreme" in text.lower():
            court_type = "SJC"
        
        if not text or len(text) < 5:
            return None
        
        return {
            'case_name': text,
            'opinion_url': href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}",
            'court_type': court_type,
            'source': self.source_name,
            'source_url': self.base_url
        }
    
    def collect_cases(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """Collect cases from the appellate portal"""
        logger.info(f"Collecting cases from {self.source_name}")
        
        response = self.fetch_page(self.base_url)
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
        super().__init__("Mass.gov Trial Court Opinions", config.DATA_SOURCES["MASS_GOV_TRIAL"])
    
    def extract_cases(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract trial court cases"""
        cases = []
        
        # Similar structure to appellate scraper but for trial courts
        case_links = soup.find_all('a', href=re.compile(r'opinion|case|docket', re.I))
        
        for link in case_links:
            try:
                case_info = self._parse_trial_case_link(link)
                if case_info:
                    cases.append(case_info)
            except Exception as e:
                logger.warning(f"Error parsing trial case link: {e}")
                continue
        
        return cases
    
    def _parse_trial_case_link(self, link) -> Optional[Dict]:
        """Parse a trial court case link"""
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
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
        
        if not text or len(text) < 5:
            return None
        
        return {
            'case_name': text,
            'opinion_url': href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}",
            'court_type': court_type,
            'source': self.source_name,
            'source_url': self.base_url
        }
    
    def collect_cases(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """Collect trial court cases"""
        logger.info(f"Collecting cases from {self.source_name}")
        
        response = self.fetch_page(self.base_url)
        if not response:
            logger.error(f"Failed to fetch {self.base_url}")
            return []
        
        soup = self.parse_html(response.text)
        cases = self.extract_cases(soup)
        
        if start_date or end_date:
            cases = [c for c in cases if self.filter_by_date(c, start_date, end_date)]
        
        logger.info(f"Found {len(cases)} cases from {self.source_name}")
        return cases
