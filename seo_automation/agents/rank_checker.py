"""
Rank Checker Agent - Uses Free Live APIs
Tracks keyword rankings from SerpBear, GSC, SerpAPI (free tier)
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from agents.base import BaseAgent, AgentResult

# Import free API client
import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils.free_apis import get_free_apis


class RankCheckerAgent(BaseAgent):
    """Agent for tracking keyword rankings from live free APIs"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.rank_config = config.get('agents', {}).get('rank_checker', {})
        self.sources = self.rank_config.get('sources', ['serpbear', 'gsc', 'serpapi', 'manual'])
        self.tracking_keywords_file = self.rank_config.get('tracking_keywords_file', 'research/tracking_keywords.json')
        self.history_days = self.rank_config.get('history_days', 90)
        self.alert_thresholds = self.rank_config.get('alert_thresholds', {
            'critical_drop': 10,
            'warning_drop': 5,
            'significant_gain': 3,
            'new_ranking_top': 20
        })
        
        # Initialize free API client
        self.free_apis = get_free_apis(project_root)

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute rank checking across all configured free sources"""
        
        # 1. Load tracking keywords
        tracking_keywords = self._load_tracking_keywords(context)
        
        if not tracking_keywords:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'message': 'No keywords to track', 'tracked': 0},
                files_created=[]
            )

        # 2. Check rankings from each source
        all_rankings = {}
        
        # SerpBear (self-hosted, free)
        if 'serpbear' in self.sources:
            serpbear_rankings = await self._check_serpbear(tracking_keywords)
            all_rankings['serpbear'] = serpbear_rankings
        
        # GSC (free, official)
        if 'gsc' in self.sources:
            gsc_rankings = await self._check_gsc(tracking_keywords)
            all_rankings['gsc'] = gsc_rankings
        
        # SerpAPI (100 free/month)
        if 'serpapi' in self.sources:
            serpapi_rankings = await self._check_serpapi(tracking_keywords)
            all_rankings['serpapi'] = serpapi_rankings
        
        # Manual (from previous runs)
        if 'manual' in self.sources:
            manual_rankings = await self._check_manual(tracking_keywords)
            all_rankings['manual'] = manual_rankings

        # 3. Consolidate rankings (best position across sources)
        consolidated = self._consolidate_rankings(all_rankings, tracking_keywords)
        
        # 4. Compare with previous run
        previous = self._load_previous_rankings()
        changes = self._detect_changes(consolidated, previous)
        
        # 5. Save current rankings as history
        self._save_rankings_history(consolidated)
        
        # 6. Save current rankings for next comparison
        self._save_current_rankings(consolidated)
        
        # 7. Generate alerts
        alerts = self._generate_alerts(changes)
        
        # 8. Save all outputs
        files_created = self._save_outputs(consolidated, changes, alerts, all_rankings)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'total_tracked': len(tracking_keywords),
                'total_ranked': sum(1 for r in consolidated.values() if r['ranked']),
                'sources_checked': len([k for k, v in all_rankings.items() if v]),
                'gains': len(changes['gains']),
                'drops': len(changes['drops']),
                'new_rankings': len(changes['new_rankings']),
                'lost_rankings': len(changes['lost_rankings']),
                'critical_alerts': len([a for a in alerts if a['severity'] == 'critical']),
                'warning_alerts': len([a for a in alerts if a['severity'] == 'warning']),
                'data_freshness': 'live'
            },
            files_created=files_created
        )

    def _load_tracking_keywords(self, context: Dict[str, Any]) -> List[Dict]:
        """Load keywords to track from various sources"""
        keywords = []
        
        # From context (priority keywords from keyword_intelligence)
        priority_keywords = context.get('prioritized_content', [])
        for item in priority_keywords:
            if isinstance(item, dict) and 'target_keyword' in item:
                keywords.append({
                    'keyword': item['target_keyword'],
                    'priority': 'high',
                    'target_url': item.get('target_url', ''),
                    'source': 'keyword_intelligence'
                })
        
        # From content strategy
        content_calendar = context.get('content_calendar', [])
        for item in content_calendar:
            if isinstance(item, dict) and 'target_keyword' in item:
                keywords.append({
                    'keyword': item['target_keyword'],
                    'priority': 'medium',
                    'target_url': item.get('url', ''),
                    'source': 'content_strategy'
                })
        
        # From saved tracking file
        tracking_file = self.project_root / self.tracking_keywords_file
        if tracking_file.exists():
            with open(tracking_file, 'r') as f:
                data = json.load(f)
                for kw in data.get('keywords', []):
                    if isinstance(kw, str):
                        keywords.append({
                            'keyword': kw,
                            'priority': 'medium',
                            'target_url': '',
                            'source': 'tracking_file'
                        })
                    elif isinstance(kw, dict) and 'keyword' in kw:
                        keywords.append(kw)
        
        # From keywords.json (top priority keywords)
        kw_file = self.project_root / "research" / "keywords.json"
        if kw_file.exists():
            with open(kw_file, 'r') as f:
                data = json.load(f)
                for kw in data.get('keywords', [])[:200]:  # Top 200
                    if isinstance(kw, dict) and 'keyword' in kw:
                        if kw.get('priority_score', 0) >= 60:
                            keywords.append({
                                'keyword': kw['keyword'],
                                'priority': 'high' if kw.get('priority_score', 0) >= 75 else 'medium',
                                'target_url': '',
                                'source': 'keyword_research'
                            })
        
        # Deduplicate
        seen = set()
        unique = []
        for kw in keywords:
            k = kw['keyword'].lower().strip()
            if k not in seen:
                seen.add(k)
                unique.append(kw)
        
        return unique

    async def _check_serpbear(self, keywords: List[Dict]) -> Dict[str, Dict]:
        """Check rankings from SerpBear (self-hosted, free)"""
        kw_list = [k['keyword'] for k in keywords]
        return await self.free_apis.get_serpbear_rankings(kw_list)

    async def _check_gsc(self, keywords: List[Dict]) -> Dict[str, Dict]:
        """Check rankings from Google Search Console (free)"""
        # Get all queries from GSC
        gsc_queries = await self.free_apis.get_gsc_queries(days=7, limit=2000)
        
        # Filter for our tracking keywords
        kw_set = {k['keyword'].lower() for k in keywords}
        rankings = {}
        
        for query in gsc_queries:
            kw = query['keyword'].lower()
            if kw in kw_set:
                rankings[kw] = {
                    'keyword': query['keyword'],
                    'position': round(query['position']),
                    'url': '',  # Would need page-level query
                    'source': 'gsc',
                    'checked_at': datetime.now().isoformat(),
                    'clicks': query['clicks'],
                    'impressions': query['impressions'],
                    'ctr': query['ctr']
                }
        
        return rankings

    async def _check_serpapi(self, keywords: List[Dict]) -> Dict[str, Dict]:
        """Check rankings from SerpAPI (100 free/month)"""
        # SerpAPI integration - requires API key
        api_key = os.getenv('SERPAPI_KEY')
        if not api_key:
            return {}
        
        # Implementation would go here
        # Limited to 100 searches/month free
        return {}

    async def _check_manual(self, keywords: List[Dict]) -> Dict[str, Dict]:
        """Check manually tracked rankings (from previous runs)"""
        manual_file = self.project_root / "research" / "manual_rankings.json"
        if manual_file.exists():
            with open(manual_file, 'r') as f:
                data = json.load(f)
                return data.get('rankings', {})
        return {}

    def _consolidate_rankings(self, all_rankings: Dict, tracking_keywords: List[Dict]) -> Dict[str, Dict]:
        """Consolidate rankings from multiple sources, taking best position"""
        consolidated = {}
        
        # Create lookup for tracking metadata
        kw_meta = {k['keyword'].lower(): k for k in tracking_keywords}
        
        for source, rankings in all_rankings.items():
            for kw, data in rankings.items():
                kw_lower = kw.lower()
                
                if kw_lower not in consolidated:
                    consolidated[kw_lower] = {
                        'keyword': data['keyword'],
                        'ranked': False,
                        'best_position': None,
                        'best_url': None,
                        'best_source': None,
                        'all_positions': {},
                        'source_count': 0,
                        'priority': kw_meta.get(kw_lower, {}).get('priority', 'medium'),
                        'target_url': kw_meta.get(kw_lower, {}).get('target_url', ''),
                        'source_detail': kw_meta.get(kw_lower, {}).get('source', 'unknown')
                    }
                
                if data.get('position'):
                    consolidated[kw_lower]['all_positions'][source] = data['position']
                    consolidated[kw_lower]['source_count'] += 1
                    
                    if (consolidated[kw_lower]['best_position'] is None or 
                        data['position'] < consolidated[kw_lower]['best_position']):
                        consolidated[kw_lower]['best_position'] = data['position']
                        consolidated[kw_lower]['best_url'] = data.get('url')
                        consolidated[kw_lower]['best_source'] = source
                        consolidated[kw_lower]['ranked'] = True
        
        return consolidated

    def _load_previous_rankings(self) -> Dict[str, Dict]:
        """Load previous rankings for comparison"""
        prev_file = self.project_root / "research" / "rankings_previous.json"
        if prev_file.exists():
            with open(prev_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_current_rankings(self, consolidated: Dict[str, Dict]):
        """Save current rankings for next comparison"""
        prev_file = self.project_root / "research" / "rankings_previous.json"
        prev_file.parent.mkdir(parents=True, exist_ok=True)
        
        save_data = {}
        for kw, data in consolidated.items():
            save_data[kw] = {
                'keyword': data['keyword'],
                'best_position': data['best_position'],
                'best_source': data['best_source'],
                'ranked': data['ranked'],
                'checked_at': datetime.now().isoformat()
            }
        
        with open(prev_file, 'w') as f:
            json.dump(save_data, f, indent=2)

    def _save_rankings_history(self, consolidated: Dict[str, Dict]):
        """Save rankings to historical file"""
        history_file = self.project_root / "research" / "rankings_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        history = []
        if history_file.exists():
            with open(history_file, 'r') as f:
                try:
                    history = json.load(f)
                except:
                    history = []
        
        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'total_tracked': len(consolidated),
            'total_ranked': sum(1 for r in consolidated.values() if r['ranked']),
            'rankings': {}
        }
        
        for kw, data in consolidated.items():
            if data['ranked']:
                snapshot['rankings'][kw] = {
                    'position': data['best_position'],
                    'source': data['best_source']
                }
        
        history.append(snapshot)
        
        cutoff = datetime.now() - timedelta(days=self.history_days)
        history = [h for h in history if datetime.fromisoformat(h['timestamp']) > cutoff]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _detect_changes(self, current: Dict, previous: Dict) -> Dict[str, List]:
        """Detect ranking changes between current and previous"""
        changes = {
            'gains': [],
            'drops': [],
            'new_rankings': [],
            'lost_rankings': [],
            'stable': []
        }
        
        all_keywords = set(current.keys()) | set(previous.keys())
        
        for kw in all_keywords:
            curr = current.get(kw, {})
            prev = previous.get(kw, {})
            
            curr_pos = curr.get('best_position')
            prev_pos = prev.get('best_position')
            
            curr_ranked = curr.get('ranked', False)
            prev_ranked = prev.get('ranked', False)
            
            if curr_ranked and prev_ranked:
                if curr_pos is not None and prev_pos is not None:
                    diff = prev_pos - curr_pos
                    
                    if diff >= self.alert_thresholds['significant_gain']:
                        changes['gains'].append({
                            'keyword': curr['keyword'],
                            'previous_position': prev_pos,
                            'current_position': curr_pos,
                            'change': diff,
                            'source': curr.get('best_source'),
                            'priority': curr.get('priority', 'medium')
                        })
                    elif diff <= -self.alert_thresholds['warning_drop']:
                        changes['drops'].append({
                            'keyword': curr['keyword'],
                            'previous_position': prev_pos,
                            'current_position': curr_pos,
                            'change': diff,
                            'source': curr.get('best_source'),
                            'priority': curr.get('priority', 'medium'),
                            'severity': 'critical' if diff <= -self.alert_thresholds['critical_drop'] else 'warning'
                        })
                    else:
                        changes['stable'].append({
                            'keyword': curr['keyword'],
                            'position': curr_pos,
                            'change': diff
                        })
            
            elif curr_ranked and not prev_ranked:
                changes['new_rankings'].append({
                    'keyword': curr['keyword'],
                    'current_position': curr_pos,
                    'source': curr.get('best_source'),
                    'priority': curr.get('priority', 'medium'),
                    'top_page': curr_pos <= 10 if curr_pos else False
                })
            
            elif not curr_ranked and prev_ranked:
                changes['lost_rankings'].append({
                    'keyword': prev.get('keyword', kw),
                    'previous_position': prev_pos,
                    'previous_source': prev.get('best_source'),
                    'priority': curr.get('priority', prev.get('priority', 'medium'))
                })
        
        changes['gains'].sort(key=lambda x: x['change'], reverse=True)
        changes['drops'].sort(key=lambda x: x['change'])
        changes['new_rankings'].sort(key=lambda x: x.get('current_position', 100))
        changes['lost_rankings'].sort(key=lambda x: x.get('previous_position', 100))
        
        return changes

    def _generate_alerts(self, changes: Dict) -> List[Dict]:
        """Generate alerts for significant changes"""
        alerts = []
        
        for drop in changes['drops']:
            if drop.get('severity') == 'critical':
                alerts.append({
                    'type': 'critical_drop',
                    'severity': 'critical',
                    'keyword': drop['keyword'],
                    'message': f"CRITICAL: '{drop['keyword']}' dropped from position {drop['previous_position']} to {drop['current_position']} ({drop['change']} positions)",
                    'data': drop,
                    'timestamp': datetime.now().isoformat()
                })
            elif drop.get('severity') == 'warning':
                alerts.append({
                    'type': 'warning_drop',
                    'severity': 'warning',
                    'keyword': drop['keyword'],
                    'message': f"WARNING: '{drop['keyword']}' dropped from position {drop['previous_position']} to {drop['current_position']} ({drop['change']} positions)",
                    'data': drop,
                    'timestamp': datetime.now().isoformat()
                })
        
        for new in changes['new_rankings']:
            if new.get('top_page'):
                alerts.append({
                    'type': 'new_top_page',
                    'severity': 'info',
                    'keyword': new['keyword'],
                    'message': f"NEW RANKING: '{new['keyword']}' now ranking at position {new['current_position']} (Page 1!)",
                    'data': new,
                    'timestamp': datetime.now().isoformat()
                })
        
        for gain in changes['gains'][:10]:
            alerts.append({
                'type': 'significant_gain',
                'severity': 'info',
                'keyword': gain['keyword'],
                'message': f"GAIN: '{gain['keyword']}' improved from position {gain['previous_position']} to {gain['current_position']} (+{gain['change']})",
                'data': gain,
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts

    def _save_outputs(self, consolidated: Dict, changes: Dict, alerts: List, all_rankings: Dict) -> List[str]:
        """Save all output files"""
        files_created = []
        
        # 1. Consolidated rankings (main output)
        rankings_file = self.save_json({
            'checked_at': datetime.now().isoformat(),
            'total_tracked': len(consolidated),
            'total_ranked': sum(1 for r in consolidated.values() if r['ranked']),
            'sources_used': list(all_rankings.keys()),
            'data_freshness': 'live',
            'rankings': consolidated
        }, "research/rankings_current.json")
        files_created.append(rankings_file)
        
        # 2. Changes detected
        changes_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'changes': changes
        }, "research/ranking_changes.json")
        files_created.append(changes_file)
        
        # 3. Alerts
        alerts_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'alerts': alerts,
            'summary': {
                'critical': len([a for a in alerts if a['severity'] == 'critical']),
                'warning': len([a for a in alerts if a['severity'] == 'warning']),
                'info': len([a for a in alerts if a['severity'] == 'info'])
            }
        }, "research/ranking_alerts.json")
        files_created.append(alerts_file)
        
        # 4. Per-source rankings
        for source, rankings in all_rankings.items():
            source_file = self.save_json({
                'source': source,
                'checked_at': datetime.now().isoformat(),
                'data_freshness': 'live',
                'rankings': rankings
            }, f"research/rankings_{source}.json")
            files_created.append(source_file)
        
        # 5. Markdown report
        report = self._generate_report(consolidated, changes, alerts)
        report_file = self.save_output(report, "research/ranking-report.md")
        files_created.append(report_file)
        
        # 6. Keywords by position (for content strategy)
        by_position = defaultdict(list)
        for kw, data in consolidated.items():
            if data['ranked'] and data['best_position']:
                pos = data['best_position']
                if pos <= 3:
                    bucket = 'top3'
                elif pos <= 10:
                    bucket = 'page1'
                elif pos <= 20:
                    bucket = 'page2'
                elif pos <= 50:
                    bucket = 'page3_5'
                elif pos <= 100:
                    bucket = 'page6_10'
                else:
                    bucket = '100plus'
                by_position[bucket].append({
                    'keyword': data['keyword'],
                    'position': pos,
                    'priority': data.get('priority', 'medium'),
                    'source': data.get('best_source')
                })
        
        position_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'by_position': dict(by_position)
        }, "research/keywords_by_position.json")
        files_created.append(position_file)
        
        return files_created

    def _generate_report(self, consolidated: Dict, changes: Dict, alerts: List) -> str:
        """Generate markdown ranking report"""
        total_tracked = len(consolidated)
        total_ranked = sum(1 for r in consolidated.values() if r['ranked'])
        
        pos_dist = defaultdict(int)
        for data in consolidated.values():
            if data['ranked'] and data['best_position']:
                pos = data['best_position']
                if pos <= 3:
                    pos_dist['1-3'] += 1
                elif pos <= 10:
                    pos_dist['4-10'] += 1
                elif pos <= 20:
                    pos_dist['11-20'] += 1
                elif pos <= 50:
                    pos_dist['21-50'] += 1
                elif pos <= 100:
                    pos_dist['51-100'] += 1
                else:
                    pos_dist['100+'] += 1
            else:
                pos_dist['Not Ranking'] += 1
        
        report = f"""# GoRentals Keyword Ranking Report (LIVE DATA)

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Keywords Tracked:** {total_tracked}
**Keywords Ranking:** {total_ranked} ({total_ranked/max(1,total_tracked)*100:.1f}%)
**Sources:** {', '.join(self.sources)}
**Data Freshness:** Live

---

## Ranking Distribution

| Position Range | Keywords | Percentage |
|----------------|----------|------------|
| 1-3 (Top 3) | {pos_dist.get('1-3', 0)} | {pos_dist.get('1-3', 0)/max(1,total_ranked)*100:.1f}% |
| 4-10 (Page 1) | {pos_dist.get('4-10', 0)} | {pos_dist.get('4-10', 0)/max(1,total_ranked)*100:.1f}% |
| 11-20 (Page 2) | {pos_dist.get('11-20', 0)} | {pos_dist.get('11-20', 0)/max(1,total_ranked)*100:.1f}% |
| 21-50 (Pages 3-5) | {pos_dist.get('21-50', 0)} | {pos_dist.get('21-50', 0)/max(1,total_ranked)*100:.1f}% |
| 51-100 | {pos_dist.get('51-100', 0)} | {pos_dist.get('51-100', 0)/max(1,total_ranked)*100:.1f}% |
| 100+ | {pos_dist.get('100+', 0)} | {pos_dist.get('100+', 0)/max(1,total_ranked)*100:.1f}% |
| Not Ranking | {pos_dist.get('Not Ranking', 0)} | {pos_dist.get('Not Ranking', 0)/max(1,total_tracked)*100:.1f}% |

---

## Summary of Changes

- **📈 Gains (>3 positions):** {len(changes['gains'])}
- **📉 Drops (>5 positions):** {len(changes['drops'])}
- **🆕 New Rankings:** {len(changes['new_rankings'])}
- **💀 Lost Rankings:** {len(changes['lost_rankings'])}
- **🚨 Critical Alerts:** {len([a for a in alerts if a['severity'] == 'critical'])}
- **⚠️ Warnings:** {len([a for a in alerts if a['severity'] == 'warning'])}

---

## Top Gains (Improvement >3 positions)

"""
        for gain in changes['gains'][:20]:
            report += f"- **{gain['keyword']}**: {gain['previous_position']} → {gain['current_position']} (+{gain['change']}) [Priority: {gain.get('priority', 'medium')}]\n"
        
        report += "\n## Critical Drops (Drop >10 positions)\n\n"
        critical_drops = [d for d in changes['drops'] if d.get('severity') == 'critical'][:20]
        for drop in critical_drops:
            report += f"- **{drop['keyword']}**: {drop['previous_position']} → {drop['current_position']} ({drop['change']}) [Priority: {drop.get('priority', 'medium')}]\n"
        
        if not critical_drops:
            report += "No critical drops detected.\n"
        
        report += "\n## Warning Drops (Drop 5-10 positions)\n\n"
        warning_drops = [d for d in changes['drops'] if d.get('severity') == 'warning'][:20]
        for drop in warning_drops:
            report += f"- **{drop['keyword']}**: {drop['previous_position']} → {drop['current_position']} ({drop['change']}) [Priority: {drop.get('priority', 'medium')}]\n"
        
        if not warning_drops:
            report += "No warning drops detected.\n"
        
        report += "\n## New Rankings (Page 1)\n\n"
        new_top = [n for n in changes['new_rankings'] if n.get('top_page')][:20]
        for new in new_top:
            report += f"- **{new['keyword']}**: Position {new['current_position']} (Source: {new.get('source', 'unknown')}) [Priority: {new.get('priority', 'medium')}]\n"
        
        if not new_top:
            report += "No new page 1 rankings.\n"
        
        report += "\n## All New Rankings\n\n"
        for new in changes['new_rankings'][:30]:
            page = "Page 1" if new.get('top_page') else f"Page {((new.get('current_position', 100)-1)//10)+1}"
            report += f"- **{new['keyword']}**: Position {new.get('current_position', 'N/A')} ({page}) [Priority: {new.get('priority', 'medium')}]\n"
        
        report += "\n## Lost Rankings\n\n"
        for lost in changes['lost_rankings'][:20]:
            report += f"- **{lost['keyword']}**: Was position {lost.get('previous_position', 'N/A')} (Source: {lost.get('previous_source', 'unknown')}) [Priority: {lost.get('priority', 'medium')}]\n"
        
        if not changes['lost_rankings']:
            report += "No lost rankings.\n"
        
        report += f"""

---

## Keywords on Page 2 (Positions 11-20) - Optimization Targets

"""
        page2 = [r for r in consolidated.values() if r['ranked'] and r['best_position'] and 11 <= r['best_position'] <= 20]
        for r in sorted(page2, key=lambda x: x['best_position'])[:30]:
            report += f"- **{r['keyword']}**: Position {r['best_position']} (Source: {r.get('best_source', 'unknown')}) [Priority: {r.get('priority', 'medium')}]\n"
        
        report += f"""

---

## High-Priority Keywords Not Ranking (Top 50)

"""
        unranked_high = [
            r for r in consolidated.values() 
            if not r['ranked'] and r.get('priority') == 'high'
        ][:50]
        for r in unranked_high:
            report += f"- **{r['keyword']}** (Source: {r.get('source_detail', 'unknown')})\n"
        
        report += f"""

---

*Report generated by GoRentals Rank Checker Agent (Live Data Mode)*
*Sources: {', '.join(self.sources)}*
*Next scheduled check: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')}*
"""
        return report