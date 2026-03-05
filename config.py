"""
LinkedIn Strategic Intelligence Monitor — ADOR Digatron
Products: Battery Testers · Cell Testers · EOL Testers ·
          Cell Grading Machines · Formation Equipment · Power Conversion Systems

Quota design: 9 searches/day × 31 days = 279/month
              3 SerpAPI keys × 100/month = 300 available  ✅

Search breakdown:
  ── Target Accounts & Buyers (6 searches) ──────────────────────────────────
  S1  Indian gigafactory & cell plant builders  → formation, grading, EOL testers
  S2  Global cell manufacturers (Asia ops)      → full equipment suite
  S3  EV OEMs expanding battery validation      → EOL testers, cell testers, cyclers
  S4  Battery testing service labs              → direct cycler / tester buyers
  S5  Buyer intent — equipment questions        → anyone publicly asking to buy
  S6  New battery facility announcements        → greenfield plants = equipment need

  ── Competitor Intelligence (3 searches) ───────────────────────────────────
  S7  Neware + Arbin          (top 2 direct competitors)
  S8  Basytec + Maccor + Bitrode
  S9  Chroma ATE + NH Research + Wonik PNE
"""
import os


# ══════════════════════════════════════════════════════════════════════════════
# 🔑  SERPAPI KEYS  (GitHub Secrets: SERPAPI_KEY_1, SERPAPI_KEY_2, SERPAPI_KEY_3)
# ══════════════════════════════════════════════════════════════════════════════
SERPAPI_KEYS = [
    k for k in [
        os.getenv("SERPAPI_KEY_1", ""),
        os.getenv("SERPAPI_KEY_2", ""),
        os.getenv("SERPAPI_KEY_3", ""),
    ] if k
]

# ══════════════════════════════════════════════════════════════════════════════
# 📧  EMAIL  (Gmail SMTP)
#     EMAIL_SENDER     → GitHub Secret  (your Gmail address)
#     EMAIL_PASSWORD   → GitHub Secret  (Gmail App Password, 16 chars)
#     EMAIL_RECIPIENTS → GitHub Secret  (comma-separated addresses)
# ══════════════════════════════════════════════════════════════════════════════
EMAIL_SENDER     = os.getenv("EMAIL_SENDER",    "gambhiremihir@gmail.com")
EMAIL_PASSWORD   = os.getenv("EMAIL_PASSWORD",  "")
_raw             = os.getenv("EMAIL_RECIPIENTS", "gambhiremihir@gmail.com")
EMAIL_RECIPIENTS = [e.strip() for e in _raw.split(",") if e.strip()]
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️  SEARCH SETTINGS
#     SEARCH_TIME_FILTER: qdr:d = past day (right for daily runs)
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_TIME_FILTER     = "qdr:d"
MAX_RESULTS_PER_SEARCH = 10

# ══════════════════════════════════════════════════════════════════════════════
# 🔍  THE 9 SEARCHES
#
#  Each entry is a dict:
#    label    → section heading in the email
#    kind     → "account", "buyer", or "competitor"
#    query    → raw Google query string (full control)
#    context  → one-line note explaining why this search matters (shown in email)
# ══════════════════════════════════════════════════════════════════════════════
SEARCHES = [

    # ── S1: Indian gigafactory & cell plant builders ───────────────────────
    # Any new plant, capacity expansion, equipment commissioning from these
    # companies is a direct sales opportunity for formation + grading + EOL.
    {
        "label":   "Indian Gigafactory & Cell Plant Builders",
        "kind":    "account",
        "context": "New plant / expansion = opportunity for formation equipment, cell graders & EOL testers",
        "query": (
            'site:linkedin.com '
            '("Waaree" OR "Ola Electric" OR "Agratas" OR "Exide Energy" '
            ' OR "Amara Raja" OR "Epsilon Advanced Materials" OR "Servotech") '
            '("gigafactory" OR "cell plant" OR "new facility" OR "production line" '
            ' OR "capacity expansion" OR "GWh" OR "groundbreaking" OR "inauguration" '
            ' OR "commissioning" OR "MOU" OR "investment" OR "battery manufacturing")'
        ),
    },

    # ── S2: Global cell manufacturers ─────────────────────────────────────
    # New plants, JVs, supply agreements from the world's biggest cell makers.
    # Any Asia/India expansion = procurement cycle for our full equipment range.
    {
        "label":   "Global Cell Manufacturers — New Plants & Deals",
        "kind":    "account",
        "context": "New plant / JV / supply deal from global cell makers = full equipment procurement",
        "query": (
            'site:linkedin.com '
            '("CATL" OR "Samsung SDI" OR "LG Energy Solution" OR "Panasonic Energy" '
            ' OR "BYD" OR "EVE Energy" OR "CALB" OR "Gotion") '
            '("new plant" OR "new factory" OR "new facility" OR "gigafactory" '
            ' OR "joint venture" OR "JV" OR "supply agreement" OR "investment" '
            ' OR "capacity expansion" OR "GWh" OR "groundbreaking" OR "commissioning")'
        ),
    },

    # ── S3: EV OEMs expanding battery validation ───────────────────────────
    # When OEMs expand in-house battery test centres they buy EOL testers,
    # pack testers and cell cyclers directly.
    {
        "label":   "EV OEMs — Battery Validation Expansion",
        "kind":    "account",
        "context": "New battery lab / validation centre = EOL tester, pack tester & cycler opportunity",
        "query": (
            'site:linkedin.com '
            '("Mahindra" OR "Tata Motors" OR "Hyundai" OR "BMW" OR "Stellantis" '
            ' OR "Maruti Suzuki" OR "Toyota" OR "Volkswagen" OR "Mercedes") '
            '("battery lab" OR "battery testing" OR "battery validation" '
            ' OR "EV battery" OR "cell testing" OR "pack testing" '
            ' OR "new facility" OR "new plant" OR "capacity" OR "commissioning")'
        ),
    },

    # ── S4: Battery testing service labs ──────────────────────────────────
    # TÜV, SGS, Intertek etc. ARE the business of testing — they buy equipment
    # whenever they open a new lab or expand existing capability.
    {
        "label":   "Battery Testing Service Labs — New Capacity",
        "kind":    "account",
        "context": "New battery testing lab or capacity expansion = direct cycler / cell tester purchase",
        "query": (
            'site:linkedin.com '
            '("TÜV SÜD" OR "TUV SUD" OR "SGS" OR "Intertek" OR "Bureau Veritas" '
            ' OR "ARAI" OR "NABL" OR "UL Solutions" OR "Dekra") '
            '("battery" OR "cell") '
            '("new lab" OR "new facility" OR "new center" OR "new centre" '
            ' OR "expansion" OR "commissioning" OR "capability" OR "accreditation")'
        ),
    },

    # ── S5: Buyer intent — people publicly asking for equipment ────────────
    # Anyone on LinkedIn asking which battery tester / cycler / grader to buy.
    # Rare but the highest-value lead type — direct active buyer.
    {
        "label":   "Buyer Intent — Equipment Questions",
        "kind":    "buyer",
        "context": "Someone publicly asking which battery tester / cycler / grader to buy",
        "query": (
            'site:linkedin.com '
            '("battery tester" OR "battery cycler" OR "cell tester" '
            ' OR "formation equipment" OR "cell grader" OR "EOL tester" '
            ' OR "battery formation" OR "power conversion system") '
            '("recommend" OR "recommendation" OR "anyone used" OR "looking for" '
            ' OR "which one" OR "best option" OR "good vendor" OR "supplier" '
            ' OR "sourcing" OR "rfq" OR "quote" OR "replace" OR "alternative to")'
        ),
    },

    # ── S6: New battery facility announcements ─────────────────────────────
    # Any company announcing a new battery plant, lab, or R&D centre — even
    # companies not on our radar — is a potential buyer.
    {
        "label":   "New Battery Facility Announcements",
        "kind":    "buyer",
        "context": "Any new battery plant or lab = potential buyer for our full equipment range",
        "query": (
            'site:linkedin.com '
            '("battery" OR "lithium" OR "cell") '
            '("new plant" OR "new factory" OR "new lab" OR "new facility" '
            ' OR "new R&D center" OR "new testing center" OR "groundbreaking" '
            ' OR "inauguration" OR "first production" OR "start of production" '
            ' OR "commissioning" OR "GWh" OR "gigafactory") '
            '-hiring -vacancy -job'
        ),
    },

    # ── S7: Neware + Arbin ─────────────────────────────────────────────────
    # Top 2 direct competitors. New products, contracts, partnerships,
    # customer wins, expansions — all affect our positioning.
    {
        "label":   "Neware & Arbin",
        "kind":    "competitor",
        "context": "",
        "query": (
            'site:linkedin.com '
            '("Neware" OR "Arbin Instruments" OR "Arbin") '
            '("new product" OR "product launch" OR "new contract" OR "order" '
            ' OR "partnership" OR "distribution" OR "expansion" OR "new customer" '
            ' OR "customer win" OR "supply agreement" OR "MOU" OR "investment" '
            ' OR "funding" OR "acquisition" OR "new facility")'
        ),
    },

    # ── S8: Basytec + Maccor + Bitrode ────────────────────────────────────
    {
        "label":   "Basytec, Maccor & Bitrode",
        "kind":    "competitor",
        "context": "",
        "query": (
            'site:linkedin.com '
            '("Basytec" OR "Maccor" OR "Bitrode" OR "Sovema") '
            '("new product" OR "product launch" OR "new contract" OR "order" '
            ' OR "partnership" OR "distribution" OR "expansion" OR "new customer" '
            ' OR "customer win" OR "supply agreement" OR "MOU" OR "investment" '
            ' OR "funding" OR "acquisition" OR "new facility")'
        ),
    },

    # ── S9: Chroma ATE + NH Research + Wonik PNE ──────────────────────────
    {
        "label":   "Chroma ATE, NH Research & Wonik PNE",
        "kind":    "competitor",
        "context": "",
        "query": (
            'site:linkedin.com '
            '("Chroma ATE" OR "Chroma Systems" OR "NH Research" OR "Wonik PNE") '
            '("new product" OR "product launch" OR "new contract" OR "order" '
            ' OR "partnership" OR "distribution" OR "expansion" OR "new customer" '
            ' OR "customer win" OR "supply agreement" OR "MOU" OR "investment" '
            ' OR "funding" OR "acquisition" OR "new facility")'
        ),
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# 🚫  NOISE FILTER
#     Word-level and phrase-level checks applied to title + snippet.
#     Any match = post discarded.
# ══════════════════════════════════════════════════════════════════════════════
NOISE_WORDS = {
    "hiring", "vacancy", "vacancies", "recruiter", "recruitment",
    "internship", "fresher", "applicants",
    "cagr", "forecast", "segmentation",
}

NOISE_PHRASES = [
    # Market research spam
    "market report", "market research", "market size", "market forecast",
    "market outlook", "market analysis", "market cagr", "market dynamics",
    "market highlights", "market revenue", "market demand",
    "key players", "leading players", "major players",
    "billion by 20", "million by 20", "from 2026", "from 2025",
    # Jobs
    "we are hiring", "we're hiring", "job opening", "apply now",
    "open position", "join our team", "send your cv",
    # Events
    "register now", "webinar", "podcast",
]
