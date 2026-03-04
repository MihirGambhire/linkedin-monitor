"""
LinkedIn Post Monitor - Configuration
Edit the values below with your details.
"""
import os


class Config:
    # ══════════════════════════════════════════════════════════════
    # 🔐 LINKEDIN SESSION COOKIE
    # ══════════════════════════════════════════════════════════════
    # Get this from: LinkedIn → F12 → Application → Cookies → li_at
    LINKEDIN_LI_AT = os.getenv("LINKEDIN_LI_AT", "your_li_at_cookie_here")

    # ══════════════════════════════════════════════════════════════
    # 🌐 RESIDENTIAL PROXY (required when running on GitHub Actions)
    # ══════════════════════════════════════════════════════════════
    # GitHub Actions runs from Microsoft Azure datacenter IPs which
    # LinkedIn detects and blocks. A residential proxy routes traffic
    # through a real home IP, bypassing this block.
    #
    # Recommended providers (all have residential proxies):
    #   • Webshare        → https://www.webshare.io          (~$5/mo, easy setup)
    #   • Oxylabs         → https://oxylabs.io               (enterprise)
    #   • Bright Data     → https://brightdata.com           (enterprise)
    #   • Smartproxy      → https://smartproxy.com           (mid-range)
    #
    # Format:  "http://USERNAME:PASSWORD@PROXY_HOST:PORT"
    # Example: "http://user123:pass456@gate.smartproxy.com:10000"
    #
    # ⚠️  NEVER hardcode credentials here — store them in GitHub Secrets
    #     as PROXY_URL and reference via os.getenv (already done below).
    #
    # Set PROXY_URL = "" or leave the secret unset to disable proxy
    # (useful for local testing on your own machine).
    PROXY = os.getenv("PROXY_URL", "")

    # ══════════════════════════════════════════════════════════════
    # 📧 EMAIL SETTINGS
    # ══════════════════════════════════════════════════════════════
    EMAIL_SENDER    = os.getenv("EMAIL_SENDER",    "sales1@digatron.com")
    EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD",  "your_password")
    EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "gambhiremihir@gmail.com")

    # Outlook SMTP settings
    SMTP_HOST = "smtp-mail.outlook.com"
    SMTP_PORT = 587

    # ══════════════════════════════════════════════════════════════
    # 🔍 SEARCH KEYWORDS  (buyer-intent only)
    # ══════════════════════════════════════════════════════════════
    # Each keyword here is a phrase that a REAL BUYER would type
    # when they have a purchasing need. Generic topic terms like
    # "BESS" or "Cell Assembly Line" are intentionally excluded
    # because they return news/jobs/market-reports — not leads.
    KEYWORDS = [
        # ── Direct equipment purchase intent ──────────────────────
        "looking for battery tester",
        "need battery cycler",
        "sourcing battery test equipment",
        "battery testing equipment supplier",
        "recommend battery formation equipment",
        "quote for battery tester",
        "battery cell tester vendor",

        # ── Formation & cycling ───────────────────────────────────
        "battery formation cycling equipment",
        "cell formation equipment supplier",
        "need battery formation system",
        "battery cycler recommendation",

        # ── BESS commissioning / procurement ─────────────────────
        "BESS procurement",
        "commissioning battery energy storage",
        "battery storage project tender",
        "BESS integrator looking for",
        "EPC BESS project",

        # ── Cell manufacturing line setup ─────────────────────────
        "setting up gigafactory",
        "setting up battery cell manufacturing",
        "battery manufacturing line equipment",
        "cell assembly line supplier",
        "turnkey battery manufacturing",

        # ── EV / automotive battery testing ──────────────────────
        "EV battery testing equipment",
        "automotive battery validation",
        "EV pack testing equipment",

        # ── Competitor displacement ───────────────────────────────
        "alternative to Neware",
        "alternative to Arbin",
        "replace Neware cycler",
        "replace Basytec",
        "Maccor alternative",
    ]

    # ══════════════════════════════════════════════════════════════
    # 🚫 NOISE FILTERS — posts containing ANY of these phrases
    #    are automatically discarded (not leads, just content).
    # ══════════════════════════════════════════════════════════════
    SPAM_PHRASES = [
        # Job postings
        "we are hiring", "we're hiring", "job opening", "job opportunity",
        "apply now", "send your cv", "send your resume", "hiring now",
        "open position", "career opportunity", "join our team",
        "new mandate", "we are looking for a", "seeking a ",
        # Market reports / press releases
        "market to reach", "cagr", "market size", "according to the",
        "press release", "research report", "market report",
        "billion by 20", "million by 20",
        # General news / awards
        "world's first", "proud to announce", "excited to share",
        "we are excited to share", "we are proud", "successfully completed",
        "commissioning of", "in partnership with", "new partnership",
        # Podcasts / webinars / events
        "podcast", "webinar", "register now", "join us at",
        "booth number", "see you at", "meet us at",
        # Educational content
        "learn more about", "discover how", "blog walks through",
        "fundamentals:", "introduction to",
    ]

    # ══════════════════════════════════════════════════════════════
    # ⚙️  ADVANCED SETTINGS
    # ══════════════════════════════════════════════════════════════
    # Only include posts from the last N days (1 = today only)
    MAX_POST_AGE_DAYS = 1

    # How many times to scroll each feed page
    SCROLL_TIMES = 5

    # LinkedIn groups to monitor (optional — get ID from the group URL)
    GROUP_IDS = []

    # Specific profiles to monitor (optional — slug is the part after /in/)
    PROFILE_SLUGS = []

    # Browser user agent
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
