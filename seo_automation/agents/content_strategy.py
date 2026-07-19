"""
Content Strategy Agent
Creates topical maps, content calendars, identifies content gaps
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class ContentStrategyAgent(BaseAgent):
    """Agent for creating topical maps, content calendars, and identifying content gaps"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.strategy_config = config.get('agents', {}).get('content_strategy', {})
        self.topical_depth = self.strategy_config.get('topical_map_depth', 3)
        self.cluster_min = self.strategy_config.get('cluster_min_keywords', 5)
        self.content_types = self.strategy_config.get('content_types', [
            'pillar_page', 'cluster_article', 'comparison_page', 
            'guide', 'faq_page', 'landing_page', 'category_page'
        ])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute content strategy creation"""
        # Get keywords from keyword intelligence
        keywords = context.get('keywords', [])
        if not keywords:
            kw_file = self.project_root / "research" / "keywords.json"
            if kw_file.exists():
                with open(kw_file, 'r') as f:
                    data = json.load(f)
                    keywords = data.get('keywords', [])

        # Get SERP analysis data
        serp_data = context.get('serp_analysis', {})
        
        # Get competitor data
        competitor_data = context.get('competitor_data', {})

        # Build topical map
        topical_map = self._build_topical_map(keywords)
        
        # Create content clusters
        clusters = self._create_content_clusters(topical_map)
        
        # Identify content gaps
        content_gaps = self._identify_content_gaps(keywords, context.get('existing_content', []), competitor_data)
        
        # Create content calendar
        content_calendar = self._create_content_calendar(clusters, content_gaps)
        
        # Prioritize content production
        prioritized = self._prioritize_content(content_calendar, keywords)
        
        # Save outputs
        files_created = []
        
        # Topical map
        map_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_topics': len(topical_map),
            'topical_map': topical_map
        }, "research/topical_map.json")
        files_created.append(map_file)
        
        # Content clusters
        cluster_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_clusters': len(clusters),
            'clusters': clusters
        }, "research/content_clusters.json")
        files_created.append(cluster_file)
        
        # Content gaps
        gaps_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_gaps': len(content_gaps),
            'gaps': content_gaps
        }, "research/content_gaps.json")
        files_created.append(gaps_file)
        
        # Content calendar
        cal_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'period': 'quarterly',
            'total_items': len(content_calendar),
            'calendar': content_calendar
        }, "research/content_calendar.json")
        files_created.append(cal_file)
        
        # Prioritized production list
        priority_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_items': len(prioritized),
            'items': prioritized
        }, "research/production_priorities.json")
        files_created.append(priority_file)
        
        # Markdown report
        report = self._generate_report(topical_map, clusters, content_gaps, content_calendar, prioritized)
        report_file = self.save_output(report, "research/content-calendar.md")
        files_created.append(report_file)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'topics': len(topical_map),
                'clusters': len(clusters),
                'gaps_found': len(content_gaps),
                'calendar_items': len(content_calendar),
                'prioritized_items': len(prioritized)
            },
            files_created=files_created
        )

    def _build_topical_map(self, keywords: List[Dict]) -> Dict[str, Any]:
        """Build hierarchical topical map from keywords"""
        # Group keywords by primary topic
        topic_groups = defaultdict(list)
        
        for kw in keywords:
            keyword = kw.get('keyword', '').lower()
            kw_type = kw.get('type', 'general')
            intent = kw.get('intent', 'commercial')
            volume = kw.get('volume', 0)
            
            # Determine primary topic
            primary = self._extract_primary_topic(keyword)
            topic_groups[primary].append({
                'keyword': keyword,
                'type': kw_type,
                'intent': intent,
                'volume': volume,
                'difficulty': kw.get('difficulty', 30),
                'priority_score': kw.get('priority_score', 0)
            })
        
        # Build hierarchical map
        topical_map = {}
        for topic, kws in topic_groups.items():
            # Sort by priority
            kws.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
            
            # Identify pillar (highest volume + commercial intent)
            pillar = self._identify_pillar(kws)
            
            # Create sub-clusters
            sub_clusters = self._create_sub_clusters(kws)
            
            topical_map[topic] = {
                'pillar_keyword': pillar,
                'total_keywords': len(kws),
                'total_volume': sum(k['volume'] for k in kws),
                'sub_clusters': sub_clusters,
                'content_types_needed': self._determine_content_types(kws),
                'priority': self._calculate_topic_priority(kws)
            }
        
        return dict(sorted(topical_map.items(), key=lambda x: x[1]['priority'], reverse=True))

    def _extract_primary_topic(self, keyword: str) -> str:
        """Extract primary topic from keyword"""
        kw = keyword.lower()
        
        # Category mapping
        if any(t in kw for t in ['bike', 'scooter', 'two wheeler', 'motorcycle']):
            return 'bike_rentals'
        elif any(t in kw for t in ['car', 'sedan', 'suv', 'hatchback', 'self drive', 'automobile']):
            return 'car_rentals'
        elif any(t in kw for t in ['camera', 'dslr', 'mirrorless', 'lens', 'photography', 'videography']):
            return 'camera_rentals'
        elif any(t in kw for t in ['wedding', 'marriage', 'bridal', 'engagement', 'reception']):
            return 'wedding_rentals'
        elif any(t in kw for t in ['party', 'event', 'celebration', 'birthday', 'decoration']):
            return 'party_rentals'
        elif any(t in kw for t in ['furniture', 'sofa', 'bed', 'table', 'chair', 'home']):
            return 'furniture_rentals'
        elif any(t in kw for t in ['tools', 'drill', 'equipment', 'construction', 'diy']):
            return 'tools_rentals'
        elif any(t in kw for t in ['laptop', 'computer', 'electronics', 'gadget', 'tech']):
            return 'electronics_rentals'
        elif any(t in kw for t in ['peer to peer', 'p2p', 'marketplace', 'platform', 'rent anything']):
            return 'rental_marketplace'
        elif any(t in kw for t in ['hyderabad', 'secunderabad', 'gachibowli', 'hitech', 'banjara', 'jubilee', 'kukatpally', 'madhapur', 'secunderabad']):
            return 'local_hyderabad'
        else:
            return 'general_rental'

    def _identify_pillar(self, keywords: List[Dict]) -> str:
        """Identify pillar keyword for a topic"""
        # Pillar = high volume + commercial intent + broad
        commercial_kws = [k for k in keywords if k['intent'] in ['commercial', 'transactional']]
        if commercial_kws:
            return max(commercial_kws, key=lambda x: x['volume'])['keyword']
        return max(keywords, key=lambda x: x['volume'])['keyword'] if keywords else ''

    def _create_sub_clusters(self, keywords: List[Dict]) -> List[Dict]:
        """Create sub-clusters within a topic"""
        clusters = defaultdict(list)
        
        for kw in keywords:
            keyword = kw['keyword'].lower()
            
            # Determine sub-cluster
            if any(t in keyword for t in ['price', 'cost', 'cheap', 'affordable', 'rate']):
                sub = 'pricing_cost'
            elif any(t in keyword for t in ['how', 'guide', 'tips', 'choose', 'select']):
                sub = 'guides_howto'
            elif any(t in keyword for t in ['best', 'top', 'review', 'compare', 'vs']):
                sub = 'comparisons_reviews'
            elif any(t in keyword for t in ['near me', 'in hyderabad', 'in secunderabad', 'gachibowli', 'hitech']):
                sub = 'local_area'
            elif any(t in keyword for t in ['monthly', 'weekly', 'long term', 'longterm']):
                sub = 'long_term_rental'
            elif any(t in keyword for t in ['wedding', 'party', 'event', 'corporate']):
                sub = 'occasion_based'
            elif any(t in keyword for t in ['delivery', 'pickup', 'doorstep', 'online booking']):
                sub = 'booking_process'
            else:
                sub = 'general'
            
            clusters[sub].append(kw)
        
        # Convert to list format
        result = []
        for name, kws in clusters.items():
            if len(kws) >= 3:  # Minimum cluster size
                result.append({
                    'cluster_name': name,
                    'keywords': [k['keyword'] for k in kws],
                    'count': len(kws),
                    'total_volume': sum(k['volume'] for k in kws),
                    'primary_intent': max(set(k['intent'] for k in kws), key=lambda x: sum(1 for k in kws if k['intent'] == x)),
                    'content_types': self._determine_content_types(kws)
                })
        
        return sorted(result, key=lambda x: x['total_volume'], reverse=True)

    def _determine_content_types(self, keywords: List[Dict]) -> List[str]:
        """Determine which content types are needed for keywords"""
        intents = set(k['intent'] for k in keywords)
        types = set()
        
        if 'commercial' in intents or 'transactional' in intents:
            types.add('landing_page')
            types.add('category_page')
        if 'informational' in intents:
            types.add('blog_post')
            types.add('guide')
        if any('how' in k['keyword'].lower() for k in keywords):
            types.add('faq_page')
        if any('vs' in k['keyword'].lower() or 'compare' in k['keyword'].lower() for k in keywords):
            types.add('comparison_page')
        if any('local' in k['keyword'].lower() or 'near me' in k['keyword'].lower() for k in keywords):
            types.add('local_page')
        
        return list(types) or ['blog_post']

    def _calculate_topic_priority(self, keywords: List[Dict]) -> float:
        """Calculate topic priority score"""
        if not keywords:
            return 0
        
        total_volume = sum(k['volume'] for k in keywords)
        avg_difficulty = sum(k.get('difficulty', 30) for k in keywords) / len(keywords)
        commercial_ratio = sum(1 for k in keywords if k['intent'] in ['commercial', 'transactional']) / len(keywords)
        
        # Score: volume weighted, difficulty inverse, commercial boost
        priority = (total_volume / 100) * (100 - avg_difficulty) / 100 * (1 + commercial_ratio)
        return round(priority, 1)

    def _create_content_clusters(self, topical_map: Dict) -> List[Dict]:
        """Create detailed content clusters from topical map"""
        clusters = []
        
        for topic, data in topical_map.items():
            for sub in data.get('sub_clusters', []):
                if sub['count'] >= self.cluster_min:
                    clusters.append({
                        'cluster_id': f"{topic}_{sub['cluster_name']}",
                        'topic': topic,
                        'cluster_name': sub['cluster_name'],
                        'pillar_keyword': data['pillar_keyword'],
                        'keywords': sub['keywords'],
                        'total_volume': sub['total_volume'],
                        'primary_intent': sub['primary_intent'],
                        'content_types': sub['content_types'],
                        'priority': data['priority'],
                        'status': 'planned'
                    })
        
        return sorted(clusters, key=lambda x: x['priority'], reverse=True)

    def _identify_content_gaps(self, keywords: List[Dict], existing_content: List[Dict], competitor_data: Dict) -> List[Dict]:
        """Identify content gaps vs competitors and our own coverage"""
        # Extract existing topics
        existing_topics = set()
        for content in existing_content:
            existing_topics.add(content.get('target_keyword', '').lower())
            existing_topics.update(content.get('keywords', []))
        
        # Extract competitor topics
        competitor_topics = set()
        for comp in competitor_data.get('competitors', []):
            for kw in comp.get('organic_keywords', []):
                competitor_topics.add(kw.lower())
        
        gaps = []
        for kw in keywords:
            kw_lower = kw['keyword'].lower()
            if kw_lower not in existing_topics:
                in_competitor = kw_lower in competitor_topics
                gaps.append({
                    'keyword': kw['keyword'],
                    'type': kw.get('type', 'general'),
                    'intent': kw['intent'],
                    'volume': kw['volume'],
                    'difficulty': kw.get('difficulty', 30),
                    'in_competitor': in_competitor,
                    'gap_type': 'competitor' if in_competitor else 'missing',
                    'priority': self._calculate_gap_priority(kw, in_competitor),
                    'suggested_content_type': self._suggest_content_type(kw),
                    'cluster': self._extract_primary_topic(kw['keyword'])
                })
        
        return sorted(gaps, key=lambda x: x['priority'], reverse=True)

    def _calculate_gap_priority(self, kw: Dict, in_competitor: bool) -> float:
        """Calculate priority for content gap"""
        volume = kw['volume']
        difficulty = kw.get('difficulty', 30)
        intent = kw['intent']
        
        base = volume / 100 * (100 - difficulty) / 100
        if in_competitor:
            base *= 1.5  # Competitor has it, higher priority
        if intent in ['commercial', 'transactional']:
            base *= 1.3
        elif intent == 'informational':
            base *= 1.0
        
        return round(base, 1)

    def _suggest_content_type(self, kw: Dict) -> str:
        """Suggest content type for a keyword"""
        intent = kw['intent']
        keyword = kw['keyword'].lower()
        
        if intent in ['transactional', 'commercial']:
            if 'vs' in keyword or 'compare' in keyword:
                return 'comparison_page'
            elif 'best' in keyword or 'top' in keyword:
                return 'listicle'
            else:
                return 'landing_page'
        elif intent == 'informational':
            if 'how to' in keyword or 'guide' in keyword:
                return 'guide'
            elif 'what is' in keyword or 'what are' in keyword:
                return 'definition_post'
            else:
                return 'blog_post'
        elif 'near me' in keyword or 'in hyderabad' in keyword:
            return 'local_page'
        else:
            return 'blog_post'

    def _create_content_calendar(self, clusters: List[Dict], gaps: List[Dict]) -> List[Dict]:
        """Create quarterly content calendar"""
        calendar = []
        week = 1
        
        # High priority gaps first
        high_gaps = [g for g in gaps if g['priority'] >= 50][:20]
        
        for gap in high_gaps:
            calendar.append({
                'week': week,
                'quarter': f"Q{((week-1)//13)+1}",
                'content_id': f"gap_{gap['keyword'].replace(' ', '_')}",
                'type': 'gap_fill',
                'title': f"{gap['suggested_content_type'].replace('_', ' ').title()}: {gap['keyword']}",
                'target_keyword': gap['keyword'],
                'content_type': gap['suggested_content_type'],
                'cluster': gap['cluster'],
                'priority': gap['priority'],
                'status': 'planned',
                'estimated_words': self._estimate_word_count(gap['suggested_content_type']),
                'target_date': (datetime.now() + timedelta(weeks=week)).strftime('%Y-%m-%d')
            })
            week += 1
        
        # Cluster content
        for cluster in clusters[:15]:
            for content_type in cluster['content_types']:
                calendar.append({
                    'week': week,
                    'quarter': f"Q{((week-1)//13)+1}",
                    'content_id': f"cluster_{cluster['cluster_id']}_{content_type}",
                    'type': 'cluster_content',
                    'title': f"{content_type.replace('_', ' ').title()}: {cluster['pillar_keyword']}",
                    'target_keyword': cluster['pillar_keyword'],
                    'content_type': content_type,
                    'cluster': cluster['topic'],
                    'priority': cluster['priority'],
                    'status': 'planned',
                    'estimated_words': self._estimate_word_count(content_type),
                    'target_date': (datetime.now() + timedelta(weeks=week)).strftime('%Y-%m-%d')
                })
                week += 1
        
        return calendar

    def _estimate_word_count(self, content_type: str) -> int:
        """Estimate word count for content type"""
        counts = {
            'landing_page': 1500,
            'category_page': 2000,
            'blog_post': 1800,
            'guide': 3000,
            'faq_page': 1200,
            'comparison_page': 2500,
            'listicle': 2200,
            'definition_post': 1500,
            'local_page': 1800
        }
        return counts.get(content_type, 1800)

    def _prioritize_content(self, calendar: List[Dict], keywords: List[Dict]) -> List[Dict]:
        """Create prioritized production list"""
        kw_lookup = {k['keyword']: k for k in keywords}
        
        for item in calendar:
            kw = kw_lookup.get(item['target_keyword'], {})
            item['kw_volume'] = kw.get('volume', 0)
            item['kw_difficulty'] = kw.get('difficulty', 30)
            item['kw_intent'] = kw.get('intent', 'commercial')
            # Composite priority score
            item['production_priority'] = round(
                item['priority'] * 0.4 + 
                (item['kw_volume'] / 100) * 0.3 + 
                (100 - item['kw_difficulty']) / 100 * 0.3, 1
            )
        
        return sorted(calendar, key=lambda x: x['production_priority'], reverse=True)

    def _generate_report(self, topical_map: Dict, clusters: List[Dict], gaps: List[Dict], 
                        calendar: List[Dict], priorities: List[Dict]) -> str:
        """Generate markdown report"""
        report = f"""# Content Strategy & Calendar

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Topics Mapped:** {len(topical_map)}
**Content Clusters:** {len(clusters)}
**Content Gaps:** {len(gaps)}
**Calendar Items:** {len(calendar)}
**Prioritized Items:** {len(priorities)}

---

## Topical Map ({len(topical_map)} Topics)

| Topic | Pillar Keyword | Keywords | Volume | Priority | Content Types |
|-------|----------------|----------|--------|----------|---------------|
"""
        for topic, data in list(topical_map.items())[:15]:
            report += f"| {topic.replace('_', ' ').title()} | {data['pillar_keyword']} | {data['total_keywords']} | {data['total_volume']:,} | {data['priority']} | {', '.join(data['content_types_needed'])} |\n"

        report += f"""

---

## Content Clusters ({len(clusters)} Clusters)

| Cluster | Topic | Pillar | Volume | Intent | Types | Priority |
|---------|-------|--------|--------|--------|-------|----------|
"""
        for cluster in clusters[:20]:
            report += f"| {cluster['cluster_name']} | {cluster['topic']} | {cluster['pillar_keyword']} | {cluster['total_volume']:,} | {cluster['primary_intent']} | {', '.join(cluster['content_types'][:2])} | {cluster['priority']} |\n"

        report += f"""

---

## Content Gaps ({len(gaps)} Identified)

### High Priority Gaps (Competitor Has, We Don't)
| Keyword | Volume | Difficulty | In Competitor | Priority | Type |
|---------|--------|------------|---------------|----------|------|
"""
        high_gaps = [g for g in gaps if g['priority'] >= 50 and g['in_competitor']][:15]
        for gap in high_gaps:
            report += f"| {gap['keyword']} | {gap['volume']:,} | {gap['difficulty']} | ✅ Yes | {gap['priority']} | {gap['suggested_content_type']} |\n"

        report += f"""

### Our Missing Content (Not in Competitor)
| Keyword | Volume | Difficulty | Priority | Type |
|---------|--------|------------|----------|------|
"""
        our_gaps = [g for g in gaps if g['priority'] >= 50 and not g['in_competitor']][:15]
        for gap in our_gaps:
            report += f"| {gap['keyword']} | {gap['volume']:,} | {gap['difficulty']} | {gap['priority']} | {gap['suggested_content_type']} |\n"

        report += f"""

---

## Content Calendar (Next {len(calendar)} Weeks)

| Week | Quarter | Title | Type | Cluster | Priority | Target Date |
|------|---------|-------|------|---------|----------|-------------|
"""
        for item in calendar[:30]:
            report += f"| {item['week']} | {item['quarter']} | {item['title'][:50]} | {item['content_type']} | {item['cluster']} | {item['priority']} | {item['target_date']} |\n"

        report += f"""

---

## Production Priorities (Top 20)

| Rank | Title | Keyword | Volume | Difficulty | Type | Production Priority |
|------|-------|---------|--------|------------|------|---------------------|
"""
        for i, item in enumerate(priorities[:20], 1):
            report += f"| {i} | {item['title'][:45]} | {item['target_keyword']} | {item.get('kw_volume', 0):,} | {item.get('kw_difficulty', 0)} | {item['content_type']} | {item['production_priority']} |\n"

        report += f"""

---

## Recommended Actions

### This Week
1. **Produce top 5 priority items** from production list
2. **Set up content templates** for each content type
3. **Assign writers** to high-priority gaps

### This Month
1. **Complete all competitor gap content** (top 20)
2. **Build pillar pages** for top 5 topics
3. **Create cluster content** for top 3 clusters

### Quarterly Goals
- Publish {len(calendar)} pieces of content
- Cover {len(clusters)} topic clusters
- Fill {len([g for g in gaps if g['in_competitor']])} competitor gaps
- Achieve topical authority in top 5 topics

---
*Generated by GoRentals Content Strategy Agent*
"""
        return report