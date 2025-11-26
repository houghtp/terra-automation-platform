"""
AI-powered prospect research service for Sales Outreach Prep.

This service handles multi-step AI research workflows:
1. Interprets natural language research goals (via OpenAI)
2. Executes deterministic research workflows (via Firecrawl)
3. Synthesizes and cleans results (via OpenAI)

Reuses centralized API clients from content_broadcaster:
- OpenAIClient for AI interpretation and synthesis
- FirecrawlClient for web search and scraping

Example workflows:
- Venue research: venues → events → organizations
- Direct search: search query → organizations
- Association members: association → member directory
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.utils.external_api_clients import (
    get_openai_client_from_secret,
    get_firecrawl_client_from_secret,
    OpenAIClient,
    FirecrawlClient
)

logger = get_logger(__name__)


class ProspectResearchService:
    """
    AI-powered research service for discovering prospect organizations.

    Follows the same pattern as content_broadcaster's AIResearchService:
    - Initializes clients from Secrets Management
    - Uses OpenAI for interpretation and synthesis
    - Uses Firecrawl for search and scraping
    - Provides clean async interfaces
    """

    def __init__(self, tenant_id: Optional[str] = None):
        """
        Initialize research service.

        Args:
            tenant_id: Tenant ID for secrets retrieval
        """
        self.tenant_id = tenant_id
        self.openai_client: Optional[OpenAIClient] = None
        self.firecrawl_client: Optional[FirecrawlClient] = None

    async def _init_clients(self, db_session, accessed_by_user=None):
        """
        Initialize API clients from Secrets Management.

        Args:
            db_session: Database session
            accessed_by_user: User accessing secrets (for audit trail)

        Raises:
            ValueError: If required secrets not found
        """
        try:
            # Get OpenAI client
            self.openai_client = await get_openai_client_from_secret(
                db_session=db_session,
                tenant_id=self.tenant_id,
                secret_name="OpenAI API Key",
                accessed_by_user=accessed_by_user
            )

            # Get Firecrawl client
            self.firecrawl_client = await get_firecrawl_client_from_secret(
                db_session=db_session,
                tenant_id=self.tenant_id,
                secret_name="Firecrawl API Key",
                accessed_by_user=accessed_by_user
            )

            logger.info(
                "ProspectResearchService API clients initialized",
                tenant_id=self.tenant_id
            )

        except Exception as e:
            logger.error(
                "Failed to initialize API clients",
                tenant_id=self.tenant_id,
                error=str(e)
            )
            raise ValueError(
                "Failed to initialize research service. "
                "Ensure OpenAI and Firecrawl API keys are configured in Secrets Management."
            ) from e

    async def _interpret_research_goal(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Use OpenAI to interpret natural language research goal.

        Args:
            prompt: Natural language research goal from user

        Returns:
            Dict with extracted search parameters:
            {
                "research_type": "venue_research" | "direct_search" | "association_members",
                "geography": "UK" | "San Francisco" | None,
                "event_size": "400+" | None,
                "industry": "tech" | "corporate" | None,
                "search_queries": ["query1", "query2", ...],
                "reasoning": "Why this research type was chosen"
            }
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Call _init_clients() first.")

        system_prompt = """You are a research planning assistant for B2B sales prospecting.

Your task: Analyze the user's research goal and extract structured search parameters.

Research types available:
1. "venue_research" - Research venues → events → organizations (e.g., "Find organizers of corporate events at large venues")
2. "direct_search" - Search for companies/organizations directly (e.g., "Find SaaS companies in Austin")
3. "association_members" - Find members of associations/groups (e.g., "Find members of UK Marketing Association")

Extract:
- research_type: Choose the most appropriate type
- geography: Location/country if specified
- event_size: Audience size if mentioned (e.g., "400+", "1000+")
- industry: Industry/sector if mentioned
- search_queries: 3-5 Google search queries to execute
- reasoning: Brief explanation of your choices

Return valid JSON only."""

        user_prompt = f"""Research goal: "{prompt}"

Analyze this and return JSON with the structure above."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.openai_client.chat_completion(
                messages=messages,
                temperature=0.3,  # Lower temperature for more deterministic output
                model="gpt-4"
            )

            # Parse JSON response
            research_plan = json.loads(response)

            logger.info(
                "Research goal interpreted",
                research_type=research_plan.get("research_type"),
                num_queries=len(research_plan.get("search_queries", []))
            )

            return research_plan

        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response as JSON", error=str(e))
            raise ValueError("AI returned invalid response format") from e
        except Exception as e:
            logger.exception("Failed to interpret research goal")
            raise

    async def _determine_workflow_strategy(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Use AI to determine the best search strategy for the research goal.

        Analyzes prompt to decide:
        1. direct_contacts_by_role - Role-based search (e.g., "Find CTOs in London")
        2. direct_contacts_at_company - Company-specific search (e.g., "Find event managers at Barclays")
        3. unknown_orgs_then_contacts - Multi-step (e.g., "Find organizers of corporate events")

        Args:
            prompt: Natural language research goal

        Returns:
            {
                "strategy": "direct_contacts_by_role" | "direct_contacts_at_company" | "unknown_orgs_then_contacts",
                "target_roles": ["CTO", "Chief Technology Officer"],
                "target_company": "Barclays Bank" | null,
                "geography": "London" | null,
                "linkedin_queries": ["CTO London", "Chief Technology Officer London"],
                "reasoning": "Explanation of strategy choice"
            }
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Call _init_clients() first.")

        system_prompt = """You are a prospect research strategist. Analyze the research goal and determine the best search strategy.

**Three strategies available:**

1. **direct_contacts_by_role** - Role/title-based search across companies
   - Use when: User wants people by role, no specific company mentioned
   - Example: "Find all CTOs in London", "marketing directors in tech"
   - Result: Search LinkedIn for role + geography

2. **direct_contacts_at_company** - Search for people at specific company
   - Use when: Company name is explicitly mentioned
   - Example: "Find event managers at Barclays Bank", "engineers at Google UK"
   - Result: Search LinkedIn for role + company

3. **unknown_orgs_then_contacts** - Multi-step discovery
   - Use when: Organizations are unknown and need to be discovered first
   - Example: "Find organizers of corporate awards events", "venue managers for tech conferences"
   - Result: Discover organizations → then find contacts

**Your task:**
- Analyze the prompt
- Choose the best strategy
- Extract: target_roles, target_company (if mentioned), geography
- Generate 3-5 LinkedIn search queries optimized for the strategy
- **IMPORTANT**: For LinkedIn searches, ALWAYS add "site:linkedin.com/in/" to force Google to search LinkedIn profiles only
- Explain your reasoning

Return JSON:
{
  "strategy": "direct_contacts_by_role" | "direct_contacts_at_company" | "unknown_orgs_then_contacts",
  "target_roles": ["role1", "role2"],
  "target_company": "Company Name" or null,
  "geography": "Location" or null,
  "linkedin_queries": ["query1 site:linkedin.com/in/", "query2 site:linkedin.com/in/", ...],
  "reasoning": "Why this strategy was chosen"
}

**Example linkedin_queries**:
- "CTO London site:linkedin.com/in/"
- "Chief Technology Officer Google site:linkedin.com/in/"
- "event manager Barclays Bank site:linkedin.com/in/" """

        user_prompt = f"""Research goal: "{prompt}"

Analyze this and determine the best search strategy."""

        try:
            response = await self.openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                model="gpt-4"
            )

            strategy = json.loads(response)

            logger.info(
                "Workflow strategy determined",
                strategy=strategy.get("strategy"),
                target_company=strategy.get("target_company"),
                num_queries=len(strategy.get("linkedin_queries", []))
            )

            return strategy

        except json.JSONDecodeError as e:
            logger.error("Failed to parse strategy response", error=str(e))
            raise ValueError("AI returned invalid strategy format") from e
        except Exception as e:
            logger.exception("Failed to determine workflow strategy")
            raise

    async def venue_research_workflow(
        self,
        research_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute venue research workflow: venues → events → organizations.

        Args:
            research_plan: Interpreted research plan from _interpret_research_goal()

        Returns:
            List of organizations found:
            [
                {
                    "name": "British Events Association",
                    "website": "https://...",
                    "context": "Organizes UK Business Awards at ExCeL London",
                    "source": "venue_research",
                    "confidence": "high"
                }
            ]
        """
        if not self.firecrawl_client:
            raise ValueError("Firecrawl client not initialized. Call _init_clients() first.")

        organizations = []
        search_queries = research_plan.get("search_queries", [])

        logger.info(
            "Starting venue research workflow",
            num_queries=len(search_queries)
        )

        # Step 1: Search for venues
        venues = []
        for query in search_queries[:3]:  # Limit to first 3 queries
            try:
                search_results = await self.firecrawl_client.search(
                    query=query,
                    limit=5
                )

                for result in search_results:
                    venues.append({
                        "name": result.get("title", "Unknown venue"),
                        "url": result.get("url"),
                        "snippet": result.get("snippet", "")
                    })

                logger.info(f"Venue search completed", query=query, results=len(search_results))

            except Exception as e:
                logger.warning(f"Venue search failed", query=query, error=str(e))
                continue

        # Step 2: For each venue, search for events
        for venue in venues[:10]:  # Limit to top 10 venues
            event_query = f"{venue['name']} corporate events awards"

            try:
                event_results = await self.firecrawl_client.search(
                    query=event_query,
                    limit=3
                )

                # Step 3: For each event, try to identify organizer
                for event in event_results:
                    try:
                        # Scrape event page to find organizer
                        page_content = await self.firecrawl_client.scrape(
                            url=event.get("url"),
                            formats=["markdown"]
                        )

                        markdown = page_content.get("markdown", "")

                        # Use OpenAI to extract organizer from page content
                        org = await self._extract_organizer_from_content(
                            markdown[:2000],  # First 2000 chars
                            event.get("title"),
                            venue["name"]
                        )

                        if org:
                            organizations.append(org)

                    except Exception as e:
                        logger.warning(
                            "Failed to extract organizer",
                            event=event.get("title"),
                            error=str(e)
                        )
                        continue

            except Exception as e:
                logger.warning(
                    "Event search failed",
                    venue=venue["name"],
                    error=str(e)
                )
                continue

        logger.info(
            "Venue research workflow completed",
            organizations_found=len(organizations)
        )

        return organizations

    async def direct_search_workflow(
        self,
        research_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute direct organization search workflow.

        Args:
            research_plan: Interpreted research plan

        Returns:
            List of organizations found
        """
        if not self.firecrawl_client:
            raise ValueError("Firecrawl client not initialized. Call _init_clients() first.")

        organizations = []
        search_queries = research_plan.get("search_queries", [])

        logger.info(
            "Starting direct search workflow",
            num_queries=len(search_queries)
        )

        for query in search_queries[:5]:  # Limit to 5 queries
            try:
                search_results = await self.firecrawl_client.search(
                    query=query,
                    limit=10
                )

                for result in search_results:
                    # Try to extract organization from search result
                    org = {
                        "name": result.get("title", "Unknown organization"),
                        "website": result.get("url"),
                        "context": result.get("snippet", ""),
                        "source": "direct_search",
                        "confidence": "medium"
                    }

                    organizations.append(org)

                logger.info(
                    "Direct search completed",
                    query=query,
                    results=len(search_results)
                )

            except Exception as e:
                logger.warning(f"Direct search failed", query=query, error=str(e))
                continue

        logger.info(
            "Direct search workflow completed",
            organizations_found=len(organizations)
        )

        return organizations

    async def _search_linkedin_for_prospects(
        self,
        queries: List[str],
        max_results_per_query: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Execute LinkedIn searches and extract prospect information.

        Args:
            queries: LinkedIn search queries
            max_results_per_query: Max results per query

        Returns:
            List of prospects:
            [
                {
                    "full_name": "John Doe",
                    "job_title": "CTO",
                    "company_name": "TechCorp",
                    "company_website": "https://techcorp.com",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                    "location": "London, UK",
                    "confidence": "high",
                    "source": "LinkedIn search"
                }
            ]
        """
        if not self.firecrawl_client:
            raise ValueError("Firecrawl client not initialized.")

        prospects = []

        for query in queries[:5]:  # Limit to 5 queries
            try:
                logger.info(f"LinkedIn search", query=query)

                # Use Firecrawl to search (it can handle LinkedIn)
                results = await self.firecrawl_client.search(
                    query=query,
                    limit=max_results_per_query
                )

                for result in results:
                    # Parse LinkedIn profile from search result
                    prospect = self._parse_linkedin_profile(result, query)
                    if prospect:
                        prospects.append(prospect)

                logger.info(
                    "LinkedIn search completed",
                    query=query,
                    prospects_found=len(results)
                )

            except Exception as e:
                logger.warning(f"LinkedIn search failed", query=query, error=str(e))
                continue

        logger.info(
            "LinkedIn prospect search completed",
            total_prospects=len(prospects)
        )

        return prospects

    def _parse_linkedin_profile(
        self,
        search_result: Dict[str, Any],
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse LinkedIn profile data from search result.

        Args:
            search_result: Firecrawl search result
            query: Original search query

        Returns:
            Prospect dict or None
        """
        try:
            # Extract from title/snippet
            title = search_result.get("title", "")
            snippet = search_result.get("snippet", "")
            url = search_result.get("url", "")

            # Basic validation
            if not title or "linkedin.com/in/" not in url.lower():
                return None

            # Remove " | LinkedIn", " - LinkedIn" suffixes
            title = title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()

            # Initialize with defaults
            full_name = "Unknown"
            job_title = None
            company_name = None

            # Strategy 1: Parse from title format "John Doe - CTO at TechCorp"
            if " - " in title:
                parts = title.split(" - ", 1)  # Split on first " - " only
                full_name = parts[0].strip()

                if len(parts) > 1:
                    job_company = parts[1].strip()

                    # Extract job title and company
                    if " at " in job_company:
                        job_parts = job_company.split(" at ", 1)
                        job_title = job_parts[0].strip()
                        company_name = job_parts[1].strip() if len(job_parts) > 1 else None
                    else:
                        # Just job title, no company
                        job_title = job_company
            else:
                # No " - " separator, title might just be the name
                full_name = title.strip()

            # Strategy 2: If job title or company not found, try snippet
            if not job_title or not company_name:
                # LinkedIn snippets often have format like:
                # "John Doe - CTO at TechCorp - London, UK · View John's profile"
                # or "Chief Technology Officer at Microsoft. Experience: ..."
                if snippet:
                    snippet_clean = snippet.replace(" · ", " - ").replace(" | ", " - ")

                    # Try to find "at [Company]" pattern
                    if " at " in snippet_clean and not company_name:
                        # Find the "at" phrase
                        at_index = snippet_clean.lower().find(" at ")
                        if at_index > 0:
                            # Extract company (take text after "at" until next separator)
                            company_text = snippet_clean[at_index + 4:].split(".")[0].split("-")[0].strip()
                            if company_text and len(company_text) < 100:  # Sanity check
                                company_name = company_text

                    # Try to find job title if not already found
                    if not job_title:
                        # Look for common title patterns before "at"
                        if " at " in snippet_clean:
                            at_index = snippet_clean.lower().find(" at ")
                            # Get text before "at" (might be job title)
                            before_at = snippet_clean[:at_index].strip()
                            # Check if it looks like a job title (not too long, contains typical title words)
                            title_keywords = ["chief", "officer", "director", "manager", "head", "lead", "senior", "cto", "ceo", "vp"]
                            if any(keyword in before_at.lower() for keyword in title_keywords):
                                # Take last sentence/phrase before "at"
                                job_title_candidate = before_at.split(".")[-1].split("-")[-1].strip()
                                if len(job_title_candidate) < 80:  # Reasonable length
                                    job_title = job_title_candidate

            # Log what we extracted for debugging
            logger.debug(
                "LinkedIn profile parsed",
                full_name=full_name,
                job_title=job_title or "Unknown",
                company_name=company_name or "Unknown",
                title_source=title[:100],
                snippet_source=snippet[:100] if snippet else None
            )

            return {
                "full_name": full_name,
                "job_title": job_title or "Unknown",
                "company_name": company_name or "Unknown",
                "company_website": None,  # Not available from search results
                "linkedin_url": url,
                "location": None,  # Could parse from snippet if needed
                "confidence": "medium",
                "source": f"LinkedIn search: {query}"
            }

        except Exception as e:
            logger.warning("Failed to parse LinkedIn profile", error=str(e), title=title, snippet=snippet[:100] if snippet else None)
            return None

    async def _direct_contacts_workflow(
        self,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute direct contact search workflow (role-based or company-specific).

        Args:
            strategy: Strategy from _determine_workflow_strategy()

        Returns:
            List of prospects
        """
        linkedin_queries = strategy.get("linkedin_queries", [])

        if not linkedin_queries:
            logger.warning("No LinkedIn queries in strategy")
            return []

        logger.info(
            "Starting direct contacts workflow",
            strategy_type=strategy.get("strategy"),
            num_queries=len(linkedin_queries)
        )

        # Search LinkedIn
        prospects = await self._search_linkedin_for_prospects(linkedin_queries)

        return prospects

    async def _unknown_orgs_then_contacts_workflow(
        self,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute multi-step workflow: discover organizations → find contacts.

        Args:
            strategy: Strategy from _determine_workflow_strategy()

        Returns:
            List of prospects
        """
        logger.info("Starting multi-step workflow: organizations → contacts")

        # Step 1: Discover organizations using existing logic
        # Use the old _interpret_research_goal for org discovery
        research_plan = {
            "research_type": "venue_research",  # Default to venue research
            "search_queries": strategy.get("linkedin_queries", []),
            "geography": strategy.get("geography"),
            "reasoning": strategy.get("reasoning")
        }

        # Execute venue or direct search to find orgs
        organizations = await self.venue_research_workflow(research_plan)

        if not organizations:
            logger.warning("No organizations found in multi-step workflow")
            return []

        logger.info(f"Discovered {len(organizations)} organizations")

        # Step 2: For each organization, search for contacts
        prospects = []
        target_roles = strategy.get("target_roles", ["CEO", "Operations Manager", "Director"])

        for org in organizations[:10]:  # Limit to 10 orgs
            org_name = org.get("name", "Unknown")

            # Generate LinkedIn queries for this org
            queries = [
                f"{role} {org_name}" for role in target_roles[:3]
            ]

            logger.info(f"Searching contacts at {org_name}")

            # Search for contacts at this organization
            org_prospects = await self._search_linkedin_for_prospects(queries, max_results_per_query=5)

            # Add organization context to prospects
            for prospect in org_prospects:
                prospect["company_website"] = org.get("website")
                prospect["discovered_via_org"] = org_name

            prospects.extend(org_prospects)

        logger.info(
            "Multi-step workflow completed",
            organizations_found=len(organizations),
            prospects_found=len(prospects)
        )

        return prospects

    async def _extract_organizer_from_content(
        self,
        content: str,
        event_name: str,
        venue_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Use OpenAI to extract organizer information from scraped content.

        Args:
            content: Markdown content from event page
            event_name: Name of the event
            venue_name: Name of the venue

        Returns:
            Organization dict if found, None otherwise
        """
        if not self.openai_client:
            return None

        prompt = f"""Extract the organizing company/organization from this event page content.

Event: {event_name}
Venue: {venue_name}

Content:
{content}

Return JSON with:
{{
    "name": "Organization name",
    "website": "URL if found",
    "context": "Brief context about what they organize",
    "confidence": "high" | "medium" | "low"
}}

If no clear organizer found, return: {{"name": null}}"""

        try:
            response = await self.openai_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                model="gpt-4"
            )

            result = json.loads(response)

            if result.get("name"):
                result["source"] = "venue_research"
                return result

        except Exception as e:
            logger.warning("Failed to extract organizer with AI", error=str(e))

        return None

    async def _synthesize_results(
        self,
        organizations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use OpenAI to clean, deduplicate, and enrich organization list.

        Args:
            organizations: Raw list of organizations from research

        Returns:
            Cleaned and deduplicated list
        """
        if not self.openai_client or not organizations:
            return organizations

        logger.info(
            "Synthesizing research results",
            organizations_count=len(organizations)
        )

        prompt = f"""Clean and deduplicate this list of organizations.

Organizations found:
{json.dumps(organizations, indent=2)[:5000]}

Tasks:
1. Remove duplicates (same organization with different names)
2. Clean organization names (remove noise, standardize format)
3. Validate/clean website URLs
4. Merge context from duplicates
5. Sort by confidence (high → medium → low)

Return JSON array of cleaned organizations with same structure."""

        try:
            response = await self.openai_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                model="gpt-4"
            )

            cleaned = json.loads(response)

            logger.info(
                "Results synthesized",
                original_count=len(organizations),
                cleaned_count=len(cleaned)
            )

            return cleaned

        except Exception as e:
            logger.exception("Failed to synthesize results")
            # Return original if synthesis fails
            return organizations

    async def research_organizations(
        self,
        prompt: str,
        db_session,
        accessed_by_user=None
    ) -> Dict[str, Any]:
        """
        Complete AI research workflow.

        Workflow:
        1. Initialize API clients from Secrets Management
        2. Interpret natural language prompt with OpenAI
        3. Execute appropriate research workflow with Firecrawl
        4. Synthesize results with OpenAI

        Args:
            prompt: Natural language research goal
            db_session: Database session for secrets retrieval
            accessed_by_user: User accessing secrets (for audit trail)

        Returns:
            Research results:
            {
                "prompt": "Original prompt",
                "research_plan": {...},
                "organizations": [...],
                "research_steps": [...],
                "completed_at": "ISO timestamp"
            }
        """
        logger.info("Starting AI research", prompt=prompt[:100])

        # Step 1: Initialize clients
        await self._init_clients(db_session, accessed_by_user=accessed_by_user)

        # Step 2: Interpret research goal
        research_plan = await self._interpret_research_goal(prompt)

        # Step 3: Execute appropriate workflow
        research_type = research_plan.get("research_type", "direct_search")

        if research_type == "venue_research":
            organizations = await self.venue_research_workflow(research_plan)
        elif research_type == "direct_search":
            organizations = await self.direct_search_workflow(research_plan)
        else:
            # Default to direct search
            organizations = await self.direct_search_workflow(research_plan)

        # Step 4: Synthesize results
        cleaned_organizations = await self._synthesize_results(organizations)

        # Build final result
        result = {
            "prompt": prompt,
            "research_plan": research_plan,
            "organizations": cleaned_organizations,
            "research_steps": [
                f"Interpreted research goal: {research_plan.get('reasoning')}",
                f"Executed {research_type} workflow",
                f"Found {len(organizations)} organizations",
                f"Cleaned and deduplicated to {len(cleaned_organizations)} organizations"
            ],
            "completed_at": datetime.now().isoformat()
        }

        logger.info(
            "AI research completed",
            research_type=research_type,
            organizations_found=len(cleaned_organizations)
        )

        return result

    async def research_prospects(
        self,
        prompt: str,
        db_session,
        accessed_by_user=None
    ) -> Dict[str, Any]:
        """
        NEW: Complete AI research workflow that returns prospects directly.

        This is the simplified workflow that:
        1. Determines optimal search strategy
        2. Executes LinkedIn searches (with multi-step if needed)
        3. Returns prospects ready for import

        Args:
            prompt: Natural language research goal
            db_session: Database session for secrets retrieval
            accessed_by_user: User accessing secrets (for audit trail)

        Returns:
            {
                "prompt": "Original prompt",
                "strategy": {
                    "strategy": "direct_contacts_by_role" | "direct_contacts_at_company" | "unknown_orgs_then_contacts",
                    "target_roles": [...],
                    "target_company": "...",
                    "linkedin_queries": [...],
                    "reasoning": "..."
                },
                "prospects": [
                    {
                        "full_name": "John Doe",
                        "job_title": "CTO",
                        "company_name": "TechCorp",
                        "company_website": "https://techcorp.com",
                        "linkedin_url": "...",
                        "confidence": "medium",
                        "source": "LinkedIn search"
                    }
                ],
                "metadata": {
                    "total_prospects": 25,
                    "strategy_used": "direct_contacts_by_role"
                },
                "completed_at": "ISO timestamp"
            }
        """
        logger.info("Starting AI prospect research", prompt=prompt[:100])

        # Step 1: Initialize clients
        await self._init_clients(db_session, accessed_by_user=accessed_by_user)

        # Step 2: Determine optimal search strategy
        strategy = await self._determine_workflow_strategy(prompt)

        # Step 3: Execute workflow based on strategy
        strategy_type = strategy.get("strategy")

        if strategy_type == "unknown_orgs_then_contacts":
            # Multi-step: Discover orgs → find contacts
            prospects = await self._unknown_orgs_then_contacts_workflow(strategy)
        else:
            # Direct search (role-based or company-specific)
            prospects = await self._direct_contacts_workflow(strategy)

        # Build final result
        result = {
            "prompt": prompt,
            "strategy": strategy,
            "prospects": prospects,
            "metadata": {
                "total_prospects": len(prospects),
                "strategy_used": strategy_type,
                "target_company": strategy.get("target_company"),
                "geography": strategy.get("geography")
            },
            "completed_at": datetime.now().isoformat()
        }

        logger.info(
            "AI prospect research completed",
            strategy=strategy_type,
            prospects_found=len(prospects)
        )

        return result
