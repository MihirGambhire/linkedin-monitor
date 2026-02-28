"""
Search module — finds LinkedIn posts via Google Search (SerpAPI).

Uses SerpAPI's Google Search endpoint with `site:linkedin.com` filtering
to discover publicly visible LinkedIn posts matching keyword categories.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from serpapi import GoogleSearch

from .config import (
    KEYWORD_CATEGORIES,
    SearchConfig,
    build_search_query,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single LinkedIn post found via search."""

    title: str
    url: str
    snippet: str
    category: str
    found_at: str  # ISO timestamp

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, SearchResult):
            return False
        return self.url == other.url


def _clean_linkedin_url(url: str) -> str:
    """Remove Google redirect wrappers and tracking params."""
    # Sometimes SerpAPI returns clean URLs, but verify
    if "linkedin.com" in url:
        # Strip query params that are just tracking noise
        base = url.split("?")[0]
        return base
    return url


def search_category(
    category: str,
    keywords: List[str],
    config: SearchConfig,
) -> List[SearchResult]:
    """
    Search Google for LinkedIn posts matching keywords in one category.

    Args:
        category: Category name (e.g., "Cell/Battery Tester")
        keywords: List of keyword strings for this category
        config: Search configuration with API key and params

    Returns:
        List of SearchResult objects
    """
    query = build_search_query(category, keywords)
    logger.info(f"[{category}] Searching: {query[:120]}...")

    params = {
        "engine": "google",
        "q": query,
        "api_key": config.serpapi_key,
        "num": config.max_results_per_category,
        "tbs": config.time_filter,  # Time-based filter (e.g., past week)
        "hl": "en",
        "gl": "in",  # Geo-location India (relevant for ADOR Digatron)
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        logger.error(f"[{category}] SerpAPI request failed: {e}")
        return []

    organic = results.get("organic_results", [])
    logger.info(f"[{category}] Found {len(organic)} results")

    parsed: List[SearchResult] = []
    for item in organic:
        url = _clean_linkedin_url(item.get("link", ""))
        if "linkedin.com" not in url:
            continue

        parsed.append(
            SearchResult(
                title=item.get("title", "Untitled Post"),
                url=url,
                snippet=item.get("snippet", ""),
                category=category,
                found_at=datetime.utcnow().isoformat(),
            )
        )

    return parsed


def search_all_categories(
    config: Optional[SearchConfig] = None,
    categories: Optional[List[str]] = None,
) -> Dict[str, List[SearchResult]]:
    """
    Run searches across all (or selected) keyword categories.

    Args:
        config: Search configuration. If None, uses defaults (env vars).
        categories: Optional list of category names to search.
                    If None, searches all categories.

    Returns:
        Dict mapping category name -> list of SearchResult
    """
    if config is None:
        config = SearchConfig()

    if not config.serpapi_key:
        logger.error(
            "SERPAPI_KEY not set. Export it as an environment variable."
        )
        return {}

    target_categories = categories or list(KEYWORD_CATEGORIES.keys())

    all_results: Dict[str, List[SearchResult]] = {}
    seen_urls: set = set()

    for cat_name in target_categories:
        if cat_name not in KEYWORD_CATEGORIES:
            logger.warning(f"Unknown category: {cat_name}, skipping.")
            continue

        keywords = KEYWORD_CATEGORIES[cat_name]
        results = search_category(cat_name, keywords, config)

        # Deduplicate across categories
        unique = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)

        all_results[cat_name] = unique
        logger.info(
            f"[{cat_name}] {len(unique)} unique results "
            f"({len(results) - len(unique)} duplicates removed)"
        )

    total = sum(len(v) for v in all_results.values())
    logger.info(f"Total unique results across all categories: {total}")
    return all_results
