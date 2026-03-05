"""
LinkedIn Strategic Intelligence Monitor — ADOR Digatron
9 searches/day, 3 SerpAPI keys in rotation (279 searches/month, under 300 quota).

Sections in email:
  🏭 Target Account Signals  — companies that could buy our equipment
  🎯 Potential Buyers        — people/companies actively looking to buy
  🕵️ Competitor Intelligence — strategic updates from Neware, Arbin, etc.
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
    def __init__(self, url: str, title: str, snippet: str,
                 label: str, context: str, kind: str):
        self.url     = url.split("?")[0]
        self.title   = title.strip()
        self.snippet = snippet.strip()
        self.label   = label    # search group label
        self.context = context  # why this matters (shown in email for accounts/buyers)
        self.kind    = kind     # "account" | "buyer" | "competitor"

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, Post) and self.url == other.url


# ── Persistence ───────────────────────────────────────────────────────────────
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


# ── Noise filter ──────────────────────────────────────────────────────────────
def _is_noise(post: Post) -> bool:
    combined = (post.title + " " + post.snippet).lower()
    words = set(re.findall(r'\b\w+\b', combined))
    if words & config.NOISE_WORDS:
        return True
    if any(p in combined for p in config.NOISE_PHRASES):
        return True
    return False


# ── Search ────────────────────────────────────────────────────────────────────
def run_all_searches(key_pool) -> List[Post]:
    """Run all 9 searches, return raw (unfiltered) Post objects."""
    all_posts: List[Post] = []
    global_seen_urls: set = set()

    for search in config.SEARCHES:
        api_key = next(key_pool)
        label   = search["label"]
        kind    = search["kind"]
        context = search["context"]
        query   = search["query"]

        logger.info(f"[{kind.upper()}] {label}")

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
            organic = GoogleSearch(params).get_dict().get("organic_results", [])
        except Exception as e:
            logger.error(f"  SerpAPI error: {e}")
            organic = []

        logger.info(f"  → {len(organic)} raw results")

        for item in organic:
            url = item.get("link", "").split("?")[0]
            if "linkedin.com" not in url or url in global_seen_urls:
                continue
            # Reject personal profile pages (/in/) — just people who work
            # at a company, not actual posts or company updates.
            path = "/" + url.split("linkedin.com", 1)[-1].lstrip("/")
            if path.startswith("/in/"):
                logger.debug(f"  [skip-profile] {url}")
                continue
            # Only keep known content URL types
            if not any(s in path for s in ["/posts/", "/feed/update/", "/company/", "/pulse/"]):
                logger.debug(f"  [skip-url] {url}")
                continue
            global_seen_urls.add(url)
            all_posts.append(Post(
                url     = url,
                title   = item.get("title",   ""),
                snippet = item.get("snippet", ""),
                label   = label,
                context = context,
                kind    = kind,
            ))

        time.sleep(1)  # be polite to SerpAPI

    return all_posts


# ── Filter ────────────────────────────────────────────────────────────────────
def filter_posts(posts: List[Post], seen: set) -> List[Post]:
    accepted = []
    for p in posts:
        if p.url in seen:
            logger.debug(f"  [seen]  {p.title[:70]}")
            continue
        if _is_noise(p):
            logger.debug(f"  [noise] {p.title[:70]}")
            continue
        logger.info(f"  ✅ [{p.kind}] {p.label}: {p.title[:65]}")
        accepted.append(p)
    return accepted


# ── Email builders ────────────────────────────────────────────────────────────
def _post_card(p: Post, show_context: bool) -> str:
    ctx_html = ""
    if show_context and p.context:
        ctx_html = (
            f'<div style="font-size:11px;color:#777;font-style:italic;'
            f'margin-bottom:7px;">{p.context}</div>'
        )
    return f"""
    <div style="border:1px solid #e4e4e4;border-radius:8px;padding:15px 18px;
                margin-bottom:10px;background:#fff;">
      <p style="margin:0 0 5px;font-size:14px;font-weight:600;line-height:1.4;">
        <a href="{p.url}" style="color:#0077B5;text-decoration:none;"
           target="_blank">{p.title or p.url}</a>
      </p>
      {ctx_html}
      <p style="margin:0 0 11px;font-size:13px;color:#555;line-height:1.55;">
        {p.snippet}
      </p>
      <a href="{p.url}"
         style="display:inline-block;background:#0077B5;color:#fff;
                text-decoration:none;padding:5px 13px;border-radius:5px;
                font-size:12px;font-weight:600;">
        View on LinkedIn →
      </a>
    </div>"""


def _group_section(
    posts_by_label: Dict[str, List[Post]],
    accent: str,
    show_context: bool,
    empty_msg: str,
) -> str:
    if not posts_by_label:
        return f'<p style="color:#999;font-style:italic;font-size:13px;">{empty_msg}</p>'

    html = ""
    for label, posts in posts_by_label.items():
        cards = "".join(_post_card(p, show_context) for p in posts)
        html += f"""
        <div style="margin-bottom:22px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:.8px;
                      text-transform:uppercase;color:{accent};
                      border-bottom:2px solid;border-color:{accent}22;
                      padding-bottom:5px;margin-bottom:10px;">
            {label} &nbsp;·&nbsp; {len(posts)} update{"s" if len(posts)>1 else ""}
          </div>
          {cards}
        </div>"""
    return html


def _section_header(emoji: str, title: str, subtitle: str,
                    color: str, count: int) -> str:
    return f"""
    <div style="border-left:4px solid {color};padding-left:12px;margin-bottom:4px;">
      <span style="font-size:16px;font-weight:700;color:#1a1a2e;">{emoji} {title}</span>
      <span style="margin-left:10px;background:{color};color:#fff;font-size:11px;
                   font-weight:700;padding:2px 9px;border-radius:10px;">{count}</span>
    </div>
    <div style="font-size:12px;color:#888;padding-left:16px;
                margin-bottom:16px;">{subtitle}</div>"""


def _build_html(
    accounts: Dict[str, List[Post]],
    buyers:   Dict[str, List[Post]],
    comps:    Dict[str, List[Post]],
) -> str:
    n_acc  = sum(len(v) for v in accounts.values())
    n_buy  = sum(len(v) for v in buyers.values())
    n_comp = sum(len(v) for v in comps.values())
    total  = n_acc + n_buy + n_comp
    now    = datetime.now(timezone.utc)

    acc_html  = _group_section(accounts, "#0077B5", True,
                               "No strategic updates from target accounts today.")
    buy_html  = _group_section(buyers,   "#1a7a4a", True,
                               "No active buyer signals found today.")
    comp_html = _group_section(comps,    "#c0392b", False,
                               "No competitor updates found today.")

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f0f2f5;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <div style="max-width:660px;margin:26px auto;background:#fff;
              border-radius:12px;overflow:hidden;
              box-shadow:0 2px 12px rgba(0,0,0,0.09);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#003f6b 0%,#0077B5 100%);
                padding:24px 30px 20px;">
      <div style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-.2px;">
        📡 LinkedIn Strategic Intelligence
      </div>
      <div style="color:rgba(255,255,255,0.7);font-size:12px;margin-top:3px;">
        ADOR Digatron &nbsp;·&nbsp; {now.strftime("%b %d, %Y")}
      </div>
      <!-- Summary pills -->
      <div style="margin-top:15px;display:flex;gap:10px;flex-wrap:wrap;">
        <div style="background:rgba(255,255,255,0.15);border-radius:20px;
                    padding:5px 15px;">
          <span style="color:#fff;font-size:17px;font-weight:700;">{n_acc}</span>
          <span style="color:rgba(255,255,255,0.75);font-size:11px;
                       margin-left:5px;">Account Signal{"s" if n_acc!=1 else ""}</span>
        </div>
        <div style="background:rgba(255,255,255,0.15);border-radius:20px;
                    padding:5px 15px;">
          <span style="color:#fff;font-size:17px;font-weight:700;">{n_buy}</span>
          <span style="color:rgba(255,255,255,0.75);font-size:11px;
                       margin-left:5px;">Buyer Signal{"s" if n_buy!=1 else ""}</span>
        </div>
        <div style="background:rgba(255,255,255,0.15);border-radius:20px;
                    padding:5px 15px;">
          <span style="color:#fff;font-size:17px;font-weight:700;">{n_comp}</span>
          <span style="color:rgba(255,255,255,0.75);font-size:11px;
                       margin-left:5px;">Competitor Update{"s" if n_comp!=1 else ""}</span>
        </div>
      </div>
    </div>

    <div style="padding:24px 30px;">

      <!-- Section 1: Target Accounts -->
      {_section_header("🏭", "Target Account Signals", "Strategic updates from companies likely to buy our equipment", "#0077B5", n_acc)}
      {acc_html}

      <!-- Section 2: Potential Buyers -->
      <div style="margin-top:30px;">
        {_section_header("🎯", "Potential Buyers", "People or companies actively looking to buy battery test, formation or grading equipment", "#1a7a4a", n_buy)}
        {buy_html}
      </div>

      <!-- Section 3: Competitor Intelligence -->
      <div style="margin-top:30px;">
        {_section_header("🕵️", "Competitor Intelligence", "New contracts, products, partnerships and expansions from Neware, Arbin, Basytec, Maccor, Bitrode, Chroma, NH Research, Wonik PNE", "#c0392b", n_comp)}
        {comp_html}
      </div>

    </div>

    <!-- Footer -->
    <div style="background:#f7f7f7;border-top:1px solid #eee;padding:11px 30px;
                text-align:center;font-size:11px;color:#bbb;">
      ADOR Digatron LinkedIn Monitor &nbsp;·&nbsp;
      {now.strftime("%Y-%m-%d %H:%M")} UTC &nbsp;·&nbsp;
      {total} post{"s" if total!=1 else ""} today
    </div>

  </div>
</body>
</html>"""


def _build_plain(
    accounts: Dict[str, List[Post]],
    buyers:   Dict[str, List[Post]],
    comps:    Dict[str, List[Post]],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _section(title, groups):
        lines = [f"\n{'='*55}", f"  {title}", f"{'='*55}"]
        if not groups:
            lines.append("  Nothing found today.")
        for label, posts in groups.items():
            lines.append(f"\n  ── {label}")
            for p in posts:
                lines += [
                    f"     • {p.title}",
                    f"       {p.snippet[:180]}",
                    f"       {p.url}",
                    "",
                ]
        return "\n".join(lines)

    return (
        f"LinkedIn Strategic Intelligence — ADOR Digatron\n"
        f"Generated: {now}\n"
        + _section("🏭 TARGET ACCOUNT SIGNALS", accounts)
        + _section("🎯 POTENTIAL BUYERS", buyers)
        + _section("🕵️  COMPETITOR INTELLIGENCE", comps)
    )


def send_email(
    accounts: Dict[str, List[Post]],
    buyers:   Dict[str, List[Post]],
    comps:    Dict[str, List[Post]],
) -> bool:
    n_acc  = sum(len(v) for v in accounts.values())
    n_buy  = sum(len(v) for v in buyers.values())
    n_comp = sum(len(v) for v in comps.values())
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    subject_parts = []
    if n_acc:  subject_parts.append(f"{n_acc} account signal{'s' if n_acc>1 else ''}")
    if n_buy:  subject_parts.append(f"{n_buy} buyer signal{'s' if n_buy>1 else ''}")
    if n_comp: subject_parts.append(f"{n_comp} competitor update{'s' if n_comp>1 else ''}")

    msg            = MIMEMultipart("alternative")
    msg["From"]    = config.EMAIL_SENDER
    msg["To"]      = ", ".join(config.EMAIL_RECIPIENTS)
    msg["Subject"] = f"📡 LinkedIn Intel [{today}] — " + " · ".join(subject_parts)

    msg.attach(MIMEText(_build_plain(accounts, buyers, comps), "plain"))
    msg.attach(MIMEText(_build_html(accounts, buyers, comps),  "html"))

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
    logger.info(f"LinkedIn Strategic Monitor — {now}")
    logger.info(f"Searches: {len(config.SEARCHES)}  |  Keys: {len(config.SERPAPI_KEYS)}")
    logger.info("=" * 60)

    if not config.SERPAPI_KEYS:
        logger.error(
            "No SerpAPI keys found. "
            "Set SERPAPI_KEY_1, SERPAPI_KEY_2, SERPAPI_KEY_3 in GitHub Secrets."
        )
        return

    seen     = _load_seen()
    key_pool = _key_cycle()

    # Run all 9 searches
    logger.info("── Running searches...")
    raw_posts = run_all_searches(key_pool)
    logger.info(f"   Total raw: {len(raw_posts)}")

    # Filter
    logger.info("── Filtering...")
    accepted = filter_posts(raw_posts, seen)
    logger.info(f"   Accepted: {len(accepted)}")

    if not accepted:
        logger.info("Nothing new to report. No email sent.")
        return

    # Group by kind → by label
    accounts: Dict[str, List[Post]] = {}
    buyers:   Dict[str, List[Post]] = {}
    comps:    Dict[str, List[Post]] = {}

    for p in accepted:
        if p.kind == "account":
            accounts.setdefault(p.label, []).append(p)
        elif p.kind == "buyer":
            buyers.setdefault(p.label, []).append(p)
        else:
            comps.setdefault(p.label, []).append(p)

    # Send
    if send_email(accounts, buyers, comps):
        for p in accepted:
            seen.add(p.url)
        _save_seen(seen)
        logger.info(f"seen_posts.json updated — {len(seen)} URLs tracked total.")

    logger.info("=" * 60)
    logger.info("Done.")
    logger.info("=" * 60)


def _key_cycle():
    return cycle(config.SERPAPI_KEYS)


if __name__ == "__main__":
    main()
