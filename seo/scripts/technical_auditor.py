#!/usr/bin/env python3
"""
GoRentls SEO System — Inspector Agent (Technical Auditor)
Audits pages for SEO issues, verifies schema, metadata, and llms.txt.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
REPORT_PATH = SEO_DIR / "reports" / "technical_audit.md"

# Load config/env
try:
    from config import CONFIG
except ImportError:
    CONFIG = {}

# Import Obscura extractor
sys.path.append(str(SCRIPT_DIR))
import obscura_extractor

GORP_SITE_URL = CONFIG.get("GORP_SITE_URL", os.environ.get("GORP_SITE_URL", "https://gorentls.com"))
AUDIT_PATHS = ["/", "/rentals", "/about"]


def log_debug(msg: str):
    sys.stderr.write(f"[DEBUG] [Inspector] {msg}\n")
    sys.stderr.flush()


def run_audit():
    log_debug(f"Starting Technical Audit of {GORP_SITE_URL}...")
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    audit_results = []
    has_issues = False

    # Audit targeted pages
    for path in AUDIT_PATHS:
        url = GORP_SITE_URL.rstrip("/") + path
        log_debug(f"Auditing page: {url}")

        # Fetch contents
        meta = obscura_extractor.fetch_meta(url)
        markdown = obscura_extractor.fetch_markdown(url)
        links = obscura_extractor.fetch_links(url)

        title = meta.get("title", "")
        description = meta.get("description", "")

        # Word count check
        word_count = len(markdown.split())

        # Checks
        issues = []
        warnings = []

        # 1. Title Checks
        if not title:
            issues.append("Missing <title> tag")
        elif len(title) < 30 or len(title) > 60:
            warnings.append(f"Title length ({len(title)} chars) should be between 30 and 60 chars (Title: '{title}')")

        # 2. Description Checks
        if not description:
            issues.append("Missing <meta name=\"description\"> tag")
        elif len(description) < 70 or len(description) > 160:
            warnings.append(f"Description length ({len(description)} chars) should be between 70 and 160 chars")

        # 3. H1 Checks
        h1_tags = [line for line in markdown.splitlines() if line.startswith("# ") and not line.startswith("##")]
        if not h1_tags:
            issues.append("Missing H1 heading")
        elif len(h1_tags) > 1:
            warnings.append(f"Multiple H1 tags found: {h1_tags}")

        # 4. Word Count Check
        if word_count < 300:
            warnings.append(f"Low word count ({word_count} words). Target at least 300 words.")

        # 5. Schema Check
        has_schema = "application/ld+json" in markdown or "schema.org" in markdown.lower()
        if not has_schema:
            warnings.append("No schema/JSON-LD structured data detected")

        # 6. FAQ Check if content is long
        if word_count > 500 and "faq" not in markdown.lower():
            warnings.append("Content exceeds 500 words but no FAQ block found")

        # 7. Internal Links check
        internal_links = [l for l in links if GORP_SITE_URL in l or l.startswith("/")]
        if len(internal_links) < 3:
            warnings.append(f"Low internal link count ({len(internal_links)} internal links found)")

        audit_results.append({
            "path": path,
            "url": url,
            "title": title,
            "description": description,
            "word_count": word_count,
            "issues": issues,
            "warnings": warnings,
            "has_schema": has_schema,
            "internal_links_count": len(internal_links)
        })
        if issues or warnings:
            has_issues = True

    # Audit llms.txt
    llms_url = GORP_SITE_URL.rstrip("/") + "/llms.txt"
    log_debug(f"Auditing llms.txt at: {llms_url}")
    llms_md = obscura_extractor.fetch_markdown(llms_url)
    llms_len = len(llms_md)
    llms_exists = llms_len > 100 and "failed" not in llms_md.lower()

    llms_issues = []
    if not llms_exists:
        llms_issues.append("llms.txt not found or too short (< 100 chars)")
    elif "gorentls" not in llms_md.lower():
        llms_issues.append("llms.txt exists but does not reference brand 'gorentls'")

    # Format human-readable markdown report
    report_lines = []
    report_lines.append(f"# Technical Audit Report: {today_str}\n")
    report_lines.append(f"**Target Site:** {GORP_SITE_URL}\n")

    report_lines.append("## Page Audits\n")
    for r in audit_results:
        report_lines.append(f"### Path: `{r['path']}`")
        report_lines.append(f"- **URL:** {r['url']}")
        report_lines.append(f"- **Title:** {r['title'] or '*None*'}")
        report_lines.append(f"- **Word Count:** {r['word_count']} words")
        report_lines.append(f"- **Structured Data (Schema):** {'✅ Present' if r['has_schema'] else '❌ Missing'}")
        report_lines.append(f"- **Internal Links:** {r['internal_links_count']}")

        if r["issues"]:
            report_lines.append("- **Critical Issues:**")
            for issue in r["issues"]:
                report_lines.append(f"  - ❌ {issue}")
        if r["warnings"]:
            report_lines.append("- **Optimizations & Warnings:**")
            for warn in r["warnings"]:
                report_lines.append(f"  - ⚠️ {warn}")
        report_lines.append("")

    report_lines.append("## AI Discoverability (llms.txt)\n")
    report_lines.append(f"- **Location:** `{llms_url}`")
    if llms_issues:
        report_lines.append("- **Status:** ❌ Issues detected:")
        for issue in llms_issues:
            report_lines.append(f"  - {issue}")
    else:
        report_lines.append("- **Status:** ✅ Valid llms.txt found")
    report_lines.append("")

    # Save to report path
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        log_debug(f"Technical audit report written to: {REPORT_PATH}")
    except Exception as e:
        log_debug(f"Failed to write audit report: {e}")

    summary = {
        "status": "success",
        "audited_at": datetime.now().isoformat(),
        "has_issues": has_issues or len(llms_issues) > 0,
        "pages_audited": len(audit_results),
        "results": audit_results,
        "llms_txt": {
            "exists": llms_exists,
            "issues": llms_issues
        }
    }
    print(json.dumps(summary))
    sys.exit(0)


if __name__ == "__main__":
    run_audit()
