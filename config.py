"""
LinkedIn Intelligence Monitor — Configuration
ADOR Digatron
Products: Battery/Cell Testers, EOL Testers, Cell Grading Machines,
          Formation Equipment, Power Conversion Systems

Keywords sourced from senior management, combined with buyer-intent signals.
Two pipelines:
  LEAD_SEARCHES       — people/companies likely to BUY from ADOR Digatron
  COMPETITOR_SEARCHES — what competitors are announcing / doing
"""
import os


# ══════════════════════════════════════════════════════════════════════════════
# 🔑  SERPAPI KEYS  (GitHub Secrets: SERPAPI_KEY_1, SERPAPI_KEY_2)
# ══════════════════════════════════════════════════════════════════════════════
SERPAPI_KEYS = [
    k for k in [
        os.getenv("SERPAPI_KEY_1", ""),
        os.getenv("SERPAPI_KEY_2", ""),
    ] if k
]

# ══════════════════════════════════════════════════════════════════════════════
# 📧  EMAIL  (Gmail SMTP)
#     EMAIL_SENDER     → GitHub Secret  (your Gmail address)
#     EMAIL_PASSWORD   → GitHub Secret  (Gmail App Password, 16 chars)
#     EMAIL_RECIPIENTS → GitHub Secret  (comma-separated list of addresses)
# ══════════════════════════════════════════════════════════════════════════════
EMAIL_SENDER     = os.getenv("EMAIL_SENDER",    "gambhiremihir@gmail.com")
EMAIL_PASSWORD   = os.getenv("EMAIL_PASSWORD",  "")
_raw             = os.getenv("EMAIL_RECIPIENTS", "gambhiremihir@gmail.com")
EMAIL_RECIPIENTS = [e.strip() for e in _raw.split(",") if e.strip()]
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587


# ══════════════════════════════════════════════════════════════════════════════
# 🎯  LEAD SEARCHES
#
#  Format: list of (label, raw_google_query) tuples.
#  Each tuple = one SerpAPI API call.
#
#  Design:
#    Senior product keywords are paired with INTENT SIGNAL groups so we only
#    surface posts from BUYERS, not analysts, journalists, or educators.
#
#  Intent signal groups:
#    _ASKING   → asking peers for a recommendation or vendor
#    _SOURCING → actively procuring / shortlisting vendors
#    _BUILDING → new plant / lab / facility = upcoming equipment purchase
#    _REPLACING → unhappy with competitor = direct sales opportunity
# ══════════════════════════════════════════════════════════════════════════════

_ASKING = (
    '"recommend" OR "recommendation" OR "looking for" OR "anyone used" '
    'OR "which vendor" OR "can anyone suggest" OR "who supplies" '
    'OR "best option" OR "anyone know" OR "any suggestions"'
)

_SOURCING = (
    '"supplier" OR "vendor" OR "sourcing" OR "procurement" '
    'OR "RFQ" OR "request for quote" OR "tender" OR "shortlisting" '
    'OR "evaluating" OR "comparing vendors"'
)

_BUILDING = (
    '"new plant" OR "new facility" OR "setting up" OR "expanding" '
    'OR "groundbreaking" OR "commissioning" OR "new line" '
    'OR "new capacity" OR "greenfield" OR "new lab"'
)

_REPLACING = (
    '"alternative to" OR "replace" OR "switch from" '
    'OR "unhappy with" OR "issues with" OR "looking to replace"'
)


LEAD_SEARCHES = [

    # ── i. Cell / Battery Tester — asking for recommendations ─────────────
    # R&D labs, cell manufacturers, EV OEMs asking peers which tester to buy
    (
        "Battery / Cell Tester — Asking for Recommendation",
        (
            'site:linkedin.com '
            '("Battery Tester" OR "Battery Cycler" OR "Battery Capacity Tester" '
            ' OR "Battery Aging Machine" OR "Battery Charger-Discharger" '
            ' OR "Cell Tester" OR "Cell Cycler" OR "Cell Capacity Tester" '
            ' OR "Cell Aging Machine" OR "Cell Grading Machine") '
            f'({_ASKING})'
        ),
    ),

    # ── i. Cell / Battery Tester — actively sourcing / procuring ──────────
    (
        "Battery / Cell Tester — Procurement & Sourcing",
        (
            'site:linkedin.com '
            '("Battery Tester" OR "Battery Cycler" OR "Cell Tester" '
            ' OR "Cell Cycler" OR "Computer Operated Battery Cycler" '
            ' OR "Battery Charger-Discharger" OR "Cell Charger Discharger") '
            f'({_SOURCING})'
        ),
    ),

    # ── i. Cell / Battery Tester — new lab setup ──────────────────────────
    # Companies opening new battery labs = imminent equipment purchase
    (
        "New Battery Lab / Testing Facility",
        (
            'site:linkedin.com '
            '("battery lab" OR "battery testing lab" OR "cell testing lab" '
            ' OR "battery testing facility" OR "electrochemical lab" '
            ' OR "battery R&D center" OR "battery test center") '
            f'({_BUILDING})'
        ),
    ),

    # ── i. Cell / Battery Tester — competitor replacement ─────────────────
    (
        "Battery Tester — Competitor Replacement Signals",
        (
            'site:linkedin.com '
            '("Battery Tester" OR "Battery Cycler" OR "Cell Tester" '
            ' OR "Cell Cycler" OR "Cell Grading Machine") '
            f'({_REPLACING})'
        ),
    ),

    # ── ii. BESS — Power Conversion System sourcing ────────────────────────
    # BESS manufacturers need PCS — a direct Digatron product
    (
        "BESS / PCS — Equipment Sourcing",
        (
            'site:linkedin.com '
            '("Power Conversion System" OR "PCS" OR "C&I BESS" OR "C&I ESS" '
            ' OR "ESS for Data Centers" OR "BESS Manufacturing Plant" '
            ' OR "Battery Pack Assembly Plant" OR "Battery Energy Storage System") '
            f'({_ASKING} OR {_SOURCING} OR {_BUILDING})'
        ),
    ),

    # ── iii. Cell Assembly Line — new plant / equipment sourcing ───────────
    # Gigafactory builders need formation equipment, grading, PCS
    (
        "Cell Assembly Line — New Plant / Equipment",
        (
            'site:linkedin.com '
            '("Lithium ion cell assembly line" OR "Battery cell manufacturing" '
            ' OR "Pouch cell line" OR "Cylindrical cell line" '
            ' OR "Prismatic cell assembly" OR "Cell Manufacturing Plant" '
            ' OR "Battery formation ageing" OR "Cell formation system" '
            ' OR "Formation testing equipment" OR "Environmental chamber battery" '
            ' OR "Advanced chemistry cell manufacturing") '
            f'({_ASKING} OR {_SOURCING} OR {_BUILDING})'
        ),
    ),

    # ── iii. GWH-scale plant announcements ────────────────────────────────
    # GWH projects = large formation + grading + PCS orders
    (
        "GWH Scale Battery Plant Announcements",
        (
            'site:linkedin.com '
            '("GWH" OR "gigawatt hour" OR "gigafactory") '
            '("cell manufacturing" OR "battery plant" OR "assembly line" '
            ' OR "formation" OR "cell grading" OR "production line") '
            '("new" OR "expand" OR "build" OR "groundbreaking" '
            ' OR "commissioning" OR "capacity")'
        ),
    ),

    # ── iv. Cell Chemistries — testing equipment needed ───────────────────
    # New chemistry labs / startups will need testers supporting these chemistries
    (
        "New Cell Chemistry Labs Needing Test Equipment",
        (
            'site:linkedin.com '
            '("Sodium Ion" OR "Sodium-Ion" OR "Na-ion" OR "Metal Air" '
            ' OR "Aluminum Air" OR "Sodium Silicate" OR "Lead Acid" '
            ' OR "Nickel Cadmium" OR "Ni-Cd" OR "Agnostic Chemistry") '
            '("tester" OR "cycler" OR "testing" OR "characterization" '
            ' OR "validation" OR "lab" OR "equipment" OR "formation" OR "new")'
        ),
    ),

]


# ══════════════════════════════════════════════════════════════════════════════
# 🕵️  COMPETITOR SEARCHES
#
#  Format: list of (label, raw_google_query) tuples.
#  Strategy: find LinkedIn posts about competitor activity —
#    product launches, partnerships, customer wins, new markets, pricing.
#  Job ads are stripped at query level (-hiring -vacancy).
# ══════════════════════════════════════════════════════════════════════════════

COMPETITOR_SEARCHES = [

    (
        "Neware",
        (
            'site:linkedin.com "Neware" '
            '("battery tester" OR "battery cycler" OR "cell tester" '
            ' OR "new product" OR "launched" OR "partnership" '
            ' OR "customer" OR "order" OR "contract" OR "cell grading") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "Arbin Instruments",
        (
            'site:linkedin.com "Arbin" '
            '("battery tester" OR "battery cycler" OR "cell tester" '
            ' OR "new product" OR "launched" OR "partnership" '
            ' OR "customer" OR "order" OR "contract") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "Basytec",
        (
            'site:linkedin.com "Basytec" '
            '("battery" OR "cell tester" OR "cycler" OR "formation" '
            ' OR "new product" OR "partnership" OR "customer" OR "contract") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "Maccor",
        (
            'site:linkedin.com "Maccor" '
            '("battery tester" OR "cycler" OR "new product" '
            ' OR "partnership" OR "customer" OR "contract" OR "expansion") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "Bitrode",
        (
            'site:linkedin.com "Bitrode" '
            '("battery" OR "tester" OR "cycler" '
            ' OR "new product" OR "partnership" OR "customer" OR "contract") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "Chroma",
        (
            'site:linkedin.com "Chroma" '
            '("battery tester" OR "battery cycler" OR "cell tester" '
            ' OR "formation" OR "new product" OR "partnership" OR "contract") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "ACEY / Sinexcel / Nebula Electronics / SEMCO",
        (
            'site:linkedin.com '
            '("ACEY" OR "Sinexcel" OR "Nebula Electronics" OR "SEMCO") '
            '("battery" OR "cell tester" OR "cycler" OR "formation" '
            ' OR "new product" OR "partnership" OR "customer") '
            '-hiring -vacancy -apply'
        ),
    ),

    (
        "DNA Technologies / Encore / Indygreen / RePower",
        (
            'site:linkedin.com '
            '("DNA Technologies" OR "Encore Systems" '
            ' OR "Indygreen Technologies" OR "RePower") '
            '("battery" OR "tester" OR "cycler" OR "new" '
            ' OR "partnership" OR "customer" OR "contract") '
            '-hiring -vacancy -apply'
        ),
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# ⚙️  SEARCH SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_TIME_FILTER     = "qdr:w"   # qdr:d = day, qdr:w = week, qdr:m = month
MAX_RESULTS_PER_SEARCH = 10


# ══════════════════════════════════════════════════════════════════════════════
# 🚫  SPAM FILTERS
# ══════════════════════════════════════════════════════════════════════════════

# Applied to LEAD posts — discard anything that is clearly not a buyer signal
LEAD_SPAM_PHRASES = [
    "we are hiring", "we're hiring", "job opening", "job opportunity",
    "apply now", "send your cv", "send your resume", "hiring now",
    "open position", "career opportunity", "join our team",
    "new mandate", "we are looking for a", "seeking a",
    "market to reach", "cagr", "market size", "market report",
    "research report", "press release", "billion by 20", "million by 20",
    "webinar", "register now", "join us at", "booth number",
    "see you at", "meet us at", "fundamentals:", "introduction to",
    "blog post", "white paper",
]

LEAD_SPAM_WORDS = {
    "hiring", "vacancy", "vacancies", "recruiter", "recruitment",
    "internship", "fresher", "applicants", "shortlisted",
}

# Applied to COMPETITOR posts — only strip pure job ads
COMPETITOR_SPAM_PHRASES = [
    "we are hiring", "we're hiring", "job opening",
    "apply now", "send your cv", "open position", "join our team",
]

COMPETITOR_SPAM_WORDS = {
    "hiring", "vacancy", "vacancies", "recruiter",
}
