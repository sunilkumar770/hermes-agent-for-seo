#!/usr/bin/env python3
"""
GoRentls SEO System — Evolution Engine (self_improving_engine.py)
Tracks SEO experiments, evaluates ranking outcomes, stores strategy knowledge,
detects anomalies, and triggers self-healing repairs.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
MEMORY_DIR = SEO_DIR / "memory"

EXPERIMENTS_PATH = MEMORY_DIR / "experiments.json"
LEARNINGS_PATH = MEMORY_DIR / "learnings.json"
STRATEGY_PATH = MEMORY_DIR / "strategy.json"
ANOMALIES_PATH = MEMORY_DIR / "anomalies.json"


def log_debug(msg: str):
    sys.stderr.write(f"[DEBUG] [Evolution] {msg}\n")
    sys.stderr.flush()


def init_memory():
    """Initialize empty memory JSON structures if missing."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not EXPERIMENTS_PATH.exists():
        with open(EXPERIMENTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        log_debug(f"Created {EXPERIMENTS_PATH}")

    if not LEARNINGS_PATH.exists():
        with open(LEARNINGS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        log_debug(f"Created {LEARNINGS_PATH}")

    if not STRATEGY_PATH.exists():
        default_strategy = {
            "title_tag_patterns": {
                "best_patterns": [
                    {"pattern": "Rent {item} in {city} | GoRentls", "avg_ctr_lift": 0.0},
                    {"pattern": "Best {item} Rental {city} - GoRentls", "avg_ctr_lift": 0.0}
                ]
            },
            "content_length_optimal": 350,
            "keyword_density_target": 1.5,
            "schema_types_that_help": {
                "types": ["Product", "LocalBusiness"]
            },
            "city_pages_performance": {}
        }
        with open(STRATEGY_PATH, "w", encoding="utf-8") as f:
            json.dump(default_strategy, f, indent=2)
        log_debug(f"Created {STRATEGY_PATH}")

    if not ANOMALIES_PATH.exists():
        with open(ANOMALIES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        log_debug(f"Created {ANOMALIES_PATH}")


def load_json(path: Path) -> dict:
    if not path.exists():
        return [] if "experiments" in path.name or "learnings" in path.name or "anomalies" in path.name else {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] if "experiments" in path.name or "learnings" in path.name or "anomalies" in path.name else {}


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_experiment(experiment: dict):
    """Log a new SEO experiment."""
    init_memory()
    experiments = load_json(EXPERIMENTS_PATH)

    # Unique id
    unique_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    experiment["id"] = unique_id
    experiment["started_at"] = datetime.now().isoformat()
    experiment["status"] = "running"

    experiments.append(experiment)
    save_json(EXPERIMENTS_PATH, experiments)
    log_debug(f"Logged experiment {unique_id} for: {experiment.get('target', 'unknown')}")
    return unique_id


def evaluate_experiments(current_metrics: dict, min_days: int = 14) -> list:
    """Evaluate running experiments against new metrics."""
    init_memory()
    experiments = load_json(EXPERIMENTS_PATH)
    learnings = load_json(LEARNINGS_PATH)
    strategy = load_json(STRATEGY_PATH)

    evaluated_count = 0
    now = datetime.now()

    for exp in experiments:
        if exp.get("status") != "running":
            continue

        started_at = datetime.fromisoformat(exp.get("started_at"))
        if now - started_at < timedelta(days=min_days):
            continue  # Not enough time has passed to draw conclusions

        target_kw = exp.get("keyword", "").lower()
        if not target_kw or target_kw not in current_metrics:
            continue

        before = exp.get("before_metrics", {})
        after = current_metrics[target_kw]

        before_pos = before.get("position", 0.0)
        after_pos = after.get("position", 0.0)
        before_ctr = before.get("ctr", 0.0)
        after_ctr = after.get("ctr", 0.0)

        outcome = "neutral"
        if after_pos > 0 and before_pos > 0:
            pos_diff = before_pos - after_pos  # positive if position improved (e.g. 5 -> 3)
            ctr_diff = after_ctr - before_ctr

            if pos_diff >= 2.0 or ctr_diff >= 1.0:
                outcome = "positive"
            elif pos_diff <= -2.0 or ctr_diff <= -1.0:
                outcome = "negative"

        # Record learning
        learning = {
            "experiment_id": exp["id"],
            "keyword": target_kw,
            "change_type": exp.get("change_type", "general"),
            "before_pos": before_pos,
            "after_pos": after_pos,
            "before_ctr": before_ctr,
            "after_ctr": after_ctr,
            "outcome": outcome,
            "evaluated_at": now.isoformat()
        }
        learnings.append(learning)

        # Update strategy heuristics based on positive outcomes
        if outcome == "positive":
            pattern = exp.get("title_pattern")
            if pattern:
                patterns_list = strategy.setdefault("title_tag_patterns", {}).setdefault("best_patterns", [])
                found = False
                for p in patterns_list:
                    if p["pattern"] == pattern:
                        p["avg_ctr_lift"] = round((p["avg_ctr_lift"] + (after_ctr - before_ctr)) / 2, 2)
                        found = True
                        break
                if not found:
                    patterns_list.append({"pattern": pattern, "avg_ctr_lift": round(after_ctr - before_ctr, 2)})

        exp["status"] = "completed"
        exp["ended_at"] = now.isoformat()
        exp["outcome"] = outcome
        evaluated_count += 1

    if evaluated_count > 0:
        save_json(EXPERIMENTS_PATH, experiments)
        save_json(LEARNINGS_PATH, learnings)
        save_json(STRATEGY_PATH, strategy)
        log_debug(f"Evaluated {evaluated_count} experiment(s).")

    return learnings


def detect_anomalies(scan_data: dict) -> list:
    """Analyze scan data for severe drops, untracked targets, or scraper failures."""
    init_memory()
    anomalies = load_json(ANOMALIES_PATH)

    detected = []
    now_str = datetime.now().isoformat()

    # 1. Severe Rank Drops
    for drop in scan_data.get("drops", []):
        if drop.get("drop_amount", 0) >= 5:
            detected.append({
                "type": "severe_drop",
                "keyword": drop["keyword"],
                "details": f"Rank dropped by {drop['drop_amount']} positions (from {drop['previous_position']} to {drop['current_position']})",
                "timestamp": now_str
            })

    # 2. Scraper Mass Failure
    tracked = scan_data.get("tracked_keywords", 0)
    total = scan_data.get("total_keywords", 0)
    if total > 0 and tracked / total < 0.5:
        detected.append({
            "type": "scraper_mass_failure",
            "details": f"Only tracked {tracked}/{total} keywords. Scraper might be blocked or misconfigured.",
            "timestamp": now_str
        })

    # 3. Untracked target keywords
    untracked = scan_data.get("untracked_keywords", [])
    if untracked:
        detected.append({
            "type": "untracked_keywords",
            "details": f"Keywords missing in SerpBear: {untracked}",
            "timestamp": now_str
        })

    if detected:
        anomalies.extend(detected)
        save_json(ANOMALIES_PATH, anomalies)
        log_debug(f"Detected {len(detected)} anomaly/anomalies.")

    return detected


def self_heal(scan_data: dict, audit_data: dict = None) -> list:
    """Propose self-healing actions based on anomalies and audit data."""
    actions = []

    # 1. Check for untracked keywords to insert into SerpBear
    untracked = scan_data.get("untracked_keywords", [])
    if untracked:
        actions.append({
            "agent": "Publisher",
            "action": "sync_keywords_serpbear",
            "details": f"Need to insert target keywords: {untracked}"
        })

    # 2. Check for missing metadata in audit results
    if audit_data and audit_data.get("results"):
        for res in audit_data["results"]:
            issues = res.get("issues", [])
            for issue in issues:
                if "Missing <title>" in issue or "Missing <meta name=\"description\">" in issue:
                    actions.append({
                        "agent": "Publisher",
                        "action": "fix_metadata",
                        "target_url": res["url"],
                        "details": f"Auto-heal metadata for: {res['url']}"
                    })

    # 3. Check for llms.txt failure
    if audit_data and audit_data.get("llms_txt", {}).get("issues"):
        actions.append({
            "agent": "Publisher",
            "action": "regenerate_llmstxt",
            "details": f"llms.txt issue: {audit_data['llms_txt']['issues']}"
        })

    return actions


def run_evolution_cycle(scan_data: dict, audit_data: dict = None) -> dict:
    """Run a complete Evolution cycle."""
    init_memory()

    # Convert GSC or scan rankings to dictionary format
    current_metrics = {}
    for drop in scan_data.get("drops", []):
        current_metrics[drop["keyword"].lower()] = {
            "position": drop["current_position"],
            "ctr": 0.0  # Or extract from GSC if available
        }

    # Evaluate any pending experiments
    evaluate_experiments(current_metrics, min_days=0)  # Using 0 for testing/immediate evaluation

    # Run anomaly detection
    anomalies = detect_anomalies(scan_data)

    # Run self healing actions
    healing_actions = self_heal(scan_data, audit_data)

    strategy = load_json(STRATEGY_PATH)
    learnings = load_json(LEARNINGS_PATH)

    return {
        "status": "success",
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
        "healing_actions": healing_actions,
        "learnings_count": len(learnings),
        "best_title_patterns": strategy.get("title_tag_patterns", {}).get("best_patterns", [])
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoRentls SEO Evolution Engine CLI")
    parser.add_argument("--init", action="store_true", help="Initialize strategy and memory files")
    parser.add_argument("--status", action="store_true", help="Display memory and experiments status")
    parser.add_argument("--strategy", action="store_true", help="Print current strategy findings")
    parser.add_argument("--learnings", action="store_true", help="Print accumulated learnings")
    args = parser.parse_args()

    if args.init:
        init_memory()
        print("SEO Memory successfully initialized.")
        sys.exit(0)

    if args.status:
        init_memory()
        experiments = load_json(EXPERIMENTS_PATH)
        learnings = load_json(LEARNINGS_PATH)
        anomalies = load_json(ANOMALIES_PATH)
        print(f"--- SEO System Memory Status ---")
        print(f"Total Experiments logged: {len(experiments)}")
        print(f"Running Experiments: {len([e for e in experiments if e.get('status') == 'running'])}")
        print(f"Accumulated learnings: {len(learnings)}")
        print(f"Total anomalies flagged: {len(anomalies)}")
        sys.exit(0)

    if args.strategy:
        init_memory()
        strategy = load_json(STRATEGY_PATH)
        print(json.dumps(strategy, indent=2))
        sys.exit(0)

    if args.learnings:
        init_memory()
        learnings = load_json(LEARNINGS_PATH)
        print(json.dumps(learnings, indent=2))
        sys.exit(0)

    # Dry run
    dry_run_scan = {"drops": [], "tracked_keywords": 0, "total_keywords": 0, "untracked_keywords": []}
    res = run_evolution_cycle(dry_run_scan)
    print(json.dumps(res, indent=2))
