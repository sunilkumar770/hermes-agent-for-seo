"""
Keyword Intelligence Agent
Discovers, clusters, and prioritizes keywords for GoRentals SEO
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class KeywordIntelligenceAgent(BaseAgent):
    """Agent for comprehensive keyword research and intelligence"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.keyword_config = config.get('agents', {}).get('keyword_intelligence', {})
        self.sources = self.keyword_config.get('sources', [])
        self.clustering = self.keyword_config.get('clustering', {})

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute keyword intelligence gathering"""
        all_keywords = []

        # 1. Primary brand keywords
        primary_keywords = self._get_primary_keywords()
        all_keywords.extend(primary_keywords)

        # 2. Secondary category keywords
        secondary_keywords = self._get_secondary_keywords()
        all_keywords.extend(secondary_keywords)

        # 3. Long-tail keyword generation
        long_tail = self._generate_long_tail_keywords()
        all_keywords.extend(long_tail)

        # 4. Local Hyderabad keywords
        local_keywords = self._generate_local_keywords()
        all_keywords.extend(local_keywords)

        # 5. Competitor gap keywords (from context)
        competitor_keywords = self._get_competitor_gaps(context)
        all_keywords.extend(competitor_keywords)

        # 6. Question/Intent keywords
        question_keywords = self._generate_question_keywords()
        all_keywords.extend(question_keywords)

        # 7. Seasonal keywords
        seasonal_keywords = self._get_seasonal_keywords()
        all_keywords.extend(seasonal_keywords)

        # 8. Semantic clustering
        clusters = self._cluster_keywords(all_keywords)

        # 9. Score and prioritize
        scored_keywords = self._score_keywords(all_keywords, clusters)

        # Save outputs
        files_created = []
        
        # Full keyword list
        keyword_file = self.save_json(
            {
                'generated_at': datetime.now().isoformat(),
                'total_keywords': len(scored_keywords),
                'keywords': scored_keywords
            },
            "research/keywords.json"
        )
        files_created.append(keyword_file)

        # Keyword clusters
        cluster_file = self.save_json(
            {
                'generated_at': datetime.now().isoformat(),
                'method': self.clustering.get('method', 'semantic'),
                'clusters': clusters
            },
            "research/keyword_clusters.json"
        )
        files_created.append(cluster_file)

        # Prioritized action list
        priority_keywords = [k for k in scored_keywords if k['priority_score'] >= 70]
        action_file = self.save_json(
            {
                'generated_at': datetime.now().isoformat(),
                'high_priority_count': len(priority_keywords),
                'keywords': priority_keywords
            },
            "research/priority_keywords.json"
        )
        files_created.append(action_file)

        # Markdown report
        report = self._generate_report(scored_keywords, clusters)
        report_file = self.save_output(report, "research/keyword-research.md")
        files_created.append(report_file)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'total_keywords': len(scored_keywords),
                'clusters': len(clusters),
                'high_priority': len(priority_keywords),
                'keywords': scored_keywords,
                'files': files_created
            },
            files_created=files_created
        )

    def _get_primary_keywords(self) -> List[Dict[str, Any]]:
        """Core brand and primary keywords"""
        return [
            {'keyword': 'gorentals', 'type': 'brand', 'intent': 'navigational', 'volume': 1000, 'difficulty': 15},
            {'keyword': 'go rentals', 'type': 'brand', 'intent': 'navigational', 'volume': 800, 'difficulty': 20},
            {'keyword': 'go rentals hyderabad', 'type': 'brand_local', 'intent': 'navigational', 'volume': 500, 'difficulty': 10},
        ]

    def _get_secondary_keywords(self) -> List[Dict[str, Any]]:
        """Secondary category keywords"""
        categories = [
            ('bike rentals hyderabad', 'category', 'commercial', 2900, 35),
            ('bike rental hyderabad', 'category', 'commercial', 2400, 35),
            ('camera rentals hyderabad', 'category', 'commercial', 590, 25),
            ('car rentals hyderabad', 'category', 'commercial', 4400, 45),
            ('self drive cars hyderabad', 'category', 'commercial', 1600, 40),
            ('party rentals hyderabad', 'category', 'commercial', 390, 30),
            ('rental marketplace', 'category', 'informational', 720, 50),
            ('rent anything hyderabad', 'category', 'commercial', 110, 25),
            ('rental platform hyderabad', 'category', 'commercial', 140, 30),
        ]
        return [
            {'keyword': kw, 'type': typ, 'intent': intent, 'volume': vol, 'difficulty': diff}
            for kw, typ, intent, vol, diff in categories
        ]

    def _generate_long_tail_keywords(self) -> List[Dict[str, Any]]:
        """Generate long-tail variations programmatically"""
        modifiers = [
            'best', 'affordable', 'cheap', 'premium', 'luxury', 'budget',
            'near me', 'online', 'instant', 'same day', 'weekly', 'monthly',
            'with driver', 'without driver', 'self drive', 'chauffeur',
            'for wedding', 'for event', 'for trip', 'for office', 'for students'
        ]
        
        bases = [
            'bike rental', 'bike rentals', 'camera rental', 'camera rentals',
            'car rental', 'car rentals', 'self drive car', 'self drive cars',
            'wedding car', 'party rental', 'equipment rental', 'laptop rental'
        ]

        locations = [
            'hyderabad', 'secunderabad', 'gachibowli', 'madhapur', 'hitech city',
            'kukatpally', 'banjara hills', 'jubilee hills', 'kondapur', 'miyapur',
            'lb nagar', 'dilsukhnagar', 'uppal', 'shamshabad', 'warangal', 'nizamabad'
        ]

        keywords = []
        for base in bases:
            for mod in modifiers:
                for loc in locations[:5]:  # Limit locations for volume
                    kw = f"{mod} {base} {loc}".strip()
                    keywords.append({
                        'keyword': kw,
                        'type': 'long_tail',
                        'intent': 'commercial' if any(m in mod for m in ['best', 'affordable', 'cheap', 'premium']) else 'informational',
                        'volume': self._estimate_volume(kw),
                        'difficulty': self._estimate_difficulty(kw)
                    })
        return keywords[:2000]  # Cap at 2000

    def _generate_local_keywords(self) -> List[Dict[str, Any]]:
        """Generate hyper-local area-specific keywords"""
        areas = [
            'gachibowli', 'madhapur', 'hitech city', 'kukatpally', 'banjara hills',
            'jubilee hills', 'kondapur', 'miyapur', 'lb nagar', 'dilsukhnagar',
            'uppal', 'shamshabad', 'begumpet', 'somajiguda', 'punjagutta',
            'ameerpet', 'sr nagar', 'malakpet', 'chandanagar', 'bachupally',
            'nizampet', 'beeramguda', 'patancheru', 'medchal', 'shankarpally'
        ]
        
        services = ['bike rental', 'car rental', 'camera rental', 'self drive car', 'wedding car']
        
        keywords = []
        for area in areas:
            for service in services:
                keywords.append({
                    'keyword': f"{service} {area}",
                    'type': 'local',
                    'intent': 'commercial',
                    'volume': self._estimate_volume(f"{service} {area}"),
                    'difficulty': 20,
                    'area': area
                })
                keywords.append({
                    'keyword': f"{service} near {area}",
                    'type': 'local',
                    'intent': 'commercial',
                    'volume': self._estimate_volume(f"{service} near {area}"),
                    'difficulty': 15,
                    'area': area
                })
        return keywords

    def _get_competitor_gaps(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract competitor gap keywords from context"""
        competitor_data = context.get('competitor_keywords', [])
        if isinstance(competitor_data, list):
            return [
                {**kw, 'source': 'competitor_gap', 'type': 'gap'}
                for kw in competitor_data
                if kw.get('gap_score', 0) > 0.5
            ]
        return []

    def _generate_question_keywords(self) -> List[Dict[str, Any]]:
        """Generate People Also Ask style question keywords"""
        question_templates = [
            "how much does {service} cost in {location}",
            "where to rent {service} in {location}",
            "best {service} in {location}",
            "is {service} worth it in {location}",
            "how to book {service} in {location}",
            "what documents needed for {service} in {location}",
            "{service} vs buying in {location}",
            "cheapest {service} in {location}",
            "luxury {service} in {location}",
            "{service} with driver in {location}"
        ]

        services = ['bike rental', 'car rental', 'camera rental', 'self drive car', 'wedding car']
        locations = ['hyderabad', 'secunderabad', 'gachibowli', 'madhapur', 'kukatpally']

        keywords = []
        for template in question_templates:
            for service in services:
                for location in locations:
                    kw = template.format(service=service, location=location)
                    keywords.append({
                        'keyword': kw,
                        'type': 'question',
                        'intent': 'informational',
                        'volume': self._estimate_volume(kw),
                        'difficulty': 15
                    })
        return keywords[:500]

    def _get_seasonal_keywords(self) -> List[Dict[str, Any]]:
        """Seasonal and event-based keywords"""
        seasonal = [
            {'keyword': 'wedding season bike rental hyderabad', 'months': [10, 11, 12, 1, 2], 'volume': 300, 'difficulty': 30},
            {'keyword': 'summer car rental hyderabad', 'months': [3, 4, 5, 6], 'volume': 400, 'difficulty': 35},
            {'keyword': 'diwali camera rental hyderabad', 'months': [10, 11], 'volume': 200, 'difficulty': 25},
            {'keyword': 'new year party rentals hyderabad', 'months': [12], 'volume': 500, 'difficulty': 28},
            {'keyword': 'sankranti equipment rental hyderabad', 'months': [1], 'volume': 150, 'difficulty': 20},
            {'keyword': 'college fest rentals hyderabad', 'months': [2, 3, 9, 10], 'volume': 300, 'difficulty': 25},
            {'keyword': 'corporate event rentals hyderabad', 'months': [1, 2, 3, 9, 10, 11, 12], 'volume': 250, 'difficulty': 28},
        ]
        current_month = datetime.now().month
        return [
            {**kw, 'type': 'seasonal', 'intent': 'commercial', 'is_current_season': current_month in kw['months']}
            for kw in seasonal
        ]

    def _estimate_volume(self, keyword: str) -> int:
        """Estimate search volume based on keyword characteristics"""
        words = len(keyword.split())
        if words <= 2:
            return 1000
        elif words == 3:
            return 300
        elif words == 4:
            return 100
        else:
            return 50

    def _estimate_difficulty(self, keyword: str) -> int:
        """Estimate keyword difficulty"""
        if 'hyderabad' in keyword and len(keyword.split()) <= 3:
            return 35
        elif 'near me' in keyword:
            return 25
        elif len(keyword.split()) >= 5:
            return 15
        return 30

    def _cluster_keywords(self, keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cluster keywords by semantic similarity"""
        clusters = defaultdict(list)
        
        for kw in keywords:
            # Simple clustering by keyword type and base terms
            base_terms = ['bike', 'car', 'camera', 'wedding', 'party', 'self drive', 'rental', 'rent']
            cluster_key = 'general'
            
            for term in base_terms:
                if term in kw['keyword'].lower():
                    cluster_key = term
                    break
            
            # Sub-cluster by intent
            cluster_key = f"{cluster_key}_{kw['intent']}"
            clusters[cluster_key].append(kw)

        # Convert to list format
        result = []
        for name, kws in clusters.items():
            if len(kws) >= 3:  # Minimum cluster size
                avg_volume = sum(k['volume'] for k in kws) // len(kws)
                avg_difficulty = sum(k['difficulty'] for k in kws) // len(kws)
                result.append({
                    'cluster_name': name,
                    'keyword_count': len(kws),
                    'avg_volume': avg_volume,
                    'avg_difficulty': avg_difficulty,
                    'top_keywords': sorted(kws, key=lambda x: x['volume'], reverse=True)[:10],
                    'intent_distribution': self._get_intent_distribution(kws)
                })
        
        return sorted(result, key=lambda x: x['keyword_count'], reverse=True)

    def _get_intent_distribution(self, keywords: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get intent distribution within cluster"""
        dist = defaultdict(int)
        for k in keywords:
            dist[k['intent']] += 1
        return dict(dist)

    def _score_keywords(self, keywords: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and prioritize keywords"""
        # Create cluster lookup
        cluster_lookup = {}
        for cluster in clusters:
            for kw in cluster['top_keywords']:
                cluster_lookup[kw['keyword']] = cluster['cluster_name']

        scored = []
        for kw in keywords:
            # Volume score (0-40)
            vol_score = min(kw['volume'] / 100, 40)
            
            # Difficulty inverse (0-30) - lower difficulty = higher score
            diff_score = max(30 - kw['difficulty'], 0)
            
            # Intent value (0-20)
            intent_values = {'transactional': 20, 'commercial': 18, 'navigational': 15, 'informational': 10}
            intent_score = intent_values.get(kw.get('intent', 'informational'), 10)
            
            # Type bonus (0-10)
            type_bonus = {
                'brand': 10, 'brand_local': 10,
                'category': 8, 'local': 8,
                'long_tail': 5, 'question': 5,
                'seasonal': 5 if kw.get('is_current_season') else 2,
                'gap': 8
            }.get(kw.get('type', ''), 0)
            
            # Cluster authority bonus
            cluster_bonus = 5 if kw['keyword'] in cluster_lookup else 0
            
            priority_score = vol_score + diff_score + intent_score + type_bonus + cluster_bonus
            
            scored.append({
                **kw,
                'priority_score': round(priority_score, 1),
                'volume_score': round(vol_score, 1),
                'difficulty_score': round(diff_score, 1),
                'intent_score': intent_score,
                'type_bonus': type_bonus,
                'cluster': cluster_lookup.get(kw['keyword'], 'unclustered')
            })
        
        return sorted(scored, key=lambda x: x['priority_score'], reverse=True)

    def _generate_report(self, keywords: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> str:
        """Generate markdown report"""
        high_priority = [k for k in keywords if k['priority_score'] >= 70]
        
        report = f"""# GoRentals Keyword Research Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Keywords Analyzed:** {len(keywords)}
**Semantic Clusters:** {len(clusters)}
**High Priority Keywords (Score ≥ 70):** {len(high_priority)}

---

## Executive Summary

This report contains comprehensive keyword intelligence for GoRentals Hyderabad.
Keywords are scored on a 0-100 priority scale based on volume, difficulty, intent, and type.

---

## Top 20 Priority Keywords

| Keyword | Type | Intent | Volume | Difficulty | Score | Cluster |
|---------|------|--------|--------|------------|-------|---------|
"""
        for kw in high_priority[:20]:
            report += f"| {kw['keyword']} | {kw['type']} | {kw['intent']} | {kw['volume']} | {kw['difficulty']} | {kw['priority_score']} | {kw['cluster']} |\n"

        report += f"""

---

## Semantic Clusters ({len(clusters)})

"""
        for cluster in clusters[:15]:
            report += f"""### {cluster['cluster_name'].replace('_', ' ').title()}
- **Keywords:** {cluster['keyword_count']}
- **Avg Volume:** {cluster['avg_volume']}
- **Avg Difficulty:** {cluster['avg_difficulty']}
- **Intent Distribution:** {cluster['intent_distribution']}
- **Top Keywords:** {', '.join([k['keyword'] for k in cluster['top_keywords'][:5]])}

"""

        # Type distribution
        type_dist = defaultdict(int)
        for kw in keywords:
            type_dist[kw['type']] += 1

        report += f"""---

## Keyword Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
"""
        for typ, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(keywords) * 100
            report += f"| {typ} | {count} | {pct:.1f}% |\n"

        # Intent distribution
        intent_dist = defaultdict(int)
        for kw in keywords:
            intent_dist[kw['intent']] += 1

        report += f"""

---

## Search Intent Distribution

| Intent | Count | Percentage |
|--------|-------|------------|
"""
        for intent, count in sorted(intent_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(keywords) * 100
            report += f"| {intent} | {count} | {pct:.1f}% |\n"

        # Action items
        report += f"""

---

## Recommended Actions

### Immediate (This Week)
1. **Create pillar pages** for top 5 clusters: {', '.join([c['cluster_name'] for c in clusters[:5]])}
2. **Optimize existing pages** for {len([k for k in high_priority if k['type'] in ['brand', 'brand_local']])} brand keywords
3. **Build local landing pages** for top 10 Hyderabad areas

### Short Term (This Month)
1. **Produce {len([k for k in high_priority if k['type'] == 'long_tail'])} long-tail articles** targeting commercial intent
2. **Answer {len([k for k in high_priority if k['type'] == 'question'])} question keywords** in FAQ sections
3. **Prepare seasonal content** for upcoming season

### Ongoing
1. **Monitor competitor gaps** weekly
2. **Track ranking changes** for priority keywords
3. **Expand local coverage** to all 33 Telangana districts

---

*Report generated by GoRentals Keyword Intelligence Agent*
"""
        return report