"""
SEO Content Rating Agent
Evaluates and scores SEO content quality across multiple dimensions:
readability, keyword optimization, search intent, EEAT, structure, originality
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class ContentRatingAgent(BaseAgent):
    """Agent for rating and scoring SEO content quality"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.rating_config = config.get('agents', {}).get('content_rating', {})
        self.weights = self.rating_config.get('scoring_weights', {
            'readability': 20,
            'keyword_optimization': 20,
            'search_intent_match': 15,
            'content_depth': 15,
            'eeat_signals': 10,
            'structure_formatting': 10,
            'internal_linking': 5,
            'originality': 5
        })
        self.thresholds = self.rating_config.get('quality_thresholds', {
            'excellent': 85,
            'good': 70,
            'needs_improvement': 50,
            'poor': 30
        })
        self.checks = self.rating_config.get('checks', [])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute content rating across all available content"""
        
        # 1. Load content to rate
        content_items = self._load_content_to_rate(context)
        
        if not content_items:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'message': 'No content to rate', 'rated': 0},
                files_created=[]
            )

        # 2. Rate each piece of content
        ratings = []
        for item in content_items:
            rating = await self._rate_content(item)
            ratings.append(rating)

        # 3. Generate summary statistics
        summary = self._generate_summary(ratings)

        # 4. Save outputs
        files_created = self._save_outputs(ratings, summary)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'total_rated': len(ratings),
                'summary': summary,
                'ratings': ratings
            },
            files_created=files_created
        )

    def _load_content_to_rate(self, context: Dict[str, Any]) -> List[Dict]:
        """Load all content from various sources for rating"""
        content_items = []

        # From SEO writer output (written content)
        written_file = self.project_root / "content" / "metadata" / "written_content.json"
        if written_file.exists():
            with open(written_file, 'r') as f:
                data = json.load(f)
                for item in data.get('items', []):
                    if item.get('filepath') and Path(item['filepath']).exists():
                        content_items.append({
                            'id': item['content_id'],
                            'title': item.get('title', ''),
                            'filepath': item['filepath'],
                            'target_keyword': item.get('target_keyword', ''),
                            'content_type': item.get('content_type', 'blog_post'),
                            'source': 'seo_writer'
                        })

        # From drafts directory
        drafts_dir = self.project_root / "content" / "blog-posts"
        if drafts_dir.exists():
            for md_file in drafts_dir.rglob("*.md"):
                if not md_file.name.startswith('_'):
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Parse frontmatter
                    title, body = self._parse_markdown(content)
                    content_items.append({
                        'id': md_file.stem,
                        'title': title,
                        'filepath': str(md_file),
                        'content': body,
                        'target_keyword': self._extract_target_keyword(title, body),
                        'content_type': 'blog_post',
                        'source': 'drafts'
                    })

        # From existing SEO content
        seo_drafts = self.project_root.parent / "seo" / "drafts"
        if seo_drafts.exists():
            for md_file in seo_drafts.rglob("*.md"):
                if not md_file.name.startswith('_'):
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    title, body = self._parse_markdown(content)
                    content_items.append({
                        'id': f"seo_{md_file.stem}",
                        'title': title,
                        'filepath': str(md_file),
                        'content': body,
                        'target_keyword': self._extract_target_keyword(title, body),
                        'content_type': 'seo_content',
                        'source': 'seo_drafts'
                    })

        return content_items

    def _parse_markdown(self, content: str) -> tuple:
        """Parse markdown with frontmatter"""
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                # Extract title from frontmatter
                title_match = re.search(r'title:\s*["\']?([^"\']+)["\']?', frontmatter)
                title = title_match.group(1) if title_match else ''
                return title, body
        # No frontmatter, extract first h1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = h1_match.group(1) if h1_match else ''
        return title, content

    def _extract_target_keyword(self, title: str, body: str) -> str:
        """Extract likely target keyword from content"""
        # Check for explicit keyword in frontmatter would be better
        # For now, use most frequent meaningful phrase in title
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        # Filter common words
        stopwords = {'the', 'and', 'for', 'with', 'how', 'what', 'where', 'when', 'why', 'best', 'top', 'guide', 'complete', 'hyderabad'}
        filtered = [w for w in words if w not in stopwords]
        if filtered:
            return filtered[0]
        return ''

    async def _rate_content(self, item: Dict) -> Dict:
        """Rate a single piece of content across all dimensions"""
        
        # Load content if not already loaded
        if 'content' not in item and item.get('filepath'):
            with open(item['filepath'], 'r', encoding='utf-8') as f:
                full_content = f.read()
            _, item['content'] = self._parse_markdown(full_content)

        content = item.get('content', '')
        title = item.get('title', '')
        target_keyword = item.get('target_keyword', '').lower()

        scores = {}
        details = {}

        # 1. Readability (Flesch-Kincaid)
        scores['readability'], details['readability'] = self._score_readability(content)

        # 2. Keyword Optimization
        scores['keyword_optimization'], details['keyword_optimization'] = self._score_keyword_optimization(
            content, title, target_keyword
        )

        # 3. Search Intent Match
        scores['search_intent_match'], details['search_intent_match'] = self._score_search_intent(
            content, title, target_keyword, item.get('content_type', '')
        )

        # 4. Content Depth
        scores['content_depth'], details['content_depth'] = self._score_content_depth(
            content, target_keyword
        )

        # 5. EEAT Signals
        scores['eeat_signals'], details['eeat_signals'] = self._score_eeat_signals(
            content, title
        )

        # 6. Structure & Formatting
        scores['structure_formatting'], details['structure_formatting'] = self._score_structure(
            content
        )

        # 7. Internal Linking
        scores['internal_linking'], details['internal_linking'] = self._score_internal_links(
            content
        )

        # 8. Originality (heuristic)
        scores['originality'], details['originality'] = self._score_originality(content)

        # Calculate weighted total
        total_score = sum(
            scores[dim] * self.weights.get(dim, 0) / 100 
            for dim in scores
        )
        total_score = round(total_score, 1)

        # Determine rating label
        if total_score >= self.thresholds['excellent']:
            rating = 'excellent'
        elif total_score >= self.thresholds['good']:
            rating = 'good'
        elif total_score >= self.thresholds['needs_improvement']:
            rating = 'needs_improvement'
        else:
            rating = 'poor'

        return {
            'content_id': item['id'],
            'title': title,
            'filepath': item.get('filepath', ''),
            'target_keyword': target_keyword,
            'content_type': item.get('content_type', ''),
            'source': item.get('source', ''),
            'rated_at': datetime.now().isoformat(),
            'overall_score': total_score,
            'rating': rating,
            'dimension_scores': scores,
            'dimension_details': details,
            'word_count': len(content.split()),
            'recommendations': self._generate_recommendations(scores, details)
        }

    def _score_readability(self, content: str) -> tuple:
        """Score readability using Flesch-Kincaid"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = content.split()
        syllables = sum(self._count_syllables(w) for w in words)
        
        if not sentences or not words:
            return 0, {'error': 'No content'}
        
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllables / len(words)
        
        # Flesch Reading Ease
        flesch = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        flesch = max(0, min(100, flesch))
        
        # Convert to 0-100 score (higher = more readable)
        if flesch >= 60:
            score = 90
        elif flesch >= 50:
            score = 75
        elif flesch >= 30:
            score = 60
        else:
            score = 40
        
        return score, {
            'flesch_reading_ease': round(flesch, 1),
            'avg_sentence_length': round(avg_sentence_length, 1),
            'avg_syllables_per_word': round(avg_syllables_per_word, 2),
            'sentence_count': len(sentences),
            'word_count': len(words)
        }

    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count"""
        word = word.lower()
        vowels = 'aeiouy'
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith('e') and count > 1:
            count -= 1
        return max(1, count)

    def _score_keyword_optimization(self, content: str, title: str, target_kw: str) -> tuple:
        """Score keyword optimization"""
        if not target_kw:
            return 50, {'note': 'No target keyword specified'}
        
        content_lower = content.lower()
        title_lower = title.lower()
        kw_lower = target_kw.lower()
        
        # Primary keyword in title
        in_title = kw_lower in title_lower
        # Primary keyword in first 100 words
        first_100 = ' '.join(content_lower.split()[:100])
        in_first_100 = kw_lower in first_100
        # Primary keyword frequency
        kw_count = content_lower.count(kw_lower)
        word_count = len(content.split())
        density = (kw_count * len(kw_lower.split())) / word_count * 100 if word_count > 0 else 0
        
        # Optimal density 0.5-2.5%
        if 0.5 <= density <= 2.5:
            density_score = 100
        elif 0.25 <= density < 0.5 or 2.5 < density <= 4:
            density_score = 70
        elif density > 4:
            density_score = 30  # keyword stuffing
        else:
            density_score = 50
        
        # Keyword in headings
        headings = re.findall(r'^#{2,4}\s+(.+)$', content, re.MULTILINE)
        in_headings = sum(1 for h in headings if kw_lower in h.lower())
        heading_score = min(100, in_headings * 20 + 40)
        
        # LSI/related terms (simple check)
        related_terms = self._get_related_terms(target_kw)
        related_found = sum(1 for t in related_terms if t in content_lower)
        related_score = min(100, related_found * 10 + 30)
        
        total = (
            (30 if in_title else 0) +
            (20 if in_first_100 else 0) +
            density_score * 0.3 +
            heading_score * 0.2 +
            related_score * 0.2
        )
        
        return round(total), {
            'in_title': in_title,
            'in_first_100_words': in_first_100,
            'keyword_count': kw_count,
            'keyword_density': round(density, 2),
            'density_score': density_score,
            'in_headings': in_headings,
            'heading_score': heading_score,
            'related_terms_found': related_found,
            'related_score': related_score
        }

    def _get_related_terms(self, keyword: str) -> List[str]:
        """Get related terms for a keyword (simplified)"""
        # In production, use LSI API or semantic analysis
        kw_lower = keyword.lower()
        related_map = {
            'bike rental': ['bicycle', 'cycle', 'rent', 'hire', 'two wheeler', 'scooty'],
            'car rental': ['automobile', 'vehicle', 'hire', 'self drive', 'rent a car'],
            'camera rental': ['photography', 'lens', 'DSLR', 'mirrorless', 'video', 'shoot'],
            'party rental': ['event', 'celebration', 'wedding', 'decoration', 'equipment'],
            'wedding': ['marriage', 'bridal', 'ceremony', 'reception', 'venue']
        }
        for key, terms in related_map.items():
            if key in kw_lower:
                return terms
        return []

    def _score_search_intent(self, content: str, title: str, target_kw: str, content_type: str) -> tuple:
        """Score how well content matches search intent"""
        
        intent_indicators = {
            'informational': ['how to', 'what is', 'guide', 'tutorial', 'tips', 'learn', 'understand', 'explain'],
            'commercial': ['best', 'top', 'review', 'compare', 'vs', 'price', 'cost', 'buy', 'recommend', 'rating'],
            'transactional': ['book', 'order', 'rent', 'hire', 'price', 'booking', 'reserve', 'deal', 'discount'],
            'navigational': ['login', 'sign in', 'dashboard', 'account', 'contact', 'location', 'near me']
        }
        
        # Detect likely intent from keyword
        kw_lower = target_kw.lower()
        detected_intent = 'informational'
        for intent, indicators in intent_indicators.items():
            if any(ind in kw_lower for ind in indicators):
                detected_intent = intent
                break
        
        if 'vs' in kw_lower or 'compare' in kw_lower:
            detected_intent = 'commercial'
        if any(t in kw_lower for t in ['rent', 'book', 'hire', 'price', 'cost']):
            detected_intent = 'transactional'
        
        # Check content for intent signals
        content_lower = content.lower()
        intent_scores = {}
        for intent, indicators in intent_indicators.items():
            matches = sum(1 for ind in indicators if ind in content_lower)
            intent_scores[intent] = matches
        
        # Score based on match with detected intent
        matched = intent_scores.get(detected_intent, 0)
        total_signals = sum(intent_scores.values())
        
        if detected_intent == 'informational':
            # Needs comprehensive coverage, how-to, definitions
            has_howto = any(p in content_lower for p in ['step', 'how to', 'guide', 'process'])
            has_definitions = 'what is' in content_lower or 'definition' in content_lower
            has_examples = 'example' in content_lower or 'for instance' in content_lower
            score = 50 + (20 if has_howto else 0) + (15 if has_definitions else 0) + (15 if has_examples else 0)
        elif detected_intent == 'commercial':
            # Needs comparisons, reviews, pros/cons
            has_comparison = 'vs' in content_lower or 'compar' in content_lower
            has_pros_cons = 'pros' in content_lower and 'cons' in content_lower
            has_pricing = 'price' in content_lower or 'cost' in content_lower or '₹' in content
            has_reviews = 'review' in content_lower or 'rating' in content_lower
            score = 40 + (20 if has_comparison else 0) + (15 if has_pros_cons else 0) + (15 if has_pricing else 0) + (10 if has_reviews else 0)
        elif detected_intent == 'transactional':
            # Needs clear CTA, booking info, pricing
            has_cta = any(c in content_lower for c in ['book now', 'rent now', 'contact', 'call', 'whatsapp', 'enquire'])
            has_pricing = 'price' in content_lower or 'rate' in content_lower or '₹' in content
            has_availability = 'available' in content_lower or 'availability' in content_lower
            has_contact = 'phone' in content_lower or 'email' in content_lower or 'contact' in content_lower
            score = 40 + (25 if has_cta else 0) + (20 if has_pricing else 0) + (10 if has_availability else 0) + (5 if has_contact else 0)
        else:
            score = 50
        
        return min(100, score), {
            'detected_intent': detected_intent,
            'intent_signals': intent_scores,
            'matched_signals': matched,
            'total_signals': total_signals
        }

    def _score_content_depth(self, content: str, target_kw: str) -> tuple:
        """Score content depth and comprehensiveness"""
        word_count = len(content.split())
        
        # Word count scoring
        if word_count >= 3000:
            wc_score = 100
        elif word_count >= 2000:
            wc_score = 90
        elif word_count >= 1500:
            wc_score = 80
        elif word_count >= 1000:
            wc_score = 70
        elif word_count >= 500:
            wc_score = 50
        else:
            wc_score = 30
        
        # Heading structure
        headings = re.findall(r'^#{2,4}\s+(.+)$', content, re.MULTILINE)
        h2_count = len([h for h in headings if f'## {h}' in content])
        h3_count = len(re.findall(r'^###\s+', content, re.MULTILINE))
        
        structure_score = min(100, 40 + h2_count * 10 + h3_count * 5)
        
        # FAQ section
        has_faq = bool(re.search(r'(FAQ|Frequently Asked|Questions?)', content, re.IGNORECASE))
        faq_score = 100 if has_faq else 0
        
        # Lists and tables
        bullet_lists = len(re.findall(r'^[\-\*]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\d+\.\s+', content, re.MULTILINE))
        tables = len(re.findall(r'\|.*\|', content))
        formatting_score = min(100, bullet_lists * 3 + numbered_lists * 5 + tables * 15)
        
        # Images/media references
        images = len(re.findall(r'!\[.*?\]\(.*?\)', content))
        media_score = min(100, images * 15)
        
        total = (wc_score * 0.35 + structure_score * 0.25 + faq_score * 0.15 + 
                formatting_score * 0.15 + media_score * 0.10)
        
        return round(total), {
            'word_count': word_count,
            'wc_score': wc_score,
            'h2_count': h2_count,
            'h3_count': h3_count,
            'structure_score': structure_score,
            'has_faq': has_faq,
            'faq_score': faq_score,
            'bullet_lists': bullet_lists,
            'numbered_lists': numbered_lists,
            'tables': tables,
            'formatting_score': formatting_score,
            'images': images,
            'media_score': media_score
        }

    def _score_eeat_signals(self, content: str, title: str) -> tuple:
        """Score EEAT (Experience, Expertise, Authoritativeness, Trustworthiness)"""
        content_lower = content.lower()
        
        # Experience signals
        experience_signals = {
            'personal_experience': any(p in content_lower for p in ['i tested', 'i tried', 'my experience', 'we tested', 'in our experience']),
            'case_study': 'case study' in content_lower,
            'real_example': 'for example' in content_lower or 'e.g.' in content_lower,
            'specific_details': any(p in content_lower for p in ['₹', 'percent', '%', 'specific', 'exact', 'precisely'])
        }
        exp_score = sum(experience_signals.values()) * 20
        
        # Expertise signals
        expertise_signals = {
            'author_bio': 'author' in content_lower or 'written by' in content_lower,
            'credentials': any(c in content_lower for c in ['certified', 'expert', 'specialist', 'professional', 'years of experience']),
            'technical_depth': any(t in content_lower for t in ['technical', 'specification', 'specs', 'details', 'parameters']),
            'citations': 'source:' in content_lower or 'reference:' in content_lower or 'study' in content_lower
        }
        exp_score = sum(expertise_signals.values()) * 20
        
        # Authoritativeness signals
        authority_signals = {
            'external_links': len(re.findall(r'https?://[^\s\)]+', content)) > 0,
            'brand_mentions': any(b in content_lower for b in ['gorentals', 'go rentals', 'industry', 'market leader']),
            'data_stats': any(d in content_lower for d in ['data', 'statistics', 'survey', 'report', 'research']),
            'awards_recognition': any(a in content_lower for a in ['award', 'recognized', 'certified', 'accredited'])
        }
        auth_score = sum(authority_signals.values()) * 20
        
        # Trustworthiness signals
        trust_signals = {
            'contact_info': any(c in content_lower for c in ['contact', 'phone', 'email', 'address', 'location']),
            'transparency': any(t in content_lower for t in ['refund', 'cancellation', 'policy', 'terms', 'guarantee']),
            'reviews_testimonials': any(r in content_lower for r in ['review', 'testimonial', 'customer', 'feedback', 'rating']),
            'security_privacy': any(s in content_lower for s in ['secure', 'privacy', 'ssl', 'encrypted', 'safe'])
        }
        trust_score = sum(trust_signals.values()) * 20
        
        total = min(100, (exp_score + exp_score + auth_score + trust_score) / 4)
        
        return round(total), {
            'experience': exp_score,
            'expertise': exp_score,
            'authoritativeness': auth_score,
            'trustworthiness': trust_score,
            'experience_details': experience_signals,
            'expertise_details': expertise_signals,
            'authority_details': authority_signals,
            'trust_details': trust_signals
        }

    def _score_structure(self, content: str) -> tuple:
        """Score content structure and formatting"""
        # Heading hierarchy
        h1 = len(re.findall(r'^#\s+', content, re.MULTILINE))
        h2 = len(re.findall(r'^##\s+', content, re.MULTILINE))
        h3 = len(re.findall(r'^###\s+', content, re.MULTILINE))
        h4 = len(re.findall(r'^####\s+', content, re.MULTILINE))
        
        # Proper hierarchy: 1 H1, multiple H2, H3 under H2
        hierarchy_score = 100
        if h1 != 1:
            hierarchy_score -= 30
        if h2 == 0:
            hierarchy_score -= 30
        if h3 > 0 and h2 == 0:
            hierarchy_score -= 20
        
        # Paragraph length
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        avg_para_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        if 50 <= avg_para_length <= 150:
            para_score = 100
        elif 30 <= avg_para_length < 50 or 150 < avg_para_length <= 250:
            para_score = 75
        else:
            para_score = 50
        
        # Lists usage
        bullet_lists = len(re.findall(r'^[\-\*]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\d+\.\s+', content, re.MULTILINE))
        list_score = min(100, (bullet_lists + numbered_lists) * 10)
        
        # Table usage
        tables = len(re.findall(r'\|.*\|', content))
        table_score = min(100, tables * 20)
        
        total = (hierarchy_score * 0.3 + para_score * 0.3 + list_score * 0.2 + table_score * 0.2)
        
        return round(total), {
            'h1_count': h1,
            'h2_count': h2,
            'h3_count': h3,
            'h4_count': h4,
            'hierarchy_score': hierarchy_score,
            'avg_paragraph_length': round(avg_para_length, 1),
            'paragraph_score': para_score,
            'bullet_lists': bullet_lists,
            'numbered_lists': numbered_lists,
            'list_score': list_score,
            'tables': tables,
            'table_score': table_score
        }

    def _score_internal_links(self, content: str) -> tuple:
        """Score internal linking"""
        # Find markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        internal_links = []
        external_links = []
        for text, url in links:
            if url.startswith('/') or url.startswith('./') or 'gorentals' in url.lower():
                internal_links.append({'anchor': text, 'url': url})
            elif url.startswith('http'):
                external_links.append({'anchor': text, 'url': url})
        
        internal_count = len(internal_links)
        
        # Score based on count (optimal 3-8)
        if 3 <= internal_count <= 8:
            count_score = 100
        elif 1 <= internal_count <= 2:
            count_score = 60
        elif 9 <= internal_count <= 12:
            count_score = 80
        elif internal_count > 12:
            count_score = 50
        else:
            count_score = 20
        
        # Anchor text diversity
        anchors = [l['anchor'].lower() for l in internal_links]
        unique_anchors = len(set(anchors))
        diversity_score = min(100, unique_anchors / max(1, len(anchors)) * 100) if anchors else 0
        
        # Contextual links (not in lists)
        contextual = sum(1 for l in internal_links if not re.search(r'^[\-\*]\s', l.get('context', '')))
        contextual_score = min(100, contextual * 15)
        
        total = (count_score * 0.4 + diversity_score * 0.3 + contextual_score * 0.3)
        
        return round(total), {
            'internal_count': internal_count,
            'external_count': len(external_links),
            'count_score': count_score,
            'anchor_diversity': round(diversity_score, 1),
            'diversity_score': diversity_score,
            'contextual_links': contextual,
            'contextual_score': contextual_score,
            'internal_links': internal_links[:10]
        }

    def _score_originality(self, content: str) -> tuple:
        """Score content originality (heuristic)"""
        # This is a simplified heuristic - in production use Copyscape/API
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Check for common boilerplate patterns
        boilerplate_patterns = [
            r'looking for.*?hyderabad',
            r'come to the right place',
            r'look no further',
            r'best.*?in hyderabad',
            r'top.*?in hyderabad',
            r'contact us today',
            r'book now',
            r'call us at'
        ]
        
        boilerplate_count = 0
        for pattern in boilerplate_patterns:
            boilerplate_count += len(re.findall(pattern, content, re.IGNORECASE))
        
        # Unique phrases (3+ word ngrams that appear once)
        words = content.lower().split()
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        trigram_counts = defaultdict(int)
        for t in trigrams:
            trigram_counts[t] += 1
        unique_trigrams = sum(1 for t, c in trigram_counts.items() if c == 1)
        total_trigrams = len(trigrams)
        uniqueness_ratio = unique_trigrams / total_trigrams if total_trigrams > 0 else 0
        
        # Penalize boilerplate, reward uniqueness
        base_score = 70
        boilerplate_penalty = min(30, boilerplate_count * 5)
        uniqueness_bonus = min(20, uniqueness_ratio * 50)
        
        score = base_score - boilerplate_penalty + uniqueness_bonus
        score = max(0, min(100, score))
        
        return round(score), {
            'boilerplate_matches': boilerplate_count,
            'unique_trigrams': unique_trigrams,
            'total_trigrams': total_trigrams,
            'uniqueness_ratio': round(uniqueness_ratio, 3),
            'boilerplate_penalty': boilerplate_penalty,
            'uniqueness_bonus': round(uniqueness_bonus, 1)
        }

    def _generate_recommendations(self, scores: Dict, details: Dict) -> List[str]:
        """Generate actionable recommendations based on scores"""
        recs = []
        
        if scores['readability'] < 70:
            recs.append("Improve readability: shorten sentences, use simpler words, add transition words")
        
        if scores['keyword_optimization'] < 70:
            d = details['keyword_optimization']
            if not d.get('in_title'):
                recs.append("Add target keyword to title tag")
            if not d.get('in_first_100_words'):
                recs.append("Include target keyword in first 100 words")
            if d.get('keyword_density', 0) < 0.5:
                recs.append("Increase keyword density naturally (target 0.5-2.5%)")
            elif d.get('keyword_density', 0) > 3:
                recs.append("Reduce keyword density to avoid stuffing")
            if d.get('in_headings', 0) == 0:
                recs.append("Add target keyword to at least one H2/H3 heading")
        
        if scores['search_intent_match'] < 70:
            recs.append(f"Better match {details['search_intent_match'].get('detected_intent', 'search intent')} - add relevant content elements")
        
        if scores['content_depth'] < 70:
            d = details['content_depth']
            if d.get('word_count', 0) < 1500:
                recs.append("Expand content depth - target 1500+ words for comprehensive coverage")
            if not d.get('has_faq'):
                recs.append("Add FAQ section to address common questions")
            if d.get('images', 0) == 0:
                recs.append("Add relevant images with descriptive alt text")
        
        if scores['eeat_signals'] < 60:
            recs.append("Strengthen EEAT signals: add author bio, cite sources, include testimonials, show credentials")
        
        if scores['structure_formatting'] < 70:
            d = details['structure_formatting']
            if d.get('h2_count', 0) < 3:
                recs.append("Add more H2 sections to improve structure")
            if d.get('avg_paragraph_length', 0) > 200:
                recs.append("Break up long paragraphs for better readability")
        
        if scores['internal_linking'] < 60:
            d = details['internal_linking']
            if d.get('internal_count', 0) < 3:
                recs.append("Add 3-8 internal links to related content")
            if d.get('anchor_diversity', 0) < 50:
                recs.append("Diversify anchor text for internal links")
        
        if scores['originality'] < 60:
            recs.append("Reduce boilerplate phrases, add more unique insights and specific examples")
        
        return recs[:8]  # Limit to top 8

    def _generate_summary(self, ratings: List[Dict]) -> Dict:
        """Generate summary statistics"""
        if not ratings:
            return {}
        
        total = len(ratings)
        by_rating = defaultdict(int)
        avg_scores = defaultdict(list)
        
        for r in ratings:
            by_rating[r['rating']] += 1
            for dim, score in r['dimension_scores'].items():
                avg_scores[dim].append(score)
        
        summary = {
            'total_rated': total,
            'rating_distribution': dict(by_rating),
            'average_scores': {
                dim: round(sum(scores) / len(scores), 1)
                for dim, scores in avg_scores.items()
            },
            'overall_average': round(sum(r['overall_score'] for r in ratings) / total, 1),
            'by_source': defaultdict(lambda: {'count': 0, 'avg_score': 0})
        }
        
        # By source
        source_scores = defaultdict(list)
        for r in ratings:
            source_scores[r['source']].append(r['overall_score'])
        
        summary['by_source'] = {
            src: {'count': len(scores), 'avg_score': round(sum(scores)/len(scores), 1)}
            for src, scores in source_scores.items()
        }
        
        # Top and bottom
        sorted_ratings = sorted(ratings, key=lambda x: x['overall_score'], reverse=True)
        summary['top_5'] = [
            {'id': r['content_id'], 'title': r['title'], 'score': r['overall_score'], 'rating': r['rating']}
            for r in sorted_ratings[:5]
        ]
        summary['bottom_5'] = [
            {'id': r['content_id'], 'title': r['title'], 'score': r['overall_score'], 'rating': r['rating']}
            for r in sorted_ratings[-5:]
        ]
        
        return summary

    def _save_outputs(self, ratings: List[Dict], summary: Dict) -> List[str]:
        """Save rating outputs"""
        files_created = []
        
        # JSON output
        json_file = self.save_json({
            'rated_at': datetime.now().isoformat(),
            'total_rated': len(ratings),
            'summary': summary,
            'ratings': ratings
        }, "research/content-ratings.json")
        files_created.append(json_file)
        
        # Markdown report
        report = self._generate_report(ratings, summary)
        md_file = self.save_output(report, "research/content-quality-report.md")
        files_created.append(md_file)
        
        # Priority improvements
        needs_work = [r for r in ratings if r['rating'] in ['needs_improvement', 'poor']]
        if needs_work:
            improvements = self.save_json({
                'generated_at': datetime.now().isoformat(),
                'count': len(needs_work),
                'items': [
                    {
                        'content_id': r['content_id'],
                        'title': r['title'],
                        'score': r['overall_score'],
                        'priority': 'high' if r['rating'] == 'poor' else 'medium',
                        'recommendations': r['recommendations']
                    }
                    for r in sorted(needs_work, key=lambda x: x['overall_score'])
                ]
            }, "research/content-improvement-priorities.json")
            files_created.append(improvements)
        
        return files_created

    def _generate_report(self, ratings: List[Dict], summary: Dict) -> str:
        """Generate markdown report"""
        report = f"""# GoRentals Content Quality Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Content Rated:** {summary.get('total_rated', 0)}
**Overall Average Score:** {summary.get('overall_average', 0)}/100

---

## Rating Distribution

| Rating | Count | Percentage |
|--------|-------|------------|
| Excellent (≥85) | {summary.get('rating_distribution', {}).get('excellent', 0)} | {summary.get('rating_distribution', {}).get('excellent', 0)/max(1, summary.get('total_rated', 1))*100:.1f}% |
| Good (70-84) | {summary.get('rating_distribution', {}).get('good', 0)} | {summary.get('rating_distribution', {}).get('good', 0)/max(1, summary.get('total_rated', 1))*100:.1f}% |
| Needs Improvement (50-69) | {summary.get('rating_distribution', {}).get('needs_improvement', 0)} | {summary.get('rating_distribution', {}).get('needs_improvement', 0)/max(1, summary.get('total_rated', 1))*100:.1f}% |
| Poor (<50) | {summary.get('rating_distribution', {}).get('poor', 0)} | {summary.get('rating_distribution', {}).get('poor', 0)/max(1, summary.get('total_rated', 1))*100:.1f}% |

---

## Average Scores by Dimension

| Dimension | Average Score | Weight |
|-----------|---------------|--------|
| Readability | {summary.get('average_scores', {}).get('readability', 0)} | 20% |
| Keyword Optimization | {summary.get('average_scores', {}).get('keyword_optimization', 0)} | 20% |
| Search Intent Match | {summary.get('average_scores', {}).get('search_intent_match', 0)} | 15% |
| Content Depth | {summary.get('average_scores', {}).get('content_depth', 0)} | 15% |
| EEAT Signals | {summary.get('average_scores', {}).get('eeat_signals', 0)} | 10% |
| Structure & Formatting | {summary.get('average_scores', {}).get('structure_formatting', 0)} | 10% |
| Internal Linking | {summary.get('average_scores', {}).get('internal_linking', 0)} | 5% |
| Originality | {summary.get('average_scores', {}).get('originality', 0)} | 5% |

---

## Top 5 Performing Content

| Content | Score | Rating |
|---------|-------|--------|
"""
        for item in summary.get('top_5', []):
            report += f"| {item['title'][:60]} | {item['score']} | {item['rating']} |\n"
        
        report += "\n## Bottom 5 Content (Needs Attention)\n\n"
        report += "| Content | Score | Rating | Priority |\n|---------|-------|--------|----------|\n"
        for item in summary.get('bottom_5', []):
            priority = 'HIGH' if item['rating'] == 'poor' else 'MEDIUM'
            report += f"| {item['title'][:60]} | {item['score']} | {item['rating']} | {priority} |\n"
        
        report += "\n## By Source\n\n"
        for src, data in summary.get('by_source', {}).items():
            report += f"- **{src}**: {data['count']} items, avg score {data['avg_score']}\n"
        
        # Detailed ratings
        report += "\n---\n\n## Detailed Ratings\n\n"
        for r in sorted(ratings, key=lambda x: x['overall_score'], reverse=True):
            report += f"""### {r['title']} ({r['content_id']})
- **Score:** {r['overall_score']}/100 ({r['rating'].replace('_', ' ').title()})
- **Target Keyword:** {r['target_keyword'] or 'Not specified'}
- **Type:** {r['content_type']}
- **Word Count:** {r['word_count']}
- **Dimensions:**
"""
            for dim, score in r['dimension_scores'].items():
                report += f"  - {dim.replace('_', ' ').title()}: {score}/100\n"
            
            if r['recommendations']:
                report += "- **Recommendations:**\n"
                for rec in r['recommendations']:
                    report += f"  - {rec}\n"
            
            report += "\n"
        
        report += f"""
---

*Report generated by GoRentals Content Rating Agent*
"""
        return report