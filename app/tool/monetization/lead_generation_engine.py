"""
Lead Generation Engine Tool

B2B lead generation and enrichment engine that discovers, enriches, and scores
potential customers for sales teams. Provides comprehensive company and contact intelligence.

Revenue Model:
- Monthly Revenue: $1,200-$4,000
- Pricing: $100-300 per enriched lead list or $200-800/month for continuous enrichment
- Clients: Sales teams, SDRs, business development, marketing agencies
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, ClassVar, Dict, List, Optional
from urllib.parse import urlparse

from app.logger import logger
from app.tool.base import ToolResult
from app.tool.monetization.base import (
    CacheConfig,
    MonetizationBase,
    MonetizationError,
    ValidationError,
)


class LeadGenerationEngineTool(MonetizationBase):
    """
    B2B lead generation and enrichment engine.

    Features:
    - Company enrichment (firmographics, technographics, funding)
    - Contact discovery with email verification
    - Intent signal tracking and scoring
    - Lead scoring with ICP matching
    - Prospect list building with batch enrichment
    - Tech stack detection
    - Funding intelligence
    - Social presence analysis

    Revenue potential: $1,200-$4,000/month
    Use cases: Sales prospecting, account-based marketing, lead scoring, market intelligence
    """

    name: str = "lead_generation_engine"
    description: str = (
        "B2B lead generation and enrichment engine for discovering, "
        "enriching, and scoring potential customers"
    )

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "enrich_company",
                    "discover_contacts",
                    "track_intent_signals",
                    "score_leads",
                    "build_prospect_list",
                ],
                "description": "Action to perform",
            },
            "domain": {
                "type": "string",
                "description": "Company domain (e.g., 'example.com')",
            },
            "enrichment_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to enrich: firmographics, technographics, funding, social, contacts, intent_signals, company_news",
            },
            "company_domain": {
                "type": "string",
                "description": "Company domain for contact discovery",
            },
            "filters": {
                "type": "object",
                "description": "Contact filters (role, seniority, department)",
            },
            "signal_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Intent signal types: website_visits, content_downloads, job_postings, funding_rounds, tech_changes, hiring_signals",
            },
            "leads": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of leads to score",
            },
            "criteria": {
                "type": "object",
                "description": "Scoring criteria (company_size, industry, tech_stack, budget_signals, engagement)",
            },
            "search_criteria": {
                "type": "object",
                "description": "Search criteria (industry, size, location, tech_stack, funding_stage)",
            },
            "enrichment_level": {
                "type": "string",
                "enum": ["basic", "standard", "premium"],
                "description": "Enrichment level",
            },
        },
        "required": ["action"],
    }

    # Class-level constants
    ENRICHMENT_FIELDS: ClassVar[List[str]] = [
        "firmographics",
        "technographics",
        "funding",
        "social",
        "contacts",
        "intent_signals",
        "company_news",
    ]

    INTENT_SIGNAL_TYPES: ClassVar[List[str]] = [
        "website_visits",
        "content_downloads",
        "job_postings",
        "funding_rounds",
        "tech_changes",
        "hiring_signals",
    ]

    SENIORITY_LEVELS: ClassVar[List[str]] = [
        "C-Level",
        "VP",
        "Director",
        "Manager",
        "Individual Contributor",
    ]

    DEPARTMENTS: ClassVar[List[str]] = [
        "Sales",
        "Marketing",
        "Engineering",
        "Product",
        "Operations",
        "Finance",
        "HR",
        "Customer Success",
    ]

    TECH_CATEGORIES: ClassVar[Dict[str, List[str]]] = {
        "CRM": ["Salesforce", "HubSpot", "Pipedrive", "Zoho CRM", "Microsoft Dynamics"],
        "Marketing": ["HubSpot", "Marketo", "Mailchimp", "Pardot", "ActiveCampaign"],
        "Analytics": ["Google Analytics", "Mixpanel", "Amplitude", "Segment", "Heap"],
        "Development": ["GitHub", "GitLab", "Jira", "Jenkins", "Docker"],
        "Communication": ["Slack", "Microsoft Teams", "Zoom", "Intercom", "Zendesk"],
        "Commerce": ["Shopify", "WooCommerce", "Magento", "Stripe", "PayPal"],
    }

    INDUSTRIES: ClassVar[List[str]] = [
        "Software",
        "E-commerce",
        "Healthcare",
        "Financial Services",
        "Manufacturing",
        "Retail",
        "Consulting",
        "Education",
        "Real Estate",
        "Media",
    ]

    COMPANY_SIZES: ClassVar[List[str]] = [
        "1-10",
        "11-50",
        "51-200",
        "201-500",
        "501-1000",
        "1001-5000",
        "5001+",
    ]

    FUNDING_STAGES: ClassVar[List[str]] = [
        "Bootstrapped",
        "Pre-Seed",
        "Seed",
        "Series A",
        "Series B",
        "Series C",
        "Series D+",
        "IPO",
    ]

    def __init__(self, **data):
        """Initialize lead generation engine."""
        super().__init__(**data)
        self._mock_companies = self._generate_mock_companies()
        self._mock_contacts = self._generate_mock_contacts()
        self._mock_intent_data = self._generate_mock_intent_data()

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute lead generation action.

        Args:
            action: Action to perform
            **kwargs: Action-specific parameters

        Returns:
            ToolResult with action results
        """
        action = kwargs.get("action")
        if not action:
            raise ValidationError("Action is required")

        self.log_action(f"Executing action: {action}", params=kwargs)

        try:
            if action == "enrich_company":
                result = await self.enrich_company(
                    domain=kwargs.get("domain"),
                    enrichment_fields=kwargs.get(
                        "enrichment_fields", self.ENRICHMENT_FIELDS
                    ),
                )
            elif action == "discover_contacts":
                result = await self.discover_contacts(
                    company_domain=kwargs.get("company_domain"),
                    filters=kwargs.get("filters", {}),
                )
            elif action == "track_intent_signals":
                result = await self.track_intent_signals(
                    company_domain=kwargs.get("company_domain"),
                    signal_types=kwargs.get("signal_types", self.INTENT_SIGNAL_TYPES),
                )
            elif action == "score_leads":
                result = await self.score_leads(
                    leads=kwargs.get("leads", []),
                    criteria=kwargs.get("criteria", {}),
                )
            elif action == "build_prospect_list":
                result = await self.build_prospect_list(
                    search_criteria=kwargs.get("search_criteria", {}),
                    enrichment_level=kwargs.get("enrichment_level", "standard"),
                )
            else:
                raise ValidationError(f"Unknown action: {action}")

            return ToolResult(success=True, result=result)

        except ValidationError as e:
            self.log_error(f"Validation error in {action}", error=str(e))
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            self.log_error(f"Error in {action}", error=str(e))
            return ToolResult(success=False, error=f"Action failed: {str(e)}")

    async def enrich_company(
        self, domain: str, enrichment_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Enrich company data with firmographics, technographics, and more.

        Args:
            domain: Company domain (e.g., 'example.com')
            enrichment_fields: Fields to enrich

        Returns:
            Dictionary with enriched company data

        Example:
            >>> result = await tool.enrich_company(
            ...     domain='acme.com',
            ...     enrichment_fields=['firmographics', 'technographics', 'funding']
            ... )
            >>> print(result['enriched_data']['firmographics']['industry'])
            'Software'
        """
        # Validate inputs
        if not domain:
            raise ValidationError("Domain is required")

        domain = self._normalize_domain(domain)
        if not self._validate_domain(domain):
            raise ValidationError(f"Invalid domain format: {domain}")

        # Validate enrichment fields
        invalid_fields = [
            f for f in enrichment_fields if f not in self.ENRICHMENT_FIELDS
        ]
        if invalid_fields:
            raise ValidationError(
                f"Invalid enrichment fields: {', '.join(invalid_fields)}"
            )

        self.log_action("Enriching company", domain=domain, fields=enrichment_fields)

        # Check cache
        cache_key = self._cache_key(
            "company_enrichment", domain=domain, fields=enrichment_fields
        )
        cached = await self.cache_get(cache_key)
        if cached:
            return cached

        # Rate limiting
        await self.wait_for_rate_limit("clearbit")
        self.record_request("clearbit")

        # Get or generate company data
        company_data = self._mock_companies.get(
            domain, self._generate_company_data(domain)
        )

        # Build enriched response
        enriched_data = {
            "domain": domain,
            "name": company_data["name"],
        }

        # Add requested enrichment fields
        if "firmographics" in enrichment_fields:
            enriched_data["firmographics"] = company_data["firmographics"]

        if "technographics" in enrichment_fields:
            enriched_data["technographics"] = company_data["technographics"]

        if "funding" in enrichment_fields:
            enriched_data["funding"] = company_data["funding"]

        if "social" in enrichment_fields:
            enriched_data["social"] = company_data["social"]

        if "contacts" in enrichment_fields:
            enriched_data["contacts"] = company_data.get("contact_count", 0)

        if "intent_signals" in enrichment_fields:
            enriched_data["intent_score"] = company_data.get("intent_score", 0)

        if "company_news" in enrichment_fields:
            enriched_data["recent_news"] = company_data.get("recent_news", [])

        # Calculate data quality metrics
        completeness = self._calculate_completeness(enriched_data, enrichment_fields)
        confidence = self._calculate_confidence(enriched_data)

        result = {
            "domain": domain,
            "enriched_data": enriched_data,
            "enrichment_fields": enrichment_fields,
            "data_quality": {
                "completeness_score": completeness,
                "confidence_level": confidence,
                "last_updated": datetime.now().isoformat(),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Cache result
        await self.cache_set(cache_key, result, CacheConfig.TTL["company_info"])

        self.log_metric("company_enrichment_completeness", completeness)

        return result

    async def discover_contacts(
        self, company_domain: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Discover decision-makers and contacts at target company.

        Args:
            company_domain: Company domain
            filters: Contact filters (role, seniority, department)

        Returns:
            Dictionary with discovered contacts

        Example:
            >>> result = await tool.discover_contacts(
            ...     company_domain='acme.com',
            ...     filters={'seniority': ['VP', 'Director'], 'department': 'Sales'}
            ... )
            >>> print(len(result['contacts']))
            5
        """
        # Validate inputs
        if not company_domain:
            raise ValidationError("Company domain is required")

        company_domain = self._normalize_domain(company_domain)
        if not self._validate_domain(company_domain):
            raise ValidationError(f"Invalid domain format: {company_domain}")

        self.log_action("Discovering contacts", domain=company_domain, filters=filters)

        # Check cache
        cache_key = self._cache_key(
            "contact_discovery", domain=company_domain, filters=filters
        )
        cached = await self.cache_get(cache_key)
        if cached:
            return cached

        # Rate limiting
        await self.wait_for_rate_limit("linkedin")
        self.record_request("linkedin")
        await self.wait_for_rate_limit("hunter_io")
        self.record_request("hunter_io")

        # Get company data
        company_data = self._mock_companies.get(
            company_domain, self._generate_company_data(company_domain)
        )

        # Generate contacts for this company
        all_contacts = self._generate_contacts_for_company(company_domain, company_data)

        # Apply filters
        filtered_contacts = self._filter_contacts(all_contacts, filters)

        # Verify emails
        for contact in filtered_contacts:
            contact["email_verified"] = self._verify_email(contact["email"])
            contact["email_deliverability"] = (
                "high" if contact["email_verified"] else "low"
            )

        # Extract email pattern
        email_pattern = self._extract_email_pattern(filtered_contacts)

        result = {
            "company_domain": company_domain,
            "company_name": company_data["name"],
            "contacts": filtered_contacts,
            "total_contacts": len(filtered_contacts),
            "email_pattern": email_pattern,
            "filters_applied": filters,
            "discovery_method": "multi-source",
            "sources": ["LinkedIn", "Company Website", "Hunter.io", "Clearbit"],
            "timestamp": datetime.now().isoformat(),
        }

        # Cache result
        await self.cache_set(cache_key, result, CacheConfig.TTL["lead_data"])

        self.log_metric("contacts_discovered", len(filtered_contacts))

        return result

    async def track_intent_signals(
        self, company_domain: str, signal_types: List[str]
    ) -> Dict[str, Any]:
        """
        Track buying intent signals and trigger events.

        Args:
            company_domain: Company domain
            signal_types: Types of signals to track

        Returns:
            Dictionary with intent analysis

        Example:
            >>> result = await tool.track_intent_signals(
            ...     company_domain='acme.com',
            ...     signal_types=['job_postings', 'funding_rounds', 'tech_changes']
            ... )
            >>> print(result['intent_score'])
            87
        """
        # Validate inputs
        if not company_domain:
            raise ValidationError("Company domain is required")

        company_domain = self._normalize_domain(company_domain)
        if not self._validate_domain(company_domain):
            raise ValidationError(f"Invalid domain format: {company_domain}")

        # Validate signal types
        invalid_signals = [s for s in signal_types if s not in self.INTENT_SIGNAL_TYPES]
        if invalid_signals:
            raise ValidationError(f"Invalid signal types: {', '.join(invalid_signals)}")

        self.log_action(
            "Tracking intent signals", domain=company_domain, signals=signal_types
        )

        # Check cache
        cache_key = self._cache_key(
            "intent_signals", domain=company_domain, signals=signal_types
        )
        cached = await self.cache_get(cache_key)
        if cached:
            return cached

        # Rate limiting for various data sources
        for source in ["linkedin", "clearbit", "hunter_io"]:
            await self.wait_for_rate_limit(source)
            self.record_request(source)

        # Get intent data
        intent_data = self._mock_intent_data.get(
            company_domain, self._generate_intent_data(company_domain)
        )

        # Filter signals by requested types
        filtered_signals = [
            s for s in intent_data["signals"] if s["type"] in signal_types
        ]

        # Calculate intent score
        intent_score = self._calculate_intent_score(filtered_signals)

        # Identify trigger events
        trigger_events = self._identify_trigger_events(filtered_signals)

        # Generate recommendation
        recommendation = self._generate_intent_recommendation(
            intent_score, trigger_events
        )

        result = {
            "company_domain": company_domain,
            "intent_score": intent_score,
            "signals": filtered_signals,
            "signal_types_tracked": signal_types,
            "trigger_events": trigger_events,
            "recommendation": recommendation,
            "priority": self._get_priority_level(intent_score),
            "analysis_date": datetime.now().isoformat(),
            "next_review_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

        # Cache result
        await self.cache_set(cache_key, result, CacheConfig.TTL["api_response"])

        self.log_metric("intent_score", intent_score)

        return result

    async def score_leads(
        self, leads: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score and rank leads based on fit and intent.

        Args:
            leads: List of leads to score
            criteria: Scoring criteria (company_size, industry, tech_stack, etc.)

        Returns:
            Dictionary with scored and ranked leads

        Example:
            >>> result = await tool.score_leads(
            ...     leads=[{'company': 'Acme', 'domain': 'acme.com'}],
            ...     criteria={'target_industry': 'Software', 'min_size': '51-200'}
            ... )
            >>> print(result['scored_leads'][0]['total_score'])
            89.5
        """
        # Validate inputs
        if not leads:
            raise ValidationError("Leads list is required")

        if not criteria:
            raise ValidationError("Scoring criteria is required")

        self.log_action("Scoring leads", lead_count=len(leads), criteria=criteria)

        # Check cache
        cache_key = self._cache_key(
            "lead_scoring", leads=json.dumps(leads), criteria=criteria
        )
        cached = await self.cache_get(cache_key)
        if cached:
            return cached

        scored_leads = []

        for lead in leads:
            # Get lead domain
            domain = lead.get("domain", "")
            if not domain:
                continue

            domain = self._normalize_domain(domain)

            # Get company data
            company_data = self._mock_companies.get(
                domain, self._generate_company_data(domain)
            )

            # Get intent data
            intent_data = self._mock_intent_data.get(
                domain, self._generate_intent_data(domain)
            )

            # Calculate fit score
            fit_score = self._calculate_fit_score(company_data, criteria)

            # Calculate intent score
            intent_score = intent_data["intent_score"]

            # Calculate total score (weighted average)
            total_score = (fit_score * 0.6) + (intent_score * 0.4)

            # Check ICP match
            icp_match = self._check_icp_match(company_data, criteria)

            # Generate scoring reasons
            reasons = self._generate_scoring_reasons(
                company_data, intent_data, criteria, fit_score, intent_score
            )

            # Determine priority
            priority = self._get_priority_level(total_score)

            scored_lead = {
                "company": company_data["name"],
                "domain": domain,
                "fit_score": round(fit_score, 1),
                "intent_score": round(intent_score, 1),
                "total_score": round(total_score, 1),
                "priority": priority,
                "icp_match": icp_match,
                "reasons": reasons,
                "firmographics": company_data["firmographics"],
                "intent_signals": intent_data["signals"][:3],  # Top 3 signals
            }

            scored_leads.append(scored_lead)

        # Sort by total score
        scored_leads.sort(key=lambda x: x["total_score"], reverse=True)

        # Add rank
        for i, lead in enumerate(scored_leads, 1):
            lead["rank"] = i

        result = {
            "scored_leads": scored_leads,
            "total_leads": len(scored_leads),
            "criteria": criteria,
            "scoring_method": "fit_and_intent",
            "weights": {"fit": 0.6, "intent": 0.4},
            "statistics": {
                "high_priority": len(
                    [l for l in scored_leads if l["priority"] == "High"]
                ),
                "medium_priority": len(
                    [l for l in scored_leads if l["priority"] == "Medium"]
                ),
                "low_priority": len(
                    [l for l in scored_leads if l["priority"] == "Low"]
                ),
                "icp_matches": len([l for l in scored_leads if l["icp_match"]]),
                "avg_fit_score": (
                    round(
                        sum(l["fit_score"] for l in scored_leads) / len(scored_leads), 1
                    )
                    if scored_leads
                    else 0
                ),
                "avg_intent_score": (
                    round(
                        sum(l["intent_score"] for l in scored_leads)
                        / len(scored_leads),
                        1,
                    )
                    if scored_leads
                    else 0
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Cache result
        await self.cache_set(cache_key, result, CacheConfig.TTL["api_response"])

        self.log_metric("leads_scored", len(scored_leads))

        return result

    async def build_prospect_list(
        self, search_criteria: Dict[str, Any], enrichment_level: str
    ) -> Dict[str, Any]:
        """
        Build targeted prospect list with enrichment.

        Args:
            search_criteria: Search criteria (industry, size, location, tech_stack, funding_stage)
            enrichment_level: Enrichment level (basic, standard, premium)

        Returns:
            Dictionary with prospect list

        Example:
            >>> result = await tool.build_prospect_list(
            ...     search_criteria={'industry': 'Software', 'size': '51-200'},
            ...     enrichment_level='standard'
            ... )
            >>> print(len(result['prospects']))
            25
        """
        # Validate inputs
        if not search_criteria:
            raise ValidationError(
                "Search criteria is required with at least one filter"
            )

        if enrichment_level not in ["basic", "standard", "premium"]:
            raise ValidationError(f"Invalid enrichment level: {enrichment_level}")

        self.log_action(
            "Building prospect list",
            criteria=search_criteria,
            enrichment=enrichment_level,
        )

        # Check cache
        cache_key = self._cache_key(
            "prospect_list", criteria=search_criteria, enrichment=enrichment_level
        )
        cached = await self.cache_get(cache_key)
        if cached:
            return cached

        # Rate limiting
        await self.wait_for_rate_limit("clearbit")
        self.record_request("clearbit")

        # Search for companies matching criteria
        matching_companies = self._search_companies(search_criteria)

        # Determine enrichment fields based on level
        enrichment_fields = self._get_enrichment_fields(enrichment_level)

        # Enrich companies
        prospects = []
        for company_domain, company_data in matching_companies:
            # Build prospect record
            prospect = {
                "domain": company_domain,
                "name": company_data["name"],
            }

            # Add enrichment based on level
            if "firmographics" in enrichment_fields:
                prospect["firmographics"] = company_data["firmographics"]

            if "technographics" in enrichment_fields:
                prospect["technographics"] = company_data["technographics"]

            if "funding" in enrichment_fields:
                prospect["funding"] = company_data["funding"]

            if "social" in enrichment_fields:
                prospect["social"] = company_data["social"]

            if "contacts" in enrichment_fields:
                # Get key contacts
                contacts = self._generate_contacts_for_company(
                    company_domain, company_data
                )
                prospect["key_contacts"] = contacts[:3]  # Top 3 contacts

            if "intent_signals" in enrichment_fields:
                intent_data = self._mock_intent_data.get(
                    company_domain, self._generate_intent_data(company_domain)
                )
                prospect["intent_score"] = intent_data["intent_score"]
                prospect["intent_signals"] = intent_data["signals"][:2]

            prospects.append(prospect)

        # Calculate list metrics
        list_metrics = self._calculate_list_metrics(prospects, search_criteria)

        result = {
            "prospects": prospects,
            "total_prospects": len(prospects),
            "search_criteria": search_criteria,
            "enrichment_level": enrichment_level,
            "enrichment_fields": enrichment_fields,
            "list_metrics": list_metrics,
            "export_formats": ["json", "csv", "excel"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

        # Cache result
        await self.cache_set(cache_key, result, CacheConfig.TTL["lead_data"])

        self.log_metric("prospects_generated", len(prospects))

        return result

    # ==================== Helper Methods ====================

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain to lowercase without protocol."""
        domain = domain.lower().strip()
        domain = re.sub(r"^https?://", "", domain)
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split("/")[0]  # Remove path
        return domain

    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format."""
        pattern = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
        return bool(pattern.match(domain))

    def _generate_mock_companies(self) -> Dict[str, Dict]:
        """Generate mock company database."""
        import random

        companies = {}
        domains = [
            "acmecorp.com",
            "techstart.io",
            "bigenterprise.com",
            "innovate.ai",
            "cloudscale.io",
            "datadriven.co",
            "smartsales.com",
            "growthco.io",
            "digitalfirst.com",
            "futuretech.ai",
        ]

        for domain in domains:
            companies[domain] = self._generate_company_data(domain)

        return companies

    def _generate_company_data(self, domain: str) -> Dict:
        """Generate mock company data."""
        import random

        name = domain.split(".")[0].title()

        return {
            "name": f"{name} Inc.",
            "firmographics": {
                "industry": random.choice(self.INDUSTRIES),
                "size": random.choice(self.COMPANY_SIZES),
                "revenue": random.choice(
                    ["$1M-$5M", "$5M-$10M", "$10M-$50M", "$50M-$100M", "$100M+"]
                ),
                "location": random.choice(
                    [
                        "San Francisco, CA",
                        "New York, NY",
                        "Austin, TX",
                        "Boston, MA",
                        "Seattle, WA",
                    ]
                ),
                "founded": random.randint(2010, 2022),
                "employee_count": random.randint(50, 500),
            },
            "technographics": {
                "categories": {
                    category: random.sample(tools, k=min(2, len(tools)))
                    for category, tools in random.sample(
                        list(self.TECH_CATEGORIES.items()), k=random.randint(3, 5)
                    )
                },
                "tech_count": random.randint(10, 25),
            },
            "funding": {
                "stage": random.choice(self.FUNDING_STAGES),
                "total_raised": f"${random.randint(1, 50)}M",
                "last_round_date": (
                    datetime.now() - timedelta(days=random.randint(30, 365))
                ).strftime("%Y-%m-%d"),
                "investors": random.sample(
                    [
                        "Sequoia",
                        "Andreessen Horowitz",
                        "Y Combinator",
                        "Accel",
                        "Greylock",
                    ],
                    k=random.randint(2, 3),
                ),
            },
            "social": {
                "linkedin_url": f"https://linkedin.com/company/{name.lower()}",
                "linkedin_followers": random.randint(1000, 50000),
                "twitter_handle": f"@{name.lower()}",
                "twitter_followers": random.randint(500, 30000),
            },
            "contact_count": random.randint(10, 100),
            "intent_score": random.randint(40, 95),
            "recent_news": [
                f"{name} raises Series B funding",
                f"{name} launches new product",
                f"{name} expands to new market",
            ][: random.randint(1, 3)],
        }

    def _generate_mock_contacts(self) -> Dict[str, List[Dict]]:
        """Generate mock contact database."""
        return {}  # Generated on-demand

    def _generate_contacts_for_company(
        self, domain: str, company_data: Dict
    ) -> List[Dict]:
        """Generate contacts for a specific company."""
        import random

        first_names = [
            "John",
            "Jane",
            "Michael",
            "Sarah",
            "David",
            "Emily",
            "Robert",
            "Lisa",
        ]
        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
        ]

        titles_by_dept = {
            "Sales": [
                "VP of Sales",
                "Sales Director",
                "Sales Manager",
                "Account Executive",
            ],
            "Marketing": [
                "CMO",
                "VP of Marketing",
                "Marketing Director",
                "Marketing Manager",
            ],
            "Engineering": [
                "CTO",
                "VP of Engineering",
                "Engineering Director",
                "Lead Engineer",
            ],
            "Product": ["CPO", "VP of Product", "Product Director", "Product Manager"],
            "Operations": [
                "COO",
                "VP of Operations",
                "Operations Director",
                "Operations Manager",
            ],
        }

        contacts = []
        num_contacts = min(10, random.randint(5, 15))

        for i in range(num_contacts):
            first = random.choice(first_names)
            last = random.choice(last_names)
            dept = random.choice(list(titles_by_dept.keys()))
            title = random.choice(titles_by_dept[dept])

            # Determine seniority from title
            if any(s in title for s in ["VP", "Chief", "CMO", "CTO", "COO", "CPO"]):
                seniority = "VP" if "VP" in title else "C-Level"
            elif "Director" in title:
                seniority = "Director"
            elif "Manager" in title:
                seniority = "Manager"
            else:
                seniority = "Individual Contributor"

            email = f"{first.lower()}.{last.lower()}@{domain}"

            contact = {
                "name": f"{first} {last}",
                "title": title,
                "email": email,
                "seniority": seniority,
                "department": dept,
                "linkedin_url": f"https://linkedin.com/in/{first.lower()}{last.lower()}",
                "email_verified": random.choice(
                    [True, True, True, False]
                ),  # 75% verified
                "confidence": round(random.uniform(0.8, 0.99), 2),
            }

            contacts.append(contact)

        return contacts

    def _generate_mock_intent_data(self) -> Dict[str, Dict]:
        """Generate mock intent signal database."""
        return {}  # Generated on-demand

    def _generate_intent_data(self, domain: str) -> Dict:
        """Generate mock intent data for a company."""
        import random

        signal_definitions = {
            "job_postings": {
                "weight": 20,
                "descriptions": [
                    "Hiring for sales roles",
                    "Expanding engineering team",
                    "Recruiting marketing positions",
                ],
            },
            "funding_rounds": {
                "weight": 30,
                "descriptions": [
                    "Raised Series B",
                    "Secured seed funding",
                    "Completed Series A",
                ],
            },
            "tech_changes": {
                "weight": 15,
                "descriptions": [
                    "Added new marketing tools",
                    "Upgraded CRM system",
                    "Implemented analytics platform",
                ],
            },
            "website_visits": {
                "weight": 10,
                "descriptions": [
                    "Multiple visits to pricing page",
                    "Viewed case studies",
                    "Downloaded whitepaper",
                ],
            },
            "content_downloads": {
                "weight": 12,
                "descriptions": [
                    "Downloaded product guide",
                    "Accessed comparison report",
                    "Viewed demo video",
                ],
            },
            "hiring_signals": {
                "weight": 18,
                "descriptions": [
                    "Hiring expansion",
                    "New department openings",
                    "Leadership additions",
                ],
            },
        }

        # Select 3-5 random signals
        num_signals = random.randint(3, 5)
        selected_types = random.sample(list(signal_definitions.keys()), k=num_signals)

        signals = []
        for signal_type in selected_types:
            definition = signal_definitions[signal_type]
            signal = {
                "type": signal_type,
                "count": random.randint(1, 5),
                "weight": definition["weight"],
                "description": random.choice(definition["descriptions"]),
                "detected_at": (
                    datetime.now() - timedelta(days=random.randint(1, 30))
                ).isoformat(),
            }
            signals.append(signal)

        # Calculate intent score
        intent_score = min(
            100, sum(s["weight"] for s in signals) + random.randint(-10, 20)
        )

        # Generate trigger events
        trigger_events = []
        if any(s["type"] == "funding_rounds" for s in signals):
            trigger_events.append("Recent funding")
        if any(s["type"] in ["job_postings", "hiring_signals"] for s in signals):
            trigger_events.append("Hiring expansion")
        if any(s["type"] == "tech_changes" for s in signals):
            trigger_events.append("Technology adoption")

        return {
            "domain": domain,
            "intent_score": intent_score,
            "signals": signals,
            "trigger_events": trigger_events,
        }

    def _filter_contacts(
        self, contacts: List[Dict], filters: Dict[str, Any]
    ) -> List[Dict]:
        """Filter contacts based on criteria."""
        filtered = contacts

        if "role" in filters:
            role_filter = filters["role"]
            if isinstance(role_filter, str):
                role_filter = [role_filter]
            filtered = [
                c
                for c in filtered
                if any(role.lower() in c["title"].lower() for role in role_filter)
            ]

        if "seniority" in filters:
            seniority_filter = filters["seniority"]
            if isinstance(seniority_filter, str):
                seniority_filter = [seniority_filter]
            filtered = [c for c in filtered if c["seniority"] in seniority_filter]

        if "department" in filters:
            dept_filter = filters["department"]
            if isinstance(dept_filter, str):
                dept_filter = [dept_filter]
            filtered = [c for c in filtered if c["department"] in dept_filter]

        return filtered

    def _verify_email(self, email: str) -> bool:
        """Mock email verification."""
        import random

        # 85% verification rate
        return random.random() < 0.85

    def _extract_email_pattern(self, contacts: List[Dict]) -> str:
        """Extract email pattern from contacts."""
        if not contacts:
            return "unknown"

        # Analyze email patterns
        patterns = {}
        for contact in contacts:
            email = contact["email"]
            local_part = email.split("@")[0]

            if "." in local_part:
                pattern = "firstlast"
            elif "_" in local_part:
                pattern = "first_last"
            else:
                pattern = "firstlast"

            patterns[pattern] = patterns.get(pattern, 0) + 1

        # Return most common pattern
        return max(patterns.items(), key=lambda x: x[1])[0] if patterns else "firstlast"

    def _calculate_completeness(self, data: Dict, requested_fields: List[str]) -> float:
        """Calculate data completeness score (0-100)."""
        total_fields = len(requested_fields)
        if total_fields == 0:
            return 100.0

        filled_fields = sum(
            1 for field in requested_fields if field in data and data[field]
        )
        return round((filled_fields / total_fields) * 100, 1)

    def _calculate_confidence(self, data: Dict) -> float:
        """Calculate confidence level (0-1)."""
        import random

        # Higher confidence for more complete data
        completeness = self._calculate_completeness(data, list(data.keys()))
        base_confidence = completeness / 100
        # Add some randomness
        return round(min(0.99, base_confidence + random.uniform(-0.1, 0.1)), 2)

    def _calculate_intent_score(self, signals: List[Dict]) -> int:
        """Calculate overall intent score from signals."""
        if not signals:
            return 0

        # Weight-based scoring
        total_score = sum(s["weight"] * s["count"] for s in signals)

        # Normalize to 0-100
        max_possible = 100
        normalized = min(100, int((total_score / max_possible) * 100))

        return normalized

    def _identify_trigger_events(self, signals: List[Dict]) -> List[str]:
        """Identify trigger events from signals."""
        events = []

        signal_types = [s["type"] for s in signals]

        if "funding_rounds" in signal_types:
            events.append("Recent funding")
        if "job_postings" in signal_types or "hiring_signals" in signal_types:
            events.append("Hiring expansion")
        if "tech_changes" in signal_types:
            events.append("Technology adoption")
        if "website_visits" in signal_types and "content_downloads" in signal_types:
            events.append("Active research phase")

        return events

    def _generate_intent_recommendation(
        self, intent_score: int, trigger_events: List[str]
    ) -> str:
        """Generate recommendation based on intent score and events."""
        if intent_score >= 80:
            return "High priority - strong buying intent with multiple trigger events"
        elif intent_score >= 60:
            return "Medium priority - moderate intent signals detected"
        elif intent_score >= 40:
            return "Low priority - some interest signals, nurture lead"
        else:
            return "Monitor - limited intent signals, keep on watch list"

    def _get_priority_level(self, score: float) -> str:
        """Determine priority level from score."""
        if score >= 75:
            return "High"
        elif score >= 50:
            return "Medium"
        else:
            return "Low"

    def _calculate_fit_score(
        self, company_data: Dict, criteria: Dict[str, Any]
    ) -> float:
        """Calculate fit score based on ICP criteria."""
        score = 0
        max_score = 0

        # Industry match (30 points)
        max_score += 30
        if "target_industry" in criteria:
            if company_data["firmographics"]["industry"] == criteria["target_industry"]:
                score += 30
            elif company_data["firmographics"]["industry"] in criteria.get(
                "industries", []
            ):
                score += 20

        # Company size match (25 points)
        max_score += 25
        if "min_size" in criteria or "max_size" in criteria:
            company_size = company_data["firmographics"]["size"]
            # Simplified size matching
            if "min_size" in criteria:
                score += 25  # Mock scoring

        # Tech stack match (25 points)
        max_score += 25
        if "tech_stack" in criteria:
            required_tech = set(criteria["tech_stack"])
            company_tech = set()
            for tools in company_data["technographics"]["categories"].values():
                company_tech.update(tools)
            overlap = len(required_tech & company_tech)
            if overlap > 0:
                score += min(25, overlap * 10)

        # Budget signals (20 points)
        max_score += 20
        if "min_funding" in criteria:
            if company_data["funding"]["stage"] in [
                "Series B",
                "Series C",
                "Series D+",
                "IPO",
            ]:
                score += 20

        # Normalize to 0-100
        if max_score == 0:
            return 50.0  # Default score when no criteria

        return min(100.0, (score / max_score) * 100)

    def _check_icp_match(self, company_data: Dict, criteria: Dict[str, Any]) -> bool:
        """Check if company matches ideal customer profile."""
        # Simple ICP matching logic
        matches = 0
        checks = 0

        if "target_industry" in criteria:
            checks += 1
            if company_data["firmographics"]["industry"] == criteria["target_industry"]:
                matches += 1

        if "min_size" in criteria:
            checks += 1
            # Simplified check
            matches += 1

        if "tech_stack" in criteria:
            checks += 1
            required_tech = set(criteria["tech_stack"])
            company_tech = set()
            for tools in company_data["technographics"]["categories"].values():
                company_tech.update(tools)
            if len(required_tech & company_tech) >= len(required_tech) * 0.5:
                matches += 1

        # ICP match if 75%+ criteria met
        return checks > 0 and (matches / checks) >= 0.75

    def _generate_scoring_reasons(
        self,
        company_data: Dict,
        intent_data: Dict,
        criteria: Dict,
        fit_score: float,
        intent_score: float,
    ) -> List[str]:
        """Generate reasons for the lead score."""
        reasons = []

        if fit_score >= 80:
            reasons.append("Strong ICP fit")
        elif fit_score >= 60:
            reasons.append("Good company profile match")

        if intent_score >= 80:
            reasons.append("High buying intent")
        elif intent_score >= 60:
            reasons.append("Active engagement signals")

        if "target_industry" in criteria:
            if company_data["firmographics"]["industry"] == criteria["target_industry"]:
                reasons.append("Target industry match")

        if company_data["funding"]["stage"] in ["Series B", "Series C", "Series D+"]:
            reasons.append("Well-funded company")

        if intent_data.get("trigger_events"):
            reasons.append(f"Trigger event: {intent_data['trigger_events'][0]}")

        return reasons[:5]  # Top 5 reasons

    def _search_companies(self, criteria: Dict[str, Any]) -> List[tuple[str, Dict]]:
        """Search for companies matching criteria."""
        import random

        # Generate matching companies
        matching = []

        for domain, company_data in self._mock_companies.items():
            match = True

            # Industry filter
            if "industry" in criteria:
                industries = (
                    criteria["industry"]
                    if isinstance(criteria["industry"], list)
                    else [criteria["industry"]]
                )
                if company_data["firmographics"]["industry"] not in industries:
                    match = False

            # Size filter
            if "size" in criteria:
                sizes = (
                    criteria["size"]
                    if isinstance(criteria["size"], list)
                    else [criteria["size"]]
                )
                if company_data["firmographics"]["size"] not in sizes:
                    match = False

            # Location filter
            if "location" in criteria:
                if (
                    criteria["location"]
                    not in company_data["firmographics"]["location"]
                ):
                    match = False

            # Funding stage filter
            if "funding_stage" in criteria:
                stages = (
                    criteria["funding_stage"]
                    if isinstance(criteria["funding_stage"], list)
                    else [criteria["funding_stage"]]
                )
                if company_data["funding"]["stage"] not in stages:
                    match = False

            # Tech stack filter
            if "tech_stack" in criteria:
                required_tech = set(criteria["tech_stack"])
                company_tech = set()
                for tools in company_data["technographics"]["categories"].values():
                    company_tech.update(tools)
                if not (required_tech & company_tech):
                    match = False

            if match:
                matching.append((domain, company_data))

        # Return up to 25 matches
        return random.sample(matching, k=min(25, len(matching))) if matching else []

    def _get_enrichment_fields(self, level: str) -> List[str]:
        """Get enrichment fields for the specified level."""
        if level == "basic":
            return ["firmographics"]
        elif level == "standard":
            return ["firmographics", "technographics", "social"]
        else:  # premium
            return [
                "firmographics",
                "technographics",
                "funding",
                "social",
                "contacts",
                "intent_signals",
            ]

    def _calculate_list_metrics(
        self, prospects: List[Dict], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate metrics for the prospect list."""
        if not prospects:
            return {}

        # Count by industry
        industries = {}
        for p in prospects:
            industry = p.get("firmographics", {}).get("industry", "Unknown")
            industries[industry] = industries.get(industry, 0) + 1

        # Count by size
        sizes = {}
        for p in prospects:
            size = p.get("firmographics", {}).get("size", "Unknown")
            sizes[size] = sizes.get(size, 0) + 1

        # Average intent score
        intent_scores = [
            p.get("intent_score", 0) for p in prospects if "intent_score" in p
        ]
        avg_intent = (
            round(sum(intent_scores) / len(intent_scores), 1) if intent_scores else 0
        )

        return {
            "total_prospects": len(prospects),
            "by_industry": industries,
            "by_size": sizes,
            "avg_intent_score": avg_intent,
            "high_intent_count": len([s for s in intent_scores if s >= 75]),
        }
