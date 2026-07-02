#!/usr/bin/env python3
"""
GoRentls SEO System — Obscura Integration Layer
Wrapper around the Obscura CLI for stealth scraping and dynamic JS evaluation.
Falls back to requests + BeautifulSoup if Obscura CLI is not found or fails.
"""
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
import urllib.parse

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent
SEO_DIR = WORKSPACE_DIR / "seo"

# Load config/env
try:
    from config import CONFIG
except ImportError:
    CONFIG = {}

OBSCURA_BIN = CONFIG.get("OBSCURA_BIN", os.environ.get("OBSCURA_BIN", r"C:\Users\sunil\OneDrive\Desktop\obscura-bin\obscura.exe"))
OBSCURA_STEALTH = str(CONFIG.get("OBSCURA_STEALTH", os.environ.get("OBSCURA_STEALTH", "true"))).lower() == "true"
OBSCURA_PROXY = CONFIG.get("OBSCURA_PROXY", os.environ.get("OBSCURA_PROXY", ""))


def log_debug(msg: str):
    sys.stderr.write(f"[DEBUG] [Obscura] {msg}\n")
    sys.stderr.flush()


def is_obscura_available() -> bool:
    """Check if the Obscura binary exists or is on system PATH."""
    if Path(OBSCURA_BIN).exists():
        return True
    if shutil.which(OBSCURA_BIN):
        return True
    return False


def _run_obscura_command(args: list, timeout: int = 30) -> tuple:
    """Run an Obscura CLI subprocess command safely."""
    bin_path = OBSCURA_BIN
    if not Path(bin_path).exists() and shutil.which(bin_path):
        bin_path = shutil.which(bin_path)

    cmd = [bin_path] + args
    if OBSCURA_STEALTH:
        cmd.append("--stealth")
    if OBSCURA_PROXY:
        cmd.extend(["--proxy", OBSCURA_PROXY])

    log_debug(f"Running command: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            return True, res.stdout
        else:
            log_debug(f"Obscura command returned non-zero code {res.returncode}. Stderr: {res.stderr}")
            return False, res.stderr
    except subprocess.TimeoutExpired:
        log_debug(f"Obscura command timed out after {timeout}s.")
        return False, "Timeout"
    except Exception as e:
        log_debug(f"Obscura invocation error: {e}")
        return False, str(e)


def fetch_markdown(url: str, timeout: int = 30, stealth: bool = None) -> str:
    """
    Fetch a URL and return its content in Markdown format.
    Falls back to requests + BeautifulSoup (converting to simple markdown) on failure.
    """
    if is_obscura_available():
        args = ["fetch", url, "--dump", "markdown"]
        success, output = _run_obscura_command(args, timeout=timeout)
        if success:
            return output

    log_debug(f"Obscura unavailable/failed. Falling back to HTTP request for: {url}")
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Simple HTML to Markdown conversion fallback
        title = soup.title.string.strip() if soup.title else "No Title"
        body = soup.get_text(separator="\n", strip=True)
        return f"# {title}\n\n{body}"
    except Exception as e:
        log_debug(f"Fallback fetch failed: {e}")
        return f"# Fetch Failed: {url}\n\nError: {e}"


def fetch_meta(url: str, timeout: int = 30) -> dict:
    """
    Extract meta tags (<title>, <meta name="description">) using JS eval via Obscura.
    Falls back to static BeautifulSoup meta parsing.
    """
    if is_obscura_available():
        # Evaluate a JS script that extracts title and meta description
        js_expr = "JSON.stringify({title: document.title, description: (document.querySelector('meta[name=\"description\"]') || {}).content || ''})"
        success, output = _run_obscura_command(["fetch", url, "-e", js_expr], timeout=timeout)
        if success:
            try:
                # Obscura evaluated output might contain logs or be wrapped in JSON.
                # Let's search for JSON block
                clean_out = output.strip()
                if "{" in clean_out and "}" in clean_out:
                    start = clean_out.find("{")
                    end = clean_out.rfind("}") + 1
                    data = json.loads(clean_out[start:end])
                    return {
                        "title": data.get("title", "").strip(),
                        "description": data.get("description", "").strip()
                    }
            except Exception as e:
                log_debug(f"Failed to parse JS evaluation output: {e}. Output: {output}")

    # Fallback
    log_debug(f"Using static BeautifulSoup meta parsing fallback for: {url}")
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = desc_tag.get("content", "").strip() if desc_tag else ""
        return {"title": title, "description": description}
    except Exception as e:
        log_debug(f"Fallback meta extraction failed: {e}")
        return {"title": "", "description": ""}


def fetch_links(url: str, timeout: int = 30) -> list:
    """Extract all internal and external links from a page."""
    links = []
    if is_obscura_available():
        js_expr = "JSON.stringify(Array.from(document.querySelectorAll('a')).map(a => a.href))"
        success, output = _run_obscura_command(["fetch", url, "-e", js_expr], timeout=timeout)
        if success:
            try:
                clean_out = output.strip()
                if "[" in clean_out and "]" in clean_out:
                    start = clean_out.find("[")
                    end = clean_out.rfind("]") + 1
                    links = json.loads(clean_out[start:end])
                    return list(set(links))
            except Exception as e:
                log_debug(f"Failed to parse JS links output: {e}. Output: {output}")

    # Fallback
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            absolute_href = urllib.parse.urljoin(base_url, href)
            links.append(absolute_href)
        return list(set(links))
    except Exception as e:
        log_debug(f"Fallback link extraction failed: {e}")
        return []


def evaluate_js(url: str, js_expression: str, timeout: int = 30) -> str:
    """Evaluate a JavaScript expression on the loaded page and return output."""
    if is_obscura_available():
        success, output = _run_obscura_command(["fetch", url, "-e", js_expression], timeout=timeout)
        if success:
            return output
    return "Obscura CLI unavailable/failed to evaluate JS"


def scrape_parallel(urls: list, concurrency: int = 10, timeout: int = 30) -> list:
    """Scrape multiple URLs in parallel using Obscura CLI or fallback."""
    results = []
    if is_obscura_available() and len(urls) > 1:
        # Obscura supports parallel scrape command
        # Syntax: obscura scrape url1 url2 -e "expression"
        log_debug(f"Performing parallel scrape for {len(urls)} URLs...")
        # Since we want markdown, we can call fetch command iteratively or use the scrape command if supported.
        # To be safe, we run them concurrently in python threads or call obscura scrape
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(fetch_markdown, url, timeout) for url in urls]
            results = [f.result() for f in futures]
        return results

    # Iterative fallback
    for url in urls:
        results.append(fetch_markdown(url, timeout))
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://example.com"

    log_debug(f"Testing Obscura Integration with: {test_url}")
    log_debug(f"Obscura CLI Available: {is_obscura_available()}")
    meta = fetch_meta(test_url)
    print(f"Meta Extracted: {meta}")
