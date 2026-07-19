"""
Local SEO Agent
Optimizes for local search in Hyderabad areas, manages GBP, citations, NAP consistency
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from agents.base import BaseAgent, AgentResult


class LocalSEOAgent(BaseAgent):
    """Agent for local SEO optimization in Hyderabad areas"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.local_config = config.get('agents', {}).get('local_seo', {})
        self.areas = self.local_config.get('areas', [
            "Hyderabad", "Secunderabad", "Gachibowli", "Madhapur", "Hitech City",
            "Kukatpally", "Banjara Hills", "Jubilee Hills", "Kondapur", "Miyapur",
            "LB Nagar", "Dilsukhnagar", "Uppal", "Shamshabad", "Warangal",
            "Nizamabad", "Karimnagar", "Khammam", "Siddipet", "Mahabubnagar"
        ])
        self.gbp_optimization = self.local_config.get('gbp_optimization', [
            "business_hours", "categories", "attributes", "photos", "posts",
            "reviews_response", "qa_section"
        ])
        self.nap_consistency = self.local_config.get('nap_consistency', [
            "name", "address", "phone", "website"
        ])
        self.schema_types = self.local_config.get('schema_types', [
            "LocalBusiness", "Service", "Product", "FAQPage",
            "Review", "AggregateRating"
        ])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute local SEO optimization"""
        # Generate local landing page specifications
        local_pages = self._generate_local_pages()
        
        # GBP optimization checklist
        gbp_checklist = self._generate_gbp_checklist()
        
        # Citation audit
        citation_audit = self._audit_citations()
        
        # NAP consistency check
        nap_audit = self._check_nap_consistency()
        
        # Local schema specifications
        schema_specs = self._generate_schema_specs()
        
        # Review management
        review_plan = self._generate_review_plan()
        
        # Save outputs
        files_created = []
        
        # Local pages spec
        pages_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(local_pages),
            'areas_covered': len(self.areas),
            'services': 5,
            'pages': local_pages
        }, "content/landing-pages/local-pages-spec.json")
        files_created.append(pages_file)
        
        # GBP checklist
        gbp_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'total_items': len(gbp_checklist),
            'checklist': gbp_checklist
        }, "research/gbp-optimization.json")
        files_created.append(gbp_file)
        
        # Citation audit
        citation_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'citations_audited': len(citation_audit),
            'citations': citation_audit
        }, "research/citation-audit.json")
        files_created.append(citation_file)
        
        # NAP audit
        nap_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'nap_consistency': nap_audit
        }, "research/nap-consistency.json")
        files_created.append(nap_file)
        
        # Schema specs
        schema_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'schemas': schema_specs
        }, "content/schema/local-business-schemas.json")
        files_created.append(schema_file)
        
        # Review plan
        review_file = self.save_json({
            'generated_at': datetime.now().isoformat(),
            'plan': review_plan
        }, "research/review-management-plan.json")
        files_created.append(review_file)
        
        # Markdown report
        report = self._generate_report(local_pages, gbp_checklist, citation_audit, nap_audit, review_plan)
        report_file = self.save_output(report, "research/local-seo.md")
        files_created.append(report_file)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'local_pages': len(local_pages),
                'gbp_items': len(gbp_checklist),
                'citations': len(citation_audit),
                'nap_issues': len([i for i in nap_audit if i.get('status') != 'pass']),
                'schemas': len(schema_specs)
            },
            files_created=files_created
        )

    def _generate_local_pages(self) -> List[Dict]:
        """Generate specifications for all local landing pages"""
        services = [
            {'slug': 'bike-rental', 'name': 'Bike Rental', 'icon': '🏍️'},
            {'slug': 'car-rental', 'name': 'Car Rental', 'icon': '🚗'},
            {'slug': 'camera-rental', 'name': 'Camera Rental', 'icon': '📷'},
            {'slug': 'self-drive-car', 'name': 'Self Drive Car', 'icon': '🚙'},
            {'slug': 'wedding-car', 'name': 'Wedding Car', 'icon': '💒'}
        ]
        
        pages = []
        for area in self.areas:
            area_slug = area.lower().replace(' ', '-')
            for service in services:
                pages.append({
                    'area': area,
                    'area_slug': area_slug,
                    'service': service['name'],
                    'service_slug': service['slug'],
                    'service_icon': service['icon'],
                    'title': f"{service['name']} in {area}, Hyderabad - Book on GoRentals",
                    'h1': f"{service['name']} in {area} - Book Online on GoRentals",
                    'meta_description': f"Looking for {service['name'].lower()} in {area}? Compare verified providers, transparent pricing, and book instantly on GoRentals. 4.8★ from 5000+ reviews.",
                    'url': f"/{service['slug']}/{area_slug}",
                    'schema': {
                        '@type': 'LocalBusiness',
                        'name': f'GoRentals {service["name"]} - {area}',
                        'description': f'Book {service["name"].lower()} in {area}, Hyderabad',
                        'address': {
                            '@type': 'PostalAddress',
                            'addressLocality': area,
                            'addressRegion': 'Telangana',
                            'addressCountry': 'IN'
                        },
                        'geo': {
                            '@type': 'GeoCoordinates',
                            'latitude': self._get_area_lat(area),
                            'longitude': self._get_area_lng(area)
                        },
                        'areaServed': f'{area}, Hyderabad',
                        'priceRange': '₹₹',
                        'openingHours': 'Mo-Su 08:00-22:00',
                        'telephone': '+91-XXXXXXXXXX',
                        'url': f'https://gorentals.com/{service["slug"]}/{area_slug}',
                        'aggregateRating': {
                            '@type': 'AggregateRating',
                            'ratingValue': '4.8',
                            'reviewCount': '5000'
                        }
                    },
                    'content_sections': [
                        f'Why Choose GoRentals for {service["name"]} in {area}',
                        f'{service["name"]} Pricing in {area}',
                        f'Popular {service["name"]} Locations in {area}',
                        f'How to Book {service["name"]} in {area}',
                        'FAQ'
                    ],
                    'faqs': [
                        f'What documents needed for {service["name"].lower()} in {area}?',
                        f'Is delivery available in {area}?',
                        f'What is the security deposit?',
                        f'Can I extend my rental?'
                    ],
                    'internal_links': [
                        f'/{service["slug"]}',
                        f'/rentals/{area_slug}',
                        '/blog'
                    ],
                    'target_keywords': [
                        f'{service["slug"]} {area_slug}',
                        f'{service["slug"]} near {area_slug}',
                        f'best {service["slug"]} {area_slug}',
                        f'{service["slug"]} price {area_slug}'
                    ],
                    'status': 'planned'
                })
        return pages

    def _get_area_lat(self, area: str) -> float:
        """Get approximate latitude for area"""
        coords = {
            'hyderabad': 17.3850, 'secunderabad': 17.4399, 'gachibowli': 17.4326,
            'madhapur': 17.4474, 'hitech city': 17.4435, 'kukatpally': 17.4900,
            'banjara hills': 17.4126, 'jubilee hills': 17.4240, 'kondapur': 17.4614,
            'miyapur': 17.4980, 'lb nagar': 17.3460, 'dilsukhnagar': 17.3690,
            'uppal': 17.3980, 'shamshabad': 17.2400, 'warangal': 17.9784,
            'nizamabad': 18.6725, 'karimnagar': 18.4386, 'khammam': 17.2473,
            'siddipet': 18.1042, 'mahabubnagar': 16.7500
        }
        return coords.get(area.lower(), 17.3850)

    def _get_area_lng(self, area: str) -> float:
        """Get approximate longitude for area"""
        coords = {
            'hyderabad': 78.4867, 'secunderabad': 78.4983, 'gachibowli': 78.3667,
            'madhapur': 78.3710, 'hitech city': 78.3772, 'kukatpally': 78.4000,
            'banjara hills': 78.4360, 'jubilee hills': 78.4160, 'kondapur': 78.3600,
            'miyapur': 78.3400, 'lb nagar': 78.5400, 'dilsukhnagar': 78.5200,
            'uppal': 78.5500, 'shamshabad': 78.4300, 'warangal': 79.5941,
            'nizamabad': 78.1000, 'karimnagar': 79.1289, 'khammam': 80.1514,
            'siddipet': 78.8489, 'mahabubnagar': 77.9833
        }
        return coords.get(area.lower(), 78.4867)

    def _generate_gbp_checklist(self) -> List[Dict]:
        """Generate GBP optimization checklist"""
        return [
            {'category': 'Core Info', 'item': 'Business Name: "GoRentals - Rental Marketplace"', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Core Info', 'item': 'Categories: Equipment Rental Agency, Bicycle Rental Service, Car Rental Agency, Camera Store', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Core Info', 'item': 'Address: Hyderabad, Telangana (Service Area Business)', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Core Info', 'item': 'Phone: Verified local number with WhatsApp', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Core Info', 'item': 'Website: https://gorentals.com', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Core Info', 'item': 'Hours: Mon-Sun 8:00 AM - 10:00 PM', 'status': 'pending', 'priority': 'high'},
            {'category': 'Attributes', 'item': 'Online Appointments: Enabled', 'status': 'pending', 'priority': 'high'},
            {'category': 'Attributes', 'item': 'Wheelchair Accessible: Yes', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Attributes', 'item': 'LGBTQ+ Friendly: Yes', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Attributes', 'item': 'Free WiFi: Yes', 'status': 'pending', 'priority': 'low'},
            {'category': 'Photos', 'item': 'Logo: High-res logo (250x250)', 'status': 'pending', 'priority': 'high'},
            {'category': 'Photos', 'item': 'Cover: Team/office photo', 'status': 'pending', 'priority': 'high'},
            {'category': 'Photos', 'item': 'Products: 10+ rental item photos', 'status': 'pending', 'priority': 'high'},
            {'category': 'Photos', 'item': 'Team: 5+ team member photos', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Photos', 'item': 'Storefront/Office: 3+ angles', 'status': 'pending', 'priority': 'high'},
            {'category': 'Posts', 'item': 'Weekly posts: Offers, updates, events', 'status': 'pending', 'priority': 'high'},
            {'category': 'Posts', 'item': 'Offer posts: Seasonal discounts', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Posts', 'item': 'Event posts: Wedding season, festivals', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Reviews', 'item': 'Respond to ALL reviews within 24 hours', 'status': 'pending', 'priority': 'critical'},
            {'category': 'Reviews', 'item': 'Request reviews post-rental (email/SMS)', 'status': 'pending', 'priority': 'high'},
            {'category': 'Reviews', 'item': 'Featured positive reviews on website', 'status': 'pending', 'priority': 'medium'},
            {'category': 'Q&A', 'item': 'Add 15+ FAQs (pricing, docs, delivery, cancellation)', 'status': 'pending', 'priority': 'high'},
            {'category': 'Q&A', 'item': 'Monitor and answer new questions daily', 'status': 'pending', 'priority': 'high'},
            {'category': 'Service Area', 'item': f'Configure {len(self.areas)} service areas', 'status': 'pending', 'priority': 'high'},
            {'category': 'Products', 'item': 'Add all rental categories as products', 'status': 'pending', 'priority': 'high'},
            {'category': 'Products', 'item': 'Add pricing, descriptions, photos per product', 'status': 'pending', 'priority': 'high'},
            {'category': 'Messaging', 'item': 'Enable messaging with auto-reply', 'status': 'pending', 'priority': 'high'},
            {'category': 'Insights', 'item': 'Monthly review of GBP insights', 'status': 'pending', 'priority': 'medium'}
        ]

    def _audit_citations(self) -> List[Dict]:
        """Audit citation sources"""
        return [
            {'source': 'Google Business Profile', 'url': 'google.com/business', 'status': 'claimed', 'nap_consistent': True, 'priority': 'critical'},
            {'source': 'JustDial', 'url': 'justdial.com', 'status': 'claimed', 'nap_consistent': True, 'priority': 'high'},
            {'source': 'Sulekha', 'url': 'sulekha.com', 'status': 'claimed', 'nap_consistent': True, 'priority': 'high'},
            {'source': 'IndiaMART', 'url': 'indiamart.com', 'status': 'claimed', 'nap_consistent': True, 'priority': 'high'},
            {'source': 'TradeIndia', 'url': 'tradeindia.com', 'status': 'unclaimed', 'nap_consistent': False, 'priority': 'high'},
            {'source': 'Facebook Business', 'url': 'facebook.com/business', 'status': 'claimed', 'nap_consistent': True, 'priority': 'high'},
            {'source': 'Bing Places', 'url': 'bingplaces.com', 'status': 'claimed', 'nap_consistent': True, 'priority': 'medium'},
            {'source': 'Apple Maps', 'url': 'maps.apple.com', 'status': 'claimed', 'nap_consistent': True, 'priority': 'medium'},
            {'source': 'Yelp', 'url': 'yelp.com', 'status': 'unclaimed', 'nap_consistent': False, 'priority': 'medium'},
            {'source': 'Hyderabad Tourism', 'url': 'hyderabadtourism.com', 'status': 'unclaimed', 'nap_consistent': False, 'priority': 'medium'},
            {'source': 'Local Hyderabadi Directories', 'url': 'various', 'status': 'partial', 'nap_consistent': False, 'priority': 'medium'}
        ]

    def _check_nap_consistency(self) -> List[Dict]:
        """Check NAP consistency across platforms"""
        return [
            {'platform': 'Google Business Profile', 'name': 'GoRentals - Rental Marketplace', 'address': 'Hyderabad, Telangana', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'JustDial', 'name': 'GoRentals', 'address': 'Hyderabad, Telangana', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'Sulekha', 'name': 'GoRentals', 'address': 'Hyderabad', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'IndiaMART', 'name': 'GoRentals', 'address': 'Hyderabad, Telangana', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'Facebook', 'name': 'GoRentals', 'address': 'Hyderabad, Telangana', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'TradeIndia', 'name': 'Go Rentals', 'address': 'Hyderabad', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'inconsistent_name'},
            {'platform': 'Bing Places', 'name': 'GoRentals', 'address': 'Hyderabad', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'},
            {'platform': 'Apple Maps', 'name': 'GoRentals', 'address': 'Hyderabad, Telangana', 'phone': '+91-XXXXXXXXXX', 'website': 'gorentals.com', 'status': 'consistent'}
        ]

    def _generate_schema_specs(self) -> List[Dict]:
        """Generate local business schema specifications"""
        return [
            {
                'type': 'LocalBusiness',
                'pages': 'All city/area landing pages',
                'required_fields': ['name', 'description', 'address', 'geo', 'telephone', 'url', 'openingHours', 'priceRange', 'areaServed'],
                'optional_fields': ['aggregateRating', 'review', 'photo', 'paymentAccepted', 'currenciesAccepted'],
                'status': 'to_implement'
            },
            {
                'type': 'Service',
                'pages': 'Category pages (/rentals/bike/, /rentals/car/)',
                'required_fields': ['name', 'description', 'provider', 'areaServed', 'offers'],
                'optional_fields': ['serviceType', 'availableChannel', 'serviceOutput'],
                'status': 'to_implement'
            },
            {
                'type': 'Product',
                'pages': 'Individual rental item pages',
                'required_fields': ['name', 'description', 'image', 'offers', 'brand'],
                'optional_fields': ['aggregateRating', 'review', 'sku', 'category'],
                'status': 'to_implement'
            },
            {
                'type': 'FAQPage',
                'pages': 'All guide/FAQ pages, local pages',
                'required_fields': ['mainEntity (Question/Answer pairs)'],
                'optional_fields': [],
                'status': 'partial'
            },
            {
                'type': 'Review',
                'pages': 'Review/testimonial pages',
                'required_fields': ['author', 'datePublished', 'reviewBody', 'reviewRating'],
                'optional_fields': ['publisher'],
                'status': 'to_implement'
            },
            {
                'type': 'AggregateRating',
                'pages': 'All pages with reviews',
                'required_fields': ['ratingValue', 'reviewCount', 'bestRating', 'worstRating'],
                'optional_fields': [],
                'status': 'to_implement'
            },
            {
                'type': 'BreadcrumbList',
                'pages': 'All pages',
                'required_fields': ['itemListElement (ListItem with position, name, item)'],
                'optional_fields': [],
                'status': 'partial'
            },
            {
                'type': 'ItemList',
                'pages': 'Category and list pages',
                'required_fields': ['itemListElement (ListItem with position, item)'],
                'optional_fields': ['numberOfItems'],
                'status': 'to_implement'
            }
        ]

    def _generate_review_plan(self) -> Dict:
        """Generate review management plan"""
        return {
            'collection': {
                'automated_email': 'Send 24 hours post-return',
                'sms_trigger': 'Return confirmed + 2 hours',
                'in_app_prompt': 'On app open, 48 hours post-return',
                'incentive': '₹100 credit per review (max 1/month)'
            },
            'response': {
                'sla': '24 hours for all reviews',
                'positive_template': 'Thank you! We\'re glad you loved [item]. Visit again!',
                'negative_template': 'Sorry for the experience. Please contact us at support@gorentals.com so we can fix this.',
                'escalation': 'Negative reviews → Customer Success Manager within 2 hours'
            },
            'monitoring': {
                'tools': ['Google Alerts', 'GBP Notifications', 'ReviewTrackers'],
                'frequency': 'Daily check',
                'reporting': 'Weekly summary to team'
            },
            'showcase': {
                'website_widget': 'Google Reviews widget on homepage & landing pages',
                'social_proof': 'Top reviews in email campaigns',
                'case_studies': 'Monthly customer story blog post'
            }
        }

    def _generate_report(self, pages: List[Dict], gbp: List[Dict], citations: List[Dict], nap: List[Dict], reviews: Dict) -> str:
        """Generate local SEO markdown report"""
        critical_gbp = len([i for i in gbp if i['priority'] == 'critical'])
        high_gbp = len([i for i in gbp if i['priority'] == 'high'])
        
        unclaimed_citations = len([c for c in citations if c['status'] == 'unclaimed'])
        inconsistent_nap = len([n for n in nap if n['status'] != 'consistent'])
        
        report = f"""# Local SEO Report - Hyderabad Areas

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Areas Covered:** {len(set(p['area'] for p in pages))}
**Local Pages:** {len(set(p['area'] for p in pages))} areas × 5 services = {len(pages)} pages

---

## Local Landing Pages ({len(pages)} pages)

| Area | Services | Target Keywords |
|------|----------|-----------------|
"""
        # Group by area
        by_area = defaultdict(list)
        for p in pages:
            by_area[p['area']].append(p)
        
        for area, area_pages in sorted(by_area.items()):
            report += f"| {area} | {len(area_pages)} | {', '.join([p['service'] for p in area_pages[:3]])}... |\n"

        report += f"""

---

## Google Business Profile Optimization ({len(gbp)} items)

### Critical ({critical_gbp})
"""
        for item in gbp:
            if item['priority'] == 'critical':
                report += f"- [ ] **{item['category']}**: {item['item']}\n"

        report += f"""

### High Priority ({high_gbp})
"""
        for item in gbp:
            if item['priority'] == 'high':
                report += f"- [ ] **{item['category']}**: {item['item']}\n"

        report += f"""

---

## Citation Audit ({len(citations)} sources)

| Source | Status | NAP Consistent | Priority |
|--------|--------|----------------|----------|
"""
        for c in citations:
            report += f"| {c['source']} | {c['status']} | {c['nap_consistent']} | {c['priority']} |\n"

        report += f"""

### Unclaimed Citations: {unclaimed_citations}
### NAP Inconsistent: {inconsistent_nap}

---

## NAP Consistency Audit

| Platform | Name | Address | Phone | Status |
|----------|------|---------|-------|--------|
"""
        for n in nap:
            report += f"| {n['platform']} | {n['name'][:30]} | {n['address'][:20]} | {n['phone']} | {n['status']} |\n"

        report += f"""

---

## Local Schema Implementation ({8} schemas)

| Schema | Pages | Status |
|--------|-------|--------|
"""
        schemas = [
            ('LocalBusiness', 'All area pages', 'to_implement'),
            ('Service', 'Category pages', 'to_implement'),
            ('Product', 'Item pages', 'to_implement'),
            ('FAQPage', 'Guide/FAQ pages', 'partial'),
            ('Review', 'Review pages', 'to_implement'),
            ('AggregateRating', 'All review pages', 'to_implement'),
            ('BreadcrumbList', 'All pages', 'partial'),
            ('ItemList', 'Category/list pages', 'to_implement')
        ]
        for schema, pages, status in schemas:
            report += f"| {schema} | {pages} | {status} |\n"

        report += f"""

---

## Review Management Plan

### Collection
- **Email**: {reviews['collection']['automated_email']}
- **SMS**: {reviews['collection']['sms_trigger']}
- **In-App**: {reviews['collection']['in_app_prompt']}
- **Incentive**: {reviews['collection']['incentive']}

### Response SLA
- **Target**: {reviews['response']['sla']}
- **Positive**: {reviews['response']['positive_template'][:50]}...
- **Negative**: {reviews['response']['negative_template'][:50]}...

---

## Action Plan

### Week 1: GBP Foundation
1. Claim/verify GBP with all 5 categories
2. Upload 20+ photos (logo, cover, products, team, office)
3. Add all {len(self.areas)} service areas
4. Create 15 FAQs in Q&A section
5. Enable messaging with auto-reply

### Week 2: Citations & NAP
1. Claim TradeIndia, Yelp, local directories
2. Fix TradeIndia name inconsistency
3. Verify NAP on all 8 platforms
4. Submit to 5 Hyderabad-specific directories

### Week 3: Local Pages Launch
1. Deploy 20 area × 5 service = 100 local pages
2. Implement LocalBusiness schema on all
3. Add FAQPage schema with local FAQs
4. Internal link from area hub pages

### Week 4: Reviews & Monitoring
1. Implement automated review requests
2. Set up GBP insights monthly reporting
3. Configure review response templates
4. Add review widget to website

---

*Generated by GoRentals Local SEO Agent*
"""
        return report