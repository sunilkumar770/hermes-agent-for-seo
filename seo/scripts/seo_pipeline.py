#!/usr/bin/env python3
"""
GoRentls SEO Pipeline — Rank Scanner
FIXES: Removes all simulated/fake data. Reports real positions only.
Exit codes: 0 = success/stable, 2 = drops detected, 1 = error.
"""
import sys
import csv
import json
import requests
from datetime import datetime
from pathlib import Path

from config import CONFIG, log_debug

TARGET_KEYWORDS_PATH = CONFIG["SEO_DIR"] / "target_keywords.md" if "SEO_DIR" in CONFIG else Path(__file__).resolve().parent.parent.parent / "seo" / "target_keywords.md"
GSC_CSV_PATH = CONFIG["SEO_DIR"] / "data" / "gsc_queries.csv" if "SEO_DIR" in CONFIG else Path(__file__).resolve().parent.parent.parent / "seo" / "data" / "gsc_queries.csv"
REPORT_PATH = CONFIG["SEO_DIR"] / "reports" / "ranking_log.md" if "SEO_DIR" in CONFIG else Path(__file__).resolve().parent.parent.parent / "seo" / "reports" / "ranking_log.md"

# Re-derive paths properly
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
TARGET_KEYWORDS_PATH = SEO_DIR / "target_keywords.md"
GSC_CSV_PATH = SEO_DIR / "data" / "gsc_queries.csv"
REPORT_PATH = SEO_DIR / "reports" / "ranking_log.md"

SERPBEAR_BASE = CONFIG["SERPBEAR_BASE"]
SERPBEAR_API_KEY = CONFIG["SERPBEAR_API_KEY"]
GORP_DOMAIN = CONFIG["GORP_DOMAIN"]
RANK_DROP_THRESHOLD = CONFIG["RANK_DROP_THRESHOLD"]


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


def fetch_gsc_api_data(target_keywords):
    """Fetch live GSC data via Search Console API (service account)."""
    service_account_path = CONFIG.get("GSC_SERVICE_ACCOUNT")
    property_uri = CONFIG.get("GSC_PROPERTY", "sc-domain:gorentls.com")
    
    if not service_account_path or not Path(service_account_path).exists():
        log_debug("GSC Service Account not configured. Skipping API fetch.")
        return {}
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=credentials)
        
        # Get last 28 days of data
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=28)
        
        request = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query"],
            "rowLimit": 1000
        }
        
        response = service.searchanalytics().query(siteUrl=property_uri, body=request).execute()
        
        gsc_data = {}
        for row in response.get("rows", []):
            query = row["keys"][0].lower()
            gsc_data[query] = {
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1)
            }
        
        log_debug(f"Fetched {len(gsc_data)} queries from GSC API")
        return gsc_data
        
    except Exception as e:
        log_debug(f"GSC API fetch failed: {e}")
        return {}


def fetch_serpbear_rankings(target_keywords):
    """
    Fetches keyword rankings from SerpBear API.
    FIX: No more simulated/fake data. If SerpBear is unavailable, returns empty dict
    and keywords are reported as 'not tracked'.
    FIX: No more position=0 -> 5 fallback. Position 0 means scraper hasn't run.
    ENHANCEMENT: Falls back gracefully to GSC data when SerpBear unavailable.
    """
    rankings = {}

    if not SERPBEAR_API_KEY:
        log_debug("WARNING: SERPBEAR_API_KEY not set. Will use GSC positions as fallback.")
        return {}  # Return empty, caller will use GSC fallback

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
            log_debug(f"WARNING: Domain '{GORP_DOMAIN}' not found in SerpBear. Will use GSC fallback.")
            return {}

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
            log_debug("WARNING: No keywords found in SerpBear for this domain. Will use GSC fallback.")
            return {}

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
        log_debug(f"WARNING: Cannot connect to SerpBear at {SERPBEAR_BASE}. Will use GSC positions as fallback.")
        return {}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            log_debug(f"WARNING: SerpBear API key invalid (401). Will use GSC positions as fallback.")
        else:
            log_debug(f"WARNING: SerpBear HTTP error {e.response.status_code}. Will use GSC positions as fallback.")
        return {}
    except Exception as e:
        log_debug(f"WARNING: SerpBear API failure: {e}. Will use GSC positions as fallback.")
        return {}


def reconcile_and_log():
    log_debug(f"Starting Rank Scan at {datetime.now().isoformat()}")

    targets = parse_target_keywords()
    if not targets:
        print(json.dumps({"status": "error", "error": "No target keywords found in target_keywords.md"}))
        sys.exit(1)

    # Load CSV first, then try API to override/augment
    gsc_data = load_gsc_data()
    gsc_api_data = fetch_gsc_api_data(targets.keys())
    if gsc_api_data:
        gsc_data.update(gsc_api_data)  # API data takes precedence

    serp_rankings = fetch_serpbear_rankings(targets.keys())
    serp_available = len(serp_rankings) > 0

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = []
    report_lines.append(f"\n## Scan Date: {today_str}\n")
   
    # Dynamic column header based on data source
    if serp_available:
        report_lines.append("| Cluster | Keyword | SerpBear Pos | Prev Pos | GSC Avg Pos | Clicks | Impressions | CTR | Note |")
        report_lines.append("|---------|---------|--------------|----------|-------------|--------|-------------|-----|------|")
    else:
        report_lines.append("| Cluster | Keyword | GSC Avg Pos | Prev GSC Pos | Clicks | Impressions | CTR | Note |")
        report_lines.append("|---------|---------|-------------|--------------|--------|-------------|-----|------|")

    notable_drops = []
    untracked_keywords = []

    for kw_key, info in targets.items():
        keyword = info["keyword"]
        cluster = info["cluster"]

        gsc = gsc_data.get(kw_key, {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0})
        clicks = gsc["clicks"]
        impr = gsc["impressions"]
        ctr = gsc["ctr"]
        gsc_pos = gsc["position"]

        if serp_available and kw_key in serp_rankings:
            serp = serp_rankings[kw_key]
            pos = serp["position"]
            prev_pos = serp["last_position"]

            if pos > 0:
                # SerpBear has valid position - use it
                source = "SerpBear"
                report_pos = pos
                report_prev = prev_pos
                note = "Stable"
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
            else:
                # SerpBear position is 0 - fall back to GSC
                log_debug(f"SerpBear position=0 for '{keyword}', using GSC position {gsc_pos:.1f} as fallback")
                source = "GSC (fallback)"
                report_pos = f"{gsc_pos:.1f}*"
                report_prev = "—"
                note = "Using GSC position (SerpBear scraper not configured)"
                # Track drops based on GSC position changes if we have history
                # For now just report as stable since we don't have GSC history
        else:
            # No SerpBear data - use GSC position
            if gsc_pos > 0:
                source = "GSC"
                report_pos = f"{gsc_pos:.1f}"
                report_prev = "—"
                note = "Using GSC average position (SerpBear unavailable)"
            else:
                report_pos = "—"
                report_prev = "—"
                note = "❌ No ranking data available"
                untracked_keywords.append(keyword)

        if serp_available:
            report_lines.append(f"| {cluster} | {keyword} | {report_pos} | {report_prev} | {gsc_pos:.1f} | {clicks} | {impr} | {ctr:.1f}% | {note} |")
        else:
            report_lines.append(f"| {cluster} | {keyword} | {report_pos} | {report_prev} | {clicks} | {impr} | {ctr:.1f}% | {note} |")

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