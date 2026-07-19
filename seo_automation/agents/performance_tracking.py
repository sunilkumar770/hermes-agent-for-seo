"""
Performance Tracking Agent
Tracks SEO performance metrics: clicks, impressions, CTR, position, indexed pages, etc.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class PerformanceTrackingAgent(BaseAgent):
    """Agent for tracking SEO performance metrics"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.perf_config = config.get('agents', {}).get('performance_tracking', {})
        self.metrics = self.perf_config.get('metrics', [
            'organic_clicks', 'impressions', 'ctr', 'average_position',
            'indexed_pages', 'crawl_errors', 'core_web_vitals',
            'backlinks', 'referring_domains', 'lost_rankings', 'conversions'
        ])
        self.frequency = self.perf_config.get('frequency', 'weekly')

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute performance tracking"""
        # In production, this would pull from GSC API, SerpBear, Ahrefs API, etc.
        # For now, generate comprehensive performance data
        
        metrics = self._collect_metrics()
        
        # Compare with previous period
        comparison = self._compare_periods(metrics)
        
        # Identify anomalies
        anomalies = self._detect_anomalies(metrics, comparison)
        
        # Top performers and losers
        top_performers = self._get_top_performers(metrics)
        biggest_losers = self._get_biggest_losers(comparison)
        
        # Keyword opportunities
        opportunities = self._identify_opportunities(metrics, comparison)
        
        # Technical health
        tech_health = self._assess_technical_health(metrics)
        
        # Save outputs
        files_created = []
        
        # Full metrics
        metrics_file = self.save_json({
            'collected_at': datetime.now().isoformat(),
            'period': 'weekly',
            'metrics': metrics
        }, "research/performance-metrics.json")
        files_created.append(metrics_file)
        
        # Comparison
        comp_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'comparison': comparison
        }, "research/performance-comparison.json")
        files_created.append(comp_file)
        
        # Anomalies
        anomaly_file = self.save_json({
            'detected_at': datetime.now().isoformat(),
            'anomalies': anomalies
        }, "research/performance-anomalies.json")
        files_created.append(anomaly_file)
        
        # Opportunities
        opp_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'opportunities': opportunities
        }, "research/performance-opportunities.json")
        files_created.append(opp_file)
        
        # Markdown report
        report = self._generate_report(metrics, comparison, anomalies, 
                                       top_performers, biggest_losers, 
                                       opportunities, tech_health)
        report_file = self.save_output(report, "research/performance-report.md")
        files_created.append(report_file)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'metrics_collected': len(metrics),
                'anomalies_detected': len(anomalies),
                'opportunities': len(opportunities),
                'health_score': tech_health.get('overall_score', 0)
            },
            files_created=files_created
        )

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect all SEO performance metrics"""
        # In production, these would come from:
        # - Google Search Console API
        # - SerpBear / SerpAPI for rankings
        # - Ahrefs / SEMrush API for backlinks
        # - PageSpeed Insights API for CWV
        # - Custom analytics for conversions
        
        # Simulated comprehensive metrics
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'period': 'weekly',
            
            # Traffic metrics
            'organic_clicks': 12500,
            'impressions': 450000,
            'ctr': 2.78,
            'average_position': 12.3,
            
            # Ranking distribution
            'ranking_distribution': {
                '1-3': 45,
                '4-10': 120,
                '11-20': 180,
                '21-50': 350,
                '51-100': 420,
                '100+': 1200
            },
            
            # Top keywords by clicks
            'top_keywords_by_clicks': [
                {'keyword': 'bike rental hyderabad', 'clicks': 1200, 'position': 2, 'ctr': 12.5},
                {'keyword': 'car rental hyderabad', 'clicks': 950, 'position': 3, 'ctr': 8.2},
                {'keyword': 'camera rental hyderabad', 'clicks': 420, 'position': 1, 'ctr': 18.5},
                {'keyword': 'self drive car rental hyderabad', 'clicks': 380, 'position': 2, 'ctr': 15.0},
                {'keyword': 'bike rental near me', 'clicks': 320, 'position': 4, 'ctr': 6.8},
                {'keyword': 'rent bike hyderabad', 'clicks': 280, 'position': 3, 'ctr': 9.1},
                {'keyword': 'car hire hyderabad', 'clicks': 250, 'position': 5, 'ctr': 5.5},
                {'keyword': 'wedding car rental hyderabad', 'clicks': 220, 'position': 1, 'ctr': 22.0},
                {'keyword': 'camera rental for wedding', 'clicks': 180, 'position': 2, 'ctr': 12.0},
                {'keyword': 'monthly bike rental hyderabad', 'clicks': 150, 'position': 2, 'ctr': 8.0}
            ],
            
            # Indexing
            'indexed_pages': 247,
            'submitted_sitemap_urls': 250,
            'crawl_errors': 3,
            'excluded_pages': 120,
            
            # Core Web Vitals
            'core_web_vitals': {
                'lcp': {'value': 2.1, 'target': 2.5, 'status': 'good', 'pages_affected': ['/rentals/', '/bikes/', '/cars/', '/cameras/']},
                'fid': {'value': 45, 'target': 100, 'status': 'good', 'pages_affected': []},
                'cls': {'value': 0.15, 'target': 0.1, 'status': 'needs_improvement', 'pages_affected': ['/rentals/category/', '/blog/']},
                'inp': {'value': 180, 'target': 200, 'status': 'good', 'pages_affected': []}
            },
            
            # Backlinks
            'backlinks': {
                'total': 1240,
                'referring_domains': 340,
                'dofollow': 850,
                'nofollow': 390,
                'new_this_week': 12,
                'lost_this_week': 3,
                'top_anchors': [
                    {'anchor': 'bike rental', 'count': 245},
                    {'anchor': 'car rental', 'count': 180},
                    {'anchor': 'GoRentals', 'count': 120},
                    {'anchor': 'bike rental hyderabad', 'count': 95},
                    {'anchor': 'rental marketplace', 'count': 80}
                ],
                'top_referring_domains': [
                    {'domain': 'justdial.com', 'links': 45, 'da': 78},
                    {'domain': 'sulekha.com', 'links': 38, 'da': 72},
                    {'domain': 'indiamart.com', 'links': 32, 'da': 70},
                    {'domain': 'facebook.com', 'links': 28, 'da': 96},
                    {'domain': 'google.com/maps', 'links': 25, 'da': 100}
                ]
            },
            
            # Conversions
            'conversions': {
                'total': 340,
                'rate': 2.72,
                'by_source': {
                    'organic': 280,
                    'direct': 45,
                    'referral': 15
                },
                'by_category': {
                    'bikes': 150,
                    'cars': 120,
                    'cameras': 45,
                    'party': 25
                },
                'avg_order_value': 2800
            },
            
            # Local SEO
            'local_seo': {
                'gbp_views': 12500,
                'gbp_searches': 8200,
                'gbp_actions': {
                    'calls': 120,
                    'directions': 340,
                    'website_visits': 850
                },
                'reviews': {
                    'total': 5200,
                    'average_rating': 4.8,
                    'this_week': 15
                }
            },
            
            # Revenue attribution
            'revenue': {
                'organic_revenue': 952000,
                'organic_roi': 4.2,
                'cost_per_acquisition': 420,
                'ltv': 8500
            }
        }

    def _compare_periods(self, current: Dict) -> Dict:
        """Compare current metrics with previous period"""
        # In production, load previous period data
        # For now, simulate comparison
        
        return {
            'organic_clicks': {'current': 12500, 'previous': 11800, 'change': 700, 'pct': 5.9},
            'impressions': {'current': 450000, 'previous': 435000, 'change': 15000, 'pct': 3.4},
            'ctr': {'current': 2.78, 'previous': 2.71, 'change': 0.07, 'pct': 2.6},
            'average_position': {'current': 12.3, 'previous': 12.8, 'change': -0.5, 'pct': -3.9},
            'indexed_pages': {'current': 247, 'previous': 242, 'change': 5, 'pct': 2.1},
            'crawl_errors': {'current': 3, 'previous': 5, 'change': -2, 'pct': -40.0},
            'backlinks': {'current': 1240, 'previous': 1215, 'change': 25, 'pct': 2.1},
            'referring_domains': {'current': 340, 'previous': 332, 'change': 8, 'pct': 2.4},
            'conversions': {'current': 340, 'previous': 315, 'change': 25, 'pct': 7.9},
            'conversion_rate': {'current': 2.72, 'previous': 2.67, 'change': 0.05, 'pct': 1.9},
            'organic_revenue': {'current': 952000, 'previous': 890000, 'change': 62000, 'pct': 7.0},
            'lcp': {'current': 2.1, 'previous': 2.4, 'change': -0.3, 'pct': -12.5},
            'cls': {'current': 0.15, 'previous': 0.18, 'change': -0.03, 'pct': -16.7},
            'gbp_views': {'current': 12500, 'previous': 11800, 'change': 700, 'pct': 5.9},
            'reviews': {'current': 5200, 'previous': 5185, 'change': 15, 'pct': 0.3}
        }

    def _detect_anomalies(self, metrics: Dict, comparison: Dict) -> List[Dict]:
        """Detect anomalies in metrics"""
        anomalies = []
        
        # Check for significant drops
        for metric, data in comparison.items():
            if isinstance(data, dict) and 'pct' in data:
                if data['pct'] < -20:  # 20% drop
                    anomalies.append({
                        'type': 'significant_drop',
                        'metric': metric,
                        'change': data['pct'],
                        'severity': 'critical' if data['pct'] < -50 else 'high',
                        'description': f"{metric} dropped {abs(data['pct']):.1f}% week-over-week"
                    })
                elif data['pct'] > 50:  # 50% spike
                    anomalies.append({
                        'type': 'significant_spike',
                        'metric': metric,
                        'change': data['pct'],
                        'severity': 'medium',
                        'description': f"{metric} spiked {data['pct']:.1f}% week-over-week"
                    })
        
        # Check CWV
        cwv = metrics.get('core_web_vitals', {})
        for metric, data in cwv.items():
            if data.get('status') == 'needs_improvement':
                anomalies.append({
                    'type': 'cwv_issue',
                    'metric': metric,
                    'value': data['value'],
                    'target': data['target'],
                    'pages_affected': data.get('pages_affected', []),
                    'severity': 'high'
                })
        
        # Check ranking distribution
        ranking = metrics.get('ranking_distribution', {})
        top3 = ranking.get('1-3', 0)
        if top3 < 40:
            anomalies.append({
                'type': 'ranking_concern',
                'metric': 'top_3_rankings',
                'current': top3,
                'threshold': 40,
                'severity': 'medium',
                'description': f"Only {top3} keywords in top 3 positions"
            })
        
        return anomalies

    def _get_top_performers(self, metrics: Dict) -> List[Dict]:
        """Get top performing keywords/pages"""
        return metrics.get('top_keywords_by_clicks', [])[:10]

    def _get_biggest_losers(self, comparison: Dict) -> List[Dict]:
        """Get biggest ranking losers"""
        losers = []
        for metric, data in comparison.items():
            if isinstance(data, dict) and 'change' in data and data['change'] < 0:
                losers.append({
                    'metric': metric,
                    'change': data['change'],
                    'pct': data['pct']
                })
        return sorted(losers, key=lambda x: x['change'])[:10]

    def _identify_opportunities(self, metrics: Dict, comparison: Dict) -> List[Dict]:
        """Identify SEO opportunities"""
        opportunities = []
        
        # Keywords on page 2
        ranking = metrics.get('ranking_distribution', {})
        page2 = ranking.get('11-20', 0)
        if page2 > 100:
            opportunities.append({
                'type': 'page_2_keywords',
                'count': page2,
                'action': 'Optimize 11-20 position keywords to reach page 1',
                'potential_traffic': 'High',
                'effort': 'Medium'
            })
        
        # Low CTR keywords in top 5
        top_kws = metrics.get('top_keywords_by_clicks', [])
        for kw in top_kws:
            if kw['position'] <= 5 and kw['ctr'] < 5:
                opportunities.append({
                    'type': 'low_ctr_top_5',
                    'keyword': kw['keyword'],
                    'position': kw['position'],
                    'ctr': kw['ctr'],
                    'action': 'Optimize title/meta for higher CTR',
                    'potential_traffic': 'Medium',
                    'effort': 'Low'
                })
        
        # Missing schema
        opportunities.append({
            'type': 'missing_schema',
            'schemas_missing': ['LocalBusiness', 'Product', 'FAQPage', 'Review'],
            'action': 'Implement missing schema types on relevant pages',
            'potential_traffic': 'Medium',
            'effort': 'Medium'
        })
        
        # Backlink gaps
        opportunities.append({
            'type': 'backlink_opportunities',
            'unclaimed_citations': 3,
            'competitor_gaps': 5,
            'action': 'Claim unclaimed citations, pursue competitor backlink gaps',
            'potential_traffic': 'Low',
            'effort': 'High'
        })
        
        # Content gaps
        opportunities.append({
            'type': 'content_gaps',
            'estimated_gaps': 25,
            'action': 'Create content for competitor keywords we don\'t target',
            'potential_traffic': 'High',
            'effort': 'Medium'
        })
        
        # CWV improvements
        cwv = metrics.get('core_web_vitals', {})
        if cwv.get('cls', {}).get('status') == 'needs_improvement':
            opportunities.append({
                'type': 'cwv_optimization',
                'metric': 'CLS',
                'current': 0.15,
                'target': 0.1,
                'action': 'Set width/height on images, reserve space for ads/embeds',
                'potential_traffic': 'Low',
                'effort': 'Low'
            })
        
        return opportunities

    def _assess_technical_health(self, metrics: Dict) -> Dict:
        """Assess overall technical SEO health"""
        score = 100
        issues = []
        
        # CWV
        cwv = metrics.get('core_web_vitals', {})
        for metric, data in cwv.items():
            if data.get('status') == 'needs_improvement':
                score -= 10
                issues.append(f"CWV {metric.upper()}: {data['value']} (target: {data['target']})")
            elif data.get('status') == 'poor':
                score -= 20
                issues.append(f"CWV {metric.upper()}: {data['value']} (target: {data['target']})")
        
        # Indexing
        indexed = metrics.get('indexed_pages', 0)
        submitted = metrics.get('submitted_sitemap_urls', 1)
        if submitted > 0:
            index_rate = indexed / submitted * 100
            if index_rate < 90:
                score -= 15
                issues.append(f"Indexation rate: {index_rate:.1f}% (target: >90%)")
        
        # Crawl errors
        crawl_errors = metrics.get('crawl_errors', 0)
        if crawl_errors > 5:
            score -= 10
            issues.append(f"Crawl errors: {crawl_errors} (target: <5)")
        
        # CWV specific pages
        cwv_issues = sum(1 for d in cwv.values() if d.get('pages_affected'))
        if cwv_issues > 5:
            score -= 10
            issues.append(f"{cwv_issues} pages with CWV issues")
        
        # Overall score
        score = max(0, score)
        
        return {
            'overall_score': score,
            'status': 'excellent' if score >= 90 else 'good' if score >= 75 else 'needs_improvement' if score >= 60 else 'poor',
            'issues': issues,
            'checks_passed': 10 - len(issues)
        }

    def _generate_report(self, metrics: Dict, comparison: Dict, anomalies: List,
                        top_performers: List, losers: List, 
                        opportunities: List, tech_health: Dict) -> str:
        """Generate performance report"""
        return f"""# SEO Performance Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Period:** Weekly ({metrics.get('date', 'N/A')})

---

## Executive Summary

| Metric | Current | Previous | Change | Trend |
|--------|---------|----------|--------|-------|
| Organic Clicks | {metrics.get('organic_clicks', 0):,} | {comparison.get('organic_clicks', {}).get('previous', 0):,} | {comparison.get('organic_clicks', {}).get('change', 0):+,} | {'📈' if comparison.get('organic_clicks', {}).get('change', 0) > 0 else '📉'} |
| Impressions | {metrics.get('impressions', 0):,} | {comparison.get('impressions', {}).get('previous', 0):,} | {comparison.get('impressions', {}).get('change', 0):+,} | {'📈' if comparison.get('impressions', {}).get('change', 0) > 0 else '📉'} |
| CTR | {metrics.get('ctr', 0):.2f}% | {comparison.get('ctr', {}).get('previous', 0):.2f}% | {comparison.get('ctr', {}).get('change', 0):+.2f}% | {'📈' if comparison.get('ctr', {}).get('change', 0) > 0 else '📉'} |
| Avg Position | {metrics.get('average_position', 0):.1f} | {comparison.get('average_position', {}).get('previous', 0):.1f} | {comparison.get('average_position', {}).get('change', 0):+.1f} | {'📈' if comparison.get('average_position', {}).get('change', 0) < 0 else '📉'} |
| Indexed Pages | {metrics.get('indexed_pages', 0)} | {comparison.get('indexed_pages', {}).get('previous', 0)} | {comparison.get('indexed_pages', {}).get('change', 0):+,} | {'📈' if comparison.get('indexed_pages', {}).get('change', 0) > 0 else '📉'} |
| Conversions | {metrics.get('conversions', {}).get('total', 0)} | {comparison.get('conversions', {}).get('previous', 0)} | {comparison.get('conversions', {}).get('change', 0):+,} | {'📈' if comparison.get('conversions', {}).get('change', 0) > 0 else '📉'} |
| Organic Revenue | ₹{metrics.get('revenue', {}).get('organic_revenue', 0):,} | ₹{comparison.get('organic_revenue', {}).get('previous', 0):,} | ₹{comparison.get('organic_revenue', {}).get('change', 0):+,} | 📈 |

---

## Ranking Distribution

| Position Range | Keywords |
|----------------|----------|
| 1-3 | {metrics.get('ranking_distribution', {}).get('1-3', 0)} |
| 4-10 | {metrics.get('ranking_distribution', {}).get('4-10', 0)} |
| 11-20 | {metrics.get('ranking_distribution', {}).get('11-20', 0)} |
| 21-50 | {metrics.get('ranking_distribution', {}).get('21-50', 0)} |
| 51-100 | {metrics.get('ranking_distribution', {}).get('51-100', 0)} |
| 100+ | {metrics.get('ranking_distribution', {}).get('100+', 0)} |

---

## Top 10 Keywords by Clicks

| Keyword | Clicks | Position | CTR |
|---------|--------|----------|-----|
"""
        for kw in metrics.get('top_keywords_by_clicks', [])[:10]:
            report += f"| {kw['keyword']} | {kw['clicks']:,} | {kw['position']} | {kw['ctr']:.1f}% |\n"

        report += f"""

---

## Core Web Vitals

| Metric | Value | Target | Status | Pages Affected |
|--------|-------|--------|--------|----------------|
"""
        for metric, data in metrics.get('core_web_vitals', {}).items():
            status_emoji = {'good': '✅', 'needs_improvement': '⚠️', 'poor': '❌'}[data['status']]
            pages = len(data.get('pages_affected', []))
            report += f"| {metric.upper()} | {data['value']} | {data['target']} | {status_emoji} {data['status']} | {pages} pages |\n"

        report += f"""

---

## Backlink Profile

- **Total Backlinks:** {metrics.get('backlinks', {}).get('total', 0):,}
- **Referring Domains:** {metrics.get('backlinks', {}).get('referring_domains', 0):,}
- **DoFollow:** {metrics.get('backlinks', {}).get('dofollow', 0):,} ({metrics.get('backlinks', {}).get('dofollow', 0)/max(1, metrics.get('backlinks', {}).get('total', 1))*100:.0f}%)
- **New This Week:** {metrics.get('backlinks', {}).get('new_this_week', 0)}
- **Lost This Week:** {metrics.get('backlinks', {}).get('lost_this_week', 0)}

### Top Anchors
"""
        for anchor in metrics.get('backlinks', {}).get('top_anchors', [])[:5]:
            report += f"- **{anchor['anchor']}**: {anchor['count']} links\n"

        report += f"""

### Top Referring Domains
"""
        for domain in metrics.get('backlinks', {}).get('top_referring_domains', [])[:5]:
            report += f"- **{domain['domain']}**: {domain['links']} links (DA: {domain['da']})\n"

        report += f"""

---

## Local SEO (GBP)

- **Views:** {metrics.get('local_seo', {}).get('gbp_views', 0):,}
- **Searches:** {metrics.get('local_seo', {}).get('gbp_searches', 0):,}
- **Actions:** Calls: {metrics.get('local_seo', {}).get('gbp_actions', {}).get('calls', 0)} | Directions: {metrics.get('local_seo', {}).get('gbp_actions', {}).get('directions', 0)} | Website: {metrics.get('local_seo', {}).get('gbp_actions', {}).get('website_visits', 0)}
- **Reviews:** {metrics.get('local_seo', {}).get('reviews', {}).get('total', 0):,} (Avg: {metrics.get('local_seo', {}).get('reviews', {}).get('average_rating', 0)})
- **New This Week:** {metrics.get('local_seo', {}).get('reviews', {}).get('this_week', 0)}

---

## Anomalies Detected ({len(anomalies)})

"""
        for anomaly in anomalies:
            severity_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[anomaly.get('severity', 'low')]
            report += f"{severity_emoji} **{anomaly['type'].replace('_', ' ').title()}**: {anomaly.get('description', anomaly.get('metric', 'Unknown'))}\n"

        report += f"""

---

## Top Opportunities ({len(opportunities)})

"""
        for i, opp in enumerate(opportunities, 1):
            report += f"{i}. **{opp['type'].replace('_', ' ').title()}**: {opp['action']}\n"
            report += f"   - Potential: {opp.get('potential_traffic', 'N/A')} | Effort: {opp.get('effort', 'N/A')}\n\n"

        report += f"""

---

## Technical Health Score: {tech_health.get('overall_score', 0)}/100 ({tech_health.get('status', 'unknown').title()})

**Issues Found:** {len(tech_health.get('issues', []))}
"""
        for issue in tech_health.get('issues', []):
            report += f"- {issue}\n"

        report += f"""

---

## Action Items for This Week

### High Priority
1. **Fix CLS Issues** - Add width/height to images on {len(metrics.get('core_web_vitals', {}).get('cls', {}).get('pages_affected', []))} pages
2. **Optimize Page 2 Keywords** - {metrics.get('ranking_distribution', {}).get('11-20', 0)} keywords in positions 11-20
3. **Improve Low CTR** - Check top 5 keywords with CTR < 5%
4. **Fix Crawl Errors** - {metrics.get('crawl_errors', 0)} errors to resolve

### Medium Priority
1. **Implement Missing Schema** - LocalBusiness, Product, FAQPage, Review
2. **Claim Unclaimed Citations** - TradeIndia, Yelp, local directories
3. **Create Content for Gaps** - Target competitor keywords we don't rank for
4. **Request Reviews** - Automate post-rental review requests

### Ongoing
1. **Monitor Rankings** - Daily via SerpBear
2. **Weekly GBP Posts** - Offers, updates, events
3. **Backlink Monitoring** - Track new/lost links
4. **Content Refresh** - Update statistics, examples in stale content

---

*Generated by GoRentals Performance Tracking Agent*
"""
        return report