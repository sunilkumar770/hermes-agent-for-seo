"""
Internal Linking Agent
Builds intelligent internal linking structure across topic clusters
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class InternalLinkingAgent(BaseAgent):
    """Agent for building intelligent internal linking structure"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.link_config = config.get('agents', {}).get('internal_linking', {})
        self.strategy = self.link_config.get('strategy', 'topic_cluster')
        self.max_links = self.link_config.get('max_links_per_page', 5)
        self.link_types = self.link_config.get('link_types', [
            'contextual', 'navigational', 'breadcrumb', 'related_posts'
        ])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute internal linking analysis"""
        pages = context.get('pages', [])
        clusters = context.get('clusters', [])
        existing_links = context.get('existing_links', [])
        
        # Defensive: ensure we have lists
        if not isinstance(pages, list):
            pages = []
        if not isinstance(clusters, list):
            clusters = []
        if not isinstance(existing_links, list):
            existing_links = []
        
        if not pages:
            # Load from content
            content_dir = self.project_root / "content"
            if content_dir.exists():
                for md_file in content_dir.glob("**/*.md"):
                    pages.append({
                        'url': f"/{md_file.relative_to(content_dir).with_suffix('')}",
                        'title': md_file.stem.replace('-', ' ').title(),
                        'cluster': 'general',
                        'type': 'article'
                    })
        
        # Analyze current linking structure
        link_analysis = self._analyze_links(pages, existing_links)
        
        # Generate recommended links
        recommended_links = self._generate_recommendations(pages, clusters, link_analysis)
        
        # Identify orphan pages
        orphans = self._find_orphans(pages, link_analysis)
        
        # Analyze cluster interlinking
        cluster_links = self._analyze_cluster_links(pages, clusters, link_analysis)
        
        # Generate breadcrumb recommendations
        breadcrumbs = self._generate_breadcrumbs(pages, clusters)
        
        # Save outputs
        files_created = []
        
        # Full analysis
        analysis_file = self.save_json({
            'analyzed_at': datetime.now().isoformat(),
            'total_pages': len(pages),
            'total_existing_links': len(existing_links),
            'link_analysis': link_analysis,
            'recommended_links': recommended_links,
            'orphans': orphans,
            'cluster_interlinking': cluster_links,
            'breadcrumbs': breadcrumbs
        }, "content/metadata/internal-links.json")
        files_created.append(analysis_file)
        
        # Priority fixes
        priority_fixes = [l for l in recommended_links if l.get('priority') == 'high'][:20]
        priority_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_recommendations': len(recommended_links),
            'priority_fixes': priority_fixes
        }, "content/metadata/priority-internal-links.json")
        files_created.append(priority_file)
        
        # Markdown report
        report = self._generate_report(link_analysis, recommended_links, orphans, cluster_links, breadcrumbs)
        report_file = self.save_output(report, "content/metadata/internal-linking-report.md")
        files_created.append(report_file)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'pages_analyzed': len(pages),
                'existing_links': len(existing_links),
                'recommendations': len(recommended_links),
                'orphans_found': len(orphans),
                'files': files_created
            },
            files_created=files_created
        )

    def _analyze_links(self, pages: List[Dict], existing_links: List[Dict]) -> Dict:
        """Analyze current linking structure"""
        # Build link graph
        outbound = defaultdict(list)
        inbound = defaultdict(list)
        
        for link in existing_links:
            source = link.get('source', '')
            target = link.get('target', '')
            outbound[source].append(target)
            inbound[target].append(source)
        
        # Calculate metrics
        page_metrics = {}
        for page in pages:
            if not isinstance(page, dict):
                continue
            url = page.get('url', '')
            page_metrics[url] = {
                'outbound_count': len(outbound.get(url, [])),
                'inbound_count': len(inbound.get(url, [])),
                'outbound_links': outbound.get(url, []),
                'inbound_links': inbound.get(url, []),
                'cluster': page.get('cluster', 'general'),
                'type': page.get('type', 'article')
            }
        
        # Find orphans (no inbound)
        orphans = [url for url, m in page_metrics.items() if m['inbound_count'] == 0]
        
        # Find low outbound
        low_outbound = [url for url, m in page_metrics.items() if m['outbound_count'] < 2]
        
        return {
            'total_pages': len(pages),
            'total_links': len(existing_links),
            'avg_inbound': sum(m['inbound_count'] for m in page_metrics.values()) / len(page_metrics) if page_metrics else 0,
            'avg_outbound': sum(m['outbound_count'] for m in page_metrics.values()) / len(page_metrics) if page_metrics else 0,
            'orphans': orphans,
            'low_outbound': low_outbound,
            'page_metrics': page_metrics
        }

    def _generate_recommendations(self, pages: List[Dict], clusters: List[Dict], 
                                  link_analysis: Dict) -> List[Dict]:
        """Generate internal link recommendations"""
        recommendations = []
        page_metrics = link_analysis.get('page_metrics', {})
        
        # 1. Fix orphan pages
        for orphan in link_analysis.get('orphans', []):
            cluster = None
            for p in pages:
                if p.get('url') == orphan:
                    cluster = p.get('cluster', 'general')
                    break
            
            # Find relevant sources
            sources = self._find_relevant_sources(orphan, pages, page_metrics)
            
            recommendations.append({
                'target': orphan,
                'type': 'fix_orphan',
                'priority': 'critical',
                'cluster': cluster,
                'suggested_sources': sources[:5],
                'action': f'Add inbound links from {len(sources)} relevant pages',
                'reason': 'Page has zero inbound links (orphan)'
            })
        
        # 2. Strengthen cluster interlinking
        for cluster in clusters:
            cluster_pages = [p for p in pages if p.get('cluster') == cluster.get('cluster_id', cluster.get('topic', ''))]
            cluster_urls = [p.get('url') for p in cluster_pages]
            
            # Check interlinking density
            internal_links = 0
            for url in cluster_urls:
                metrics = link_analysis.get('page_metrics', {}).get(url, {})
                outbound = metrics.get('outbound_links', [])
                internal = [l for l in outbound if l in cluster_urls]
                internal_links += len(internal)
            
            max_possible = len(cluster_urls) * (len(cluster_urls) - 1)
            density = internal_links / max_possible if max_possible > 0 else 0
            
            if density < 0.3:  # Less than 30% interlinked
                recommendations.append({
                    'type': 'cluster_interlinking',
                    'cluster': cluster.get('cluster_id', cluster.get('topic', '')),
                    'priority': 'high',
                    'current_density': round(density, 2),
                    'target_density': 0.5,
                    'action': f'Add contextual links between {len(cluster_urls)} pages in cluster',
                    'pages': cluster_urls
                })
        
        # 3. Add contextual links to high-authority pages
        high_authority = sorted(
            [(url, m['inbound_count']) for url, m in page_metrics.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        for url, inbound in high_authority:
            outbound = page_metrics.get(url, {}).get('outbound_count', 0)
            if outbound < 3:
                recommendations.append({
                    'type': 'add_outbound',
                    'source': url,
                    'priority': 'high',
                    'current_outbound': outbound,
                    'recommended': 5,
                    'action': f'Add 2-3 contextual outbound links from high-authority page',
                    'cluster': page_metrics.get(url, {}).get('cluster', 'general')
                })
        
        # 4. Add breadcrumb navigation
        recommendations.append({
            'type': 'breadcrumb_navigation',
            'priority': 'high',
            'action': 'Implement breadcrumb navigation site-wide',
            'benefit': 'Improves crawlability, user navigation, and distributes link equity'
        })
        
        # 5. Related posts widget
        recommendations.append({
            'type': 'related_posts',
            'priority': 'medium',
            'action': 'Add "Related Posts" widget to all blog posts',
            'benefit': 'Increases dwell time, distributes link equity within clusters'
        })
        
        # 6. Pagination links
        recommendations.append({
            'type': 'pagination',
            'priority': 'medium',
            'action': 'Add rel=next/prev and self-canonical to paginated category pages',
            'benefit': 'Improves crawlability of deep paginated content'
        })
        
        return recommendations

    def _find_relevant_sources(self, target: str, pages: List[Dict], page_metrics: Dict) -> List[str]:
        """Find relevant pages to link to target"""
        target_cluster = None
        for p in pages:
            if p.get('url') == target:
                target_cluster = p.get('cluster', 'general')
                break
        
        sources = []
        for page in pages:
            url = page.get('url')
            if url == target:
                continue
            
            # Same cluster = high relevance
            if page.get('cluster') == target_cluster:
                sources.insert(0, url)
            # High authority pages = good sources
            elif page_metrics.get(url, {}).get('inbound_count', 0) > 5:
                sources.append(url)
        
        return sources

    def _find_orphans(self, pages: List[Dict], link_analysis: Dict) -> List[Dict]:
        """Find orphan pages with details"""
        orphans = []
        for url in link_analysis.get('orphans', []):
            page = next((p for p in pages if p.get('url') == url), {})
            orphans.append({
                'url': url,
                'title': page.get('title', 'Unknown'),
                'cluster': page.get('cluster', 'general'),
                'type': page.get('type', 'article'),
                'priority': 'critical' if page.get('type') == 'pillar' else 'high'
            })
        return orphans

    def _analyze_cluster_links(self, pages: List[Dict], clusters: List[Dict], link_analysis: Dict) -> List[Dict]:
        """Analyze interlinking within clusters"""
        results = []
        page_metrics = link_analysis.get('page_metrics', {})
        
        for cluster in clusters:
            cluster_id = cluster.get('cluster_id', cluster.get('topic', ''))
            cluster_pages = [p for p in pages if p.get('cluster') == cluster_id]
            urls = [p.get('url') for p in cluster_pages]
            
            if len(urls) < 2:
                continue
            
            # Count internal links
            total_internal = 0
            for url in urls:
                outbound = page_metrics.get(url, {}).get('outbound_links', [])
                total_internal += sum(1 for l in outbound if l in urls)
            
            max_possible = len(urls) * (len(urls) - 1)
            density = total_internal / max_possible if max_possible > 0 else 0
            
            results.append({
                'cluster': cluster_id,
                'pages': len(urls),
                'internal_links': total_internal,
                'max_possible': max_possible,
                'density': round(density, 2),
                'status': 'good' if density > 0.3 else 'needs_improvement' if density > 0.1 else 'poor',
                'recommendation': f'Add {max(0, int(max_possible * 0.3) - total_internal)} more internal links' if density < 0.3 else 'Good interlinking'
            })
        
        return results

    def _generate_breadcrumbs(self, pages: List[Dict], clusters: List[Dict]) -> List[Dict]:
        """Generate breadcrumb structure"""
        breadcrumbs = []
        
        # Home
        breadcrumbs.append({
            'page': '/',
            'path': ['Home'],
            'structure': 'Home'
        })
        
        # Category pages
        category_breadcrumbs = defaultdict(list)
        for page in pages:
            url = page.get('url', '')
            cluster = page.get('cluster', 'general')
            
            # Build breadcrumb path
            path = ['Home']
            if '/rentals/' in url:
                path.append('Rentals')
                # Extract category
                parts = url.split('/')
                for i, part in enumerate(parts):
                    if part in ['bikes', 'cars', 'cameras', 'party', 'furniture', 'tools']:
                        path.append(part.title())
            
            breadcrumbs.append({
                'page': url,
                'path': path,
                'structure': ' > '.join(path)
            })
        
        return breadcrumbs

    def _generate_report(self, link_analysis: Dict, recommendations: List[Dict], 
                        orphans: List[Dict], cluster_links: List[Dict], breadcrumbs: List[Dict]) -> str:
        """Generate internal linking report"""
        critical = len([r for r in recommendations if r.get('priority') == 'critical'])
        high = len([r for r in recommendations if r.get('priority') == 'high'])
        medium = len([r for r in recommendations if r.get('priority') == 'medium'])
        
        report = f"""# Internal Linking Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Pages Analyzed:** {link_analysis.get('total_pages', 0)}
**Existing Links:** {link_analysis.get('total_links', 0)}
**Avg Inbound:** {link_analysis.get('avg_inbound', 0):.1f}
**Avg Outbound:** {link_analysis.get('avg_outbound', 0):.1f}

---

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Orphan Pages | {len(orphans)} | {'🔴 Critical' if len(orphans) > 0 else '✅ Good'} |
| Low Outbound | {len(link_analysis.get('low_outbound', []))} | {'⚠️ Warning' if len(link_analysis.get('low_outbound', [])) > 0 else '✅ Good'} |
| Cluster Interlinking | {sum(1 for c in cluster_links if c['status'] == 'poor')} poor | {'🔴 Needs Work' if any(c['status'] == 'poor' for c in cluster_links) else '✅ Good'} |

---

## Orphan Pages ({len(orphans)})

| URL | Title | Cluster | Priority |
|-----|-------|---------|----------|
"""
        for orphan in orphans[:20]:
            report += f"| {orphan['url']} | {orphan['title']} | {orphan['cluster']} | {orphan['priority']} |\n"

        report += f"""

---

## Cluster Interlinking ({len(cluster_links)} clusters)

| Cluster | Pages | Internal Links | Density | Status | Recommendation |
|---------|-------|----------------|---------|--------|----------------|
"""
        for cluster in cluster_links:
            report += f"| {cluster['cluster']} | {cluster['pages']} | {cluster['internal_links']} | {cluster['density']} | {cluster['status']} | {cluster['recommendation']} |\n"

        report += f"""

---

## Top Recommendations

### Critical ({len([r for r in recommendations if r.get('priority') == 'critical'])})
"""
        for rec in recommendations:
            if rec.get('priority') == 'critical':
                report += f"- **{rec['type']}**: {rec['action']}\n"

        report += f"""

### High Priority ({len([r for r in recommendations if r.get('priority') == 'high'])})
"""
        for rec in recommendations:
            if rec.get('priority') == 'high' and rec['type'] != 'fix_orphan':
                report += f"- **{rec['type']}**: {rec['action']}\n"

        report += f"""

### Medium Priority ({len([r for r in recommendations if r.get('priority') == 'medium'])})
"""
        for rec in recommendations:
            if rec.get('priority') == 'medium':
                report += f"- **{rec['type']}**: {rec['action']}\n"

        report += f"""

---

## Breadcrumb Coverage

**Pages with Breadcrumbs:** {len(breadcrumbs)}

| Page | Breadcrumb Path |
|------|-----------------|
"""
        for bc in breadcrumbs[:30]:
            report += f"| {bc['page']} | {bc['structure']} |\n"

        report += f"""

---

## Implementation Plan

### Week 1: Critical Fixes
1. **Fix {len(orphans)} orphan pages** - Add inbound links from cluster siblings
2. **Implement breadcrumb navigation** - Site-wide breadcrumb trail
3. **Add related posts widget** - To all blog posts

### Week 2: Cluster Strengthening
1. **Interlink cluster pages** - Target 30% density minimum
2. **Add outbound links from authority pages** - 3-5 per high-inbound page
3. **Implement pagination links** - rel=next/prev on category pages

### Week 3: Optimization
1. **Add related posts widget** - Contextual recommendations
2. **Optimize anchor text** - Diverse, descriptive anchor text
3. **Audit anchor text distribution** - Avoid over-optimization

---

*Generated by GoRentals Internal Linking Agent*
"""
        return report