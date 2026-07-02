#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
PIPELINE_SCRIPT = SCRIPT_DIR / "seo_pipeline.py"
CRAWLER_SCRIPT = SCRIPT_DIR / "crawl_competitors.py"
COORDINATOR_LOG = SEO_DIR / "reports" / "coordinator_log.md"
OPTIMIZATIONS_PATH = SEO_DIR / "drafts" / "weekly_optimizations.md"

def log_to_coordinator(message):
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    sys.stderr.write(log_line)
    
    # Append to coordinator_log.md
    COORDINATOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not COORDINATOR_LOG.exists():
            with open(COORDINATOR_LOG, "w", encoding="utf-8") as f:
                f.write("# GoRentls SEO Coordinator Logs\n\n")
        with open(COORDINATOR_LOG, "a", encoding="utf-8") as f:
            f.write(f"- {log_line}")
    except Exception as e:
        sys.stderr.write(f"Failed to write to coordinator log: {e}\n")

def push_to_git():
    log_to_coordinator("Checking for Git changes under seo/ directory...")
    status_res = subprocess.run(["git", "status", "--porcelain", "seo/"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
    if status_res.returncode == 0 and status_res.stdout.strip():
        log_to_coordinator("Git changes detected. Committing and pushing to GitHub...")
        subprocess.run(["git", "add", "seo/"], cwd=str(WORKSPACE_DIR))
        subprocess.run(["git", "commit", "-m", "chore(seo): auto-update daily rankings and crawl data"], cwd=str(WORKSPACE_DIR))
        push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
        if push_res.returncode == 0:
            log_to_coordinator("Successfully pushed changes to GitHub!")
        else:
            log_to_coordinator(f"Git push failed: {push_res.stderr.strip()}")
    else:
        log_to_coordinator("No changes in seo/ directory to push.")

def run_scan():
    log_to_coordinator("Running daily rank scan...")
    res = subprocess.run([sys.executable, str(PIPELINE_SCRIPT)], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
    
    # Parse the output
    stdout = res.stdout.strip()
    stderr = res.stderr.strip()
    
    if stderr:
        sys.stderr.write(f"Pipeline Stderr:\n{stderr}\n")
        
    try:
        data = json.loads(stdout)
    except Exception as e:
        log_to_coordinator(f"Failed to parse JSON from pipeline stdout. Error: {e}. Raw stdout: {stdout}")
        return {"status": "error", "error": f"JSON parse error: {e}"}, res.returncode
        
    log_to_coordinator(f"Scan finished. Status: {data.get('status')}. Total keywords: {data.get('total_keywords')}. Drops: {data.get('drops_count')}")
    return data, res.returncode

def run_crawl(drops_data):
    log_to_coordinator(f"Triggering competitor crawler for {len(drops_data)} dropped keywords...")
    res = subprocess.run(
        [sys.executable, str(CRAWLER_SCRIPT)],
        input=json.dumps(drops_data),
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_DIR)
    )
    
    stdout = res.stdout.strip()
    stderr = res.stderr.strip()
    
    if stderr:
        sys.stderr.write(f"Crawler Stderr:\n{stderr}\n")
        
    try:
        data = json.loads(stdout)
        log_to_coordinator(f"Crawler finished. Status: {data.get('status')}. Crawled URLs: {len(data.get('crawled_urls', []))}")
        return data
    except Exception as e:
        log_to_coordinator(f"Failed to parse JSON from crawler stdout. Error: {e}. Raw stdout: {stdout}")
        return {"status": "error", "error": f"JSON parse error: {e}"}

def generate_optimizations(scan_data):
    log_to_coordinator("Generating weekly optimizations draft...")
    OPTIMIZATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Format the drops table
    drops_list = scan_data.get("drops", [])
    drops_rows = ""
    for d in drops_list:
        drops_rows += f"| `/cars` | {d['keyword']} | {d['previous_position']} -> {d['current_position']} | -{d['drop_amount']} | ⚠️ **Rank Dropped** |\n"
        
    if not drops_rows:
        drops_rows = "| None | None | None | None | ✅ **No drops detected** |\n"

    template = f"""# Weekly SEO Optimizations — GoRentls
*Generated: {today_str} | Based on daily rank scan and competitor crawls*

---

## 🎯 Priority URLs with Ranking/CTR Decline

| URL | Primary Keywords | SerpBear Rank Change | Drop | Status |
|-----|------------------|----------------------|------|--------|
{drops_rows}

---

## 1. https://gorentls.com/cars
**Cluster:** Cars | **Intent:** Transactional + Local
* **Meta Title Draft:** `Local Car Rentals Near You – Self-Drive & P2P | GoRentls`
* **Meta Description Draft:** `Book local car rentals in minutes. Self-drive & peer-to-peer options from verified local hosts. No hidden fees. Compare & reserve now.`
* **Content Recommendations:**
  1. Add above-the-fold location search widget.
  2. Implement FAQ schema regarding security deposits and driver license requirements.

## 2. https://gorentls.com/bikes
**Cluster:** Bikes | **Intent:** Transactional + Local
* **Meta Title Draft:** `Local Bike & Scooter Rentals Near You — Hourly & Daily | GoRentls`
* **Meta Description Draft:** `Rent bikes & scooters by the hour or day. Verified local hosts, instant booking, and zero membership deposit. Find a ride near you.`

## 3. https://gorentls.com/cameras
**Cluster:** Cameras | **Intent:** Transactional + Informational
* **Meta Title Draft:** `Rent Professional Cameras & Lenses — Canon, Sony, Nikon | GoRentls`
* **Meta Description Draft:** `Rent cinema cameras, mirrorless bodies, and lenses from verified local creators. Doorstep delivery and damage protection included.`

---

## 📋 Implementation Checklist

- [ ] Deploy updated Meta Titles and Descriptions to page metadata.
- [ ] Add FAQPage schema to `/cars` and `/bikes` routes.
- [ ] Verify pages build and compile successfully with `npm run build`.
- [ ] Commit metadata updates to main branch.
"""
    try:
        with open(OPTIMIZATIONS_PATH, "w", encoding="utf-8") as f:
            f.write(template)
        log_to_coordinator(f"Optimizations draft successfully written to {OPTIMIZATIONS_PATH}")
    except Exception as e:
        log_to_coordinator(f"Failed to generate optimizations: {e}")

def main():
    parser = argparse.ArgumentParser(description="GoRentls SEO Coordinator Orchestrator")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--full", action="store_true", help="Run full scan, crawl, and optimization draft")
    group.add_argument("--scan-only", action="store_true", help="Run daily rank scan only")
    group.add_argument("--crawl-only", action="store_true", help="Run competitor crawler only")
    
    args = parser.parse_args()
    
    # Default to --full if no argument provided
    if not (args.full or args.scan_only or args.crawl_only):
        args.full = True
        
    log_to_coordinator("=== Starting SEO Coordinator Run ===")
    
    if args.scan_only:
        run_scan()
        push_to_git()
        
    elif args.crawl_only:
        # Expect drops JSON from stdin
        if not sys.stdin.isatty():
            try:
                drops_data = json.loads(sys.stdin.read().strip())
                run_crawl(drops_data)
                push_to_git()
            except Exception as e:
                log_to_coordinator(f"Failed to parse stdin drops JSON: {e}")
                sys.exit(1)
        else:
            log_to_coordinator("Error: --crawl-only requires drops JSON on stdin.")
            sys.exit(1)
            
    elif args.full:
        scan_data, code = run_scan()
        if code == 2:
            log_to_coordinator("Rank drops detected. Initiating competitor crawling stage...")
            run_crawl(scan_data.get("drops", []))
            generate_optimizations(scan_data)
        else:
            log_to_coordinator("Rank scan completed. No drops detected. Skipping competitor crawler.")
            generate_optimizations(scan_data)
            
        push_to_git()
        
    log_to_coordinator("=== SEO Coordinator Run Complete ===")

if __name__ == "__main__":
    main()
