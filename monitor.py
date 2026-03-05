"""
LinkedIn Post Monitor — SerpAPI Edition
Runs two separate pipelines and sends one consolidated email:

  Section 1 — POTENTIAL CUSTOMERS
    Posts from people actively looking to buy battery test/formation equipment,
    set up manufacturing lines, or procure BESS systems.

  Section 2 — COMPETITOR INTELLIGENCE
    Posts from or about Neware, Arbin, Basytec, Maccor, Bitrode —
    new products, partnerships, expansions, customer wins.

No browser / Playwright / Selenium required.
"""

import json
import logging
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itertools import cycle
from typing import Dict, List

from serpapi import GoogleSearch

import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("monitor.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────
class Post:
    def __init__(self, url: str, title: str, snippet: str, category: str, kind: str):
        self.url      = url.split("?")[0]
        self.title    = title.strip()
        self.snippet  = snippet.strip()
        self.category = category
        self.kind     = kind   # "lead" or "competitor"
        self.score    = 0

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, Post) and self.url == other.url


# ── Seen-posts persistence ────────────────────────────────────────────────────
SEEN_FILE = "seen_posts.json"


def _load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


# ── API key rotation ──────────────────────────────────────────────────────────
def _key_cycle():
    return cycle(config.SERPAPI_KEYS)


# ── Search ────────────────────────────────────────────────────────────────────
def _build_lead_query(keywords: List[str]) -> str:
    """
    Target LinkedIn posts where someone is actively looking to buy.
    Searches linkedin.com/posts and linkedin.com/feed/update.
    """
    site   = "site:linkedin.com/posts OR site:linkedin.com/feed/update"
    kw_or  = " OR ".join(f'"{kw}"' for kw in keywords)
    return f"{site} ({kw_or})"


def _build_competitor_query(keywords: List[str]) -> str:
    """
    Find competitor mentions/announcements on LinkedIn.
    Broader site match — competitor profiles and company pages also relevant.
    """
    site   = "site:linkedin.com"
    kw_or  = " OR ".join(f'"{kw}"' for kw in keywords)
    # Exclude job-related results at query level
    return f"{site} ({kw_or}) -hiring -vacancy -apply"


def _serpapi_search(query: str, api_key: str) -> List[dict]:
    params = {
        "engine":  "google",
        "q":       query,
        "api_key": api_key,
        "num":     config.MAX_RESULTS_PER_SEARCH,
        "tbs":     config.SEARCH_TIME_FILTER,
        "hl":      "en",
        "gl":      "in",
    }
    try:
        results = GoogleSearch(params).get_dict()
        return results.get("organic_results", [])
    except Exception as e:
        logger.error(f"  SerpAPI error: {e}")
        return []


def search_leads(key_pool) -> List[Post]:
    """Search all LEAD_CATEGORIES and return raw Post objects."""
    all_posts: List[Post] = []
    seen_urls: set = set()

    for category, keywords in config.LEAD_CATEGORIES.items():
        api_key = next(key_pool)
        query   = _build_lead_query(keywords)
        logger.info(f"[LEAD] {category}")
        logger.info(f"  Query: {query[:120]}...")

        organic = _serpapi_search(query, api_key)
        logger.info(f"  → {len(organic)} raw results")

        for item in organic:
            url = item.get("link", "").split("?")[0]
            if "linkedin.com" not in url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_posts.append(Post(
                url      = url,
                title    = item.get("title",   ""),
                snippet  = item.get("snippet", ""),
                category = category,
                kind     = "lead",
            ))

        time.sleep(1)

    return all_posts


def search_competitors(key_pool) -> List[Post]:
    """Search all COMPETITOR_CATEGORIES and return raw Post objects."""
    all_posts: List[Post] = []
    seen_urls: set = set()

    for category, keywords in config.COMPETITOR_CATEGORIES.items():
        api_key = next(key_pool)
        query   = _build_competitor_query(keywords)
        logger.info(f"[COMPETITOR] {category}")
        logger.info(f"  Query: {query[:120]}...")

        organic = _serpapi_search(query, api_key)
        logger.info(f"  → {len(organic)} raw results")

        for item in organic:
            url = item.get("link", "").split("?")[0]
            if "linkedin.com" not in url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_posts.append(Post(
                url      = url,
                title    = item.get("title",   ""),
                snippet  = item.get("snippet", ""),
                category = category,
                kind     = "competitor",
            ))

        time.sleep(1)

    return all_posts


# ── Scoring & filtering ───────────────────────────────────────────────────────
def _score_lead(post: Post) -> int:
    combined = (post.title + " " + post.snippet).lower()
    score    = 5  # base
    for phrase, pts in config.INTENT_PHRASES.items():
        if phrase.lower() in combined:
            score += pts
    return score


def _is_lead_spam(post: Post) -> bool:
    combined = (post.title + " " + post.snippet).lower()
    return any(p.lower() in combined for p in config.LEAD_SPAM_PHRASES)


def _is_competitor_spam(post: Post) -> bool:
    combined = (post.title + " " + post.snippet).lower()
    return any(p.lower() in combined for p in config.COMPETITOR_SPAM_PHRASES)


def filter_leads(posts: List[Post], seen: set) -> List[Post]:
    accepted = []
    for p in posts:
        if p.url in seen:
            logger.debug(f"  [skip] Already seen: {p.url}")
            continue
        if _is_lead_spam(p):
            logger.debug(f"  [skip] Spam: {p.title[:60]}")
            continue
        p.score = _score_lead(p)
        if p.score < config.MIN_LEAD_SCORE:
            logger.debug(f"  [skip] Low score ({p.score}): {p.title[:60]}")
            continue
        logger.info(f"  ✅ Lead accepted (score={p.score}): {p.title[:60]}")
        accepted.append(p)
    # Sort best leads first
    accepted.sort(key=lambda x: x.score, reverse=True)
    return accepted


def filter_competitors(posts: List[Post], seen: set) -> List[Post]:
    accepted = []
    for p in posts:
        if p.url in seen:
            logger.debug(f"  [skip] Already seen: {p.url}")
            continue
        if _is_competitor_spam(p):
            logger.debug(f"  [skip] Job ad: {p.title[:60]}")
            continue
        logger.info(f"  ✅ Competitor post accepted: {p.title[:60]}")
        accepted.append(p)
    return accepted


# ── Email ─────────────────────────────────────────────────────────────────────
def _card(p: Post) -> str:
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px 20px;
                margin-bottom:12px;background:#fff;">
      <p style="margin:0 0 6px;font-size:14px;font-weight:600;">
        <a href="{p.url}" style="color:#0077B5;text-decoration:none;"
           target="_blank">{p.title or p.url}</a>
      </p>
      <p style="margin:0 0 14px;font-size:13px;color:#555;line-height:1.5;">
        {p.snippet}
      </p>
      <a href="{p.url}"
         style="display:inline-block;background:#0077B5;color:#fff;
                text-decoration:none;padding:6px 14px;border-radius:5px;
                font-size:12px;font-weight:600;">
        View on LinkedIn →
      </a>
    </div>"""


def _section_header(title: str, subtitle: str, color: str) -> str:
    return f"""
    <div style="background:{color};border-radius:8px 8px 0 0;
                padding:14px 20px;margin-top:28px;">
      <div style="color:#fff;font-size:16px;font-weight:700;">{title}</div>
      <div style="color:rgba(255,255,255,0.85);font-size:12px;margin-top:3px;">
        {subtitle}
      </div>
    </div>
    <div style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;
                padding:16px;margin-bottom:8px;background:#fafafa;">"""


def _build_html(
    leads_by_cat: Dict[str, List[Post]],
    competitors_by_cat: Dict[str, List[Post]],
) -> str:
    total_leads = sum(len(v) for v in leads_by_cat.values())
    total_comp  = sum(len(v) for v in competitors_by_cat.values())
    now         = datetime.utcnow().strftime("%b %d, %Y")

    # ── Lead sections ─────────────────────────────────────────────────────────
    lead_html = ""
    if total_leads:
        for cat, posts in leads_by_cat.items():
            if not posts:
                continue
            lead_html += _section_header(
                cat,
                f"{len(posts)} potential customer post{'s' if len(posts) > 1 else ''}",
                "#0077B5",
            )
            for p in posts:
                lead_html += _card(p)
            lead_html += "</div>"
    else:
        lead_html = """
        <div style="color:#999;font-style:italic;padding:12px 0;">
          No new buyer-intent posts found this period.
        </div>"""

    # ── Competitor sections ───────────────────────────────────────────────────
    comp_html = ""
    if total_comp:
        for cat, posts in competitors_by_cat.items():
            if not posts:
                continue
            comp_html += _section_header(
                cat,
                f"{len(posts)} update{'s' if len(posts) > 1 else ''}",
                "#c0392b",
            )
            for p in posts:
                comp_html += _card(p)
            comp_html += "</div>"
    else:
        comp_html = """
        <div style="color:#999;font-style:italic;padding:12px 0;">
          No competitor activity found this period.
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <div style="max-width:660px;margin:30px auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0077B5,#004f7c);
                padding:26px 32px;">
      <div style="color:#fff;font-size:20px;font-weight:700;">
        🔍 LinkedIn Intelligence Report
      </div>
      <div style="color:rgba(255,255,255,0.8);font-size:13px;margin-top:5px;">
        ADOR Digatron &nbsp;·&nbsp; {now}
      </div>
      <div style="margin-top:14px;display:flex;gap:16px;">
        <div style="background:rgba(255,255,255,0.15);border-radius:8px;
                    padding:8px 16px;text-align:center;">
          <div style="color:#fff;font-size:22px;font-weight:700;">{total_leads}</div>
          <div style="color:rgba(255,255,255,0.8);font-size:11px;">Potential Leads</div>
        </div>
        <div style="background:rgba(255,255,255,0.15);border-radius:8px;
                    padding:8px 16px;text-align:center;">
          <div style="color:#fff;font-size:22px;font-weight:700;">{total_comp}</div>
          <div style="color:rgba(255,255,255,0.8);font-size:11px;">Competitor Updates</div>
        </div>
      </div>
    </div>

    <div style="padding:24px 32px;">

      <!-- Section 1: Potential Customers -->
      <div style="font-size:17px;font-weight:700;color:#333;
                  border-left:4px solid #0077B5;padding-left:12px;margin-bottom:4px;">
        🎯 Potential Customers
      </div>
      <div style="font-size:12px;color:#888;margin-bottom:8px;padding-left:16px;">
        People actively looking to buy battery test, formation, or manufacturing equipment
      </div>
      {lead_html}

      <!-- Section 2: Competitor Intelligence -->
      <div style="font-size:17px;font-weight:700;color:#333;margin-top:36px;
                  border-left:4px solid #c0392b;padding-left:12px;margin-bottom:4px;">
        🕵️ Competitor Intelligence
      </div>
      <div style="font-size:12px;color:#888;margin-bottom:8px;padding-left:16px;">
        Recent activity from Neware, Arbin, Basytec, Maccor, Bitrode
      </div>
      {comp_html}

    </div>

    <!-- Footer -->
    <div style="background:#f9f9f9;padding:14px 32px;text-align:center;
                font-size:11px;color:#aaa;border-top:1px solid #eee;">
      Auto-generated by LinkedIn Intelligence Monitor &nbsp;·&nbsp;
      {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC
    </div>

  </div>
</body>
</html>"""


def _build_plain(
    leads_by_cat: Dict[str, List[Post]],
    competitors_by_cat: Dict[str, List[Post]],
) -> str:
    lines = [
        "LinkedIn Intelligence Report — ADOR Digatron",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "══ POTENTIAL CUSTOMERS ══",
    ]
    for cat, posts in leads_by_cat.items():
        if posts:
            lines.append(f"\n── {cat} ({len(posts)}) ──")
            for i, p in enumerate(posts, 1):
                lines += [f"  {i}. {p.title}", f"     {p.snippet[:200]}", f"     {p.url}", ""]

    lines += ["", "══ COMPETITOR INTELLIGENCE ══"]
    for cat, posts in competitors_by_cat.items():
        if posts:
            lines.append(f"\n── {cat} ({len(posts)}) ──")
            for i, p in enumerate(posts, 1):
                lines += [f"  {i}. {p.title}", f"     {p.snippet[:200]}", f"     {p.url}", ""]

    return "\n".join(lines)


def send_email(
    leads_by_cat: Dict[str, List[Post]],
    competitors_by_cat: Dict[str, List[Post]],
) -> bool:
    total_leads = sum(len(v) for v in leads_by_cat.values())
    total_comp  = sum(len(v) for v in competitors_by_cat.values())
    today       = datetime.utcnow().strftime("%Y-%m-%d")

    msg             = MIMEMultipart("alternative")
    msg["From"]     = config.EMAIL_SENDER
    msg["To"]       = ", ".join(config.EMAIL_RECIPIENTS)
    msg["Subject"]  = (
        f"LinkedIn Intel — {total_leads} leads · {total_comp} competitor updates — {today}"
    )
    msg.attach(MIMEText(_build_plain(leads_by_cat, competitors_by_cat), "plain"))
    msg.attach(MIMEText(_build_html(leads_by_cat, competitors_by_cat),  "html"))

    try:
        logger.info(f"Sending email to: {', '.join(config.EMAIL_RECIPIENTS)}")
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            s.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENTS, msg.as_string())
        logger.info("✅ Email sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info(f"LinkedIn Monitor — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"Lead categories     : {len(config.LEAD_CATEGORIES)}")
    logger.info(f"Competitor categories: {len(config.COMPETITOR_CATEGORIES)}")
    logger.info("=" * 60)

    if not config.SERPAPI_KEYS:
        logger.error(
            "No SerpAPI keys found. "
            "Set SERPAPI_KEY_1 and/or SERPAPI_KEY_2 as GitHub Secrets."
        )
        return

    seen     = _load_seen()
    key_pool = _key_cycle()

    # ── Run both pipelines ────────────────────────────────────────────────────
    logger.info("── Searching for potential customers...")
    raw_leads       = search_leads(key_pool)
    logger.info(f"   Raw: {len(raw_leads)} | Filtering...")
    filtered_leads  = filter_leads(raw_leads, seen)
    logger.info(f"   Accepted: {len(filtered_leads)}")

    logger.info("── Searching competitor activity...")
    raw_competitors      = search_competitors(key_pool)
    logger.info(f"   Raw: {len(raw_competitors)} | Filtering...")
    filtered_competitors = filter_competitors(raw_competitors, seen)
    logger.info(f"   Accepted: {len(filtered_competitors)}")

    # ── Group by category ─────────────────────────────────────────────────────
    leads_by_cat: Dict[str, List[Post]] = {}
    for p in filtered_leads:
        leads_by_cat.setdefault(p.category, []).append(p)

    competitors_by_cat: Dict[str, List[Post]] = {}
    for p in filtered_competitors:
        competitors_by_cat.setdefault(p.category, []).append(p)

    # ── Send email only if there is something to report ───────────────────────
    if not filtered_leads and not filtered_competitors:
        logger.info("Nothing new to report. No email sent.")
        return

    if send_email(leads_by_cat, competitors_by_cat):
        # Persist seen URLs only after successful send
        for p in filtered_leads + filtered_competitors:
            seen.add(p.url)
        _save_seen(seen)
        logger.info(f"seen_posts.json updated ({len(seen)} total URLs tracked).")

    logger.info("=" * 60)
    logger.info("Monitor complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
