# GoRentls SEO Automation Suite Deployment Guide

This guide describes how to deploy, configure, and test the pure-Python SEO automation pipeline designed for **GoRentls**.

## Phase 1: Environment Setup

1. Place a `.env` file in the `seo/` directory with the following settings:

```env
SERPBEAR_URL=http://localhost:3000
SERPBEAR_API_KEY=your_api_key_here
SERPBEAR_DB=C:\\Users\\sunil\\projects\\serpbear\\data\\database.sqlite
GORP_DOMAIN=gorentls.com
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## Phase 2: Configure Scraper in SerpBear UI

1. Open the SerpBear interface at `http://localhost:3000`.
2. Navigate to **Settings → Scraper** and choose **Serply** or **SerpApi**.
3. Input your API key and click **Save Settings**.
4. To sync target keywords, run:

```powershell
python insert_target_keywords.py
```

## Phase 3: Setup Windows Task Scheduler

Run the PowerShell script as **Administrator** to register the cron tasks natively on Windows:

```powershell
Powershell -ExecutionPolicy Bypass -File setup_windows_tasks.ps1
```

## Phase 4: Test Components

* **Daily Scan:** `python seo_pipeline.py` (Outputs JSON, logs to `ranking_log.md`, exits with `2` if drops detected).
* **Competitor Crawler:** `python crawl_competitors.py` (Expects drops JSON input).
* **Coordinator:** `python seo_coordinator.py --full` (Runs scan, crawls competitors on rank drops, generates optimizations, and pushes logs to GitHub).
