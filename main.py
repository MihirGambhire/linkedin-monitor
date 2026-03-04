"""
LinkedIn Keyword Monitor for ADOR Digatron
==========================================

Main orchestrator script that runs the full pipeline:
1. Search Google for LinkedIn posts matching keyword categories
2. Send an HTML email digest with results

Usage:
    python main.py                           # Full run (all categories)
    python main.py --categories "BESS" "Competition"   # Specific categories
    python main.py --dry-run                 # Search only, no email
    python main.py --max-results 5           # Limit results per category
    python main.py --time-filter qdr:d       # Past day only
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from src.config import (
    KEYWORD_CATEGORIES,
    EmailConfig,
    SearchConfig,
)
from src.search import search_all_categories
from src.email_sender import send_email

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Keyword Monitor for ADOR Digatron",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help=f"Categories to search. Available: {list(KEYWORD_CATEGORIES.keys())}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search and print results without sending email.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum results per category (default: 10).",
    )
    parser.add_argument(
        "--time-filter",
        default="qdr:w",
        choices=["qdr:d", "qdr:w", "qdr:m"],
        help="Time filter: qdr:d (past day), qdr:w (past week), qdr:m (past month).",
    )
    return parser.parse_args()


def print_results_summary(results: dict) -> None:
    """Print a formatted summary of search results to stdout."""
    total = sum(len(posts) for posts in results.values())
    print("\n" + "=" * 70)
    print(f"  📊 LinkedIn Keyword Monitor — {total} posts found")
    print(f"  📅 {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}")
    print("=" * 70)

    for category, posts in results.items():
        print(f"\n  📁 {category} ({len(posts)} posts)")
        print("  " + "-" * 50)
        if not posts:
            print("     No posts found.")
        for i, post in enumerate(posts, 1):
            print(f"  {i:>3}. {post.title[:60]}")
            print(f"       🔗 {post.url}")
            if post.snippet:
                snippet = post.snippet[:100] + ("..." if len(post.snippet) > 100 else "")
                print(f"       💬 {snippet}")
            print()


def main():
    args = parse_args()

    logger.info("🚀 LinkedIn Keyword Monitor starting...")
    logger.info(f"   Categories: {args.categories or 'ALL'}")
    logger.info(f"   Dry run: {args.dry_run}")
    logger.info(f"   Screenshots: Disabled")

    # -----------------------------------------------------------------------
    # Step 1: Search
    # -----------------------------------------------------------------------
    logger.info("=" * 50)
    logger.info("STEP 1/2 — Searching Google for LinkedIn posts...")
    logger.info("=" * 50)

    search_config = SearchConfig(
        max_results_per_category=args.max_results,
        time_filter=args.time_filter,
    )
    results = search_all_categories(
        config=search_config,
        categories=args.categories,
    )

    total = sum(len(p) for p in results.values())
    if total == 0:
        logger.warning("No posts found. Exiting.")
        print_results_summary(results)
        sys.exit(0)

    print_results_summary(results)

    # In dry-run mode, just print and exit
    if args.dry_run:
        logger.info("Dry-run mode — skipping email.")
        json_results = {
            cat: [
                {"title": p.title, "url": p.url, "snippet": p.snippet}
                for p in posts
            ]
            for cat, posts in results.items()
        }
        print("\n📄 JSON Output:")
        print(json.dumps(json_results, indent=2))
        sys.exit(0)

    # -----------------------------------------------------------------------
    # Step 2: Send email (no screenshots)
    # -----------------------------------------------------------------------
    logger.info("=" * 50)
    logger.info("STEP 2/2 — Sending email digest...")
    logger.info("=" * 50)

    email_config = EmailConfig()
    success = send_email(results, {}, email_config)

    if success:
        logger.info("✅ Pipeline complete! Email sent.")
        sys.exit(0)
    else:
        logger.error("❌ Pipeline failed at email step.")
        sys.exit(1)


if __name__ == "__main__":
    main()
