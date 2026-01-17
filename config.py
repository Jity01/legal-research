"""
Configuration file for Massachusetts court case collection
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Data directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CASES_DIR = os.path.join(DATA_DIR, "cases")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")
DATABASE_PATH = os.path.join(DATA_DIR, "ma_court_cases.db")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CASES_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# Date range
START_YEAR = 1900
END_YEAR = datetime.now().year

# Court types to collect
COURT_TYPES = {
    "SJC": "Supreme Judicial Court",
    "APPEALS": "Massachusetts Appeals Court",
    "SUPERIOR": "Superior Court",
    "DISTRICT": "District Court",
    "PROBATE": "Probate and Family Court",
    "HOUSING": "Housing Court",
    "JUVENILE": "Juvenile Court",
    "FEDERAL_DISTRICT": "U.S. District Court for Massachusetts",
    "FEDERAL_APPEALS": "U.S. Court of Appeals for the First Circuit",
}

# Data sources
DATA_SOURCES = {
    "MASS_GOV_APPELLATE": "https://www.mass.gov/opinion-portal",
    "MASS_GOV_TRIAL": "https://www.mass.gov/published-trial-court-opinions",
    "MASS_GOV_PUBLISHED": "https://www.mass.gov/published-sjc-and-appeals-court-opinions",
    "FEDERAL_DISTRICT": "https://www.mad.uscourts.gov/caseinfo/opinions.htm",
}

# Scraping settings
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3
TIMEOUT = 30

# Database settings
DB_ECHO = False

# Supabase configuration
# These must be set via environment variables or .env file
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set as environment variables. "
        "Create a .env file or set them in your environment. "
        "See .env.example for reference."
    )
