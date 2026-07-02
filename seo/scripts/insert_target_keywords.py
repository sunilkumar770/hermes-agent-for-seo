import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
TARGET_KEYWORDS_MD = SEO_DIR / "target_keywords.md"

# Load local .env if it exists
for env_file in [SCRIPT_DIR / ".env", SEO_DIR / ".env", WORKSPACE_DIR / ".env"]:
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

DB_PATH = os.environ.get("SERPBEAR_DB", r"c:\Users\sunil\projects\serpbear\data\database.sqlite")

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

    print(f"Connecting to SerpBear database: {DB_PATH} ...")
    if not Path(DB_PATH).exists():
        print(f"Error: Database file does not exist at {DB_PATH}. Check your SERPBEAR_DB env var.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing keywords to avoid duplicates
    cursor.execute("SELECT keyword, device FROM keyword WHERE domain = 'www.gorentls.com'")
    existing = set((row[0].lower(), row[1]) for row in cursor.fetchall())
    print(f"Found {len(existing)} existing keyword-device entries for www.gorentls.com.")

    from datetime import timezone
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
                    kw, device, "IN", "", "", "www.gorentls.com",
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
