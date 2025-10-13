"""
AI Research Service - Competitor analysis and SEO research.

This service handles:
1. Fetching top Google results for a topic (via Firecrawl)
2. Scraping competitor content (via Firecrawl)
3. AI-powered SEO analysis of competitors (via OpenAI)

Uses centralized API clients from app.features.core.utils.external_api_clients
"""

from typing import List, Dict, Any, Optional
import httpx

from app.features.core.sqlalchemy_imports import get_logger
from app.features.core.utils.external_api_clients import (
    get_openai_client_from_secret,
    get_firecrawl_client_from_secret,
    OpenAIClient,
    FirecrawlClient
)

logger = get_logger(__name__)


class AIResearchService:
    """
    Service for AI-powered content research and competitor analysis.

    Uses centralized API clients:
    - FirecrawlClient for Google search results and web scraping
    - OpenAIClient for SEO gap analysis

    Benefits:
    - Reusable API clients throughout the app
    - Centralized error handling and logging
    - Clean async interfaces
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

        logger.info("API clients initialized successfully", tenant_id=self.tenant_id)

    async def fetch_google_results(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, str]]:
        """
        Fetch top Google results using Firecrawl's search endpoint.

        Args:
            query: Search query
            num_results: Number of results to fetch

        Returns:
            List of dicts with 'title', 'url', and optionally 'markdown'
        """
        if not self.firecrawl_client:
            raise ValueError("Firecrawl client not initialized. Call _init_clients() first.")

        try:
            results = await self.firecrawl_client.search(
                query=query,
                limit=num_results
            )

            # Normalize result structure
            top_results = []
            for res in results[:num_results]:
                top_results.append({
                    "title": res.get('title', 'No title available'),
                    "url": res.get('url', 'No URL available'),
                    "markdown": res.get('markdown', '')  # Pre-scraped content if available
                })

            # Pad with empty results if needed
            while len(top_results) < num_results:
                top_results.append({
                    "title": "No result found",
                    "url": "N/A",
                    "markdown": ""
                })

            logger.info(
                "Fetched Google results via Firecrawl",
                query=query,
                results_count=len(top_results)
            )

            return top_results[:num_results]

        except Exception as e:
            logger.exception("Failed to fetch Google results", query=query)
            # Return error placeholders
            return [{"title": "Error fetching results", "url": "N/A", "markdown": ""}] * num_results

    async def scrape_article_content(self, url: str) -> str:
        """
        Scrape article content from a URL using Firecrawl.

        Args:
            url: Article URL to scrape

        Returns:
            Extracted article text in markdown format
        """
        if url == "N/A" or not url:
            return "⚠ No valid URL for this search result."

        if not self.firecrawl_client:
            raise ValueError("Firecrawl client not initialized. Call _init_clients() first.")

        try:
            result = await self.firecrawl_client.scrape(
                url=url,
                formats=["markdown"]
            )

            article_text = result.get("markdown", "")

            if len(article_text) > 100:
                logger.info("Successfully scraped article", url=url, length=len(article_text))
                return article_text
            else:
                logger.warning("Could not extract meaningful content", url=url)
                return "⚠ Could not extract meaningful content."

        except Exception as e:
            # Handle specific HTTP errors gracefully
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                if status_code == 403:
                    logger.warning("Site blocked scraping (403 Forbidden)", url=url)
                    return f"⚠ Site blocked scraping: {url}"
                elif status_code == 404:
                    logger.warning("Page not found (404)", url=url)
                    return f"⚠ Page not found: {url}"
                elif status_code == 429:
                    logger.warning("Rate limit exceeded (429)", url=url)
                    return f"⚠ Rate limit exceeded for: {url}"
                else:
                    logger.warning(f"HTTP {status_code} error", url=url)
                    return f"⚠ HTTP {status_code} error: {url}"
            else:
                logger.exception("Failed to scrape article", url=url)
                return f"⚠ Failed to scrape: {url}"

    async def analyze_competitor_seo(
        self,
        combined_content: str
    ) -> str:
        """
        AI-powered SEO analysis of competitor content.

        Args:
            combined_content: Combined text from multiple competitors

        Returns:
            SEO analysis report
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Call _init_clients() first.")

        analysis_prompt = f"""
You are an advanced SEO strategist. Your task is to analyze the following articles and provide a structured SEO analysis.

### **Key SEO Areas to Analyze:**
#### **1. Keyword Optimization**
   - Identify **primary keywords**, **secondary keywords**, and **LSI (related) keywords**.
   - Suggest **long-tail queries** that could help rank in **Google's Featured Snippets**.
   - Compare keyword **density and placement** with top competitors.

#### **2. Content Structure & Readability**
   - Evaluate **H1, H2, H3 hierarchy** for clear sectioning.
   - Suggest **questions that could be H2s/H3s** to improve scannability.
   - Assess **sentence complexity (Flesch-Kincaid Score)** for readability.
   - Identify missing elements like **Table of Contents, jump links, and bulleted lists**.

#### **3. Headers & Schema Markup**
   - Identify whether **FAQ Schema, Recipe Schema, or HowTo Schema** is present.
   - Suggest **Google-approved JSON-LD structured data** improvements.
   - Ensure **Google Discover optimization** (e.g., Web Stories, short-form content).

#### **4. Internal & External Linking**
   - Identify **internal linking gaps** using **topic clusters**.
   - Recommend **external authority links** (e.g., BBC Good Food, AllRecipes).
   - Suggest **anchor text improvements** for better topic relevancy.

#### **5. Engagement & Interactive Elements**
   - Check for **star ratings, comment sections, and polls**.
   - Identify whether **videos, GIFs, or interactive elements** are used.
   - Suggest **ways to improve dwell time and reduce bounce rate**.

#### **6. On-Page SEO Optimization**
   - Assess **meta title & description** for CTR optimization.
   - Check **image alt text** and **file names** (e.g., "cottage_pie_recipe.jpg").
   - Evaluate **canonical tags, structured breadcrumbs, and URL structure**.

---
### **Content to Analyze:**
{combined_content[:10000]}

---
### **Optimization Plan:**
Provide an **actionable improvement plan** covering all six SEO areas above.
- **List specific improvements**, including **example keyword placements**.
- Ensure **recommendations align with Google's ranking factors**.
- Suggest **automation-friendly optimizations** for AI-powered content creation.
"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert SEO strategist."},
                {"role": "user", "content": analysis_prompt}
            ]

            analysis = await self.openai_client.chat_completion(
                messages=messages,
                temperature=0.7
            )

            logger.info(
                "Completed SEO analysis",
                content_length=len(combined_content),
                analysis_length=len(analysis)
            )

            return analysis

        except Exception as e:
            logger.exception("Failed to analyze competitor SEO")
            return f"⚠ Failed to perform SEO analysis: {str(e)}"

    async def process_research(
        self,
        title: str,
        db_session,
        num_results: int = 3,
        accessed_by_user=None
    ) -> Dict[str, Any]:
        """
        Complete research workflow for a content topic.

        Workflow:
        1. Initialize API clients from Secrets Management
        2. Get top Google results via Firecrawl
        3. Scrape competitor content via Firecrawl
        4. Analyze SEO opportunities via OpenAI

        Args:
            title: Content topic to research
            db_session: Database session for secrets retrieval
            num_results: Number of competitors to analyze (default 3)
            accessed_by_user: User accessing secrets (for audit trail)

        Returns:
            Dict with research_data structure:
            {
                "top_results": [...],
                "scraped_content": [...],
                "seo_analysis": "...",
                "keywords_found": [...]
            }

        Raises:
            ValueError: If API clients cannot be initialized
        """
        logger.info("Starting research process", title=title, num_results=num_results)

        # Initialize API clients
        await self._init_clients(db_session, accessed_by_user=accessed_by_user)

        # Fetch Google results using Firecrawl
        top_results = await self.fetch_google_results(
            query=title,
            num_results=num_results
        )

        # Scrape competitor content (use pre-fetched markdown if available, otherwise scrape)
        scraped_content = []
        for idx, result in enumerate(top_results, start=1):
            url = result["url"]

            # Check if Firecrawl already provided markdown content
            if result.get("markdown") and len(result["markdown"]) > 100:
                logger.info(f"Using pre-scraped content for competitor {idx}", url=url)
                content = result["markdown"]
            else:
                logger.info(f"Scraping competitor {idx} via Firecrawl", url=url)
                content = await self.scrape_article_content(url=url)

            scraped_content.append({
                "index": idx,
                "title": result["title"],
                "url": url,
                "content": content,
                "content_length": len(content)
            })

        # Combine content for analysis
        combined_content = "\n\n---\n\n".join([
            f"Source {item['index']}: {item['title']}\n\n{item['content']}"
            for item in scraped_content
        ])

        # Perform SEO analysis
        seo_analysis = await self.analyze_competitor_seo(
            combined_content=combined_content
        )

        # Build research data structure
        research_data = {
            "top_results": top_results,
            "scraped_content": scraped_content,
            "seo_analysis": seo_analysis,
            "keywords_found": [],  # TODO: Extract keywords from analysis
            "research_completed_at": None,  # Will be set by caller
        }

        logger.info(
            "Research completed",
            title=title,
            competitors_analyzed=len(scraped_content),
            analysis_length=len(seo_analysis)
        )

        return research_data
