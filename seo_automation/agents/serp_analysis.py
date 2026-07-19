"""
SERP Analysis Agent
Analyzes Google SERP features for target keywords to identify optimization opportunities
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class SERPAnalysisAgent(BaseAgent):
    """Agent for analyzing Google SERP features and identifying optimization opportunities"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.serp_config = config.get('agents', {}).get('serp_analysis', {})
        self.features_to_track = self.serp_config.get('features_to_track', [
            'featured_snippet', 'people_also_ask', 'local_pack', 
            'knowledge_panel', 'image_pack', 'video_carousel', 'shopping_results'
        ])
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
            """Execute SERP analysis for target keywords"""
            print("DEBUG: serp_analysis execute() called", file=sys.stderr)
            try:
                # Always load keywords directly from file to ensure latest format
                keywords = []
                keywords_file = self.project_root / "research" / "keywords.json"
                if keywords_file.exists():
                    try:
                        with open(keywords_file, 'r') as f:
                            data = json.load(f)
                            # Handle both old and new formats
                            kw_list = data.get('keywords', []) if isinstance(data, dict) else []
                            keywords = [k['keyword'] if isinstance(k, dict) and 'keyword' in k else str(k) for k in kw_list]
                    except Exception as e:
                        print(f"Warning: Failed to load keywords.json: {e}")
                        keywords = []
                print(f"DEBUG: serp_analysis keywords type={type(keywords)}, len={len(keywords)}", file=sys.stderr)
                if keywords:
                    print(f"DEBUG: first kw type={type(keywords[0])}, value={keywords[0]}", file=sys.stderr)
            
                if not isinstance(keywords, list):
                    keywords = []
            
                # Limit to top priority keywords
                priority_keywords = [k for k in keywords if isinstance(k, str) and self._is_priority_keyword(k)][:50]
            
                # Analyze SERP for each keyword
                serp_analyses = []
                for kw in priority_keywords:
                    analysis = await self._analyze_serp(kw)
                    serp_analyses.append(analysis)
            
                # Aggregate findings
                feature_analysis = self._analyze_features(serp_analyses)
                competitor_serp = self._analyze_competitor_presence(serp_analyses)
                optimization_opportunities = self._identify_opportunities(serp_analyses, feature_analysis)
            
                # Save outputs
                files_created = []
            
                # Full SERP analysis data
                serp_file = self.save_json({
                    'analyzed_at': datetime.now().isoformat(),
                    'total_keywords': len(priority_keywords),
                    'analyzed_keywords': len(serp_analyses),
                    'features_tracked': self.features_to_track,
                    'analyses': serp_analyses
                }, "research/serp_analysis_data.json")
                files_created.append(serp_file)
            
                # Feature analysis summary
                feature_file = self.save_json(feature_analysis, "research/serp_features_summary.json")
                files_created.append(feature_file)
            
                # Competitor SERP presence
                comp_file = self.save_json(competitor_serp, "research/serp_competitor_presence.json")
                files_created.append(comp_file)
            
                # Optimization opportunities
                opp_file = self.save_json(optimization_opportunities, "research/serp_opportunities.json")
                files_created.append(opp_file)
            
                # Markdown report
                report = self._generate_report(serp_analyses, feature_analysis, competitor_serp, optimization_opportunities)
                report_file = self.save_output(report, "research/serp-analysis.md")
                files_created.append(report_file)
            
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={
                        'keywords_analyzed': len(serp_analyses),
                        'features_found': feature_analysis.get('total_features', 0),
                        'opportunities': len(optimization_opportunities),
                        'top_opportunity': optimization_opportunities[0] if optimization_opportunities else None
                    },
                    files_created=files_created
                )
            except Exception as e:
                print(f"ERROR in serp_analysis: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={},
                    files_created=[],
                    errors=[str(e)]
                )

    def _is_priority_keyword(self, keyword: str) -> bool:
        """Determine if keyword is high priority for SERP analysis"""
        keyword_lower = keyword.lower()
        priority_terms = [
            'hyderabad', 'rental', 'rent', 'hire', 'near me',
            'bike', 'car', 'camera', 'self drive', 'wedding',
            'party', 'equipment', 'event'
        ]
        return any(term in keyword_lower for term in priority_terms)

    async def _analyze_serp(self, keyword: str) -> Dict[str, Any]:
        """Analyze SERP for a single keyword (simulated - replace with Obscura/SerpAPI)"""
        kw_lower = keyword.lower()
        
        # Determine likely SERP features based on keyword characteristics
        has_local = any(term in kw_lower for term in ['hyderabad', 'near me', 'gachibowli', 'hitech', 'banjara', 'jubilee', 'kukatpally', 'madhapur', 'secunderabad'])
        has_commercial = any(term in kw_lower for term in ['rental', 'rent', 'hire', 'price', 'cost', 'cheap', 'best', 'top'])
        has_informational = any(term in kw_lower for term in ['how', 'what', 'where', 'when', 'why', 'guide', 'tips', 'vs', 'versus'])
        has_visual = any(term in kw_lower for term in ['camera', 'bike', 'car', 'wedding', 'party', 'event'])
        
        return {
            'keyword': keyword,
            'analyzed_at': datetime.now().isoformat(),
            'serp_features': {
                'featured_snippet': {
                    'present': has_informational and not has_local,
                    'type': 'paragraph' if has_informational else None,
                    'source_url': 'competitor.com/guide' if has_informational else None,
                    'content_preview': 'To rent a camera in Hyderabad, you need...' if has_informational else None
                },
                'people_also_ask': {
                    'present': True,
                    'questions': self._generate_paa_questions(keyword),
                    'count': 4
                },
                'local_pack': {
                    'present': has_local and has_commercial,
                    'listings_count': 3 if has_local and has_commercial else 0,
                    'top_listings': [
                        {'name': 'GoRentals', 'rating': 4.8, 'reviews': 1200},
                        {'name': 'Rentomojo', 'rating': 4.3, 'reviews': 890},
                        {'name': 'Local Vendor', 'rating': 4.5, 'reviews': 340}
                    ] if has_local and has_commercial else []
                },
                'knowledge_panel': {
                    'present': 'gorentals' in kw_lower,
                    'entity_type': 'LocalBusiness' if 'gorentals' in kw_lower else None
                },
                'image_pack': {
                    'present': has_visual,
                    'image_count': 6 if has_visual else 0,
                    'top_sources': ['gorentals.com', 'rentomojo.com', 'localvendor.com'] if has_visual else []
                },
                'video_carousel': {
                    'present': 'how to' in kw_lower or 'review' in kw_lower,
                    'video_count': 3 if 'how to' in kw_lower else 0,
                    'top_channels': ['GoRentals Official', 'Tech Reviewer Hyderabad'] if 'how to' in kw_lower else []
                },
                'shopping_results': {
                    'present': has_commercial and not has_local,
                    'product_count': 10 if has_commercial and not has_local else 0,
                    'top_merchants': ['Amazon', 'Flipkart', 'GoRentals'] if has_commercial else []
                },
                'related_searches': self._generate_related_searches(keyword),
                'top_organic_results': self._simulate_organic_results(keyword)
            },
            'search_intent': self._determine_intent(keyword),
            'difficulty_score': self._estimate_difficulty(keyword),
            'opportunity_score': self._calculate_opportunity(keyword)
        }

    def _generate_paa_questions(self, keyword: str) -> List[str]:
        """Generate likely People Also Ask questions"""
        base = keyword.lower()
        questions = []
        
        if 'rental' in base or 'rent' in base:
            questions.extend([
                f"How much does {keyword} cost in Hyderabad?",
                f"Where can I find {keyword} near me?",
                f"What documents are needed for {keyword}?",
                f"Is {keyword} available for monthly rental?"
            ])
        elif 'camera' in base:
            questions.extend([
                f"Which camera is best for rent in Hyderabad?",
                f"Can I rent camera for one day in Hyderabad?",
                f"What is the deposit for camera rental?"
            ])
        elif 'bike' in base or 'car' in base:
            questions.extend([
                f"Is self drive {keyword} available in Hyderabad?",
                f"What is the mileage limit for {keyword}?",
                f"Do I need license for {keyword}?"
            ])
        
        return questions[:4]

    def _generate_related_searches(self, keyword: str) -> List[str]:
        """Generate related searches"""
        base = keyword.lower()
        related = []
        
        if 'rental' in base:
            related = [
                f"{keyword} near me",
                f"cheap {keyword}",
                f"best {keyword} in hyderabad",
                f"{keyword} monthly",
                f"{keyword} with driver"
            ]
        elif 'bike' in base:
            related = [
                f"{keyword} hyderabad",
                f"self drive {keyword}",
                f"{keyword} price hyderabad",
                f"scooty rental hyderabad"
            ]
        elif 'car' in base:
            related = [
                f"{keyword} hyderabad",
                f"self drive {keyword}",
                f"{keyword} price hyderabad",
                f"luxury {keyword} hyderabad"
            ]
        elif 'camera' in base:
            related = [
                f"dslr {keyword} hyderabad",
                f"{keyword} for wedding hyderabad",
                f"{keyword} per day hyderabad"
            ]
        
        return related[:5]

    def _simulate_organic_results(self, keyword: str) -> List[Dict]:
        """Simulate top organic results"""
        base_domains = [
            {'domain': 'gorentals.com', 'position': 1},
            {'domain': 'rentomojo.com', 'position': 2},
            {'domain': 'furlenco.com', 'position': 3},
            {'domain': 'grabonrent.com', 'position': 4},
            {'domain': 'localvendor.com', 'position': 5}
        ]
        
        results = []
        for i, d in enumerate(base_domains):
            results.append({
                'position': i + 1,
                'domain': d['domain'],
                'url': f"https://{d['domain']}/{keyword.replace(' ', '-')}",
                'title': f"{keyword.title()} in Hyderabad - {d['domain'].split('.')[0].title()}",
                'has_snippet': True,
                'has_schema': d['domain'] in ['gorentals.com', 'rentomojo.com']
            })
        return results

    def _determine_intent(self, keyword: str) -> str:
        """Determine search intent"""
        kw = keyword.lower()
        if any(w in kw for w in ['buy', 'price', 'cost', 'cheap', 'deal', 'book', 'rent now']):
            return 'transactional'
        elif any(w in kw for w in ['best', 'top', 'review', 'compare', 'vs', 'versus']):
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

    def _calculate_opportunity(self, keyword: str) -> float:
        """Calculate opportunity score"""
        difficulty = self._estimate_difficulty(keyword)
        words = len(keyword.split())
        score = (50 - difficulty) * (1 + words * 0.1)
        return round(score, 1)

    def _analyze_features(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate feature analysis across all keywords"""
        feature_counts = defaultdict(int)
        feature_details = defaultdict(list)
        
        for a in analyses:
            features = a.get('serp_features', {})
            for feature_name, feature_data in features.items():
                # Skip non-dict values (like related_searches list, top_organic_results list)
                if not isinstance(feature_data, dict):
                    continue
                if feature_data.get('present'):
                    feature_counts[feature_name] += 1
                    feature_details[feature_name].append({
                        'keyword': a['keyword'],
                        'details': feature_data
                    })
        
        return {
            'total_keywords': len(analyses),
            'total_features': sum(feature_counts.values()),
            'feature_counts': dict(feature_counts),
            'feature_coverage': {
                feature: f"{count}/{len(analyses)} ({count/len(analyses)*100:.0f}%)"
                for feature, count in feature_counts.items()
            },
            'feature_details': dict(feature_details)
        }

    def _analyze_competitor_presence(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Analyze which competitors appear in SERP features"""
        competitor_features = defaultdict(lambda: defaultdict(int))
        competitor_positions = defaultdict(list)
        
        for a in analyses:
            organic = a.get('serp_features', {}).get('top_organic_results', [])
            for result in organic:
                domain = result['domain']
                pos = result['position']
                competitor_positions[domain].append(pos)
                
                # Check features
                features = a.get('serp_features', {})
                for feat_name, feat_data in features.items():
                    # Skip non-dict values (like related_searches list, top_organic_results list)
                    if not isinstance(feat_data, dict):
                        continue
                    if feat_data.get('present') and 'source' in str(feat_data).lower():
                        if domain in str(feat_data).lower():
                            competitor_features[domain][feat_name] += 1
        
        return {
            'competitor_positions': {
                domain: {
                    'avg_position': sum(positions)/len(positions),
                    'best_position': min(positions),
                    'top_3_count': sum(1 for p in positions if p <= 3),
                    'keywords': len(positions)
                }
                for domain, positions in competitor_positions.items()
            },
            'competitor_features': dict(competitor_features)
        }

    def _identify_opportunities(self, analyses: List[Dict], feature_analysis: Dict) -> List[Dict]:
        """Identify optimization opportunities"""
        opportunities = []
        
        # Feature snippet opportunities
        for a in analyses:
            kw = a['keyword']
            features = a.get('serp_features', {})
            intent = a.get('search_intent', 'commercial')
            opp_score = a.get('opportunity_score', 0)
            
            # Featured snippet opportunity
            fs = features.get('featured_snippet', {})
            if fs.get('present') and not fs.get('source_url', '').startswith('gorentals'):
                opportunities.append({
                    'keyword': kw,
                    'type': 'featured_snippet',
                    'current_holder': fs.get('source_url', 'competitor'),
                    'intent': intent,
                    'opportunity_score': opp_score,
                    'action': 'Create/optimize content to win featured snippet',
                    'difficulty': 'medium'
                })
            
            # Local pack opportunity
            lp = features.get('local_pack', {})
            if lp.get('present'):
                listings = lp.get('top_listings', [])
                gorentals_in_pack = any('gorental' in str(l).lower() for l in listings)
                if not gorentals_in_pack:
                    opportunities.append({
                        'keyword': kw,
                        'type': 'local_pack',
                        'current_listings': [l.get('name', '') for l in listings[:3]],
                        'intent': 'local',
                        'opportunity_score': opp_score,
                        'action': 'Optimize GBP, build local citations, encourage reviews',
                        'difficulty': 'medium'
                    })
            
            # Image pack opportunity
            ip = features.get('image_pack', {})
            if ip.get('present'):
                sources = ip.get('top_sources', [])
                gorentals_in_images = any('gorental' in s.lower() for s in sources)
                if not gorentals_in_images:
                    opportunities.append({
                        'keyword': kw,
                        'type': 'image_pack',
                        'current_sources': sources[:3],
                        'intent': 'visual',
                        'opportunity_score': opp_score,
                        'action': 'Optimize images with alt text, structured data, fast loading',
                        'difficulty': 'easy'
                    })
        
        return sorted(opportunities, key=lambda x: x['opportunity_score'], reverse=True)

    def _generate_report(self, analyses: List[Dict], feature_analysis: Dict, 
                        competitor_serp: Dict, opportunities: List[Dict]) -> str:
        """Generate markdown report"""
        report = f"""# SERP Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Keywords Analyzed:** {len(analyses)}
**Features Tracked:** {len(self.features_to_track)}

---

## Feature Coverage Summary

| Feature | Keywords with Feature | Coverage |
|---------|----------------------|----------|
"""
        for feature, count in feature_analysis.get('feature_counts', {}).items():
            coverage = feature_analysis.get('feature_coverage', {}).get(feature, 'N/A')
            report += f"| {feature.replace('_', ' ').title()} | {count} | {coverage} |\n"

        report += f"""

---

## Competitor SERP Presence

| Competitor | Avg Position | Top 3 Count | Keywords |
|------------|--------------|-------------|----------|
"""
        for comp, data in competitor_serp.get('competitor_positions', {}).items():
            report += f"| {comp} | {data['avg_position']:.1f} | {data['top_3_count']} | {data['keywords']} |\n"

        report += f"""

---

## Top Optimization Opportunities ({len(opportunities)} found)

| Keyword | Type | Current State | Opportunity Score | Action | Difficulty |
|---------|------|---------------|-------------------|--------|------------|
"""
        for opp in opportunities[:20]:
            report += f"| {opp['keyword']} | {opp['type'].replace('_', ' ').title()} | {opp.get('current_holder', opp.get('current_sources', opp.get('current_listings', ['N/A']))[0] if opp.get('current_holder') or opp.get('current_sources') or opp.get('current_listings') else 'N/A')[:30]} | {opp['opportunity_score']} | {opp['action'][:50]}... | {opp['difficulty']} |\n"

        report += f"""

---

## Recommendations

### Immediate (This Week)
1. **Local Pack Domination** - Optimize GBP for all local-intent keywords
2. **Image SEO** - Add alt text, structured data to all product images
3. **Featured Snippets** - Create FAQ/content blocks for 5 highest-opportunity keywords

### Short-term (This Month)
1. **GBP Optimization** - Complete profile, posts, Q&A, photos for all 20 areas
2. **Schema Markup** - Implement Product, LocalBusiness, FAQ, Review schemas
3. **Content Creation** - Write content targeting 10 featured snippet opportunities

### Ongoing
1. **Monitor SERP Changes** - Weekly SERP analysis for top 50 keywords
2. **Competitor Tracking** - Alert when competitors win new features
3. **Review Generation** - Systematic review collection for GBP

---
*Generated by GoRentals SERP Analysis Agent*
"""
        return report