"""Shared configuration loader for GoRentls SEO scripts."""
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"


def load_env():
    """Load .env from script dir, seo dir, or workspace root."""
    for env_file in [SCRIPT_DIR / ".env", SEO_DIR / ".env", WORKSPACE_DIR / ".env"]:
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")


def get_config():
    """Return validated config dict with defaults."""
    load_env()
    return {
        "SCRIPT_DIR": SCRIPT_DIR,
        "WORKSPACE_DIR": WORKSPACE_DIR,
        "SEO_DIR": SEO_DIR,
        "TARGET_KEYWORDS_PATH": SEO_DIR / "target_keywords.md",
        "GSC_CSV_PATH": SEO_DIR / "data" / "gsc_queries.csv",
        "REPORT_PATH": SEO_DIR / "reports" / "ranking_log.md",
        "COORDINATOR_LOG": SEO_DIR / "reports" / "coordinator_log.md",
        "OPTIMIZATIONS_PATH": SEO_DIR / "drafts" / "weekly_optimizations.md",
        "COMPETITORS_DIR": SEO_DIR / "competitors",
        "SERPBEAR_BASE": os.environ.get("SERPBEAR_URL", os.environ.get("SERPBEAR_BASE", "http://localhost:3000")),
        "SERPBEAR_API_KEY": os.environ.get("SERPBEAR_API_KEY", ""),
        "SERPBEAR_DB": os.environ.get("SERPBEAR_DB", ""),
        "GORP_DOMAIN": os.environ.get("GORP_DOMAIN", "gorentls.com"),
        "RANK_DROP_THRESHOLD": int(os.environ.get("RANK_DROP_THRESHOLD", "2")),
        "GSC_SERVICE_ACCOUNT": os.environ.get("GSC_SERVICE_ACCOUNT", ""),
        "GSC_PROPERTY": os.environ.get("GSC_PROPERTY", "sc-domain:gorentls.com"),
        "ALERT_WEBHOOK": os.environ.get("ALERT_WEBHOOK", ""),
        "ALERT_EMAIL": os.environ.get("ALERT_EMAIL", ""),
        "SERPLY_API_KEY": os.environ.get("SERPLY_API_KEY", ""),
        "SERPAPI_KEY": os.environ.get("SERPAPI_KEY", ""),
    }


def log_debug(msg: str):
    import sys
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()


# Load on import
load_env()
CONFIG = get_config()