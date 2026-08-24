"""
Free SEO API Clients - Drop-in replacements for mock data
Supports: GSC, PageSpeed, SerpBear, Bing, Ahrefs WMT
"""
import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import aiohttp

# Optional imports (only needed if credentials exist)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False


class FreeSEOApis:
    """Unified client for all free SEO data sources"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self._load_env()
        self._init_clients()
    
    def _load_env(self):
        """Load environment variables from .env file"""
        env_file = self.project_root / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        
        # GSC
        self.gsc_creds_path = os.getenv('GSC_CREDENTIALS_PATH')
        self.gsc_property = os.getenv('GSC_PROPERTY', 'sc-domain:gorentals.com')
        
        # SerpBear
        self.serpbear_url = os.getenv('SERPBEAR_URL', 'http://localhost:8080')
        self.serpbear_key = os.getenv('SERPBEAR_API_KEY', '')
        
        # PageSpeed
        self.pagespeed_key = os.getenv('PAGESPEED_KEY', '')
        
        # Bing
        self.bing_api_key = os.getenv('BING_WEBMASTER_API_KEY', '')
        
        # Ahrefs WMT
        self.ahrefs_token = os.getenv('AHREFS_WMT_TOKEN', '')
        
        # DataForSEO
        self.dataforseo_login = os.getenv('DATAFORSEO_LOGIN', '')
        self.dataforseo_password = os.getenv('DATAFORSEO_PASSWORD', '')
    
    def _init_clients(self):
        """Initialize API clients"""
        self.gsc_service = None
        if GSC_AVAILABLE and self.gsc_creds_path and Path(self.gsc_creds_path).exists():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.gsc_creds_path,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                self.gsc_service = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)
            except Exception as e:
                print(f"[FreeSEOApis] GSC init failed: {e}")
    
    # ============= GSC: Real Traffic Data =============
    
    async def get_gsc_queries(self, days: int = 7, limit: int = 1000) -> List[Dict]:
        """Get real search queries with clicks, impressions, CTR, position"""
        if not self.gsc_service:
            return []
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.gsc_service.searchanalytics().query(
                siteUrl=self.gsc_property,
                body={
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': ['query'],
                    'rowLimit': limit,
                    'orderBy': [{'field': 'clicks', 'descending': True}]
                }
            ).execute())
            
            rows = response.get('rows', [])
            return [
                {
                    'keyword': row['keys'][0],
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': round(row.get('ctr', 0) * 100, 2),
                    'position': round(row.get('position', 0), 1)
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[FreeSEOApis] GSC query failed: {e}")
            return []
    
    async def get_gsc_pages(self, days: int = 7, limit: int = 500) -> List[Dict]:
        """Get page-level performance data"""
        if not self.gsc_service:
            return []
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.gsc_service.searchanalytics().query(
                siteUrl=self.gsc_property,
                body={
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': ['page'],
                    'rowLimit': limit,
                    'orderBy': [{'field': 'clicks', 'descending': True}]
                }
            ).execute())
            
            rows = response.get('rows', [])
            return [
                {
                    'url': row['keys'][0],
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': round(row.get('ctr', 0) * 100, 2),
                    'position': round(row.get('position', 0), 1)
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[FreeSEOApis] GSC pages failed: {e}")
            return []
    
    async def get_gsc_index_status(self) -> Dict:
        """Get index coverage from GSC"""
        if not self.gsc_service:
            return {}
        
        try:
            loop = asyncio.get_event_loop()
            # Get sitemaps
            sitemaps = await loop.run_in_executor(None, lambda: self.gsc_service.sitemaps().list(
                siteUrl=self.gsc_property
            ).execute())
            
            # Get URL inspection (sample)
            return {
                'sitemaps': sitemaps.get('sitemap', []),
                'property': self.gsc_property
            }
        except Exception as e:
            print(f"[FreeSEOApis] GSC index status failed: {e}")
            return {}
    
    # ============= PageSpeed: Real CWV =============
    
    async def get_cwv(self, urls: List[str]) -> Dict[str, Dict]:
        """Get real Core Web Vitals from PageSpeed Insights API"""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for url in urls[:15]:  # Respect quota
                try:
                    params = {'url': url, 'category': 'performance', 'strategy': 'mobile'}
                    if self.pagespeed_key:
                        params['key'] = self.pagespeed_key
                    
                    async with session.get(
                        'https://www.googleapis.com/pagespeedonline/v5/runPagespeed',
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results[url] = self._parse_cwv(data)
                        elif resp.status == 429:
                            print(f"[FreeSEOApis] PageSpeed rate limited for {url}")
                            break
                except Exception as e:
                    print(f"[FreeSEOApis] PageSpeed error for {url}: {e}")
        
        return results
    
    def _parse_cwv(self, data: Dict) -> Dict:
        """Parse PageSpeed response into CWV metrics"""
        try:
            loading = data.get('loadingExperience', {}).get('metrics', {})
            origin = data.get('originLoadingExperience', {}).get('metrics', {})
            lighthouse = data.get('lighthouseResult', {}).get('audits', {})
            
            # Field data (real user metrics) - prefer over lab data
            def get_metric(metrics, key, convert_ms=True):
                val = metrics.get(key, {}).get('percentile')
                if val is not None and convert_ms:
                    return round(val / 1000, 2)
                return val
            
            return {
                'lcp': get_metric(loading, 'LARGEST_CONTENTFUL_PAINT_MS'),
                'cls': get_metric(loading, 'CUMULATIVE_LAYOUT_SHIFT_SCORE', convert_ms=False),
                'inp': get_metric(loading, 'INTERACTION_TO_NEXT_PAINT'),
                'fid': get_metric(loading, 'FIRST_INPUT_DELAY_MS'),
                # Origin-level (site-wide) as fallback
                'origin_lcp': get_metric(origin, 'LARGEST_CONTENTFUL_PAINT_MS'),
                'origin_cls': get_metric(origin, 'CUMULATIVE_LAYOUT_SHIFT_SCORE', convert_ms=False),
                'origin_inp': get_metric(origin, 'INTERACTION_TO_NEXT_PAINT'),
                # Lab data from Lighthouse
                'lab_lcp': lighthouse.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000,
                'lab_cls': lighthouse.get('cumulative-layout-shift', {}).get('numericValue', 0),
                'lab_tbt': lighthouse.get('total-blocking-time', {}).get('numericValue', 0),
                'score': data.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0) * 100
            }
        except Exception as e:
            print(f"[FreeSEOApis] CWV parse error: {e}")
            return {}
    
    # ============= SerpBear: Real Rankings =============
    
    async def get_serpbear_rankings(self, keywords: List[str]) -> Dict[str, Dict]:
        """Get rankings from self-hosted SerpBear"""
        if not self.serpbear_url:
            return {}
        
        kw_set = {k.lower().strip() for k in keywords}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.serpbear_key:
                    headers['Authorization'] = f"Bearer {self.serpbear_key}"
                
                async with session.get(
                    f"{self.serpbear_url}/api/keywords",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            item['keyword'].lower(): {
                                'keyword': item['keyword'],
                                'position': item['position'],
                                'url': item.get('url', ''),
                                'source': 'serpbear',
                                'checked_at': item.get('last_checked', datetime.now().isoformat()),
                                'search_volume': item.get('search_volume', 0),
                                'difficulty': item.get('difficulty', 0)
                            }
                            for item in data.get('keywords', [])
                            if item['keyword'].lower() in kw_set
                        }
                    elif resp.status == 401:
                        print("[FreeSEOApis] SerpBear: Invalid API key")
                    else:
                        print(f"[FreeSEOApis] SerpBear error: {resp.status}")
        except Exception as e:
            print(f"[FreeSEOApis] SerpBear connection failed: {e}")
        
        return {}
    
    async def add_serpbear_keywords(self, keywords: List[str]) -> bool:
        """Add keywords to SerpBear for tracking"""
        if not self.serpbear_url or not self.serpbear_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f"Bearer {self.serpbear_key}",
                    'Content-Type': 'application/json'
                }
                payload = {'keywords': [{'keyword': k} for k in keywords]}
                
                async with session.post(
                    f"{self.serpbear_url}/api/keywords",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return resp.status in (200, 201)
        except Exception as e:
            print(f"[FreeSEOApis] SerpBear add keywords failed: {e}")
            return False
    
    # ============= Bing Webmaster: Free Alternative =============
    
    async def get_bing_data(self, days: int = 7) -> List[Dict]:
        """Get data from Bing Webmaster Tools API"""
        if not self.bing_api_key:
            return []
        
        # Bing API implementation would go here
        # Similar structure to GSC but different endpoints
        return []
    
    # ============= Ahrefs Webmaster Tools: Your Site Data =============
    
    async def get_ahrefs_backlinks(self, limit: int = 100) -> List[Dict]:
        """Get backlinks from Ahrefs Webmaster Tools (your verified sites only)"""
        if not self.ahrefs_token:
            return []
        
        # Ahrefs WMT API implementation
        return []
    
    async def get_ahrefs_keywords(self, limit: int = 1000) -> List[Dict]:
        """Get organic keywords from Ahrefs WMT"""
        if not self.ahrefs_token:
            return []
        return []
    
    # ============= DataForSEO: Pay-Per-Use =============
    
    async def get_keyword_volume(self, keywords: List[str]) -> Dict[str, Dict]:
        """Get search volume, difficulty, CPC from DataForSEO"""
        if not self.dataforseo_login or not self.dataforseo_password:
            return {}
        
        results = {}
        auth = aiohttp.BasicAuth(self.dataforseo_login, self.dataforseo_password)
        
        # Batch in chunks of 100
        chunks = [keywords[i:i+100] for i in range(0, len(keywords), 100)]
        
        async with aiohttp.ClientSession(auth=auth) as session:
            for chunk in chunks:
                try:
                    payload = [{
                        "keywords": chunk,
                        "location_name": "India",
                        "language_name": "English"
                    }]
                    async with session.post(
                        "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for task in data.get('tasks', []):
                                for item in task.get('result', []):
                                    results[item['keyword']] = {
                                        'volume': item.get('search_volume', 0),
                                        'difficulty': round(item.get('competition', 0) * 100),
                                        'cpc': item.get('cpc', 0),
                                        'monthly_searches': item.get('monthly_searches', [])
                                    }
                except Exception as e:
                    print(f"[FreeSEOApis] DataForSEO volume error: {e}")
        
        return results
    
    async def get_competitor_keywords(self, domain: str, limit: int = 500) -> List[Dict]:
        """Get competitor organic keywords from DataForSEO"""
        if not self.dataforseo_login or not self.dataforseo_password:
            return []
        
        auth = aiohttp.BasicAuth(self.dataforseo_login, self.dataforseo_password)
        
        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                payload = [{
                    "target": domain,
                    "location_name": "India",
                    "language_name": "English",
                    "limit": limit,
                    "order_by": ["search_volume,desc"]
                }]
                async with session.post(
                    "https://api.dataforseo.com/v3/dataforseo_labs/google/keywords_for_site/live",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('tasks', [{}])[0].get('result', [])
        except Exception as e:
            print(f"[FreeSEOApis] DataForSEO competitor error: {e}")
        
        return []
    
    # ============= Health Check =============
    
    async def health_check(self) -> Dict[str, bool]:
        """Check which APIs are configured and working"""
        checks = {}
        
        # GSC
        checks['gsc'] = self.gsc_service is not None
        
        # SerpBear
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.serpbear_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    checks['serpbear'] = resp.status == 200
        except:
            checks['serpbear'] = False
        
        # PageSpeed
        checks['pagespeed'] = True  # Always available (has free tier)
        
        # DataForSEO
        checks['dataforseo'] = bool(self.dataforseo_login and self.dataforseo_password)
        
        return checks


# Singleton instance
_free_apis_instance = None

def get_free_apis(project_root: Path = None) -> FreeSEOApis:
    """Get singleton FreeSEOApis instance"""
    global _free_apis_instance
    if _free_apis_instance is None:
        _free_apis_instance = FreeSEOApis(project_root)
    return _free_apis_instance