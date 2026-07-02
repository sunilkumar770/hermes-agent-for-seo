#!/usr/bin/env python3
"""Sync target keywords from target_keywords.md to SerpBear SQLite database."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import CONFIG, log_debug

TARGET_KEYWORDS_MD = CONFIG["TARGET_KEYWORDS_PATH"]
SERPBEAR_DB = CONFIG["SERPBEAR_DB"]
GORP_DOMAIN = CONFIG["GORP_DOMAIN"]


def parse_target_keywords():
    keywords_info = []
    if not TARGET_KEYWORDS_MD.exists():
        print(f"Error: {TARGET_KEYWORDS_MD} does not exist.")
        return keywords_info

    with open(TARGET_KEYWORDS_MD, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or "Keyword" in line or "---" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                keyword, cluster = parts[0], parts[1]
                keywords_info.append({
                    "keyword": keyword,
                    "cluster": cluster
                })
    return keywords_info


def insert_keywords():
    targets = parse_target_keywords()
    if not targets:
        print("No target keywords parsed.")
        return

    if not SERPBEAR_DB:
        print("Error: SERPBEAR_DB not set in .env file.")
        return

    db_path = Path(SERPBEAR_DB)
    if not db_path.exists():
        print(f"Error: Database file does not exist at {db_path}. Check your SERPBEAR_DB env var.")
        return

    print(f"Connecting to SerpBear database: {db_path} ...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing keywords to avoid duplicates
    # Use the configured domain (with or without www)
    domain_variants = [GORP_DOMAIN, f"www.{GORP_DOMAIN}"]
    placeholders = ",".join("?" * len(domain_variants))
    cursor.execute(f"SELECT keyword, device FROM keyword WHERE domain IN ({placeholders})", domain_variants)
    existing = set((row[0].lower(), row[1]) for row in cursor.fetchall())
    print(f"Found {len(existing)} existing keyword-device entries for {GORP_DOMAIN}.")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    added_count = 0
    for t in targets:
        kw = t["keyword"]
        cluster = t["cluster"]
        tags_json = f'["{cluster}"]'

        for device in ["desktop", "mobile"]:
            if (kw.lower(), device) not in existing:
                cursor.execute("""
                    INSERT INTO keyword (
                        keyword, device, country, city, latlong, domain,
                        lastUpdated, added, position, history, volume,
                        url, tags, lastResult, sticky, updating, lastUpdateError
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kw, device, "IN", "", "", GORP_DOMAIN,
                    now_iso, now_iso, 0, "{}", 0,
                    "", tags_json, "[]", 0, 0, "0"
                ))
                added_count += 1
                existing.add((kw.lower(), device))

    conn.commit()
    conn.close()
    print(f"Done! Successfully inserted {added_count} new keyword-device pairs into the SerpBear database.")


if __name__ == "__main__":
    insert_keywords()