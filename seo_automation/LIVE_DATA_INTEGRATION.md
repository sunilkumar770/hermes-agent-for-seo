# Live Data Integration Guide for GoRentals SEO Automation

## Required API Credentials

### 1. Google Search Console (GSC) - FREE
**What you get:** Real clicks, impressions, CTR, position, indexed pages, crawl errors
**Setup:**
```bash
# 1. Go to Google Cloud Console
# 2. Create project → Enable Search Console API
# 3. Create Service Account → Download JSON key
# 4. Add service account email as "Owner" in GSC property settings
```
**Config:** `config/gsc_credentials.json` (service account key)

### 2. SerpBear - SELF-HOSTED (FREE)
**What you get:** Daily rank tracking for unlimited keywords
**Setup:**
```bash
# Docker (recommended)
docker run -d \
  -p 8080:8080 \
  -e DATABASE_URL=sqlite:///serpbear.db \
  -v serpbear_data:/app/data \
  serpbear/serpbear:latest

# Or use hosted: https://serpbear.com (paid)
```
**Config:** `SERPBEAR_URL=http://localhost:8080`, `SERPBEAR_API_KEY=your_key`

### 3. SerpAPI - PAID (~$50-200/mo)
**What you get:** Real-time SERP data, PAA, local pack, shopping, etc.
**Setup:**
```bash
# Sign up at https://serpapi.com
# Get API key from dashboard
```
**Config:** `SERPAPI_KEY=your_key`

### 4. Ahrefs / SEMrush / DataForSEO - PAID ($99-500+/mo)
**What you get:** Backlinks, referring domains, competitor keywords, difficulty scores
**Setup:**
```bash
# Ahrefs: https://ahrefs.com/api
# SEMrush: https://www.semrush.com/api
# DataForSEO: https://dataforseo.com (pay-per-use, cheaper)
```
**Config:** `AHREFS_TOKEN=your_token` or `DATAFORSEO_LOGIN=...`, `DATAFORSEO_PASSWORD=...`

### 5. PageSpeed Insights - FREE (with quota)
**What you get:** Real Core Web Vitals (LCP, CLS, INP, FID)
**Setup:**
```bash
# Google Cloud Console → Enable PageSpeed Insights API
# Create API key (or use without key: 25k requests/day)
```
**Config:** `PAGESPEED_KEY=your_key` (optional)

### 6. Google Business Profile (GBP) - FREE
**What you get:** GBP views, searches, actions, reviews
**Setup:**
```bash
# Enable My Business API in Google Cloud
# OAuth2 flow required (more complex)
# Alternative: Use local SEO tools like BrightLocal API
```

---

## Environment Variables Setup

Create `.env` file in `seo_automation/`:
```bash
# seo_automation/.env
GSC_CREDENTIALS_PATH=config/gsc_credentials.json
GSC_PROPERTY=sc-domain:gorentals.com

SERPBEAR_URL=http://localhost:8080
SERPBEAR_API_KEY=your_serpbear_key

SERPAPI_KEY=your_serpapi_key

AHREFS_TOKEN=your_ahrefs_token
# OR
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password

PAGESPEED_KEY=your_pagespeed_key

GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_REPO=gorentals/seo-content
GITHUB_BRANCH=seo-automation
```

---

## Agent Updates Required

### 1. Performance Tracking Agent → Real GSC Data
```python
# agents/performance_tracking.py - replace _collect_metrics()
async def _collect_metrics(self) -> Dict:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    creds = service_account.Credentials.from_service_account_file(
        os.environ['GSC_CREDENTIALS_PATH'],
        scopes=['https://www.googleapis.com/auth/webmasters.readonly']
    )
    service = build('searchconsole', 'v1', credentials=creds)
    
    # Query last 7 days
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    request = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': ['query', 'page'],
        'rowLimit': 1000
    }
    
    response = service.searchanalytics().query(
        siteUrl=os.environ['GSC_PROPERTY'], body=request
    ).execute()
    
    # Process response into metrics dict
    return self._process_gsc_response(response)
```

### 2. Rank Checker Agent → Real SerpBear/SerpAPI
```python
# agents/rank_checker.py - replace _check_serpbear()
async def _check_serpbear(self, keywords: List[Dict]) -> Dict:
    import aiohttp
    
    url = f"{os.environ['SERPBEAR_URL']}/api/keywords"
    headers = {'Authorization': f"Bearer {os.environ['SERPBEAR_API_KEY']}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
    
    # Filter for our keywords
    rankings = {}
    for item in data.get('keywords', []):
        kw = item['keyword'].lower()
        if kw in [k['keyword'].lower() for k in keywords]:
            rankings[kw] = {
                'keyword': item['keyword'],
                'position': item['position'],
                'url': item.get('url'),
                'source': 'serpbear',
                'checked_at': datetime.now().isoformat()
            }
    return rankings
```

### 3. Technical SEO Agent → Real PageSpeed
```python
# agents/technical_seo.py - add CWV check
async def _check_core_web_vitals(self, urls: List[str]) -> Dict:
    import aiohttp
    
    results = {}
    key = os.environ.get('PAGESPEED_KEY', '')
    base_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    
    async with aiohttp.ClientSession() as session:
        for url in urls[:10]:  # API quota limits
            params = {'url': url, 'category': 'performance'}
            if key:
                params['key'] = key
            
            async with session.get(base_url, params=params) as resp:
                data = await resp.json()
                results[url] = self._parse_pagespeed(data)
    
    return results
```

### 4. Competitor Intelligence → Real Ahrefs/DataForSEO
```python
# agents/competitor_intelligence.py - replace competitor analysis
async def _get_competitor_data(self, domain: str) -> Dict:
    import aiohttp
    
    # Using DataForSEO (cheaper, pay-per-use)
    login = os.environ['DATAFORSEO_LOGIN']
    password = os.environ['DATAFORSEO_PASSWORD']
    auth = aiohttp.BasicAuth(login, password)
    
    async with aiohttp.ClientSession(auth=auth) as session:
        # Get organic keywords
        payload = [{
            "target": domain,
            "location_name": "India",
            "language_name": "English",
            "limit": 1000
        }]
        async with session.post(
            "https://api.dataforseo.com/v3/dataforseo_labs/google/keywords_for_site/live",
            json=payload
        ) as resp:
            keywords = await resp.json()
        
        # Get backlinks
        payload = [{"target": domain, "limit": 100}]
        async with session.post(
            "https://api.dataforseo.com/v3/backlinks/summary/live",
            json=payload
        ) as resp:
            backlinks = await resp.json()
    
    return self._process_competitor_data(keywords, backlinks)
```

### 5. Keyword Intelligence → Real Search Volume/Difficulty
```python
# agents/keyword_intelligence.py - replace _estimate_volume/difficulty
async def _get_real_metrics(self, keywords: List[str]) -> Dict:
    """Get real search volume and difficulty from DataForSEO"""
    import aiohttp
    
    login = os.environ['DATAFORSEO_LOGIN']
    password = os.environ['DATAFORSEO_PASSWORD']
    auth = aiohttp.BasicAuth(login, password)
    
    # Batch keywords in chunks of 100
    chunks = [keywords[i:i+100] for i in range(0, len(keywords), 100)]
    results = {}
    
    async with aiohttp.ClientSession(auth=auth) as session:
        for chunk in chunks:
            payload = [{
                "keywords": chunk,
                "location_name": "India",
                "language_name": "English"
            }]
            async with session.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                json=payload
            ) as resp:
                data = await resp.json()
                for item in data.get('tasks', [{}])[0].get('result', []):
                    results[item['keyword']] = {
                        'volume': item.get('search_volume', 0),
                        'difficulty': item.get('competition', 0) * 100,
                        'cpc': item.get('cpc', 0)
                    }
    
    return results
```

---

## Installation Steps

```bash
# 1. Install required packages
cd seo_automation
pip install google-api-python-client google-auth aiohttp python-dotenv

# 2. Add to requirements.txt
google-api-python-client>=2.100
google-auth>=2.23
aiohttp>=3.9
python-dotenv>=1.0

# 3. Load env in main.py
from dotenv import load_dotenv
load_dotenv()  # Add at top of main.py

# 4. Copy .env.example to .env and fill in keys
cp .env.example .env
```

---

## Priority Order (Start Here)

| Priority | API | Cost | Impact |
|----------|-----|------|--------|
| 1 | **GSC** | Free | Real traffic/ranking data |
| 2 | **SerpBear** | Free (self-hosted) | Daily rank tracking |
| 3 | **PageSpeed** | Free | Real CWV |
| 4 | **DataForSEO** | ~$0.001/keyword | Volume, difficulty, competitor data |
| 5 | **SerpAPI** | $50-200/mo | SERP features, PAA, local pack |
| 6 | **Ahrefs/SEMrush** | $99-500/mo | Backlinks, deep competitor intel |

---

## Quick Test: Verify GSC Works

```bash
cd seo_automation
python -c "
import os, json
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    os.environ.get('GSC_CREDENTIALS_PATH', 'config/gsc_credentials.json'),
    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
)
service = build('searchconsole', 'v1', credentials=creds)

# List sites
sites = service.sites().list().execute()
print('GSC Sites:', json.dumps(sites, indent=2))

# Query test
resp = service.searchanalytics().query(
    siteUrl=os.environ.get('GSC_PROPERTY', 'sc-domain:gorentals.com'),
    body={'startDate': '2026-07-14', 'endDate': '2026-07-21', 'rowLimit': 5}
).execute()
print('Top queries:', json.dumps(resp.get('rows', []), indent=2))
"
```

---

## Cost Estimate (Monthly)

| Service | Cost | Notes |
|---------|------|-------|
| GSC | $0 | Free |
| SerpBear (VPS) | $5-10 | DigitalOcean droplet |
| PageSpeed | $0 | Free tier |
| DataForSEO | $20-50 | Pay-per-use, ~10k keywords |
| SerpAPI | $50-200 | If need SERP features |
| **Total** | **$25-60/mo** | Production-ready |

---

## Next Steps

1. **Week 1:** Set up GSC + SerpBear (free)
2. **Week 2:** Add DataForSEO for keyword volume/difficulty + competitor data
3. **Week 3:** Integrate PageSpeed for real CWV
4. **Week 4:** Add SerpAPI if SERP features needed
5. **Ongoing:** Monitor API quotas, add caching layer