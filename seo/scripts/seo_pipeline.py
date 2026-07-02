#!/usr/bin/env python3
"""
GoRentls SEO Pipeline — Rank Scanner
FIXES: Removes all simulated/fake data. Reports real positions only.
Exit codes: 0 = success/stable, 2 = drops detected, 1 = error.
"""
import os
import sys
import csv
import json
import requests
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
TARGET_KEYWORDS_PATH = SEO_DIR / "target_keywords.md"
GSC_CSV_PATH = SEO_DIR / "data" / "gsc_queries.csv"
REPORT_PATH = SEO_DIR / "reports" / "ranking_log.md"

# Load .env
for env_file in [SCRIPT_DIR / ".env", SEO_DIR / ".env", WORKSPACE_DIR / ".env"]:
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

SERPBEAR_BASE = os.environ.get("SERPBEAR_URL", os.environ.get("SERPBEAR_BASE", "http://localhost:3000"))
SERPBEAR_API_KEY = os.environ.get("SERPBEAR_API_KEY", "")
GORP_DOMAIN = os.environ.get("GORP_DOMAIN", "gorentls.com")
RANK_DROP_THRESHOLD = int(os.environ.get("RANK_DROP_THRESHOLD", "2"))


def log_debug(msg):
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()


def parse_target_keywords():
    keywords_info = {}
    if not TARGET_KEYWORDS_PATH.exists():
        log_debug(f"Warning: {TARGET_KEYWORDS_PATH} does not exist.")
        return keywords_info
    with open(TARGET_KEYWORDS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or "Keyword" in line or "---" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                keyword, cluster, url = parts[0], parts[1], parts[2]
                keywords_info[keyword.lower()] = {
                    "keyword": keyword,
                    "cluster": cluster,
                    "url": url
                }
    return keywords_info


def load_gsc_data():
    gsc_data = {}
    if not GSC_CSV_PATH.exists():
        log_debug(f"Warning: {GSC_CSV_PATH} does not exist. GSC data will be empty.")
        return gsc_data
    with open(GSC_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row.get("Query", row.get("query", "")).strip().lower()
            if not query:
                continue
            ctr_str = row.get("CTR", "0").replace("%", "").strip()
            try:
                ctr = float(ctr_str)
            except ValueError:
                ctr = 0.0
            gsc_data[query] = {
                "clicks": int(row.get("Clicks", row.get("clicks", 0)) or 0),
                "impressions": int(row.get("Impressions", row.get("impressions", 0)) or 0),
                "ctr": ctr,
                "position": float(row.get("Position", row.get("position", 0.0)) or 0.0)
            }
    return gsc_data


def fetch_serpbear_rankings(target_keywords):
    """
    Fetches keyword rankings from SerpBear API.
    FIX: No more simulated/fake data. If SerpBear is unavailable, returns empty dict
    and keywords are reported as 'not tracked'.
    FIX: No more position=0 -> 5 fallback. Position 0 means scraper hasn't run.
    """
    rankings = {}

    if not SERPBEAR_API_KEY:
        log_debug("ERROR: SERPBEAR_API_KEY not set. Cannot fetch real rankings.")
        print(json.dumps({
            "status": "error",
            "error": "SERPBEAR_API_KEY not set. Configure in .env file."
        }))
        sys.exit(1)

    headers = {"Authorization": f"Bearer {SERPBEAR_API_KEY}"}

    try:
        # Step 1: Resolve exact domain from SerpBear
        resp = requests.get(f"{SERPBEAR_BASE}/api/domains", headers=headers, timeout=10)
        resp.raise_for_status()
        domains_data = resp.json()
        if isinstance(domains_data, dict):
            domains_list = domains_data.get("domains", [])
        else:
            domains_list = domains_data

        gorentls_domain = None
        for d in domains_list:
            domain_val = d.get("domain", "")
            domain_root = domain_val.lower().replace("www.", "")
            target_root = GORP_DOMAIN.lower().replace("www.", "")
            if domain_root == target_root:
                gorentls_domain = d
                break

        if not gorentls_domain:
            log_debug(f"ERROR: Domain '{GORP_DOMAIN}' not found in SerpBear.")
            print(json.dumps({
                "status": "error",
                "error": f"Domain '{GORP_DOMAIN}' not registered in SerpBear."
            }))
            sys.exit(1)

        actual_domain = gorentls_domain.get("domain", GORP_DOMAIN)
        log_debug(f"Resolved domain to: {actual_domain}")

        # Step 2: Fetch keywords for exact domain
        kw_resp = requests.get(
            f"{SERPBEAR_BASE}/api/keywords",
            params={"domain": actual_domain},
            headers=headers,
            timeout=15
        )
        kw_resp.raise_for_status()
        keywords_data = kw_resp.json()
        if isinstance(keywords_data, dict):
            keywords_list = keywords_data.get("keywords", [])
        else:
            keywords_list = keywords_data

        if not keywords_list:
            log_debug("ERROR: No keywords found in SerpBear for this domain.")
            log_debug("Run insert_target_keywords.py to sync target keywords to SerpBear DB.")
            print(json.dumps({
                "status": "error",
                "error": "No keywords found in SerpBear. Run insert_target_keywords.py first."
            }))
            sys.exit(1)

        # Step 3: Fetch each keyword's details (position + history)
        scraper_failures = 0
        for kw in keywords_list:
            if not isinstance(kw, dict):
                continue
            name = kw.get("keyword", "").lower()
            kw_id = kw.get("ID")
            if not kw_id:
                continue

            try:
                detail_resp = requests.get(
                    f"{SERPBEAR_BASE}/api/keyword",
                    params={"id": kw_id},
                    headers=headers,
                    timeout=10
                )
                detail_resp.raise_for_status()
                details = detail_resp.json()
                if isinstance(details, dict):
                    details = details.get("keyword", details)

                position = details.get("position", 0)
                history = details.get("history", {})

                # Determine previous position from history
                last_position = position
                if isinstance(history, dict) and len(history) >= 2:
                    sorted_keys = []
                    for k in history.keys():
                        try:
                            parts = [int(p) for p in k.split("-")]
                            if len(parts) == 3:
                                sorted_keys.append((datetime(parts[0], parts[1], parts[2]), k))
                        except Exception:
                            pass
                    sorted_keys.sort()
                    if len(sorted_keys) >= 2:
                        prev_key = sorted_keys[-2][1]
                        last_position = history.get(prev_key, position)

                # FIX: Report position 0 as scraper failure, NOT default to 5
                if position == 0:
                    scraper_failures += 1
                    log_debug(f"WARNING: Keyword '{name}' has position=0 (scraper not configured or failed).")

                rankings[name] = {
                    "position": position,
                    "last_position": last_position if last_position > 0 else position
                }

            except Exception as e:
                log_debug(f"Error fetching details for keyword ID {kw_id}: {e}")
                rankings[name] = {
                    "position": kw.get("position", 0),
                    "last_position": kw.get("position", 0)
                }

        if scraper_failures > 0:
            log_debug(f"WARNING: {scraper_failures} keyword(s) have position=0.")
            log_debug("Configure Serply/SerpApi in SerpBear -> Settings -> Scraper to get real positions.")

        # Report keywords not tracked in SerpBear (but in target_keywords.md)
        untracked = [kw for kw in target_keywords if kw not in rankings]
        if untracked:
            log_debug(f"WARNING: {len(untracked)} target keyword(s) not found in SerpBear: {untracked}")
            log_debug("Run insert_target_keywords.py to add them.")

        return rankings

    except requests.exceptions.ConnectionError:
        log_debug(f"ERROR: Cannot connect to SerpBear at {SERPBEAR_BASE}.")
        print(json.dumps({
            "status": "error",
            "error": f"Cannot connect to SerpBear at {SERPBEAR_BASE}. Is it running?"
        }))
        sys.exit(1)
    except Exception as e:
        log_debug(f"ERROR: SerpBear API failure: {e}")
        print(json.dumps({
            "status": "error",
            "error": f"SerpBear API error: {e}"
        }))
        sys.exit(1)


def reconcile_and_log():
    log_debug(f"Starting Rank Scan at {datetime.now().isoformat()}")

    targets = parse_target_keywords()
    if not targets:
        print(json.dumps({"status": "error", "error": "No target keywords found in target_keywords.md"}))
        sys.exit(1)

    gsc_data = load_gsc_data()
    serp_rankings = fetch_serpbear_rankings(targets.keys())

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = []
    report_lines.append(f"\n## Scan Date: {today_str}\n")
    report_lines.append("| Cluster | Keyword | SerpBear Pos | Prev Pos | GSC Avg Pos | Clicks | Impressions | CTR | Note |")
    report_lines.append("|---------|---------|--------------|----------|-------------|--------|-------------|-----|------|")

    notable_drops = []
    untracked_keywords = []

    for kw_key, info in targets.items():
        keyword = info["keyword"]
        cluster = info["cluster"]

        if kw_key not in serp_rankings:
            # Keyword not tracked in SerpBear
            report_lines.append(f"| {cluster} | {keyword} | — | — | — | — | — | — | ❌ Not tracked in SerpBear |")
            untracked_keywords.append(keyword)
            continue

        serp = serp_rankings[kw_key]
        pos = serp["position"]
        prev_pos = serp["last_position"]

        gsc = gsc_data.get(kw_key, {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0})
        clicks = gsc["clicks"]
        impr = gsc["impressions"]
        ctr = gsc["ctr"]
        gsc_pos = gsc["position"]

        note = "Stable"
        if pos == 0:
            note = "❌ Scraper failed (position=0)"
        else:
            pos_change = pos - prev_pos
            if pos_change >= RANK_DROP_THRESHOLD:
                note = f"⚠️ Dropped {pos_change} positions"
                notable_drops.append({
                    "keyword": keyword,
                    "cluster": cluster,
                    "url": info.get("url", ""),
                    "previous_position": prev_pos,
                    "current_position": pos,
                    "drop_amount": pos_change
                })
            elif pos_change <= -2:
                note = f"🎉 Improved {abs(pos_change)} positions"
            elif ctr > 0 and ctr < 3.0 and pos <= 5:
                note = "⚠️ Low CTR for Top 5 rank"

        report_lines.append(f"| {cluster} | {keyword} | {pos} | {prev_pos} | {gsc_pos:.1f} | {clicks} | {impr} | {ctr:.1f}% | {note} |")

    # Write report
    report_content = "\n".join(report_lines) + "\n"
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if REPORT_PATH.exists():
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(report_content)
        else:
            header = "# GoRentls SEO Rankings Log\n\nThis file logs daily rankings reconciled with Google Search Console data.\n"
            with open(REPORT_PATH, "w", encoding="utf-8") as f:
                f.write(header + report_content)
        log_debug(f"Ranking log updated at {REPORT_PATH}")
    except Exception as e:
        log_debug(f"Failed to write ranking log: {e}")

    output_data = {
        "status": "drops_detected" if notable_drops else "stable",
        "domain": GORP_DOMAIN,
        "total_keywords": len(targets),
        "tracked_keywords": len(serp_rankings),
        "untracked_keywords": untracked_keywords,
        "drops_count": len(notable_drops),
        "drops": notable_drops,
        "scanned_at": datetime.now().isoformat()
    }

    print(json.dumps(output_data))
    sys.exit(2 if notable_drops else 0)


if __name__ == "__main__":
    reconcile_and_log()
