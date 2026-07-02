#!/usr/bin/env python3
"""
GoRentls SEO System — Orchestrator (seo_coordinator.py)
Orchestrates the Scout (rank scanner), Crawler (competitor watcher),
Inspector (technical auditor), Publisher (programmatic SEO), and
Evolution Engine (self-improver) agents in a unified workflow.
"""
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
AUDITOR_SCRIPT = SCRIPT_DIR / "technical_auditor.py"
PSEO_SCRIPT = SCRIPT_DIR / "pseo_generator.py"
EVOLUTION_SCRIPT = SCRIPT_DIR / "self_improving_engine.py"

COORDINATOR_LOG = SEO_DIR / "reports" / "coordinator_log.md"
OPTIMIZATIONS_PATH = SEO_DIR / "drafts" / "weekly_optimizations.md"


def log_to_coordinator(message: str):
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    sys.stderr.write(log_line)
    sys.stderr.flush()

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


def _run_subprocess_json(script_path: Path, args: list = None, stdin_data: str = None, timeout: int = 120) -> tuple:
    """Run a Python script and parse the last line of stdout as a JSON object."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        res = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_DIR),
            timeout=timeout
        )
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        if stderr:
            sys.stderr.write(f"[{script_path.name} Stderr]:\n{stderr}\n")
            sys.stderr.flush()

        if not stdout:
            return {"status": "error", "error": "Empty stdout"}, res.returncode

        # Attempt to parse JSON block from stdout
        if "{" in stdout and "}" in stdout:
            try:
                start = stdout.find("{")
                end = stdout.rfind("}") + 1
                parsed = json.loads(stdout[start:end])
                return parsed, res.returncode
            except json.JSONDecodeError as e:
                log_to_coordinator(f"Failed to parse JSON block from {script_path.name}. Error: {e}. Output:\n{stdout}")
                return {"status": "error", "error": "JSON parse error", "raw_stdout": stdout}, res.returncode
        else:
            log_to_coordinator(f"No JSON block found in {script_path.name} output. Output:\n{stdout}")
            return {"status": "error", "error": "No JSON block found", "raw_stdout": stdout}, res.returncode

    except subprocess.TimeoutExpired:
        log_to_coordinator(f"Script {script_path.name} timed out after {timeout} seconds.")
        return {"status": "error", "error": "Timeout"}, -1
    except Exception as e:
        log_to_coordinator(f"Exception running script {script_path.name}: {e}")
        return {"status": "error", "error": str(e)}, -1


def run_scan() -> tuple:
    log_to_coordinator("Running daily rank scan...")
    data, code = _run_subprocess_json(PIPELINE_SCRIPT)
    if code in (0, 2) and data.get("status") != "error":
        log_to_coordinator(f"Scan finished. Status: {data.get('status')}. Total keywords: {data.get('total_keywords')}. Tracked: {data.get('tracked_keywords')}. Drops: {data.get('drops_count')}")
    else:
        log_to_coordinator(f"Scan failed: {data.get('error', 'unknown error')}")
    return data, code


def run_crawl(drops_data: list) -> dict:
    log_to_coordinator(f"Triggering competitor crawler for {len(drops_data)} dropped keywords...")
    data, code = _run_subprocess_json(CRAWLER_SCRIPT, stdin_data=json.dumps(drops_data))
    if code == 0 and data.get("status") != "error":
        log_to_coordinator(f"Crawler finished. Status: {data.get('status')}. Crawled URLs: {len(data.get('crawled_urls', []))}")
    else:
        log_to_coordinator(f"Crawler failed: {data.get('error', 'unknown error')}")
    return data


def run_audit() -> dict:
    log_to_coordinator("Running technical audit...")
    data, code = _run_subprocess_json(AUDITOR_SCRIPT)
    if code == 0 and data.get("status") != "error":
        log_to_coordinator(f"Audit finished. Has issues: {data.get('has_issues')}. Pages audited: {data.get('pages_audited')}")
    else:
        log_to_coordinator(f"Audit failed: {data.get('error', 'unknown error')}")
    return data


def run_pseo(max_pages: int = 5) -> dict:
    log_to_coordinator(f"Triggering programmatic SEO page generation (limit: {max_pages} pages)...")
    data, code = _run_subprocess_json(PSEO_SCRIPT, args=["--max-pages", str(max_pages)])
    if code == 0 and data.get("status") != "error":
        log_to_coordinator(f"Publisher finished. Pages generated: {data.get('pages_generated')}. Coverage: {data.get('coverage_pct')}%")
    else:
        log_to_coordinator(f"Publisher failed: {data.get('error', 'unknown error')}")
    return data


def run_evolution(scan_data: dict, audit_data: dict = None) -> dict:
    log_to_coordinator("Running self-improving evolution cycle...")
    # Prepare inputs for Evolution Engine
    # Run the cycle by executing the script in evolution mode
    # We can pass scan_data and audit_data via stdin to evolution engine
    input_data = {
        "scan_data": scan_data,
        "audit_data": audit_data
    }
    data, code = _run_subprocess_json(EVOLUTION_SCRIPT, stdin_data=json.dumps(input_data))
    if code == 0 and data.get("status") != "error":
        log_to_coordinator(f"Evolution cycle complete. Anomalies: {data.get('anomalies_count')}. Healing actions queued: {len(data.get('healing_actions', []))}")
    else:
        log_to_coordinator(f"Evolution failed: {data.get('error', 'unknown error')}")
    return data


def generate_optimizations(scan_data: dict, audit_data: dict = None, evolution_data: dict = None):
    log_to_coordinator("Generating weekly plan and optimizations draft...")
    OPTIMIZATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Format the drops table
    drops_list = scan_data.get("drops", [])
    drops_rows = ""
    for d in drops_list:
        drops_rows += f"| `{d.get('url', '/cars')}` | {d['keyword']} | {d['previous_position']} -> {d['current_position']} | -{d['drop_amount']} | ⚠️ **Rank Dropped** |\n"

    if not drops_rows:
        drops_rows = "| None | None | None | None | ✅ **No drops detected** |\n"

    # Technical audit warnings
    audit_rows = ""
    if audit_data and audit_data.get("results"):
        for res in audit_data["results"]:
            if res.get("issues") or res.get("warnings"):
                issues_combined = ", ".join(res.get("issues", []) + res.get("warnings", []))
                audit_rows += f"| `{res['path']}` | {res['word_count']} | {'✅ Yes' if res['has_schema'] else '❌ No'} | {issues_combined[:100]}... |\n"

    if not audit_rows:
        audit_rows = "| None | — | — | ✅ **No critical technical audits flagged** |\n"

    # Strategy / learnings summary
    strategy_summary = "No strategy updates yet."
    if evolution_data:
        patterns = evolution_data.get("best_title_patterns", [])
        if patterns:
            strategy_summary = "### Proven High-CTR Title Patterns:\n"
            for idx, p in enumerate(patterns[:3], 1):
                strategy_summary += f"{idx}. `{p['pattern']}` (Estimated CTR Lift: +{p.get('avg_ctr_lift', 0.0)}%)\n"

        healing_actions = evolution_data.get("healing_actions", [])
        if healing_actions:
            strategy_summary += "\n### Queued Auto-Healing Actions:\n"
            for act in healing_actions:
                strategy_summary += f"- **[{act['agent']}]** {act['action']}: {act.get('details', '')}\n"

    template = f"""# Weekly SEO Optimizations & Playbook — GoRentls
*Generated: {today_str} | Orchestrated Multi-Agent SEO Pipeline*

---

## 🎯 Priority URLs with Ranking Decline
| URL | Primary Keywords | SerpBear Rank Change | Drop | Status |
|-----|------------------|----------------------|------|--------|
{drops_rows}

---

## 📋 Technical Audit Issues
| Page Path | Word Count | Schema Structured Data | Issues & Warnings |
|-----------|------------|------------------------|-------------------|
{audit_rows}

---

## 🧠 Self-Improving Strategy & AI Insights
{strategy_summary}

---

## 🛠️ Execution Checklist
- [ ] Review priority URLs and compare with crawled competitor markdown in `seo/competitors/`.
- [ ] Address meta descriptions or thin content warnings on flagged routes.
- [ ] Deploy generated programmatic city pages inside `seo/drafts/pseo_pages/`.
- [ ] Deploy new `seo/drafts/llms.txt` to production root to improve AI agent discoverability.
- [ ] Run `git add` and push modifications to production branch.
"""

    try:
        with open(OPTIMIZATIONS_PATH, "w", encoding="utf-8") as f:
            f.write(template)
        log_to_coordinator(f"Optimizations draft successfully written to {OPTIMIZATIONS_PATH}")
    except Exception as e:
        log_to_coordinator(f"Failed to generate optimizations: {e}")


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


def main():
    parser = argparse.ArgumentParser(description="GoRentls SEO System Coordinator")
    parser.add_argument("--full", action="store_true", help="Run full scan, crawl, audit, pseo, and evolution cycle")
    parser.add_argument("--no-push", action="store_true", help="Do not commit or push to git after completion")
    parser.add_argument("--scan-only", action="store_true", help="Run daily rank scan only")
    parser.add_argument("--audit-only", action="store_true", help="Run technical auditor only")
    parser.add_argument("--pseo-only", action="store_true", help="Run programmatic SEO generator only")
    parser.add_argument("--max-pseo-pages", type=int, default=5, help="Max pages for pSEO generator run")
    parser.add_argument("--evolution-only", action="store_true", help="Run self-improving engine cycle only")
    parser.add_argument("--crawl-only", action="store_true", help="Run competitor crawler only (reads drops from stdin)")

    args = parser.parse_args()

    # Default to --full if no action flags provided
    if not (args.scan_only or args.audit_only or args.pseo_only or args.evolution_only or args.crawl_only):
        args.full = True

    log_to_coordinator("=== Starting SEO Coordinator Run ===")

    if args.scan_only:
        run_scan()

    elif args.crawl_only:
        if not sys.stdin.isatty():
            try:
                drops_data = json.loads(sys.stdin.read().strip())
                run_crawl(drops_data)
            except Exception as e:
                log_to_coordinator(f"Failed to parse stdin drops JSON: {e}")
                sys.exit(1)
        else:
            log_to_coordinator("Error: --crawl-only requires drops JSON on stdin.")
            sys.exit(1)

    elif args.audit_only:
        run_audit()

    elif args.pseo_only:
        run_pseo(max_pages=args.max_pseo_pages)

    elif args.evolution_only:
        # Dry run cycle with empty scan data
        run_evolution({"drops": [], "tracked_keywords": 0, "total_keywords": 0, "untracked_keywords": []})

    elif args.full:
        # 1. Scout Rank Scan
        scan_data, code = run_scan()

        # 2. Competitor Crawler (if drops detected)
        crawl_data = None
        if code == 2:
            log_to_coordinator("Rank drops detected. Initiating competitor crawling stage...")
            crawl_data = run_crawl(scan_data.get("drops", []))
        else:
            log_to_coordinator("Rank scan completed. No drops detected. Skipping competitor crawler.")

        # 3. Technical Audit
        audit_data = run_audit()

        # 4. Programmatic SEO Generation
        pseo_data = run_pseo(max_pages=args.max_pseo_pages)

        # 5. Run Self-Improving Engine Cycle
        evolution_data = run_evolution(scan_data, audit_data)

        # 6. Generate Weekly Checklist & Optimizations report
        generate_optimizations(scan_data, audit_data, evolution_data)

    if not args.no_push:
        push_to_git()

    log_to_coordinator("=== SEO Coordinator Run Complete ===")


if __name__ == "__main__":
    main()
