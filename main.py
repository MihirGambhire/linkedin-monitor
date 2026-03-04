"""
LinkedIn Post Monitor
Searches LinkedIn for posts containing specified keywords.
Sends an email with post URL, author name, and snippet.
STEALTH MODE: Human-like delays and anti-detection features.
"""

import time
import json
import os
import re
import smtplib
import logging
import argparse
import random
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LinkedInPostMonitor:
    def __init__(self):
        self.config = Config()
        self.driver = None
        self.seen_file = "seen_posts.json"
        self.seen_posts = self._load_seen()

    def _load_seen(self):
        if os.path.exists(self.seen_file):
            with open(self.seen_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_seen(self):
        with open(self.seen_file, 'w') as f:
            json.dump(list(self.seen_posts), f)

    def _init_driver(self):
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-agent={self.config.USER_AGENT}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--disable-features=IsolateOrigins,site-per-process")
        opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.add_argument(f"--window-position={random.randint(0,100)},{random.randint(0,100)}")

        self.driver = webdriver.Chrome(options=opts)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        try:
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.config.USER_AGENT
            })
        except Exception:
            pass
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]})"
        )
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']})"
        )
        logger.info("Chrome driver initialised with stealth settings")

    # ── Debug helpers ─────────────────────────────────────────────────────
    def _save_debug_snapshot(self, label="debug"):
        """Save a screenshot + page source to help diagnose empty results."""
        try:
            fname = f"{label}_{datetime.now().strftime('%H%M%S')}"
            self.driver.save_screenshot(f"{fname}.png")
            with open(f"{fname}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"  Debug snapshot saved: {fname}.png / {fname}.html")
        except Exception as e:
            logger.warning(f"  Could not save snapshot: {e}")

    # ── Login ─────────────────────────────────────────────────────────────
    def _login(self):
        """Login using li_at session cookie."""
        try:
            self.driver.get("https://www.linkedin.com")
            time.sleep(random.uniform(2, 4))

            self.driver.add_cookie({
                "name": "li_at",
                "value": self.config.LINKEDIN_LI_AT,
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            })

            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(random.uniform(4, 6))

            for _ in range(2):
                self.driver.execute_script(
                    f"window.scrollTo(0, {random.randint(300, 800)});"
                )
                time.sleep(random.uniform(1, 2))

            current_url = self.driver.current_url
            page_source = self.driver.page_source

            # Blocked by auth wall or CAPTCHA
            if "authwall" in current_url or "checkpoint" in current_url:
                logger.error("Login blocked — LinkedIn auth wall or CAPTCHA detected")
                self._save_debug_snapshot("login_blocked")
                return False

            # Success indicators
            if "feed" in current_url or "mynetwork" in current_url:
                logger.info(f"Logged in successfully (URL: {current_url})")
                return True

            if 'data-li-page-id' in page_source or '"loggedIn":true' in page_source:
                logger.info("Logged in (detected via page content)")
                return True

            logger.error(f"Cookie login failed. Current URL: {current_url}")
            self._save_debug_snapshot("login_failed")
            return False

        except Exception as e:
            logger.error(f"Cookie login error: {e}")
            self._save_debug_snapshot("login_error")
            return False

    # ── Public post search ────────────────────────────────────────────────
    def _search_public_posts(self, keyword):
        encoded = quote_plus(keyword)
        url = (
            f"https://www.linkedin.com/search/results/content/"
            f"?keywords={encoded}&sortBy=date_posted"
        )
        logger.info(f"  Searching public posts for: '{keyword}'")
        time.sleep(random.uniform(3, 6))
        self.driver.get(url)
        time.sleep(random.uniform(5, 8))

        if "search/results" not in self.driver.current_url:
            logger.warning(f"  Unexpected redirect to: {self.driver.current_url}")
            self._save_debug_snapshot(f"search_redirect_{keyword[:20].replace(' ','_')}")

        return self._extract_posts_from_feed(keyword, source="public")

    # ── Group post search ─────────────────────────────────────────────────
    def _search_group_posts(self, keyword, group_id):
        url = f"https://www.linkedin.com/groups/{group_id}/"
        logger.info(f"  Group {group_id}: '{keyword}'")
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))
        return self._extract_posts_from_feed(keyword, source=f"group:{group_id}")

    # ── Person/page post search ───────────────────────────────────────────
    def _search_person_posts(self, keyword, profile_slug):
        url = f"https://www.linkedin.com/in/{profile_slug}/recent-activity/shares/"
        logger.info(f"  Profile {profile_slug}: '{keyword}'")
        self.driver.get(url)
        time.sleep(random.uniform(3, 5))
        return self._extract_posts_from_feed(keyword, source=f"profile:{profile_slug}")

    # ── Core extraction logic ─────────────────────────────────────────────
    def _extract_posts_from_feed(self, keyword, source):
        found = []

        # Human-like scrolling
        for _ in range(self.config.SCROLL_TIMES):
            scroll_distance = random.randint(500, 1200)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(2, 4))
            if random.random() < 0.3:
                self.driver.execute_script(
                    f"window.scrollBy(0, -{random.randint(100, 300)});"
                )
                time.sleep(random.uniform(0.5, 1.5))

        # ── Updated selectors (LinkedIn 2024-2025 DOM) ────────────────────
        selectors = [
            # Current (most reliable as of 2024-2025)
            "div[data-view-name='search-entity-result-universal-template']",
            "li[data-occludable-entity-urn]",
            "div[class*='update-components-text']",
            # Legacy fallbacks
            "div.feed-shared-update-v2",
            "div[data-urn*='activity']",
            "li.profile-creator-shared-feed-update__container",
            "div.occludable-update",
        ]

        containers = []
        for sel in selectors:
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if containers:
                    logger.info(f"    Matched selector '{sel}' — {len(containers)} containers")
                    break
            except Exception:
                continue

        if not containers:
            logger.warning("    No containers found with any selector — saving debug snapshot")
            self._save_debug_snapshot(f"no_containers_{keyword[:20].replace(' ','_')}")
        else:
            logger.info(f"    Processing {len(containers)} containers for keyword '{keyword}'")

        for container in containers:
            post = self._extract_post_data(container, keyword, source)
            if post:
                found.append(post)

        return found

    # ── Post age parsing ──────────────────────────────────────────────────
    def _parse_post_age(self, age_text):
        if not age_text:
            return None
        age_text = age_text.strip().lower()
        now = datetime.now(timezone.utc)
        try:
            if 'just now' in age_text or age_text == 'now':
                return now
            match = re.search(r'(\d+)\s*(s|m|h|d|w|mo|yr)', age_text)
            if not match:
                return None
            value, unit = int(match.group(1)), match.group(2)
            delta_map = {
                's':  timedelta(seconds=value),
                'm':  timedelta(minutes=value),
                'h':  timedelta(hours=value),
                'd':  timedelta(days=value),
                'w':  timedelta(weeks=value),
                'mo': timedelta(days=value * 30),
                'yr': timedelta(days=value * 365),
            }
            return now - delta_map.get(unit, timedelta(days=999))
        except Exception:
            return None

    def _is_recent(self, age_text):
        post_time = self._parse_post_age(age_text)
        if post_time is None:
            return True
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.MAX_POST_AGE_DAYS)
        return post_time >= cutoff

    # ── Per-container extraction ──────────────────────────────────────────
    def _extract_post_data(self, container, keyword, source):
        try:
            # ── Post age ─────────────────────────────────────────────────
            age_text = ""
            age_selectors = [
                "span[aria-hidden='true']",
                ".update-components-actor__sub-description span[aria-hidden='true']",
                "time",
                "span.feed-shared-actor__sub-description",
                ".update-components-actor__sub-description",
                "a.app-aware-link span[aria-hidden='true']",
            ]
            time_units = ['now', 'just', 'ago', 's', 'm', 'h', 'd', 'w', 'mo', 'yr']
            for sel in age_selectors:
                try:
                    candidates = container.find_elements(By.CSS_SELECTOR, sel)
                    for el in candidates:
                        t = el.text.strip() or el.get_attribute("datetime") or ""
                        if t and any(u in t.lower() for u in time_units):
                            age_text = t
                            break
                    if age_text:
                        break
                except NoSuchElementException:
                    continue

            if not self._is_recent(age_text):
                logger.debug(f"    Skipping old post ({age_text})")
                return None

            # ── Post text ────────────────────────────────────────────────
            text = ""
            text_selectors = [
                # Current (2024-2025)
                ".update-components-text",
                ".update-components-text__text-view",
                "div[class*='update-components-text'] span[dir='ltr']",
                # Legacy
                ".feed-shared-update-v2__description",
                ".feed-shared-text",
                ".break-words",
                "span[dir='ltr']",
            ]
            for sel in text_selectors:
                try:
                    el = container.find_element(By.CSS_SELECTOR, sel)
                    text = el.text.strip()
                    if text:
                        break
                except NoSuchElementException:
                    continue

            if not text:
                return None

            # ── Keyword matching ──────────────────────────────────────────
            text_lower = text.lower()
            keyword_lower = keyword.lower()
            stopwords = {'for', 'the', 'and', 'or', 'to', 'a', 'in', 'of'}
            keyword_words = [w for w in keyword_lower.split() if w not in stopwords]

            if len(keyword_words) <= 2:
                if keyword_lower not in text_lower:
                    return None
            else:
                words_found = sum(1 for w in keyword_words if w in text_lower)
                if words_found < len(keyword_words) * 0.6:
                    return None

            # ── Noise / spam filter ───────────────────────────────────────
            # Discard posts that are clearly NOT buyer leads:
            # job ads, market reports, press releases, webinars, etc.
            spam_phrases = getattr(self.config, 'SPAM_PHRASES', [])
            if any(phrase.lower() in text_lower for phrase in spam_phrases):
                logger.debug(f"    Skipping noise post (spam phrase matched)")
                return None

            # ── Post URL ─────────────────────────────────────────────────
            post_url = ""
            url_selectors = [
                "a[href*='/feed/update/']",
                "a[href*='ugcPost']",
                "a[href*='activity']",
                "a[href*='/posts/']",
            ]
            for sel in url_selectors:
                try:
                    href = container.find_element(
                        By.CSS_SELECTOR, sel
                    ).get_attribute("href")
                    if href and "linkedin.com" in href:
                        post_url = href.split("?")[0]
                        break
                except NoSuchElementException:
                    continue

            if not post_url:
                # Last resort: scan all links
                try:
                    for a in container.find_elements(By.TAG_NAME, "a"):
                        href = a.get_attribute("href") or ""
                        if "linkedin.com" in href and any(
                            kw in href for kw in ["posts", "activity", "ugcPost"]
                        ):
                            post_url = href.split("?")[0]
                            break
                except Exception:
                    pass

            if not post_url:
                return None

            if post_url in self.seen_posts:
                return None

            # ── Author name ──────────────────────────────────────────────
            author = "Unknown"
            author_selectors = [
                ".update-components-actor__name span[aria-hidden='true']",
                ".update-components-actor__name",
                ".feed-shared-actor__name",
                ".feed-shared-update-v2__actor-name",
                "span.hoverable-link-text",
            ]
            for sel in author_selectors:
                try:
                    a = container.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if a:
                        author = a
                        break
                except NoSuchElementException:
                    continue

            # ── Snippet ───────────────────────────────────────────────────
            snippet = text[:200].replace("\n", " ").strip()
            if len(text) > 200:
                snippet += "…"

            self.seen_posts.add(post_url)

            return {
                "url": post_url,
                "author": author,
                "snippet": snippet,
                "keyword": keyword,
                "source": source,
                "post_age": age_text if age_text else "recent",
                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

        except Exception as e:
            logger.debug(f"    Extraction error: {e}")
            return None

    # ── Main run cycle ────────────────────────────────────────────────────
    def run(self):
        logger.info("=" * 55)
        logger.info(f"Monitor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 55)

        all_posts = []

        try:
            self._init_driver()
            if not self._login():
                logger.error("Login failed — aborting. Check debug snapshot artifacts.")
                return

            for keyword in self.config.KEYWORDS:
                all_posts += self._search_public_posts(keyword)

                delay = random.uniform(10, 20)
                logger.info(f"  Waiting {delay:.1f}s before next keyword...")
                time.sleep(delay)

                for group_id in self.config.GROUP_IDS:
                    all_posts += self._search_group_posts(keyword, group_id)
                    time.sleep(random.uniform(2, 4))

                for slug in self.config.PROFILE_SLUGS:
                    all_posts += self._search_person_posts(keyword, slug)
                    time.sleep(random.uniform(2, 4))

            # Deduplicate across keywords
            seen_urls = set()
            unique_posts = []
            for p in all_posts:
                if p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    unique_posts.append(p)

            logger.info(f"Total unique posts found: {len(unique_posts)}")

            if unique_posts:
                logger.info(f"Sending email with {len(unique_posts)} posts...")
                self._send_email(unique_posts)
                self._save_seen()
            else:
                logger.info("No new posts found.")

        except Exception as e:
            logger.error(f"Run error: {e}", exc_info=True)
        finally:
            if self.driver:
                self.driver.quit()

        logger.info(f"Done. {len(all_posts)} total posts found.")

    # ── Email ─────────────────────────────────────────────────────────────
    def _send_email(self, posts):
        msg = MIMEMultipart("alternative")
        msg["From"] = self.config.EMAIL_SENDER
        msg["To"] = self.config.EMAIL_RECIPIENT
        msg["Subject"] = (
            f"🎯 LinkedIn Leads: {len(posts)} buyer-intent post{'s' if len(posts) > 1 else ''} "
            f"— {datetime.now().strftime('%b %d, %Y %H:%M')}"
        )
        msg.attach(MIMEText(self._build_plain(posts), "plain"))
        msg.attach(MIMEText(self._build_html(posts), "html"))

        with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(self.config.EMAIL_SENDER, self.config.EMAIL_PASSWORD)
            s.sendmail(self.config.EMAIL_SENDER, self.config.EMAIL_RECIPIENT, msg.as_string())

        logger.info(f"Email sent → {self.config.EMAIL_RECIPIENT}")

    def _build_plain(self, posts):
        lines = [f"LinkedIn Post Monitor — {len(posts)} new posts\n"]
        for i, p in enumerate(posts, 1):
            lines += [
                f"{i}. {p['author']}",
                f"   Keyword : {p['keyword']}",
                f"   Age     : {p['post_age']}",
                f"   \"{p['snippet']}\"",
                f"   {p['url']}",
                "",
            ]
        return "\n".join(lines)

    def _build_html(self, posts):
        by_keyword = {}
        for p in posts:
            by_keyword.setdefault(p["keyword"], []).append(p)

        sections = ""
        for keyword, kw_posts in by_keyword.items():
            cards = ""
            for p in kw_posts:
                cards += f"""
                <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px 20px;
                            margin-bottom:12px;background:#fff">
                  <div style="font-size:13px;color:#888;margin-bottom:6px">
                    <strong style="color:#222">{p['author']}</strong>
                    &nbsp;·&nbsp;
                    <span style="background:#f0f7ff;color:#0077B5;padding:2px 7px;
                                 border-radius:10px;font-size:12px">{p['post_age']}</span>
                  </div>
                  <div style="color:#333;font-size:14px;line-height:1.5;margin-bottom:12px">
                    "{p['snippet']}"
                  </div>
                  <a href="{p['url']}"
                     style="display:inline-block;background:#0077B5;color:#fff;
                            text-decoration:none;padding:7px 16px;border-radius:5px;
                            font-size:13px;font-weight:600">
                    View Post →
                  </a>
                </div>"""

            sections += f"""
            <div style="margin-bottom:28px">
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;
                          letter-spacing:1px;color:#0077B5;margin-bottom:10px">
                {keyword} &nbsp;·&nbsp; {len(kw_posts)} post{'s' if len(kw_posts)>1 else ''}
              </div>
              {cards}
            </div>"""

        return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f5f5;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
  <div style="max-width:620px;margin:30px auto">
    <div style="background:#0077B5;border-radius:10px 10px 0 0;padding:22px 28px">
      <span style="color:#fff;font-size:18px;font-weight:700">LinkedIn Post Monitor</span>
      <span style="color:rgba(255,255,255,0.75);font-size:13px;float:right;margin-top:3px">
        {len(posts)} new post{'s' if len(posts)>1 else ''}
      </span>
    </div>
    <div style="background:#f5f5f5;padding:20px 0">{sections}</div>
    <div style="background:#ececec;border-radius:0 0 10px 10px;padding:12px 28px;
                text-align:center;font-size:11px;color:#aaa">
      Auto-generated · {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
    </div>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    monitor = LinkedInPostMonitor()
    monitor.run()
