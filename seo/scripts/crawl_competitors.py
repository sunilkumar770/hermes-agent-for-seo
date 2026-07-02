#!/usr/bin/env python3
"""
GoRentls Competitor Crawler — Crawl4AI + Playwright + SERP Discovery
FIXES: Proper Crawl4AI config API, BeautifulSoup fallback, timeout, JSON I/O.
NEW: Auto-discover competitors from SERP for dropped keywords.
"""
import os
import sys
import json
import asyncio
import argparse
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from config import CONFIG, log_debug

COMPETITORS_DIR = CONFIG["COMPETITORS_DIR"]
SERPLY_API_KEY = CONFIG.get("SERPLY_API_KEY", "")
SERPAPI_KEY = CONFIG.get("SERPAPI_KEY", "")

# Fallback hardcoded competitors (used when SERP discovery fails)
FALLBACK_COMPETITORS = {
    "cars": ["https://www.zoomcar.com/hyderabad", "https://www.revv.co.in/car-rental/hyderabad"],
    "bikes": ["https://www.royalbrothers.com/hyderabad", "https://www.ontrack.in"],
    "cameras": ["https://www.rentoclick.com/hyderabad", "https://www.camrent.in"],
    "local": ["https://www.rentickle.com", "https://www.rentmojo.com"]
}


def discover_competitors_serply(keyword, num_results=5):
    """Discover competitor URLs from SERP using Serply API."""
    if not SERPLY_API_KEY:
        return None
    try:
        import requests
        headers = {
            "X-API-KEY": SERPLY_API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        params = {
            "q": keyword,
            "location": "Hyderabad, Telangana, India",
            "gl": "in",
            "hl": "en",
            "num": num_results
        }
        resp = requests.get("https://api.serply.io/v1/search/", headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            urls = []
            for result in data.get("results", []):
                link = result.get("link", "")
                if link and "gorentls.com" not in link:
                    urls.append(link)
            return urls[:num_results]
    except Exception as e:
        log_debug(f"Serply SERP discovery failed for '{keyword}': {e}")
    return None


def discover_competitors_serpapi(keyword, num_results=5):
    """Discover competitor URLs from SERP using SerpApi."""
    if not SERPAPI_KEY:
        return None
    try:
        import requests
        params = {
            "engine": "google",
            "q": keyword,
            "location": "Hyderabad, Telangana, India",
            "google_domain": "google.co.in",
            "gl": "in",
            "hl": "en",
            "num": num_results,
            "api_key": SERPAPI_KEY
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            urls = []
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                if link and "gorentls.com" not in link:
                    urls.append(link)
            return urls[:num_results]
    except Exception as e:
        log_debug(f"SerpApi SERP discovery failed for '{keyword}': {e}")
    return None


def discover_competitors(keyword, cluster, num_results=3):
    """Try SERP discovery first, fall back to hardcoded competitors."""
    # Try Serply first
    urls = discover_competitors_serply(keyword, num_results)
    if urls:
        log_debug(f"Serply discovered {len(urls)} competitors for '{keyword}'")
        return urls

    # Try SerpApi
    urls = discover_competitors_serpapi(keyword, num_results)
    if urls:
        log_debug(f"SerpApi discovered {len(urls)} competitors for '{keyword}'")
        return urls

    # Fallback to hardcoded
    fallback = FALLBACK_COMPETITORS.get(cluster.lower(), FALLBACK_COMPETITORS["cars"])
    log_debug(f"Using fallback competitors for '{keyword}' (cluster: {cluster})")
    return fallback[:num_results]


async def crawl_url_crawl4ai(url):
    """
    Crawl a URL using Crawl4AI.
    FIX: Use proper CrawlerRunConfig and BrowserConfig APIs.
    FIX: Add timeout via asyncio.wait_for.
    """
    try:
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
    except ImportError:
        raise ImportError("crawl4ai not installed. Run: pip install crawl4ai")

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
    )
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        exclude_external_images=True,
        remove_overlay_elements=True,
        process_iframes=True,
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_config),
                timeout=60
            )
            if result.success:
                markdown = ""
                if result.markdown:
                    if hasattr(result.markdown, 'raw_markdown'):
                        markdown = result.markdown.raw_markdown or ""
                    elif isinstance(result.markdown, str):
                        markdown = result.markdown
                    else:
                        markdown = str(result.markdown)
                title = ""
                if result.metadata:
                    title = result.metadata.get("title", "")
                return {"markdown": markdown or "No content crawled.", "title": title}
            else:
                error_msg = getattr(result, 'error_message', 'Unknown Crawl4AI error')
                raise Exception(f"Crawl4AI failed: {error_msg}")
    except asyncio.TimeoutError:
        raise Exception("Crawl4AI timed out after 60s")
    except ImportError:
        raise
    except Exception as e:
        if "async_configs" in str(e) or "CrawlerRunConfig" in str(e):
            log_debug(f"New Crawl4AI config API failed ({e}). Using legacy API.")
            async with AsyncWebCrawler() as crawler:
                result = await asyncio.wait_for(
                    crawler.arun(url=url),
                    timeout=60
                )
                if result.success:
                    markdown = ""
                    if result.markdown:
                        if hasattr(result.markdown, 'raw_markdown'):
                            markdown = result.markdown.raw_markdown or ""
                        elif isinstance(result.markdown, str):
                            markdown = result.markdown
                        else:
                            markdown = str(result.markdown)
                    return {"markdown": markdown or "No content crawled.", "title": ""}
                raise Exception(result.error_message or "Crawl4AI execution failed.")
        raise


async def crawl_url_fallback(url):
    """
    Fallback crawl using requests + BeautifulSoup.
    FIX: Use BeautifulSoup instead of fragile regex for HTML parsing.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 not installed. Run: pip install beautifulsoup4 requests")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    loop = asyncio.get_event_loop()

    def fetch():
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text

    html = await loop.run_in_executor(None, fetch)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "No Title"

    # Remove script and style elements
    for script in soup(["script", "style", "noscript"]):
        script.decompose()

    # Extract meta description
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        meta_desc = desc_tag.get("content", "")

    body_content = []
    body_content.append(f"# {title}\n")
    body_content.append(f"**URL:** {url} (Fallback HTTP Fetch)\n")
    body_content.append(f"**Meta Description:** {meta_desc}\n")

    # Extract headings
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            level = tag.name.upper()
            body_content.append(f"## {text}\n" if level == "H1" else f"### {text}\n")

    # Extract main text content
    text_content = soup.get_text(separator=" ", strip=True)
    if text_content:
        body_content.append(f"\n{text_content[:4000]}\n")

    return {"markdown": "\n".join(body_content), "title": title}


async def send_alert(message, webhook_url=None):
    """Send alert via webhook (Slack, Teams, Discord, generic)."""
    if not webhook_url:
        webhook_url = CONFIG.get("ALERT_WEBHOOK", "")
    if not webhook_url:
        return
    try:
        import requests
        requests.post(webhook_url, json={"text": message}, timeout=10)
    except Exception as e:
        log_debug(f"Alert webhook failed: {e}")


async def main():
    drops_json = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        drops_json = sys.argv[1]
    else:
        if not sys.stdin.isatty():
            drops_json = sys.stdin.read().strip()

    if not drops_json:
        parser = argparse.ArgumentParser(description="Crawl competitor pages.")
        parser.add_argument("--keyword", help="Target keyword")
        parser.add_argument("--cluster", help="Target keyword cluster")
        parser.add_argument("--urls", help="Comma-separated competitor URLs")
        args = parser.parse_args()
        if args.keyword and args.cluster:
            urls_list = [u.strip() for u in args.urls.split(",") if u.strip()] if args.urls else discover_competitors(args.keyword, args.cluster)
            drops_data = [{"keyword": args.keyword, "cluster": args.cluster, "urls": urls_list}]
        else:
            print(json.dumps({"status": "skipped", "reason": "No drop data provided"}))
            sys.exit(0)
    else:
        try:
            parsed = json.loads(drops_json)
            if isinstance(parsed, dict):
                drops_data = parsed.get("drops", [])
            else:
                drops_data = parsed
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "error": f"Invalid JSON input: {e}"}))
            sys.exit(1)

    if not drops_data:
        print(json.dumps({"status": "skipped", "reason": "Empty drops list"}))
        sys.exit(0)

    use_crawl4ai = False
    try:
        import crawl4ai
        use_crawl4ai = True
        log_debug("Crawl4AI is available. Using AsyncWebCrawler.")
    except ImportError:
        log_debug("Crawl4AI not available. Using BeautifulSoup fallback.")

    today = datetime.now().strftime("%Y-%m-%d")
    crawled_urls = []
    crawl_errors = []
    crawl_results = []

    for drop in drops_data:
        kw = drop.get("keyword", "unknown")
        cluster = drop.get("cluster", "general")
        urls = drop.get("urls") or discover_competitors(kw, cluster)

        clean_keyword = re.sub(r"[^a-zA-Z0-9_-]", "_", kw.lower().strip())
        out_dir = COMPETITORS_DIR / cluster / clean_keyword / today
        out_dir.mkdir(parents=True, exist_ok=True)

        for url in urls:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname or "unknown_host"
            hostname = re.sub(r"[^a-zA-Z0-9.-]", "_", hostname)
            out_path = out_dir / f"{hostname}.md"

            log_debug(f"Crawling {url} for keyword '{kw}'...")

            try:
                if use_crawl4ai:
                    try:
                        result = await crawl_url_crawl4ai(url)
                        content = result["markdown"]
                        title = result.get("title", "")
                    except Exception as e:
                        log_debug(f"Crawl4AI failed for {url}: {e}. Trying fallback.")
                        result = await crawl_url_fallback(url)
                        content = result["markdown"]
                        title = result.get("title", "")
                else:
                    result = await crawl_url_fallback(url)
                    content = result["markdown"]
                    title = result.get("title", "")

                # Truncate to 8000 chars
                if len(content) > 8000:
                    content = content[:8000] + "\n\n... [Content Truncated to 8,000 Characters] ..."

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)

                log_debug(f"Saved to {out_path}")
                crawled_urls.append(url)
                crawl_results.append({
                    "url": url,
                    "title": title,
                    "word_count": len(content.split()),
                    "file": str(out_path),
                    "status": "success"
                })

            except Exception as e:
                log_debug(f"Failed to crawl {url}: {e}")
                crawl_errors.append({"url": url, "error": str(e)})
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(f"# Crawl Failed: {url}\n\nError: {e}\nTimestamp: {datetime.now().isoformat()}\n")

    # Send alert if there were drops and we crawled
    if crawl_results and CONFIG.get("ALERT_WEBHOOK"):
        msg = f"🔍 GoRentls SEO: Crawled {len(crawl_results)} competitor pages for {len(drops_data)} dropped keyword(s)."
        await send_alert(msg)

    output = {
        "status": "success" if crawled_urls else "error",
        "crawled_count": len(crawled_urls),
        "crawled_urls": crawled_urls,
        "crawl_results": crawl_results,
        "errors": crawl_errors,
        "crawled_at": datetime.now().isoformat()
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())