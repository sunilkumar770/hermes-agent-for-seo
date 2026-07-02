#!/usr/bin/env python3
"""
GoRentls SEO System — Publisher Agent (pseo_generator.py)
Generates item x city programmatic landing pages, registers them as experiments,
applies winning strategies, and generates the llms.txt discovery file.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"
PSEO_OUT_DIR = SEO_DIR / "drafts" / "pseo_pages"
STATE_FILE = SEO_DIR / "memory" / "pseo_page_state.json"
LLMS_TXT_PATH = SEO_DIR / "drafts" / "llms.txt"

# Add script dir to path
sys.path.append(str(SCRIPT_DIR))
import self_improving_engine

ITEM_CATEGORIES = ["car", "bike", "camera", "projector", "laptop", "furniture"]
CITY_TARGETS = ["hyderabad", "bangalore", "mumbai", "chennai", "delhi", "pune"]


def log_debug(msg: str):
    sys.stderr.write(f"[DEBUG] [Publisher] {msg}\n")
    sys.stderr.flush()


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"generated_slugs": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_strategy() -> dict:
    """Retrieve strategy rules from Strategy JSON."""
    strategy_path = SEO_DIR / "memory" / "strategy.json"
    if strategy_path.exists():
        with open(strategy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_llms_txt():
    """Generate the llms.txt file for LLMs and AI search engines."""
    LLMS_TXT_PATH.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# GoRentls — Rental Marketplace for Tech, Vehicles, & Gear

GoRentls is a premium rental marketplace offering local self-drive car rentals, superbike rentals, professional DSLR cameras, lenses, projectors, laptops, and home furniture across major Indian metro cities.

## Categories Available
- **Vehicles:** Self-drive cars, superbikes, scooters
- **Tech & Gear:** Professional cameras, projectors, laptops, sound systems
- **Lifestyle:** Furniture, home appliances

## Serviceable Cities
{chr(10).join([f'- {city.title()}' for city in CITY_TARGETS])}

## Key Site Map & Entry Points
- Home: https://gorentls.com/
- Browse Rentals: https://gorentls.com/rentals
- About Us: https://gorentls.com/about
- Developer & API details: https://gorentls.com/api/docs

---
Generated: {datetime.now().isoformat()}
"""
    with open(LLMS_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    log_debug(f"Generated llms.txt at: {LLMS_TXT_PATH}")


def generate_pseo_page(item: str, city: str) -> str:
    """Generate programmatic landing page markdown content."""
    slug = f"rent-{item}-in-{city}"
    strategy = get_strategy()

    # Find the best title pattern from strategy
    title_patterns = strategy.get("title_tag_patterns", {}).get("best_patterns", [])
    title_pattern = "Rent {item} in {city} | GoRentls"
    if title_patterns:
        # Pick the pattern with the highest CTR lift
        sorted_patterns = sorted(title_patterns, key=lambda x: x.get("avg_ctr_lift", 0.0), reverse=True)
        title_pattern = sorted_patterns[0]["pattern"]

    title = title_pattern.format(item=item.title(), city=city.title())
    description = f"Looking for {item} rentals in {city}? Rent top-quality {item}s from GoRentls at the lowest local rates. Fast verification, 24/7 support."

    page_content = f"""---
title: {title}
description: {description}
category: {item}
city: {city}
schema: LocalBusiness
---

# Rent {item.title()} in {city.title()}

Looking for premium, reliable, and affordable **{item} rentals** in **{city.title()}**? GoRentls is your trusted local rental partner!

Whether you need a high-quality {item} for personal use, professional gigs, or weekend travel, we offer a curated range of top-tier brands and models fully serviced and verified for quality.

## Why Choose GoRentls in {city.title()}?
- **Verified Gear & Vehicles:** Guaranteed quality checked and optimized.
- **Easy Document Verification:** Seamless, digital, and lightning-fast.
- **Doorstep Delivery & Pickup:** Get it delivered at your preferred time.
- **24/7 Customer Support:** Assistance is always just a call away.

## Local Hub Details in {city.title()}
Our local distribution center is situated in the heart of {city.title()}, enabling fast delivery and pickup services across all major neighborhoods.

---
### Frequently Asked Questions

#### 1. What are the documents required for {item} rentals?
You will need a valid government identity card (e.g., Aadhaar card or passport) and a matching address proof. For vehicle rentals, a valid driving license is mandatory.

#### 2. Are there any security deposits?
We offer zero-deposit options for verified recurring customers. First-time users may require a minimal refundable security deposit depending on the item model.
"""
    PSEO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PSEO_OUT_DIR / f"{slug}.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(page_content)

    return slug, title, description


def run_pseo(max_pages: int = 5):
    log_debug("Starting programmatic SEO generation...")
    state = load_state()
    generated_slugs = state["generated_slugs"]

    # Deduplicate list of combinations
    all_combos = []
    for item in ITEM_CATEGORIES:
        for city in CITY_TARGETS:
            slug = f"rent-{item}-in-{city}"
            all_combos.append((item, city, slug))

    total_matrix_size = len(all_combos)
    log_debug(f"Total possible pages in matrix: {total_matrix_size}")

    pages_created = 0
    for item, city, slug in all_combos:
        if slug in generated_slugs:
            continue

        log_debug(f"Generating page for: {slug}")
        slug, title, description = generate_pseo_page(item, city)

        # Log new experiment for this page
        experiment_dict = {
            "target": f"/{slug}",
            "keyword": f"{item} rental {city}",
            "change_type": "new_pseo_page",
            "title_pattern": title,
            "before_metrics": {
                "position": 0.0,
                "ctr": 0.0
            }
        }
        self_improving_engine.log_experiment(experiment_dict)

        generated_slugs.append(slug)
        pages_created += 1

        if pages_created >= max_pages:
            break

    state["generated_slugs"] = generated_slugs
    save_state(state)

    generate_llms_txt()

    coverage_pct = round((len(generated_slugs) / total_matrix_size) * 100, 2)
    log_debug(f"PSEO generation run completed. Created {pages_created} pages. Total matrix coverage: {coverage_pct}%")

    output = {
        "status": "success",
        "pages_generated": pages_created,
        "total_matrix_size": total_matrix_size,
        "covered_pages": len(generated_slugs),
        "coverage_pct": coverage_pct
    }
    print(json.dumps(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoRentls Programmatic SEO Page Publisher")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum number of pages to generate in this rotation")
    parser.add_argument("--item", type=str, help="Generate a specific item page")
    parser.add_argument("--city", type=str, help="Generate for a specific city")
    parser.add_argument("--llms-txt-only", action="store_true", help="Only generate llms.txt file")
    args = parser.parse_args()

    if args.llms_txt_only:
        generate_llms_txt()
        sys.exit(0)

    if args.item and args.city:
        slug, title, desc = generate_pseo_page(args.item, args.city)
        print(f"Generated single page: {slug} (Title: {title})")
        sys.exit(0)

    run_pseo(max_pages=args.max_pages)
