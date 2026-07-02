# GoRentls SEO Automation Suite

Automated SEO rank tracking, competitor analysis, and optimization pipeline for [gorentls.com](https://gorentls.com).

## Architecture

```
Windows Task Scheduler
    |
    v
seo_coordinator.py (orchestrator)
    |
    +-- Stage 1: seo_pipeline.py
    |   -> SerpBear API (real ranks via Serply/SerpApi)
    |   -> GSC CSV data (clicks, impressions, CTR)
    |   -> JSON output + exit code 2 if drops detected
    |
    +-- Stage 2: crawl_competitors.py (only if drops)
    |   -> Crawl4AI + Playwright
    |   -> BeautifulSoup fallback
    |   -> Competitor markdown extraction
    |
    +-- Stage 3: Generate weekly_optimizations.md
        -> Human review -> Git commit -> Deploy
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file (see `seo/scripts/instructions.md`)
4. Configure SerpBear scraper API (Serply or SerpApi)
5. Run keyword sync: `python seo/scripts/insert_target_keywords.py`
6. Register Windows tasks: `powershell -File seo/scripts/setup_windows_tasks.ps1`

## Scripts

| Script | Purpose |
|--------|---------|
| `seo_pipeline.py` | Fetches SerpBear rankings + GSC data, detects drops |
| `crawl_competitors.py` | Crawls competitor pages using Crawl4AI/BeautifulSoup |
| `seo_coordinator.py` | Orchestrates the full pipeline, auto-commits to GitHub |
| `insert_target_keywords.py` | Syncs target keywords to SerpBear SQLite DB |
| `setup_windows_tasks.ps1` | Registers Windows Task Scheduler jobs |

## License

MIT
