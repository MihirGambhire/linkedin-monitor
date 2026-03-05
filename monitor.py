"""
LinkedIn Intelligence Monitor — ADOR Digatron
Runs two pipelines via SerpAPI and sends one consolidated email:

  Section 1 — POTENTIAL CUSTOMERS
    People/companies actively looking to buy battery test, formation,
    grading, or power conversion equipment.

  Section 2 — COMPETITOR INTELLIGENCE
    What Neware, Arbin, Basytec, Maccor, Bitrode, Chroma etc. are doing.

No browser / Playwright / Selenium required.
"""

import json
import logging
import os
import re
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itertools import cycle
from typing import Dict, List, Tuple

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


# ── SerpAPI call ──────────────────────────────────────────────────────────────
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


# ── Run a list of (label, query) searches ────────────────────────────────────
def _run_searches(
    searches: List[Tuple[str, str]],
    kind: str,
    key_pool,
) -> List[Post]:
    all_posts: List[Post] = []
    seen_urls: set = set()

    for label, query in searches:
        api_key = next(key_pool)
        logger.info(f"[{kind.upper()}] {label}")
        logger.info(f"  Query: {query[:130]}...")

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
                category = label,
                kind     = kind,
            ))

        time.sleep(1)

    return all_posts


# ── Spam filtering ────────────────────────────────────────────────────────────
def _combined_text(post: Post) -> str:
    return (post.title + " " + post.snippet).lower()


def _is_lead_spam(post: Post) -> bool:
    text = _combined_text(post)
    if any(p.lower() in text for p in config.LEAD_SPAM_PHRASES):
        return True
    words = set(re.findall(r'\b\w+\b', text))
    if words & config.LEAD_SPAM_WORDS:
        return True
    return False


def _is_competitor_spam(post: Post) -> bool:
    text = _combined_text(post)
    if any(p.lower() in text for p in config.COMPETITOR_SPAM_PHRASES):
        return True
    words = set(re.findall(r'\b\w+\b', text))
    if words & config.COMPETITOR_SPAM_WORDS:
        return True
    return False


# ── Filter pipelines ──────────────────────────────────────────────────────────
def filter_leads(posts: List[Post], seen: set) -> List[Post]:
    accepted = []
    for p in posts:
        if p.url in seen:
            logger.debug(f"  [skip-seen] {p.url}")
            continue
        if _is_lead_spam(p):
            logger.debug(f"  [skip-spam] {p.title[:70]}")
            continue
        logger.info(f"  ✅ Lead: {p.title[:70]}")
        accepted.append(p)
    return accepted


def filter_competitors(posts: List[Post], seen: set) -> List[Post]:
    accepted = []
    for p in posts:
        if p.url in seen:
            logger.debug(f"  [skip-seen] {p.url}")
            continue
        if _is_competitor_spam(p):
            logger.debug(f"  [skip-spam] {p.title[:70]}")
            continue
        logger.info(f"  ✅ Competitor: {p.title[:70]}")
        accepted.append(p)
    return accepted


# ── Email ─────────────────────────────────────────────────────────────────────
def _card(p: Post) -> str:
    display = p.title if p.title and p.title.lower() not in ("", "linkedin") else p.url
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px 20px;
                margin-bottom:12px;background:#fff;">
      <p style="margin:0 0 6px;font-size:14px;font-weight:600;color:#1a1a1a;">
        <a href="{p.url}" style="color:#0077B5;text-decoration:none;"
           target="_blank">{display}</a>
      </p>
      <p style="margin:0 0 14px;font-size:13px;color:#555;line-height:1.6;">
        {p.snippet}
      </p>
      <a href="{p.url}"
         style="display:inline-block;background:#0077B5;color:#fff;
                text-decoration:none;padding:6px 16px;border-radius:5px;
                font-size:12px;font-weight:600;">
        View on LinkedIn →
      </a>
    </div>"""


def _category_block(label: str, posts: List[Post], accent: str) -> str:
    cards = "".join(_card(p) for p in posts)
    count = len(posts)
    return f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1px;color:{accent};padding-bottom:6px;
                  border-bottom:2px solid {accent};margin-bottom:14px;">
        {label} &nbsp;·&nbsp; {count} post{"s" if count > 1 else ""}
      </div>
      {cards}
    </div>"""


def _build_html(
    leads_by_cat: Dict[str, List[Post]],
    comp_by_cat: Dict[str, List[Post]],
) -> str:
    total_leads = sum(len(v) for v in leads_by_cat.values())
    total_comp  = sum(len(v) for v in comp_by_cat.values())
    now         = datetime.now(timezone.utc).strftime("%b %d, %Y")

    lead_html = (
        "".join(_category_block(cat, posts, "#0077B5")
                for cat, posts in leads_by_cat.items() if posts)
        or '<p style="color:#999;font-style:italic;">No new buyer-intent posts this period.</p>'
    )

    comp_html = (
        "".join(_category_block(cat, posts, "#b03020")
                for cat, posts in comp_by_cat.items() if posts)
        or '<p style="color:#999;font-style:italic;">No competitor activity found this period.</p>'
    )

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f0f2f5;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <div style="max-width:660px;margin:30px auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,0.1);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#004f7c,#0077B5);padding:28px 32px;">
      <div style="color:#fff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">
        🔍 LinkedIn Intelligence Report
      </div>
      <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:4px;">
        ADOR Digatron &nbsp;·&nbsp; {now}
      </div>
      <div style="display:flex;gap:12px;margin-top:16px;">
        <div style="background:rgba(255,255,255,0.15);border-radius:8px;
                    padding:10px 20px;text-align:center;min-width:80px;">
          <div style="color:#fff;font-size:26px;font-weight:700;">{total_leads}</div>
          <div style="color:rgba(255,255,255,0.8);font-size:11px;margin-top:2px;">
            Potential Leads
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.15);border-radius:8px;
                    padding:10px 20px;text-align:center;min-width:80px;">
          <div style="color:#fff;font-size:26px;font-weight:700;">{total_comp}</div>
          <div style="color:rgba(255,255,255,0.8);font-size:11px;margin-top:2px;">
            Competitor Updates
          </div>
        </div>
      </div>
    </div>

    <div style="padding:28px 32px;">

      <!-- Section 1: Leads -->
      <div style="border-left:4px solid #0077B5;padding-left:12px;margin-bottom:20px;">
        <div style="font-size:17px;font-weight:700;color:#1a1a1a;">
          🎯 Potential Customers
        </div>
        <div style="font-size:12px;color:#888;margin-top:3px;">
          Companies and individuals actively looking to buy battery test,
          formation, grading or power conversion equipment
        </div>
      </div>
      {lead_html}

      <!-- Section 2: Competitors -->
      <div style="border-left:4px solid #b03020;padding-left:12px;
                  margin-top:36px;margin-bottom:20px;">
        <div style="font-size:17px;font-weight:700;color:#1a1a1a;">
          🕵️ Competitor Intelligence
        </div>
        <div style="font-size:12px;color:#888;margin-top:3px;">
          Recent activity from Neware, Arbin, Basytec, Maccor, Bitrode,
          Chroma, ACEY, Sinexcel and others
        </div>
      </div>
      {comp_html}

    </div>

    <!-- Footer -->
    <div style="background:#f8f8f8;border-top:1px solid #eee;
                padding:14px 32px;text-align:center;
                font-size:11px;color:#bbb;">
      Auto-generated by LinkedIn Intelligence Monitor &nbsp;·&nbsp;
      {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")} UTC
    </div>
  </div>
</body>
</html>"""


def _build_plain(
    leads_by_cat: Dict[str, List[Post]],
    comp_by_cat: Dict[str, List[Post]],
) -> str:
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"LinkedIn Intelligence Report — ADOR Digatron", f"Generated: {now}", ""]

    lines.append("══ POTENTIAL CUSTOMERS ══")
    for cat, posts in leads_by_cat.items():
        if posts:
            lines.append(f"\n── {cat} ({len(posts)}) ──")
            for i, p in enumerate(posts, 1):
                lines += [f"  {i}. {p.title}", f"     {p.snippet[:200]}", f"     {p.url}", ""]

    lines.append("\n══ COMPETITOR INTELLIGENCE ══")
    for cat, posts in comp_by_cat.items():
        if posts:
            lines.append(f"\n── {cat} ({len(posts)}) ──")
            for i, p in enumerate(posts, 1):
                lines += [f"  {i}. {p.title}", f"     {p.snippet[:200]}", f"     {p.url}", ""]

    return "\n".join(lines)


def send_email(
    leads_by_cat: Dict[str, List[Post]],
    comp_by_cat: Dict[str, List[Post]],
) -> bool:
    total_leads = sum(len(v) for v in leads_by_cat.values())
    total_comp  = sum(len(v) for v in comp_by_cat.values())
    today       = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    msg            = MIMEMultipart("alternative")
    msg["From"]    = config.EMAIL_SENDER
    msg["To"]      = ", ".join(config.EMAIL_RECIPIENTS)
    msg["Subject"] = (
        f"LinkedIn Intel — {total_leads} leads · "
        f"{total_comp} competitor updates — {today}"
    )
    msg.attach(MIMEText(_build_plain(leads_by_cat, comp_by_cat), "plain"))
    msg.attach(MIMEText(_build_html(leads_by_cat, comp_by_cat),  "html"))

    try:
        logger.info(f"Sending to: {', '.join(config.EMAIL_RECIPIENTS)}")
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            s.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENTS, msg.as_string())
        logger.info("✅ Email sent.")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=" * 60)
    logger.info(f"LinkedIn Monitor — {now}")
    logger.info(f"Lead searches      : {len(config.LEAD_SEARCHES)}")
    logger.info(f"Competitor searches: {len(config.COMPETITOR_SEARCHES)}")
    logger.info("=" * 60)

    if not config.SERPAPI_KEYS:
        logger.error("No SerpAPI keys found. Set SERPAPI_KEY_1 / SERPAPI_KEY_2.")
        return

    logger.info(f"Using {len(config.SERPAPI_KEYS)} SerpAPI key(s) with round-robin rotation.")
    seen     = _load_seen()
    key_pool = _key_cycle()

    # ── Lead pipeline ─────────────────────────────────────────────────────────
    logger.info("── Searching for potential customers...")
    raw_leads      = _run_searches(config.LEAD_SEARCHES, "lead", key_pool)
    logger.info(f"   Raw: {len(raw_leads)}")
    filtered_leads = filter_leads(raw_leads, seen)
    logger.info(f"   Accepted: {len(filtered_leads)}")

    # ── Competitor pipeline ───────────────────────────────────────────────────
    logger.info("── Searching competitor activity...")
    raw_comp      = _run_searches(config.COMPETITOR_SEARCHES, "competitor", key_pool)
    logger.info(f"   Raw: {len(raw_comp)}")
    filtered_comp = filter_competitors(raw_comp, seen)
    logger.info(f"   Accepted: {len(filtered_comp)}")

    # ── Group by category ─────────────────────────────────────────────────────
    leads_by_cat: Dict[str, List[Post]] = {}
    for p in filtered_leads:
        leads_by_cat.setdefault(p.category, []).append(p)

    comp_by_cat: Dict[str, List[Post]] = {}
    for p in filtered_comp:
        comp_by_cat.setdefault(p.category, []).append(p)

    # ── Send only if something to report ─────────────────────────────────────
    if not filtered_leads and not filtered_comp:
        logger.info("Nothing new to report. No email sent.")
        return

    if send_email(leads_by_cat, comp_by_cat):
        for p in filtered_leads + filtered_comp:
            seen.add(p.url)
        _save_seen(seen)
        logger.info(f"seen_posts.json updated ({len(seen)} URLs tracked).")

    logger.info("=" * 60)
    logger.info("Monitor complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
