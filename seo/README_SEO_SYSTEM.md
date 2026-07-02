# GoRentls SEO Automation System v3  
Self‑Improving Multi‑Agent SEO with Obscura, SerpBear, and Programmatic SEO

This document explains exactly:

- What each agent does  
- How the pieces fit together  
- All code entrypoints and where to paste them  
- How to run, monitor, and extend the system

***

## 1. Architecture Overview

The system is a **multi‑agent SEO autopilot** for GoRentls:

- **Scout (Rank Scanner)** — reads rankings from SerpBear + Google Search Console, detects drops.
- **Inspector (Technical Auditor)** — audits meta tags, schema, internal links, llms.txt.
- **Publisher (Programmatic SEO)** — generates item × city pSEO landing pages and llms.txt.
- **Crawler (Competitor Watcher)** — crawls competitor sites for dropped keywords using Obscura.
- **Evolution Engine (Self‑Improver)** — logs experiments, learns what works, flags anomalies, self‑heals.
- **Coordinator (Orchestrator)** — runs all agents in order, writes weekly plan, auto‑commits to git.

Core external tools referenced:

- **SerpBear** to track keyword positions and integrate GSC data. [docs.serpbear](https://docs.serpbear.com)
- **Programmatic SEO patterns** (item × city pages, internal linking, schema, etc.). [mangools](https://mangools.com/blog/programmatic-seo/)
- **llms.txt / AI discoverability best practices** to make GoRentls visible to LLMs and AI crawlers. [flow-agency](https://www.flow-agency.com/blog/llm-seo-best-practices/)

Directory layout inside your repo:

```text
/seo
  /scripts
    obscura_extractor.py
    seo_pipeline.py
    crawl_competitors.py
    technical_auditor.py
    pseo_generator.py
    self_improving_engine.py
    seo_coordinator.py
  /data
    gsc_queries.csv         # (optional, if not using GSC API)
  /memory
    experiments.json
    learnings.json
    strategy.json
    anomalies.json
    pseo_page_state.json
  /reports
    ranking_log.md
    technical_audit.md
    coordinator_log.md
  /drafts
    pseo_pages/*.md
    llms.txt
    weekly_optimizations.md
  target_keywords.md
  .env
```

You already have most of this from your repo; just ensure the scripts and paths align.

***

## 2. Code: What to Paste Where

Create or update the following files under `seo/scripts/` in your repo.

### 2.1 `obscura_extractor.py` — Obscura Integration Layer

Paste the full content you got from me for `obscura_extractor.py` into:

```text
seo/scripts/obscura_extractor.py
```

Highlights:

- **Functions exposed:**
  - `fetch_markdown(url, timeout=30, stealth=None)`
  - `scrape_parallel(urls, concurrency=10, timeout=30)`
  - `fetch_links(url, timeout=30)`
  - `fetch_meta(url, timeout=30)`  ← for `<title>` + `<meta name="description">`
  - `evaluate_js(url, js_expression, timeout=30)`
  - `is_obscura_available()`
  - `log_debug(msg)`

- **Behavior:**
  - Tries Obscura CLI (`OBSCURA_BIN`) with stealth and optional proxy.
  - Falls back to `requests + BeautifulSoup` if Obscura is unavailable.
  - `fetch_meta` uses JS eval with Obscura when possible, so client‑rendered meta tags are detected accurately, then falls back to static parsing.

Environment variables you can set in `seo/.env`:

```ini
OBSCURA_BIN=obscura
OBSCURA_STEALTH=true
OBSCURA_PROXY=
```

***

### 2.2 `seo_pipeline.py` — Scout Agent (Rank Scanner)

Paste into:

```text
seo/scripts/seo_pipeline.py
```

Key behavior:

- Reads `target_keywords.md` (markdown table) to know:
  - `keyword`, `cluster`, `url`.
- Pulls latest positions from **SerpBear API**. [github](https://github.com/towfiqi/serpbear)
- Optionally pulls GSC data via:
  - API (if `GSC_API_ENABLED=true` and service account JSON configured), or
  - CSV at `seo/data/gsc_queries.csv`.
- Compares current vs previous positions (from SerpBear history).
- Decides:
  - If drop ≥ `RANK_DROP_THRESHOLD` positions → mark as **WARNING**.
  - If improvement ≥ 2 positions → “Improved”.
  - If Top 5 but CTR < 3% → “Low CTR for Top 5 rank”.
- Writes/updates `seo/reports/ranking_log.md` with a per‑scan section.
  - Dedupes per **calendar day** (if you run multiple scans same day, only one block exists for that date).
- Prints a JSON summary on stdout and exits with:
  - `0` when stable  
  - `2` when drops detected  
  - `1` on error

Important env vars:

```ini
SERPBEAR_URL=https://your-serpbear-instance
SERPBEAR_API_KEY=...
GORP_DOMAIN=gorentls.com
RANK_DROP_THRESHOLD=2
GSC_API_ENABLED=false        # or true if using API
GSC_PROPERTY=sc-domain:gorentls.com
GSC_SERVICE_ACCOUNT_JSON=/path/to/service-account.json   # only if API enabled
```

SerpBear docs & deployment patterns are here if you need them. [railway](https://railway.com/deploy/serpbear)

***

### 2.3 `crawl_competitors.py` — Competitor Crawler

Paste into:

```text
seo/scripts/crawl_competitors.py
```

Behavior:

- Expects a JSON list of “drops” via **stdin**:
  - Each element: `{ "keyword", "cluster", "url", "previous_position", "current_position", "drop_amount" }`
- For each dropped keyword:
  - Picks competitor URLs from `COMPETITORS` map by `cluster`.
  - Uses `scrape_parallel` (Obscura) to fetch each competitor page as Markdown.
  - Extracts SEO signals:
    - Keyword in H1/H2
    - Word count
    - Heading structure
- Outputs JSON:

```json
{
  "status": "complete",
  "crawled_at": "...",
  "results": [
    {
      "keyword": "...",
      "cluster": "cameras",
      "url": "/rentals/camera/bangalore",
      "competitor_signals": [
        {
          "keyword": "...",
          "competitor_url": "https://www.qwikpik.com/",
          "keyword_in_h1": true,
          "keyword_in_h2": false,
          "word_count": 1200,
          "headings": [...]
        }
      ]
    }
  ],
  "obscura_used": true
}
```

You can extend `COMPETITORS` later with more precise URLs per cluster.

***

### 2.4 `technical_auditor.py` — Inspector Agent

Paste into:

```text
seo/scripts/technical_auditor.py
```

What it does:

- For each audited URL (default: `SITE_URL`, `/rentals`, `/about`):
  - Uses `fetch_markdown` to get Markdown view.
  - Uses **new** `fetch_meta` to get `<title>` + `<meta name="description">` (JS aware).
  - Checks:
    - Title: present, 30–60 chars.
    - Meta description: present, 70–160 chars.
    - H1: exists and only one.
    - Word count ≥ 300.
    - Schema/JSON‑LD presence in page HTML text.
    - FAQ presence if content > 500 words.
  - Uses `fetch_links` to:
    - Extract internal links.
    - Warn if < 3 internal links from that page.

- For `llms.txt`:
  - Tries `SITE_URL/llms.txt`, checks:
    - Exists.
    - Length ≥ 100 chars.
    - Contains “gorentls”.

Output:

- Writes human‑readable `seo/reports/technical_audit.md`.
- Prints JSON summary and exits `0`.

This directly supports **LLM/AI SEO best practices**: accessible content, no blocked bots, descriptive metadata, robust linking. [youtube](https://www.youtube.com/watch?v=RyJYGpVyl0o)

***

### 2.5 `self_improving_engine.py` — Evolution Engine

Paste into:

```text
seo/scripts/self_improving_engine.py
```

Responsibilities:

1. **Experiment Tracker**
   - `log_experiment(experiment_dict)`:
     - Adds a new experiment to `experiments.json` with:
       - Unique `id` (includes microseconds).
       - `started_at`, `status="running"`, `before_metrics`.

2. **Outcome Evaluator**
   - `evaluate_experiments(current_metrics, min_days=14)`:
     - For each `running` experiment older than `min_days`:
       - Reads “before” metrics from experiment.
       - Uses `current_metrics[keyword]` (supplied by Scout/Evolution cycle).
       - Classifies outcomes:
         - `positive` if position improved ≥ 2 or CTR +1%+
         - `negative` if position worsened ≥ 2 or CTR −1%+
         - `neutral` otherwise
       - Writes a **learning** into `learnings.json`.
       - Updates `strategy.json`.

3. **Knowledge Store / Strategy**
   - Maintains:
     - `title_tag_patterns.best_patterns` + `avg_ctr_lift`
     - `content_length_optimal`, `keyword_density_target`
     - `schema_types_that_help.types`
     - `city_pages_performance` by slug, etc.

4. **Anomaly Detector**
   - `detect_anomalies(scan_data)`:
     - Flags:
       - **Severe rank drops** (≥ 5 positions).
       - **Scraper mass failure** (tracked < 50% of total).
       - **Keywords missing in SerpBear** (need insertion).
     - Writes to `anomalies.json`.

5. **Self‑Healer**
   - `self_heal(scan_data, audit_data=None)`:
     - If audit shows:
       - Missing title / description / H1 → queue actions for Publisher.
       - llms.txt issues → queue llms.txt regenerate.
     - If untracked keywords → queue SerpBear sync action.

6. **Evolution Cycle**
   - `run_evolution_cycle(scan_data, audit_data=None)`:
     - Calls evaluator + anomaly detector + self_heal.
     - Returns a summary with:
       - `evaluated_experiments`, `total_learnings`
       - `anomalies_detected`, `self_heal_actions`
       - `best_title_patterns`, `best_schema_types`
       - `city_performance`, etc.

Command‑line utilities:

```bash
python seo/scripts/self_improving_engine.py --init       # initialize memory
python seo/scripts/self_improving_engine.py --status     # quick stats
python seo/scripts/self_improving_engine.py --strategy   # dump strategy.json
python seo/scripts/self_improving_engine.py --learnings  # dump learnings.json
```

***

### 2.6 `pseo_generator.py` — Publisher Agent

Paste into:

```text
seo/scripts/pseo_generator.py
```

Key improvements:

- **Rotation with persistence:**
  - Uses `seo/memory/pseo_page_state.json` to remember which slugs were already generated.
  - Each run with `--max-pages N` will generate **new** item×city combos until the full matrix is covered.
  - `total_matrix_size = len(ITEM_CATEGORIES) × len(CITY_TARGETS)` and `coverage_pct` returned in output.

- **Experiment dedupe:**
  - Only calls `log_experiment()` for **new** slugs.
  - Prevents duplicate noise in `experiments.json` for unchanged pages.

- **Learning application:**
  - Uses `get_strategy()` to apply winning title patterns when there is positive CTR lift evidence.
  - Uses best schema types (e.g., `LocalBusiness`) when evidence exists.

- **llms.txt generator:**
  - Writes `seo/drafts/llms.txt` with:
    - Short brand description.
    - Categories.
    - List of cities.
    - Key URLs.
    - API info.
  - This supports AI/LLM discovery of GoRentls’ structure. [flow-agency](https://www.flow-agency.com/blog/llm-seo-best-practices/)

CLI:

```bash
python seo/scripts/pseo_generator.py --max-pages 10
python seo/scripts/pseo_generator.py --item camera --city bangalore
python seo/scripts/pseo_generator.py --llms-txt-only
```

***

### 2.7 `seo_coordinator.py` — Orchestrator

Paste into:

```text
seo/scripts/seo_coordinator.py
```

What it orchestrates:

1. **Scan rankings (Scout)** → `seo_pipeline.py`
2. **If drops** → run **Crawler** on dropped keywords.
3. **Run technical audit (Inspector)** → `technical_auditor.py`
4. **Generate pSEO pages (Publisher)** → `pseo_generator.py`
5. **Run Evolution Engine** → `run_evolution_cycle(scan_data, audit_data)`
6. **Generate weekly plan** → writes `seo/drafts/weekly_optimizations.md`
7. **Git auto‑commit/push (optional)**

Key functions inside:

- `_run_subprocess_json(...)`  
  Safe wrapper:
  - Timeout.
  - Captures stdout/stderr.
  - Parses only the **last line** as JSON.
  - Returns structured error when stdout is empty or invalid.

- `run_scan()`, `run_crawl()`, `run_audit()`, `run_pseo()`, `run_evolution()`
- `generate_optimizations(scan_data, audit_data, evolution_data)`:
  - Builds a Markdown “playbook” listing:
    - URLs with drops.
    - Actions per URL (title/meta/H1 to revisit).
    - Technical issues from the audit.
    - Evolution Engine insights (best patterns, best schemas, city performance).
  - This becomes your weekly implementation checklist.

- `push_to_git()`:
  - Checks `git status --porcelain seo/`.
  - If changes: adds, commits with timestamped message, and pushes `origin main`.
  - Handles commit/push failures with clear logging instead of silently failing.

CLI usage:

```bash
# Full run (all agents + Evolution Engine + git push)
python seo/scripts/seo_coordinator.py --full

# Same but without pushing to git (use first in testing)
python seo/scripts/seo_coordinator.py --full --no-push

# Individual modes:
python seo/scripts/seo_coordinator.py --scan-only
python seo/scripts/seo_coordinator.py --audit-only
python seo/scripts/seo_coordinator.py --pseo-only --max-pseo-pages 10
python seo/scripts/seo_coordinator.py --evolution-only
python seo/scripts/seo_coordinator.py --crawl-only   # reads drops JSON from stdin
```

***

## 3. Implementation Plan (Step‑by‑Step)

### Step 1: Copy scripts into your repo

Inside Antigravity IDE:

1. Create `seo/scripts/` if it doesn’t exist.
2. For each script listed above, paste the full code I generated into the matching file path.
3. Commit once locally after pasting to make it easy to diff later.

### Step 2: Configure environment + SerpBear

1. Create `seo/.env` (or use your existing one) with:

```ini
SERPBEAR_URL=https://your-serpbear-instance
SERPBEAR_API_KEY=YOUR_KEY
GORP_DOMAIN=gorentls.com
RANK_DROP_THRESHOLD=2

GSC_API_ENABLED=false
GSC_PROPERTY=sc-domain:gorentls.com
GSC_SERVICE_ACCOUNT_JSON=/absolute/path/to/service-account.json

OBSCURA_BIN=obscura
OBSCURA_STEALTH=true
OBSCURA_PROXY=
GORP_SITE_URL=https://gorentls.com
```

2. Ensure SerpBear is running and your domain is added; SerpBear supports GSC integration and domain-level tracking which the pipeline assumes. [serpapi](https://serpapi.com/blog/self-host-serpbear-coolify/)

### Step 3: Initialize the Evolution Engine

Run once:

```bash
cd <your-repo-root>

python seo/scripts/self_improving_engine.py --init
python seo/scripts/self_improving_engine.py --status
```

You should see:

- `experiments.json`, `learnings.json`, `strategy.json`, `anomalies.json` created.
- Status output with 0 experiments and empty strategy.

### Step 4: Prepare target keywords + GSC data

1. Ensure `seo/target_keywords.md` looks like:

```markdown
| Keyword                | Cluster | URL                         |
|------------------------|---------|----------------------------|
| camera rental bangalore| cameras | /rentals/camera/bangalore  |
| bike rental hyderabad  | bikes   | /rentals/bike/hyderabad    |
```

2. Either:

- Provide `seo/data/gsc_queries.csv` exported from GSC, or  
- Enable `GSC_API_ENABLED=true` and configure service account according to SerpBear+GSC tutorials. [repocloud](https://repocloud.io/details/?app_id=181)

### Step 5: Run each agent manually once

1. **Scout:**

```bash
python seo/scripts/seo_pipeline.py
```

- Check `seo/reports/ranking_log.md` created.
- Verify JSON on stdout includes `drops_count`, `drops`, `untracked_keywords`.

2. **Inspector:**

```bash
python seo/scripts/technical_auditor.py --full
```

- Check `seo/reports/technical_audit.md`.
- Confirm meta description / H1 / llms.txt issues show up if they exist.

3. **Publisher (pSEO + llms.txt):**

```bash
python seo/scripts/pseo_generator.py --max-pages 10
```

- Check `seo/drafts/pseo_pages/*.md` files.
- Check `seo/drafts/llms.txt` output and plan to mount it at `/llms.txt` on production. [youtube](https://www.youtube.com/watch?v=RyJYGpVyl0o)

4. **Evolution-only dry run:**

```bash
python seo/scripts/self_improving_engine.py --status
python seo/scripts/self_improving_engine.py --learnings
```

Initially, there won’t be much data; after weeks of experiments and scans, this becomes your AI “memory”.

### Step 6: Wire Coordinator + cron

Once individual agents look healthy:

```bash
python seo/scripts/seo_coordinator.py --full --no-push
```

Verify:

- `ranking_log.md`, `technical_audit.md`, `weekly_optimizations.md` updated.
- `coordinator_log.md` shows a full run with each agent’s status.

If everything looks good, enable git auto‑push:

```bash
python seo/scripts/seo_coordinator.py --full
```

Then schedule via cron or your CI:

```cron
0 6 * * * cd /path/to/repo && /usr/bin/python3 seo/scripts/seo_coordinator.py --full >> seo/cron.log 2>&1
```

***

## 4. How the System Learns Over Time

1. **New pages → Experiments**
   - Whenever pSEO generates a new slug, it logs an experiment with baseline metrics (`position=0`, etc.).
   - After ~14 days, the Evolution Engine compares before vs after.

2. **Learnings update strategy**
   - Positive experiments update:
     - Title patterns that increase CTR.
     - Schema types that lift rankings.
     - City‑level performance stats.

3. **Strategy influences new pages**
   - `pseo_generator.py` uses `get_strategy()` to:
     - Apply proven title patterns when evidence is strong.
     - Attach extra schema types like `LocalBusiness` only when they previously helped for similar pages.

4. **Anomalies and self‑healing**
   - Severe drops or missing keywords are logged in `anomalies.json`.
   - Self‑healer queues:
     - Meta fixes for pages with missing tags.
     - llms.txt issues → queue llms.txt regenerate.
     - Keyword sync for SerpBear.

5. **Weekly plan + human review**
   - `weekly_optimizations.md` becomes your quick human‑readable “To‑Do”:
     - URLs to fix.
     - Keywords that dropped.
     - Technical issues to address.
     - Learned best practices to roll into manual edits or templates.

***

## 5. How to Extend and Market It

From a **developer** perspective:

- Add more clusters and cities in `ITEM_CATEGORIES` and `CITY_TARGETS`.
- Extend `REFERENCE_COMPETITORS` with more precise URLs.
- Add more per‑page metrics to experiments (e.g., bounce rate, conversions) if you can feed them in.

From a **digital marketer** perspective:

- Use `weekly_optimizations.md` as the basis for:
  - Campaign briefs.
  - Content update sprints.
  - Reporting to stakeholders (what changed, what worked, what didn’t).
- Treat `strategy.json` as the “SEO brain”:
  - Export winning patterns into manual content guidelines.
  - Use best schema types and city performance insights when planning new city launches.
