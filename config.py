"""
LinkedIn Post Monitor — Configuration
Two distinct modes:
  1. LEAD_CATEGORIES      — find potential customers actively looking to buy
  2. COMPETITOR_CATEGORIES — track what competitors are doing
"""
import os


# ══════════════════════════════════════════════════════════════════════════════
# 🔑  SERPAPI KEYS  (GitHub Secrets: SERPAPI_KEY_1, SERPAPI_KEY_2)
#     Rotated evenly across searches to preserve free-tier quota.
# ══════════════════════════════════════════════════════════════════════════════
SERPAPI_KEYS = [
    k for k in [
        os.getenv("SERPAPI_KEY_1", ""),
        os.getenv("SERPAPI_KEY_2", ""),
    ] if k
]

# ══════════════════════════════════════════════════════════════════════════════
# 📧  EMAIL  (Outlook SMTP — GitHub Secrets)
# ══════════════════════════════════════════════════════════════════════════════
EMAIL_SENDER    = os.getenv("EMAIL_SENDER",   "sales1@digatron.com")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "")

# Parse comma-separated recipients from a single GitHub Secret.
# Secret name: EMAIL_RECIPIENTS
# Example value: alice@digatron.com,bob@digatron.com,charlie@gmail.com
_raw_recipients  = os.getenv("EMAIL_RECIPIENTS", "gambhiremihir@gmail.com")
EMAIL_RECIPIENTS = [e.strip() for e in _raw_recipients.split(",") if e.strip()]
SMTP_HOST       = "smtp-mail.outlook.com"
SMTP_PORT       = 587

# ══════════════════════════════════════════════════════════════════════════════
# 🎯  SECTION 1: LEAD CATEGORIES
#     Posts from people who are ACTIVELY LOOKING TO BUY.
#     These use strict spam filtering + intent scoring.
#     Each category = 1 SerpAPI call.
# ══════════════════════════════════════════════════════════════════════════════
LEAD_CATEGORIES = {

    "Battery Tester / Cycler Buyers": [
        "looking for battery tester",
        "need battery cycler",
        "sourcing battery test equipment",
        "battery testing equipment supplier",
        "quote for battery tester",
        "battery cell tester vendor",
        "battery cycler recommendation",
        "recommend battery formation equipment",
    ],

    "Formation Equipment Buyers": [
        "battery formation cycling equipment",
        "cell formation equipment supplier",
        "need battery formation system",
        "battery formation system supplier",
        "formation tester procurement",
        "battery formation machine vendor",
    ],

    "BESS Procurement": [
        "BESS procurement",
        "battery storage project tender",
        "BESS integrator looking for",
        "EPC BESS project",
        "battery energy storage tender",
        "battery storage system vendor",
    ],

    "Gigafactory / Cell Line Setup": [
        "setting up gigafactory",
        "setting up battery cell manufacturing",
        "battery manufacturing line equipment",
        "cell assembly line supplier",
        "turnkey battery manufacturing",
        "gigafactory equipment supplier",
    ],

    "EV Battery Testing": [
        "EV battery testing equipment",
        "automotive battery validation",
        "EV pack testing equipment",
        "EV battery cycler supplier",
        "electric vehicle battery tester",
    ],

    "Competitor Displacement Opportunities": [
        "alternative to Neware",
        "alternative to Arbin",
        "replace Neware cycler",
        "replace Basytec",
        "Maccor alternative",
        "Bitrode alternative",
        "unhappy with Neware",
        "issues with Arbin",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# 🕵️  SECTION 2: COMPETITOR CATEGORIES
#     Posts FROM or ABOUT competitors — news, launches, expansions, deals.
#     These use a RELAXED spam filter (announcements are exactly what we want).
#     Each entry = 1 SerpAPI call.
# ══════════════════════════════════════════════════════════════════════════════
COMPETITOR_CATEGORIES = {

    "Neware": [
        "Neware battery tester",
        "Neware cycler",
        "Neware new product",
        "Neware partnership",
        "Neware expansion",
    ],

    "Arbin Instruments": [
        "Arbin battery tester",
        "Arbin cycler",
        "Arbin new product",
        "Arbin partnership",
        "Arbin expansion",
    ],

    "Basytec": [
        "Basytec battery tester",
        "Basytec cycler",
        "Basytec new product",
        "Basytec partnership",
    ],

    "Maccor": [
        "Maccor battery tester",
        "Maccor cycler",
        "Maccor new product",
        "Maccor partnership",
    ],

    "Bitrode / Sovema": [
        "Bitrode battery tester",
        "Bitrode cycler",
        "Bitrode new product",
        "Sovema battery",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# 🕐  SEARCH TIME WINDOW
#     qdr:d = past day  (for daily runs)
#     qdr:w = past week (for weekly runs — recommended to start)
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_TIME_FILTER   = "qdr:w"
MAX_RESULTS_PER_SEARCH = 10

# ══════════════════════════════════════════════════════════════════════════════
# 🎯  INTENT PHRASES  (internal scoring for LEAD posts only)
#     Not shown in the email — used only to rank and filter.
# ══════════════════════════════════════════════════════════════════════════════
INTENT_PHRASES = {
    "looking for":          5,
    "need a":               5,
    "need to source":       6,
    "need to procure":      6,
    "can anyone recommend": 7,
    "any recommendations":  7,
    "anyone recommend":     7,
    "where can i find":     5,
    "who supplies":         6,
    "supplier for":         5,
    "sourcing":             4,
    "help me find":         5,
    "dm me":                6,
    "message me":           5,
    "rfq":                  9,
    "request for quote":    9,
    "request for proposal": 9,
    "rfp":                  8,
    "tender":               7,
    "procurement":          6,
    "vendor evaluation":    7,
    "shortlisting":         7,
    "comparing vendors":    6,
    "quote":                4,
    "pricing for":          5,
    "evaluating":           4,
    "alternative to":       7,
    "replace":              5,
    "looking to replace":   8,
    "switch from":          6,
    "setting up":           5,
    "new facility":         4,
    "greenfield":           5,
}

# Minimum score for a LEAD post to be included in email
# (Competitor posts bypass this threshold entirely)
MIN_LEAD_SCORE = 5

# ══════════════════════════════════════════════════════════════════════════════
# 🚫  LEAD SPAM PHRASES
#     Applied ONLY to lead posts. Posts matching any of these are discarded.
#     Competitor posts are NOT subject to this filter.
# ══════════════════════════════════════════════════════════════════════════════
LEAD_SPAM_PHRASES = [
    # Job postings
    "we are hiring", "we're hiring", "job opening", "job opportunity",
    "apply now", "send your cv", "send your resume", "hiring now",
    "open position", "career opportunity", "join our team",
    "new mandate", "we are looking for a", "seeking a ",
    # Market reports
    "market to reach", "cagr", "market size",
    "press release", "research report", "market report",
    "billion by 20", "million by 20",
    # Events / webinars
    "podcast", "webinar", "register now", "join us at",
    "booth number", "see you at", "meet us at",
    # Pure educational content
    "fundamentals:", "introduction to",
]

# ══════════════════════════════════════════════════════════════════════════════
# 🚫  COMPETITOR SPAM PHRASES
#     Much tighter list — we still want their announcements and news,
#     but discard pure job ads and irrelevant content.
# ══════════════════════════════════════════════════════════════════════════════
COMPETITOR_SPAM_PHRASES = [
    "we are hiring", "we're hiring", "job opening", "apply now",
    "send your cv", "open position", "join our team",
]
