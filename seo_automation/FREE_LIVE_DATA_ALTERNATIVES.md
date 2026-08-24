# Free Alternatives for Live SEO Data

## Completely Free (No Credit Card Required)

### 1. Google Search Console API - **FREE** ⭐
- **Data:** Clicks, impressions, CTR, position, indexed pages, crawl errors, sitemaps
- **Quota:** 1,000 queries/day, 100 rows/query
- **Setup:** Service account + GSC property ownership
- **Best for:** Core performance tracking

### 2. Google PageSpeed Insights API - **FREE** ⭐
- **Data:** Real CWV (LCP, CLS, INP, FID), lab + field data
- **Quota:** 25,000 requests/day (no key), 200,000 with key
- **Setup:** Optional API key from Google Cloud
- **Best for:** Technical SEO health

### 3. SerpBear (Self-Hosted) - **FREE** ⭐
- **Data:** Daily rankings, SERP features, history, alerts
- **Cost:** Only VPS (~$4-6/mo on DigitalOcean/AWS) or run locally
- **Setup:** `docker run -d -p 8080:8080 serpbear/serpbear`
- **Best for:** Rank tracking (unlimited keywords)

### 4. Bing Webmaster Tools API - **FREE**
- **Data:** Clicks, impressions, CTR, position, indexed pages, crawl issues
- **Quota:** Generous limits
- **Setup:** Bing Webmaster account + API key
- **Best for:** Second search engine data, often different rankings

### 5. Google Custom Search API - **FREE** (100 queries/day)
- **Data:** SERP results, titles, snippets, URLs
- **Quota:** 100 free queries/day, then $5/1000
- **Setup:** Custom Search Engine + API key
- **Best for:** Checking specific keyword SERPs

### 6. Ubersuggest Free Tier - **FREE** (Limited)
- **Data:** Keyword volume, difficulty, suggestions, content ideas
- **Limits:** 3 searches/day, limited results
- **Best for:** Quick keyword research

### 7. AnswerThePublic Free - **FREE** (Limited)
- **Data:** Questions, prepositions, comparisons for keywords
- **Limits:** 1-2 searches/day
- **Best for:** Question keyword research

---

## Free with Registration / Freemium

### 8. DataForSEO - **FREE $5 Credit** ⭐
- **Data:** Keywords, SERPs, backlinks, competitor data, search volume
- **Model:** Pay-per-use (~$0.001/keyword), $5 free credit = ~5,000 keywords
- **No monthly fee**, only pay for what you use
- **Best for:** Production keyword/competitor data at low cost

### 9. SerpAPI - **FREE 100 Searches/Month**
- **Data:** Full SERP (organic, PAA, local pack, shopping, ads, knowledge graph)
- **Limit:** 100 searches/month free
- **Best for:** SERP feature analysis

### 10. SEMrush Free Account - **FREE** (Limited)
- **Data:** 10 requests/day, 10 results/report
- **Includes:** Domain overview, keyword magic tool (limited), site audit (100 pages)
- **Best for:** Quick competitor checks

### 11. Ahrefs Webmaster Tools - **FREE** ⭐
- **Data:** YOUR site only - backlinks, keywords, site health, crawl data
- **No competitor data**, but full data for verified sites
- **Best for:** Deep technical + backlink analysis of your own site

### 12. SimilarWeb Free - **FREE** (Limited)
- **Data:** Traffic estimates, sources, top keywords (5), referral sites
- **Best for:** High-level competitor traffic comparison

### 13. Moz Link Explorer Free - **FREE** (10 queries/month)
- **Data:** DA, PA, linking domains, top pages
- **Best for:** Quick authority checks

---

## Open Source / Self-Hosted (Free Software)

### 14. SEO Audit Tools (Self-Hosted)

| Tool | What It Does | Hosting |
|------|--------------|---------|
| **Lighthouse CI** | Automated CWV audits | GitHub Actions / local |
| **Screaming Frog** (free 500 URLs) | Crawl, technical audit | Desktop |
| **Sitebulb** (14-day trial) | Deep technical audit | Desktop |
| **Google Lighthouse** | CWV, accessibility, SEO | Chrome DevTools / CLI |

### 15. Rank Tracking (Self-Hosted)

| Tool | Features |
|------|----------|
| **SerpBear** | Full rank tracker, Docker, API |
| **SEO Rank Monitor** (GitHub) | Python-based, SerpAPI/DataForSEO backend |
| **Ranktracker** (self-hosted) | Node.js, multiple search engines |

### 16. Keyword Research (Open Source)

```bash
# Free keyword sources via APIs/scraping:
- Google Autocomplete API (free, unofficial)
- Google Related Searches (scrape)
- People Also Ask (scrape)
- Reddit/Quora API (free tiers)
- Wikipedia API (free)
- Common Crawl (free, massive)
```

---

## Creative Free Workarounds

### 17. Google Sheets + Apps Script (FREE)
```javascript
// Free SERP tracking in Google Sheets
function getSerpRank(keyword, domain) {
  // Use UrlFetchApp to scrape or call free APIs
  // Run daily via trigger
  // Store history in sheet
}
```
- **Quota:** 30 min/day runtime, generous URL fetch
- **Best for:** No-server rank tracking

### 18. GitHub Actions + Free APIs (FREE)
```yaml
# .github/workflows/seo-daily.yml
on:
  schedule: ['0 2 * * *']  # Daily 2 AM
jobs:
  seo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: python seo_check.py  # Uses free APIs
```
- **Free:** 2,000 min/month on public repos
- **Best for:** Automated daily runs without VPS

### 19. Cloudflare Workers (FREE 100k/day)
- Run SEO checks at edge
- Cache results
- Free tier generous

### 20. Scraping (Use Responsibly)
```python
# Free but fragile - respect robots.txt
# Sources:
- Google "site:domain.com keyword" (check indexation)
- Bing "site:domain.com" (often easier)
- DuckDuckGo HTML (no JS, easier to scrape)
- Use: requests + BeautifulSoup / playwright
# Add delays, rotate user agents, cache aggressively
```

---

## Recommended Free Stack for GoRentals

### Tier 1: Zero Cost (Run Locally / GitHub Actions)
```
✅ GSC API          → Real traffic data
✅ PageSpeed API    → Real CWV
✅ Bing Webmaster   → Second engine data
✅ Ahrefs WMT       → Your backlinks + keywords
✅ SerpBear local   → Rank tracking (run on your machine)
✅ Google Sheets    → Dashboard + alerts
```

### Tier 2: ~$5/mo (VPS for SerpBear)
```
Tier 1 + SerpBear on $4 DigitalOcean droplet
→ 24/7 rank tracking, history, alerts
```

### Tier 3: ~$25/mo (DataForSEO pay-per-use)
```
Tier 2 + DataForSEO ($20 credit lasts months)
→ Real search volume, difficulty, competitor keywords, backlinks
```

---

## Implementation Priority

| Week | Add | Cost | Effort |
|------|-----|------|--------|
| 1 | GSC API + PageSpeed | $0 | 2 hrs |
| 2 | SerpBear (local Docker) | $0 | 30 min |
| 3 | Ahrefs Webmaster Tools | $0 | 1 hr |
| 4 | Bing Webmaster API | $0 | 1 hr |
| 5 | DataForSEO ($5 free credit) | $0 | 2 hrs |
| 6 | GitHub Actions automation | $0 | 1 hr |

---

## Code: Minimal Free Integration

```python
# utils/free_apis.py - Drop-in replacements for mock methods

import os, asyncio, aiohttp
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

class FreeSEOApis:
    def __init__(self):
        self.gsc_creds = os.getenv('GSC_CREDENTIALS_PATH')
        self.gsc_property = os.getenv('GSC_PROPERTY', 'sc-domain:gorentals.com')
        self.serpbear_url = os.getenv('SERPBEAR_URL', 'http://localhost:8080')
        self.pagespeed_key = os.getenv('PAGESPEED_KEY', '')
    
    # --- GSC: Real traffic data ---
    async def get_gsc_data(self, days=7):
        if not self.gsc_creds or not os.path.exists(self.gsc_creds):
            return None
        
        creds = service_account.Credentials.from_service_account_file(
            self.gsc_creds, scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('searchconsole', 'v1', credentials=creds)
        
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Run in executor (blocking call)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: service.searchanalytics().query(
            siteUrl=self.gsc_property,
            body={'startDate': start, 'endDate': end, 'dimensions': ['query'], 'rowLimit': 1000}
        ).execute())
        
        return response.get('rows', [])
    
    # --- PageSpeed: Real CWV ---
    async def get_cwv(self, urls):
        results = {}
        async with aiohttp.ClientSession() as session:
            for url in urls[:10]:  # Respect quota
                params = {'url': url, 'category': 'performance'}
                if self.pagespeed_key:
                    params['key'] = self.pagespeed_key
                
                async with session.get(
                    'https://www.googleapis.com/pagespeedonline/v5/runPagespeed',
                    params=params
                ) as resp:
                    data = await resp.json()
                    results[url] = self._parse_cwv(data)
        return results
    
    def _parse_cwv(self, data):
        try:
            loading = data.get('loadingExperience', {}).get('metrics', {})
            return {
                'lcp': loading.get('LARGEST_CONTENTFUL_PAINT_MS', {}).get('percentile', 0) / 1000,
                'cls': loading.get('CUMULATIVE_LAYOUT_SHIFT_SCORE', {}).get('percentile', 0),
                'inp': loading.get('INTERACTION_TO_NEXT_PAINT', {}).get('percentile', 0),
                'fid': loading.get('FIRST_INPUT_DELAY_MS', {}).get('percentile', 0),
            }
        except:
            return {}
    
    # --- SerpBear: Real rankings ---
    async def get_serpbear_rankings(self, keywords):
        if not self.serpbear_url:
            return {}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.serpbear_url}/api/keywords") as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
        
        kw_set = {k.lower() for k in keywords}
        return {
            item['keyword'].lower(): {
                'keyword': item['keyword'],
                'position': item['position'],
                'url': item.get('url'),
                'source': 'serpbear',
                'checked_at': datetime.now().isoformat()
            }
            for item in data.get('keywords', [])
            if item['keyword'].lower() in kw_set
        }
    
    # --- Bing Webmaster: Free alternative ---
    async def get_bing_data(self, days=7):
        # Similar to GSC but for Bing
        # Requires BING_WEBMASTER_API_KEY env var
        pass
    
    # --- Ahrefs Webmaster: Your site backlinks ---
    async def get_ahrefs_wmt(self):
        # Requires verified site in Ahrefs Webmaster Tools
        # API token from Ahrefs dashboard
        pass

# Usage in agents:
# free_apis = FreeSEOApis()
# gsc_data = await free_apis.get_gsc_data()
# cwv_data = await free_apis.get_cwv(['https://gorentals.com', 'https://gorentals.com/bikes/'])
# rankings = await free_apis.get_serpbear_rankings(['bike rental hyderabad', 'car rental hyderabad'])
```

---

## Free Data Summary Table

| Data Need | Free Source | Freshness | Reliability |
|-----------|-------------|-----------|-------------|
| **Clicks/Impressions/CTR/Position** | GSC API | ~2 days lag | ⭐⭐⭐⭐⭐ |
| **Rankings (daily)** | SerpBear (self-hosted) | Daily | ⭐⭐⭐⭐ |
| **CWV (LCP/CLS/INP)** | PageSpeed API | 28-day rolling | ⭐⭐⭐⭐ |
| **Indexed Pages** | GSC + Bing APIs | ~1 day | ⭐⭐⭐⭐ |
| **Crawl Errors** | GSC + Bing | ~1 day | ⭐⭐⭐⭐ |
| **Backlinks (your site)** | Ahrefs WMT | Weekly | ⭐⭐⭐⭐ |
| **Search Volume** | DataForSEO ($5 free) | Monthly | ⭐⭐⭐ |
| **Keyword Difficulty** | DataForSEO / Ubersuggest free | Monthly | ⭐⭐ |
| **Competitor Keywords** | DataForSEO ($5 free) | Monthly | ⭐⭐⭐ |
| **SERP Features (PAA, Local)** | SerpAPI (100 free/mo) | Real-time | ⭐⭐⭐ |
| **Traffic Estimates** | SimilarWeb free | Monthly | ⭐⭐ |

---

## Start Today (30 Minutes)

```bash
# 1. GSC Service Account (15 min)
#    - Google Cloud Console → IAM → Service Accounts → Create
#    - Enable Search Console API
#    - Download JSON → save as config/gsc_credentials.json
#    - Add email to GSC property as Owner

# 2. SerpBear (5 min)
docker run -d -p 8080:8080 -v serpbear:/app/data serpbear/serpbear

# 3. Test GSC
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
creds = service_account.Credentials.from_service_account_file('config/gsc_credentials.json', scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
svc = build('searchconsole', 'v1', credentials=creds)
print(svc.sites().list().execute())
"

# 4. Add to .env
echo "GSC_CREDENTIALS_PATH=config/gsc_credentials.json
GSC_PROPERTY=sc-domain:gorentals.com
SERPBEAR_URL=http://localhost:8080" > .env
```

**Total cost: $0** (or $4/mo if you want SerpBear on a VPS instead of local)