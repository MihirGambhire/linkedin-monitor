"""
Configuration for LinkedIn Keyword Monitor - ADOR Digatron
All keywords organized by category for efficient batched searching.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Keywords grouped by category
# Each category becomes ONE Google search query (keywords OR'd together)
# ---------------------------------------------------------------------------

KEYWORD_CATEGORIES: Dict[str, List[str]] = {
    "Cell/Battery Tester": [
        "Battery Tester",
        "Battery Cycler",
        "Battery Capacity Tester",
        "Battery Aging Machine",
        "Battery Charger-Discharger",
        "Computer Operated Battery Cycler",
        "Computer Operated Battery Tester",
        "Cell Tester",
        "Cell Cycler",
        "Cell Capacity Tester",
        "Cell Aging Machine",
        "Cell Charger Discharger",
        "Computer Operated Cell Cycler",
        "Computer Operated Cell Tester",
        "Cell Grading Machine",
    ],
    "BESS": [
        "BESS",
        "Battery Energy Storage System",
        "GWH battery",
        "Battery Pack Assembly Plant",
        "BESS Manufacturing Plant",
        "Power Conversion System",
        "PCS battery",
        "C&I BESS",
        "C&I ESS",
        "ESS for Data Centers",
    ],
    "Cell Assembly Line": [
        "Lithium ion cell assembly line",
        "Battery cell manufacturing",
        "Pouch cell line",
        "Cylindrical cell line",
        "Prismatic cell assembly",
        "Battery formation ageing",
        "Cell formation system",
        "Formation testing equipment",
        "Environmental chamber battery",
        "Advanced chemistry cell manufacturing",
        "Cell Manufacturing Plant",
    ],
    "Cell Chemistries": [
        "Sodium Ion battery",
        "Metal Air battery",
        "Aluminum Air battery",
        "Sodium Silicate battery",
        "Agnostic Chemistry battery",
        "Lead Acid battery",
        "Ni Cd battery",
        "Nickel Cadmium battery",
    ],
    "Competition": [
        "RePower battery",
        "Neware battery",
        "Chroma battery tester",
        "Bitrode battery",
        "Arbin battery",
        "ACEY battery",
        "Sinexcel",
        "Nebula Electronics battery",
        "SEMCO battery",
        "DNA Technologies battery",
        "Encore Systems battery",
        "Indygreen Technologies",
    ],
}


@dataclass
class SearchConfig:
    """Search configuration parameters."""

    # SerpAPI key (from environment)
    serpapi_key: str = field(
        default_factory=lambda: os.environ.get("SERPAPI_KEY", "")
    )

    # How many results to fetch per category query
    max_results_per_category: int = 10

    # Only show posts from the last N days
    recency_days: int = 7

    # Google search time filter: qdr:d (day), qdr:w (week), qdr:m (month)
    time_filter: str = "qdr:w"

    # LinkedIn site restriction
    site_filter: str = "site:linkedin.com/posts OR site:linkedin.com/feed/update"


@dataclass
class EmailConfig:
    """Email configuration, loaded from environment variables."""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = field(
        default_factory=lambda: os.environ.get("GMAIL_ADDRESS", "")
    )
    sender_password: str = field(
        default_factory=lambda: os.environ.get("GMAIL_APP_PASSWORD", "")
    )
    recipient_email: str = field(
        default_factory=lambda: os.environ.get(
            "RECIPIENT_EMAIL",
            os.environ.get("GMAIL_ADDRESS", ""),
        )
    )
    subject_prefix: str = "[ADOR Digatron] LinkedIn Keyword Monitor"


@dataclass
class ScreenshotConfig:
    """Screenshot capture settings."""

    viewport_width: int = 1280
    viewport_height: int = 900
    wait_seconds: int = 5          # Wait for page to load before screenshot
    timeout_seconds: int = 30      # Max time to wait for a page
    output_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "screenshots",
        )
    )


def build_search_query(category: str, keywords: List[str]) -> str:
    """
    Build a Google search query for a category.
    Combines keywords with OR and restricts to linkedin.com.

    Example output:
      ("Battery Tester" OR "Battery Cycler") site:linkedin.com/posts
    """
    quoted = [f'"{kw}"' for kw in keywords]
    keyword_clause = " OR ".join(quoted)
    return f"({keyword_clause}) (site:linkedin.com/posts OR site:linkedin.com/feed/update)"
