"""
Screenshot module — captures screenshots of LinkedIn posts using Playwright.

Uses headless Chromium to render LinkedIn post pages and save PNG screenshots.
Only works for publicly visible posts (no LinkedIn login).
"""

import logging
import os
from typing import Dict, List, Optional

from .config import ScreenshotConfig
from .search import SearchResult

logger = logging.getLogger(__name__)


async def capture_screenshot(
    url: str,
    output_path: str,
    config: ScreenshotConfig,
) -> bool:
    """
    Capture a screenshot of a URL using Playwright.

    Args:
        url: The LinkedIn post URL to screenshot
        output_path: File path to save the PNG screenshot
        config: Screenshot configuration

    Returns:
        True if screenshot was captured successfully, False otherwise
    """
    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={
                    "width": config.viewport_width,
                    "height": config.viewport_height,
                },
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            # Navigate to the URL
            await page.goto(
                url,
                wait_until="networkidle",
                timeout=config.timeout_seconds * 1000,
            )

            # Wait a bit for dynamic content to render
            await page.wait_for_timeout(config.wait_seconds * 1000)

            # Dismiss any LinkedIn login modals/overlays if they appear
            try:
                # Try to close common LinkedIn popups
                for selector in [
                    'button[aria-label="Dismiss"]',
                    'button.modal__dismiss',
                    '[data-tracking-control-name="public_post_feed-secondary-cta"]',
                    'button.contextual-sign-in-modal__modal-dismiss-btn',
                ]:
                    dismiss_btn = page.locator(selector).first
                    if await dismiss_btn.is_visible(timeout=2000):
                        await dismiss_btn.click()
                        await page.wait_for_timeout(500)
            except Exception:
                pass  # No popup to dismiss, that's fine

            # Capture screenshot
            await page.screenshot(path=output_path, full_page=False)
            await browser.close()

            logger.info(f"Screenshot saved: {output_path}")
            return True

    except Exception as e:
        logger.warning(f"Failed to screenshot {url}: {e}")
        return False


async def capture_all_screenshots(
    results: Dict[str, List[SearchResult]],
    config: Optional[ScreenshotConfig] = None,
) -> Dict[str, Optional[str]]:
    """
    Capture screenshots for all search results.

    Args:
        results: Dict of category -> list of SearchResult
        config: Screenshot configuration. If None, uses defaults.

    Returns:
        Dict mapping post URL -> screenshot file path (or None if failed)
    """
    if config is None:
        config = ScreenshotConfig()

    # Create output directory
    os.makedirs(config.output_dir, exist_ok=True)

    screenshots: Dict[str, Optional[str]] = {}
    idx = 0

    for category, posts in results.items():
        for post in posts:
            idx += 1
            safe_name = f"post_{idx:03d}.png"
            output_path = os.path.join(config.output_dir, safe_name)

            success = await capture_screenshot(
                post.url, output_path, config
            )
            screenshots[post.url] = output_path if success else None

    captured = sum(1 for v in screenshots.values() if v is not None)
    logger.info(
        f"Screenshots captured: {captured}/{len(screenshots)} posts"
    )
    return screenshots
