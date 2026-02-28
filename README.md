# 🔍 LinkedIn Keyword Monitor — ADOR Digatron

Automated LinkedIn post discovery for potential customer prospecting. Searches Google for publicly visible LinkedIn posts matching **45+ keywords** across 5 categories (Battery Testers, BESS, Cell Assembly, Cell Chemistries, Competitors) and delivers an **HTML email digest with screenshots** to your inbox.

**Runs free on GitHub Actions** — no server or local machine needed.

---

## ⚡ Quick Setup (15 minutes)

### 1. Get API Keys

| Service | What You Need | Where to Get It |
|---|---|---|
| **SerpAPI** | API Key | [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) — 100 free searches/month |
| **Gmail** | App Password | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) — requires 2FA enabled |

> **💡 Gmail App Password:** Go to Google Account → Security → 2-Step Verification (enable if needed) → App Passwords → Create one for "Mail" + "Other (LinkedIn Monitor)". Copy the 16-character password.

### 2. Create GitHub Repository

```bash
# Option A: Create new repo from this folder
cd linkedin-monitor
git init
git add .
git commit -m "Initial commit: LinkedIn Keyword Monitor"
gh repo create linkedin-monitor --public --push
# ☝️ Use --public for free GitHub Actions minutes (2000 min/month)

# Option B: Upload via GitHub.com
# Go to github.com/new → create repo → upload these files
```

### 3. Add Secrets to GitHub

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value |
|---|---|
| `SERPAPI_KEY` | Your SerpAPI API key |
| `GMAIL_ADDRESS` | Your Gmail address (e.g., `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | The 16-char app password from Step 1 |
| `RECIPIENT_EMAIL` | Email to receive digests (can be same as GMAIL_ADDRESS) |

### 4. Test It

Go to your repo → **Actions** → **LinkedIn Keyword Monitor** → **Run workflow** → Click **"Run workflow"**.

Check your email in ~5 minutes! 🎉

---

## 📅 Schedule

By default, the monitor runs **every Monday & Thursday at 9:00 AM IST** (3:30 AM UTC).

To change the schedule, edit `.github/workflows/linkedin-monitor.yml`:

```yaml
schedule:
  - cron: "30 3 * * 1,4"    # Mon & Thu at 9:00 AM IST
  # Examples:
  # "0 4 * * 1"             # Every Monday at 9:30 AM IST
  # "0 4 * * *"             # Every day at 9:30 AM IST
  # "0 4 1,15 * *"          # 1st and 15th of each month
```

---

## 🛠 Manual / Local Usage

### Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Set environment variables
```bash
# Linux/Mac
export SERPAPI_KEY="your_key"
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your_app_password"
export RECIPIENT_EMAIL="recipient@example.com"

# Windows PowerShell
$env:SERPAPI_KEY="your_key"
$env:GMAIL_ADDRESS="you@gmail.com"
$env:GMAIL_APP_PASSWORD="your_app_password"
$env:RECIPIENT_EMAIL="recipient@example.com"
```

### Run
```bash
python main.py                                   # Full run (all categories)
python main.py --categories "BESS" "Competition"  # Specific categories only
python main.py --dry-run                          # Search only, no email
python main.py --no-screenshots                   # Email without screenshots (faster)
python main.py --time-filter qdr:d                # Posts from past day only
python main.py --max-results 5                    # Limit to 5 results/category
```

---

## 📁 Project Structure

```
linkedin-monitor/
├── .github/workflows/
│   └── linkedin-monitor.yml   ← GitHub Actions cron job
├── src/
│   ├── config.py              ← Keywords, categories, settings
│   ├── search.py              ← SerpAPI Google search
│   ├── screenshot.py          ← Playwright screenshots
│   └── email_sender.py        ← Gmail SMTP email
├── main.py                    ← Orchestrator (entry point)
├── requirements.txt           ← Python dependencies
└── README.md                  ← You are here
```

---

## 🔧 Customizing Keywords

Edit `src/config.py` → `KEYWORD_CATEGORIES` dict. Each category is a list of keywords that get combined into a single Google search query:

```python
KEYWORD_CATEGORIES = {
    "My New Category": [
        "keyword one",
        "keyword two",
        "keyword three",
    ],
    # ... existing categories ...
}
```

> **⚠️ SerpAPI free tier = 100 searches/month.** Each category = 1 search. With 5 categories, that's 5 searches per run → ~20 runs/month.

---

## 🌐 Deployment Options

| Platform | Free Tier | Cron Support | Best For |
|---|---|---|---|
| **GitHub Actions** ✅ | 2000 min/mo (public repo) | Built-in | This project (recommended) |
| Oracle Cloud Free | Always-free VM | crontab | Full control, unlimited runs |
| PythonAnywhere | 1 scheduled task/day | Built-in | Simple Python scripts |
| Render | 750 hrs/mo | Cron jobs | Web service + cron |
| Railway | $5 credit/mo | Built-in | Good developer experience |

---

## 📧 Sample Email

The email digest includes:

- **Header** with total post count and date
- **Posts grouped by category** with:
  - Post title (clickable link to LinkedIn)
  - Text snippet/preview
  - Screenshot of the post (inline + as attachment)
- **Footer** with ADOR Digatron branding

---

## ⚠️ Limitations

1. **Public posts only** — LinkedIn posts behind the login wall won't appear in Google search results.
2. **SerpAPI free tier** — 100 searches/month. The tool batches keywords to minimize API calls, but heavy usage may require a paid plan ($50/mo).
3. **Screenshot reliability** — LinkedIn may show login prompts on some post pages; the tool attempts to dismiss these but may fail occasionally.
4. **Search delay** — Google indexes LinkedIn posts with a delay (hours to days), so brand-new posts won't appear immediately.

---

## 📝 License

Internal tool for ADOR Digatron. Not for redistribution.
