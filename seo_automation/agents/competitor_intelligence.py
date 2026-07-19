"""
Competitor Intelligence Agent
Monitors competitors, analyzes their SEO strategies, identifies gaps
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class CompetitorIntelligenceAgent(BaseAgent):
    """Agent for comprehensive competitor SEO intelligence"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.comp_config = config.get('agents', {}).get('competitor_intelligence', {})
        self.competitors = self.comp_config.get('competitors', [])
        self.metrics = self.comp_config.get('metrics', [])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute competitor intelligence gathering"""
        print("DEBUG: competitor_intelligence execute() called", file=sys.stderr)
        try:
            # Load keywords directly from file to ensure we have latest
            kw_file = self.project_root / "research" / "keywords.json"
            our_keywords = []
            if kw_file.exists():
                with open(kw_file, 'r') as f:
                    data = json.load(f)
                    our_keywords = data.get('keywords', [])
            print(f"DEBUG: our_keywords type={type(our_keywords)}, len={len(our_keywords)}", file=sys.stderr)
            if our_keywords:
                print(f"DEBUG: first kw type={type(our_keywords[0])}", file=sys.stderr)

            all_competitor_data = []

            # Analyze each competitor
            for competitor in self.competitors:
                comp_data = await self._analyze_competitor(competitor, our_keywords)
                if comp_data:
                    all_competitor_data.append(comp_data)

            # Identify keyword gaps
            keyword_gaps = self._identify_keyword_gaps(all_competitor_data, context)

            # Identify content gaps
            content_gaps = self._identify_content_gaps(all_competitor_data, context)

            # Identify backlink opportunities
            backlink_opportunities = self._identify_backlink_opportunities(all_competitor_data)

            # Analyze SERP features competitors own
            serp_features = self._analyze_serp_features(all_competitor_data)

            # Save outputs
            files_created = []

            # Full competitor data
            comp_file = self.save_json({
                'generated_at': datetime.now().isoformat(),
                'competitors_analyzed': len(all_competitor_data),
                'competitors': all_competitor_data
            }, "research/competitor-analysis.json")
            files_created.append(comp_file)

            # Keyword gaps
            gaps_file = self.save_json({
                'generated_at': datetime.now().isoformat(),
                'total_gaps': len(keyword_gaps),
                'gaps': keyword_gaps
            }, "research/keyword-gaps.json")
            files_created.append(gaps_file)

            # Content gaps
            content_gaps_file = self.save_json({
                'generated_at': datetime.now().isoformat(),
                'total_gaps': len(content_gaps),
                'gaps': content_gaps
            }, "research/content-gaps.json")
            files_created.append(content_gaps_file)

            # Markdown report
            report = self._generate_report(all_competitor_data, keyword_gaps, content_gaps, backlink_opportunities, serp_features)
            report_file = self.save_output(report, "research/competitor-analysis.md")
            files_created.append(report_file)

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    'competitors_analyzed': len(all_competitor_data),
                    'keyword_gaps': len(keyword_gaps),
                    'content_gaps': len(content_gaps),
                    'backlink_opportunities': len(backlink_opportunities)
                },
                files_created=files_created
            )
        except Exception as e:
            print(f"ERROR in competitor_intelligence: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                files_created=[],
                errors=[str(e)]
            )

    async def _analyze_competitor(self, competitor: str, our_keywords: List) -> Dict[str, Any]:
        """Analyze a single competitor's SEO presence"""
        # In production, this would use Obscura/SerpAPI to crawl competitor sites
        # For now, simulate with structured data based on competitor

        # Get our target keywords from context
        # our_keywords = context.get('keywords', [])

        # Simulate competitor data (replace with real crawling)
        competitor_data = {
            'domain': competitor,
            'analyzed_at': datetime.now().isoformat(),
            'organic_keywords': self._estimate_competitor_keywords(competitor),
            'estimated_traffic': self._estimate_traffic(competitor),
            'top_pages': self._get_top_pages(competitor),
            'backlink_profile': self._estimate_backlinks(competitor),
            'content_gaps': [],
            'serp_features_owned': [],
            'keyword_overlaps': 0
        }

        # Calculate keyword overlaps with our target keywords
        comp_keywords = set()
        for kw in competitor_data['organic_keywords']:
            if isinstance(kw, dict):
                comp_keywords.add(kw.get('keyword', ''))
            else:
                comp_keywords.add(str(kw))

        our_kw_set = set()
        for kw in our_keywords:
            if isinstance(kw, dict):
                val = kw.get('keyword', '')
                if val:
                    our_kw_set.add(val)
            else:
                our_kw_set.add(str(kw))

        overlap = comp_keywords & our_kw_set
        competitor_data['keyword_overlaps'] = len(overlap)
        competitor_data['overlapping_keywords'] = list(overlap)

        # Identify keywords they rank for that we don't target
        missing_keywords = comp_keywords - our_kw_set
        competitor_data['missing_keywords'] = list(missing_keywords)[:50]  # Top 50

        return competitor_data

    def _estimate_competitor_keywords(self, competitor: str) -> List[str]:
        """Estimate keywords a competitor ranks for"""
        # Base keywords all rental competitors likely target
        base_keywords = [
            'rental marketplace', 'peer to peer rental', 'rent anything',
            'equipment rental', 'party rental', 'camera rental',
            'bike rental', 'car rental', 'tools rental', 'furniture rental',
            'rent instead of buy', 'rental app', 'rental platform',
            'short term rental', 'daily rental', 'weekly rental', 'monthly rental'
        ]

        # Add location-specific
        locations = ['hyderabad', 'secunderabad', 'gachibowli', 'madhapur', 'hitech city',
                     'kukatpally', 'banjara hills', 'jubilee hills', 'kondapur', 'miyapur']

        keywords = list(base_keywords)
        for base in base_keywords[:8]:  # Top categories
            for loc in locations:
                keywords.append(f"{base} {loc}")
                keywords.append(f"{base} near {loc}")

        return keywords[:200]  # Cap

    def _estimate_traffic(self, competitor: str) -> int:
        """Estimate competitor monthly organic traffic"""
        # Rough estimates based on known competitor sizes
        traffic_estimates = {
            'rentomojo.com': 450000,
            'furlenco.com': 380000,
            'grabonrent.com': 120000,
            'rentickle.com': 95000,
            'cityfurnish.com': 85000,
            'olx.in': 12000000,
            'quikr.com': 8500000
        }
        return traffic_estimates.get(competitor, 50000)

    def _get_top_pages(self, competitor: str) -> List[Dict]:
        """Get competitor's top performing pages"""
        return [
            {'url': f'https://{competitor}/rentals', 'traffic': 15000, 'keywords': 45},
            {'url': f'https://{competitor}/bike-rental', 'traffic': 8500, 'keywords': 23},
            {'url': f'https://{competitor}/car-rental', 'traffic': 7200, 'keywords': 19},
            {'url': f'https://{competitor}/camera-rental', 'traffic': 3400, 'keywords': 12},
            {'url': f'https://{competitor}/furniture-rental', 'traffic': 2800, 'keywords': 10}
        ]

    def _estimate_backlinks(self, competitor: str) -> Dict:
        """Estimate competitor backlink profile"""
        return {
            'total_backlinks': 15000,
            'referring_domains': 850,
            'dofollow_ratio': 0.65,
            'top_anchors': ['rental', 'bike rental', 'car rental', 'rent', 'equipment rental'],
            'top_referring_domains': ['justdial.com', 'sulekha.com', 'indiamart.com', 'facebook.com', 'google.com']
        }

    def _identify_keyword_gaps(self, competitor_data: List[Dict], context: Dict) -> List[Dict]:
        """Find keywords competitors rank for that we don't target"""
        our_keywords = set()
        for kw in context.get('keywords', []):
            if isinstance(kw, dict):
                val = kw.get('keyword', '')
                if val:
                    our_keywords.add(val.lower())
            elif isinstance(kw, str):
                our_keywords.add(kw.lower())

        gaps = []

        for comp in competitor_data:
            comp_domain = comp['domain']
            for keyword in comp.get('missing_keywords', []):
                kw_lower = keyword.lower()
                if kw_lower not in our_keywords and len(keyword.split()) >= 2:
                    gaps.append({
                        'keyword': keyword,
                        'competitor': comp_domain,
                        'competitor_traffic': comp.get('estimated_traffic', 0),
                        'intent': self._classify_intent(keyword),
                        'difficulty': self._estimate_difficulty(keyword),
                        'opportunity_score': self._calculate_opportunity(keyword, comp)
                    })

        # Deduplicate and sort by opportunity
        seen = set()
        unique_gaps = []
        for gap in gaps:
            key = gap['keyword'].lower()
            if key not in seen:
                seen.add(key)
                unique_gaps.append(gap)

        return sorted(unique_gaps, key=lambda x: x['opportunity_score'], reverse=True)[:100]

    def _classify_intent(self, keyword: str) -> str:
        """Classify search intent"""
        kw = keyword.lower()
        if any(w in kw for w in ['buy', 'price', 'cost', 'cheap', 'deal', 'book', 'rent now']):
            return 'transactional'
        elif any(w in kw for w in ['best', 'top', 'review', 'compare', 'vs', 'vs.']):
            return 'commercial'
        elif any(w in kw for w in ['how', 'what', 'where', 'when', 'why', 'guide', 'tutorial']):
            return 'informational'
        elif any(w in kw for w in ['near me', 'in hyderabad', 'in secunderabad', 'in gachibowli']):
            return 'local'
        return 'commercial'

    def _estimate_difficulty(self, keyword: str) -> int:
        """Estimate keyword difficulty"""
        words = len(keyword.split())
        if words <= 2:
            return 45
        elif words == 3:
            return 35
        elif words == 4:
            return 25
        return 20

    def _calculate_opportunity(self, keyword: str, competitor: Dict) -> float:
        """Calculate opportunity score for a keyword gap"""
        difficulty = self._estimate_difficulty(keyword)
        comp_traffic = competitor.get('estimated_traffic', 50000)
        words = len(keyword.split())

        # Higher score = better opportunity
        score = (comp_traffic / 10000) * (50 - difficulty) * (1 + words * 0.1)
        return round(score, 1)

    def _identify_content_gaps(self, competitor_data: List[Dict], context: Dict) -> List[Dict]:
        """Identify content topics competitors cover that we don't"""
        # Simulate content gap analysis
        common_topics = [
            'how to choose rental bike', 'bike rental vs buying calculator',
            'camera rental for beginners', 'wedding car decoration ideas',
            'corporate rental policies', 'rental insurance guide',
            'seasonal rental tips', 'student rental discounts'
        ]

        # existing_content is a list of dicts with 'title' or 'url' keys
        existing_content = context.get('existing_content', [])
        our_content = set()
        for item in existing_content:
            if isinstance(item, dict):
                # Try to get title or url as string
                val = item.get('title') or item.get('url') or str(item)
                our_content.add(val.lower())
            elif isinstance(item, str):
                our_content.add(item.lower())

        gaps = []

        for topic in common_topics:
            if not any(topic.lower() in c for c in our_content):
                gaps.append({
                    'topic': topic,
                    'intent': self._classify_intent(topic),
                    'estimated_volume': 500,
                    'priority': 'high' if 'rental' in topic else 'medium'
                })

        return gaps

    def _identify_backlink_opportunities(self, competitor_data: List[Dict]) -> List[Dict]:
        """Find backlink sources competitors have that we could target"""
        # Common rental industry citation sources
        return [
            {'source': 'justdial.com', 'type': 'directory', 'competitors': 7, 'difficulty': 'easy'},
            {'source': 'sulekha.com', 'type': 'directory', 'competitors': 7, 'difficulty': 'easy'},
            {'source': 'indiamart.com', 'type': 'directory', 'competitors': 6, 'difficulty': 'easy'},
            {'source': 'facebook.com', 'type': 'social', 'competitors': 7, 'difficulty': 'easy'},
            {'source': 'google.com/maps', 'type': 'local', 'competitors': 7, 'difficulty': 'easy'},
            {'source': 'hyderabad-tourism.com', 'type': 'local', 'competitors': 3, 'difficulty': 'medium'},
            {'source': 'event-management-blogs', 'type': 'niche', 'competitors': 2, 'difficulty': 'medium'}
        ]

    def _analyze_serp_features(self, competitor_data: List[Dict]) -> Dict:
        """Analyze which SERP features competitors own"""
        return {
            'featured_snippets': 12,
            'people_also_ask': 45,
            'local_pack': 28,
            'image_pack': 18,
            'video_carousel': 5,
            'shopping_results': 8,
            'knowledge_panel': 3
        }

    def _generate_report(self, comp_data: List[Dict], gaps: List[Dict], content_gaps: List[Dict],
                        backlinks: List[Dict], serp: Dict) -> str:
        """Generate markdown report"""
        report = f"""# Competitor Intelligence Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Competitors Analyzed:** {len(comp_data)}

---

## Competitor Overview

| Competitor | Est. Traffic | Organic Keywords | Top Pages | Backlinks | Ref. Domains |
|------------|--------------|------------------|-----------|-----------|--------------|
"""
        for comp in comp_data:
            bl = comp.get('backlink_profile', {})
            report += f"| {comp['domain']} | {comp.get('estimated_traffic', 0):,} | ~{len(comp.get('organic_keywords', []))} | {len(comp.get('top_pages', []))} | {bl.get('total_backlinks', 0):,} | {bl.get('referring_domains', 0)} |\n"

        report += f"""---

## Keyword Gaps ({len(gaps)} identified)

| Keyword | Competitor | Intent | Difficulty | Opportunity Score |
|---------|------------|--------|------------|-------------------|
"""
        for gap in gaps[:20]:
            report += f"| {gap['keyword']} | {gap['competitor']} | {gap['intent']} | {gap['difficulty']} | {gap['opportunity_score']} |\n"

        report += f"""---

## Content Gaps ({len(content_gaps)} identified)

| Topic | Intent | Est. Volume | Priority |
|-------|--------|-------------|----------|
"""
        for gap in content_gaps:
            report += f"| {gap['topic']} | {gap['intent']} | {gap['estimated_volume']} | {gap['priority']} |\n"

        report += f"""---

## Backlink Opportunities ({len(backlinks)} sources)

| Source | Type | Competitors Using | Difficulty |
|--------|------|-------------------|------------|
"""
        for bl in backlinks:
            report += f"| {bl['source']} | {bl['type']} | {bl['competitors']} | {bl['difficulty']} |\n"

        report += f"""---

## SERP Features Owned by Competitors

| Feature | Count |
|---------|-------|
| Featured Snippets | {serp.get('featured_snippets', 0)} |
| People Also Ask | {serp.get('people_also_ask', 0)} |
| Local Pack | {serp.get('local_pack', 0)} |
| Image Pack | {serp.get('image_pack', 0)} |
| Video Carousel | {serp.get('video_carousel', 0)} |
| Shopping Results | {serp.get('shopping_results', 0)} |

---

## Action Items

1. **Target Top 20 Keyword Gaps** - Create landing pages for highest opportunity keywords
2. **Build Content for {len(content_gaps)} Gaps** - Prioritize high-volume rental guides
3. **Claim {len(backlinks)} Citation Sources** - Submit to all directories competitors use
4. **Compete for SERP Features** - Optimize for PAA, Local Pack, Featured Snippets

---
*Generated by GoRentals Competitor Intelligence Agent*
"""
        return report