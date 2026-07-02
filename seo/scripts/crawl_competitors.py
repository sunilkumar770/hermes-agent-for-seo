#!/usr/bin/env python3
import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import re

# Paths relative to script directory
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"

# Predefined mapping of clusters to competitor URLs in India/Hyderabad
COMPETITORS = {
    "cars": ["https://www.zoomcar.com/hyderabad", "https://www.revv.co.in/car-rental/hyderabad"],
    "bikes": ["https://www.royalbrothers.com/hyderabad", "https://www.ontrack.in"],
    "cameras": ["https://www.rentoclick.com/hyderabad", "https://www.camrent.in"],
    "local": ["https://www.rentickle.com", "https://www.rentmojo.com"]
}

def log_debug(msg):
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()

async def crawl_url_crawl4ai(url):
    """Crawl a URL using Crawl4AI's AsyncWebCrawler with optimized settings."""
    from crawl4ai import AsyncWebCrawler
    
    async with AsyncWebCrawler() as crawler:
        try:
            # Attempt advanced configuration for image stripping and overlay removal
            result = await crawler.arun(
                url=url,
                screenshot=False,
                remove_overlay_elements=True,
                process_iframes=True,
                exclude_external_images=True,
                bypass_cache=True
            )
        except Exception as e:
            log_debug(f"Advanced Crawl4AI flags failed ({e}). Retrying with default settings...")
            result = await crawler.arun(url=url, markdown=True)
            
        if result.success:
            return result.markdown or "No content crawled."
        else:
            raise Exception(result.error_message or "Crawl4AI execution failed.")

async def crawl_url_fallback(url):
    """Fallback crawl using standard requests for HTML and a basic extractor."""
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    loop = asyncio.get_event_loop()
    def fetch():
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text
        
    html = await loop.run_in_executor(None, fetch)
    
    # Extract title
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    title = title_match.group(1) if title_match else "No Title"
    
    body_content = []
    body_content.append(f"# {title}\n")
    body_content.append(f"Crawl source: {url} (Fallback HTTP Fetch)\n")
    
    # Extract H1s
    h1s = re.findall(r"<h1.*?>(.*?)</h1>", html, re.IGNORECASE)
    if h1s:
        body_content.append("## Headings (H1)\n")
        for h in h1s:
            clean_h = re.sub(r"<[^>]*>", "", h).strip()
            body_content.append(f"- {clean_h}")
        body_content.append("")
        
    # Extract H2s
    h2s = re.findall(r"<h2.*?>(.*?)</h2>", html, re.IGNORECASE)
    if h2s:
        body_content.append("## Headings (H2)\n")
        for h in h2s:
            clean_h = re.sub(r"<[^>]*>", "", h).strip()
            body_content.append(f"- {clean_h}")
        body_content.append("")
        
    # Extract meta description
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html, re.IGNORECASE)
    if desc_match:
        body_content.append(f"**Meta Description**: {desc_match.group(1)}\n")
        
    # Simple text extraction
    text_content = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text_content = re.sub(r"<style.*?>.*?</style>", "", text_content, flags=re.DOTALL | re.IGNORECASE)
    text_content = re.sub(r"<[^>]*>", " ", text_content)
    text_content = re.sub(r"\s+", " ", text_content).strip()
    
    body_content.append("## Content Snippet\n")
    body_content.append(text_content[:2000] + "...\n")
    
    return "\n".join(body_content)

async def main():
    # Detect if we have arguments or stdin JSON data
    drops_json = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        drops_json = sys.argv[1]
    else:
        # Check if stdin has data
        if not sys.stdin.isatty():
            drops_json = sys.stdin.read().strip()
            
    if not drops_json:
        # Parse standard command line arguments as fallback
        parser = argparse.ArgumentParser(description="Crawl competitor pages.")
        parser.add_argument("--keyword", help="Target keyword")
        parser.add_argument("--cluster", help="Target keyword cluster")
        parser.add_argument("--urls", help="Comma-separated competitor URLs")
        args = parser.parse_args()
        
        if args.keyword and args.cluster:
            urls_list = [u.strip() for u in args.urls.split(",") if u.strip()] if args.urls else COMPETITORS.get(args.cluster.lower(), [])
            drops_data = [{"keyword": args.keyword, "cluster": args.cluster, "urls": urls_list}]
        else:
            log_debug("No drop data provided. Exiting.")
            print(json.dumps({"status": "skipped", "reason": "No drop data provided"}))
            sys.exit(0)
    else:
        try:
            parsed = json.loads(drops_json)
            # Support both a direct list of drops or the full output of seo_pipeline.py
            if isinstance(parsed, dict):
                drops_data = parsed.get("drops", [])
            else:
                drops_data = parsed
        except Exception as e:
            log_debug(f"Failed to parse drops JSON: {e}")
            print(json.dumps({"status": "error", "error": f"Invalid JSON input: {e}"}))
            sys.exit(1)

    if not drops_data:
        log_debug("Drops list is empty. Skipping competitor crawls.")
        print(json.dumps({"status": "skipped", "reason": "Empty drops list"}))
        sys.exit(0)

    # Check if crawl4ai is installed
    use_crawl4ai = False
    try:
        import crawl4ai
        use_crawl4ai = True
        log_debug("Crawl4AI is available. Using AsyncWebCrawler.")
    except ImportError:
        log_debug("Crawl4AI is not available. Falling back to HTTP request extraction.")
        
    today = datetime.now().strftime("%Y-%m-%d")
    crawled_urls = []
    
    for drop in drops_data:
        kw = drop.get("keyword")
        cluster = drop.get("cluster", "general")
        urls = drop.get("urls") or COMPETITORS.get(cluster.lower(), ["https://www.zoomcar.com/hyderabad"])
        
        clean_keyword = re.sub(r"[^a-zA-Z0-9_-]", "_", kw.lower().strip())
        out_dir = SEO_DIR / "competitors" / cluster / clean_keyword / today
        out_dir.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname or "unknown_host"
            hostname = re.sub(r"[^a-zA-Z0-9.-]", "_", hostname)
            
            out_path = out_dir / f"{hostname}.md"
            log_debug(f"Crawling {url} for keyword '{kw}'...")
            
            try:
                content = ""
                if use_crawl4ai:
                    try:
                        content = await crawl_url_crawl4ai(url)
                    except Exception as e:
                        log_debug(f"Crawl4AI failed for {url}: {e}. Trying fallback.")
                        content = await crawl_url_fallback(url)
                else:
                    content = await crawl_url_fallback(url)
                
                # Truncate content to 8000 chars for LLM context efficiency
                truncated_content = content[:8000]
                if len(content) > 8000:
                    truncated_content += "\n\n... [Content Truncated to 8,000 Characters] ..."
                    
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(truncated_content)
                log_debug(f"Successfully saved to {out_path}")
                crawled_urls.append(url)
                
            except Exception as e:
                log_debug(f"Failed to crawl {url}: {e}")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(f"# Crawl Failed: {url}\n\nError: {e}\nTimestamp: {datetime.now().isoformat()}\n")

    print(json.dumps({"status": "success", "crawled_count": len(crawled_urls), "crawled_urls": crawled_urls}))

if __name__ == "__main__":
    asyncio.run(main())
