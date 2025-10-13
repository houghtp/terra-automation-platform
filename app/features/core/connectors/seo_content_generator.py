"""
SEO Content Generation Automation Service.

This service replicates the functionality of your original content creation script
but integrates with our connector infrastructure and Content Broadcaster system.
"""

import asyncio
import json
import structlog
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ...business_automations.content_broadcaster.models import ContentItem, ContentState, ApprovalStatus
from ...business_automations.content_broadcaster.services import ContentBroadcasterService
from ...connectors.connectors.services import ConnectorService
from .web_scraping import SearchScraper, WebScraper

logger = structlog.get_logger(__name__)


class SEOContentGenerationError(Exception):
    """SEO content generation specific error."""
    pass


class SEOContentGenerator:
    """
    SEO-optimized content generation using multiple AI providers.

    Replicates your original script functionality:
    1. Search for competitor content
    2. Scrape and analyze competitor articles
    3. Generate SEO-optimized content using AI
    4. Validate content quality with AI scoring
    5. Iterate until quality threshold is met
    6. Save to Content Broadcaster for review/approval
    """

    def __init__(self, tenant_id: str = "global"):
        """
        Initialize SEO content generator.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
        """
        self.tenant_id = tenant_id
        # Note: connector_service will be initialized with db session when needed
        self.connector_service = None
        self.content_service = ContentBroadcasterService()
        self.search_scraper = SearchScraper(tenant_id)
        self.web_scraper = WebScraper(tenant_id)

        # Content generation settings
        self.min_seo_score = 95  # Minimum SEO score to accept
        self.max_iterations = 3  # Max refinement iterations

    async def generate_content_from_title(
        self,
        title: str,
        created_by: str,
        db_session: Optional[AsyncSession] = None,
        ai_provider: str = "openai",
        fallback_ai: Optional[str] = "anthropic",
        search_provider: str = "serpapi",
        scraping_provider: str = "firecrawl",
        progress_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], Awaitable[None]]] = None
    ) -> ContentItem:
        """
        Generate SEO-optimized content from a title.

        This is the main entry point that replicates your script's workflow.

        Args:
            title: Content title/topic to generate content for
            created_by: User ID who requested the content
            db_session: Optional AsyncSession if caller already has one
            ai_provider: Primary AI provider for content generation
            fallback_ai: Fallback AI provider if primary fails
            search_provider: Search service for competitor research
            scraping_provider: Web scraping service for content extraction
            progress_callback: Optional coroutine for streaming progress updates

        Returns:
            ContentItem saved to database for review/approval
        """
        if db_session is not None:
            return await self._generate_with_session(
                db_session=db_session,
                title=title,
                created_by=created_by,
                ai_provider=ai_provider,
                fallback_ai=fallback_ai,
                search_provider=search_provider,
                scraping_provider=scraping_provider,
                progress_callback=progress_callback
            )

        async with get_async_session() as session:
            return await self._generate_with_session(
                db_session=session,
                title=title,
                created_by=created_by,
                ai_provider=ai_provider,
                fallback_ai=fallback_ai,
                search_provider=search_provider,
                scraping_provider=scraping_provider,
                progress_callback=progress_callback
            )

    async def _generate_with_session(
        self,
        db_session: AsyncSession,
        title: str,
        created_by: str,
        ai_provider: str,
        fallback_ai: Optional[str],
        search_provider: str,
        scraping_provider: str,
        progress_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], Awaitable[None]]]
    ) -> ContentItem:
        async def emit(stage: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
            if progress_callback:
                await progress_callback(stage, message, data or {})

        try:
            logger.info(f"Starting SEO content generation for: '{title}'")
            await emit("start", f"Starting SEO content generation for '{title}'.")

            # Initialize connector service with database session and tenant
            self.connector_service = ConnectorService(db_session, self.tenant_id)

            # Step 1: Research competitor content
            await emit("research.start", "Researching competitor content...")
            competitor_data = await self._research_competitors(title, search_provider, scraping_provider)
            await emit(
                "research.complete",
                "Competitor research completed.",
                {"sources": len(competitor_data)}
            )

            # Step 2: Analyze competitor content for SEO insights
            await emit("analysis.start", "Analyzing competitor SEO insights...")
            seo_analysis = await self._analyze_competitor_content(competitor_data, ai_provider, fallback_ai)
            await emit("analysis.complete", "SEO analysis ready.")

            # Step 3: Generate initial content
            await emit("generation.start", "Generating initial draft...")
            blog_content = await self._generate_initial_content(title, seo_analysis, ai_provider, fallback_ai)
            await emit(
                "generation.draft_ready",
                "Initial draft generated.",
                {"content_length": len(blog_content)}
            )

            # Step 4: Iterative quality improvement
            final_content, final_score = await self._improve_content_quality(
                title,
                blog_content,
                seo_analysis,
                ai_provider,
                fallback_ai,
                progress_callback=progress_callback
            )
            await emit(
                "quality.complete",
                "SEO quality validation complete.",
                {"seo_score": final_score}
            )

            # Step 5: Save to Content Broadcaster for review
            await emit("saving.start", "Saving generated content to Content Broadcaster...")
            content_item = await self._save_to_content_broadcaster(
                title=title,
                content=final_content,
                created_by=created_by,
                metadata={
                    "seo_score": final_score,
                    "ai_provider": ai_provider,
                    "fallback_ai": fallback_ai,
                    "search_provider": search_provider,
                    "scraping_provider": scraping_provider,
                    "competitor_research": competitor_data,
                    "generation_type": "seo_optimized"
                }
            )
            await emit(
                "saving.complete",
                "Content saved and ready for review.",
                {"content_id": content_item.id, "seo_score": final_score}
            )

            logger.info(f"Content generation completed for '{title}' with SEO score: {final_score}")
            return content_item

        except Exception as e:
            await emit("error", f"Content generation failed: {str(e)}")
            logger.error(f"Content generation failed for '{title}': {str(e)}")
            raise SEOContentGenerationError(f"Content generation failed: {str(e)}")

    async def _research_competitors(
        self,
        title: str,
        search_provider: str,
        scraping_provider: str
    ) -> List[Dict[str, Any]]:
        """
        Research competitor content for a given title.

        Args:
            title: Topic to research
            search_provider: Search service to use
            scraping_provider: Scraping service to use

        Returns:
            List of competitor data with content and metadata
        """
        try:
            logger.info(f"Researching competitors for: '{title}'")

            # Get top search results
            search_results = await self.search_scraper.get_top_google_results(
                query=title,
                num_results=3,  # Limit to top 3 for quality analysis
                preferred_service=search_provider
            )

            competitor_data = []

            # Scrape each competitor article
            for idx, result in enumerate(search_results, 1):
                try:
                    logger.info(f"Scraping competitor {idx}: {result['url']}")

                    content = await self.web_scraper.scrape_article(
                        url=result['url'],
                        preferred_service=scraping_provider
                    )

                    competitor_data.append({
                        "position": idx,
                        "title": result['title'],
                        "url": result['url'],
                        "snippet": result.get('snippet', ''),
                        "content": content,
                        "scraped_at": datetime.now(timezone.utc).isoformat()
                    })

                except Exception as e:
                    logger.warning(f"Failed to scrape competitor {idx}: {str(e)}")
                    competitor_data.append({
                        "position": idx,
                        "title": result['title'],
                        "url": result['url'],
                        "snippet": result.get('snippet', ''),
                        "content": f"⚠ Failed to scrape: {str(e)}",
                        "scraped_at": datetime.now(timezone.utc).isoformat()
                    })

            logger.info(f"Completed competitor research with {len(competitor_data)} sources")
            return competitor_data

        except Exception as e:
            logger.error(f"Competitor research failed: {str(e)}")
            raise SEOContentGenerationError(f"Competitor research failed: {str(e)}")

    async def _analyze_competitor_content(
        self,
        competitor_data: List[Dict[str, Any]],
        ai_provider: str,
        fallback_ai: Optional[str]
    ) -> str:
        """
        Analyze competitor content for SEO insights.

        This replicates your analyze_competitor_content function.

        Args:
            competitor_data: List of competitor content data
            ai_provider: Primary AI provider
            fallback_ai: Fallback AI provider

        Returns:
            SEO analysis text
        """
        try:
            # Combine all competitor content
            combined_content = "\n\n".join([
                f"=== Competitor {data['position']}: {data['title']} ===\n{data['content']}"
                for data in competitor_data
                if data['content'] and not data['content'].startswith("⚠")
            ])

            # Your original analysis prompt
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
{combined_content}

### **Optimization Plan:**
Provide an **actionable improvement plan** covering all six SEO areas above.
- **List specific improvements**, including **example keyword placements**.
- Ensure **recommendations align with Google's ranking factors**.
- Suggest **automation-friendly optimizations** for AI-powered content creation.
"""

            # Get AI analysis
            ai_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                connector_type=ai_provider,
                tenant_id=self.tenant_id
            )

            try:
                if hasattr(ai_connector, 'chat_completion'):
                    response = await ai_connector.chat_completion(
                        messages=[
                            {"role": "system", "content": "You are an expert SEO strategist."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=0.7
                    )

                    if isinstance(response, dict) and 'content' in response:
                        return response['content']
                    return str(response)

            except Exception as e:
                logger.warning(f"Primary AI provider {ai_provider} failed: {str(e)}")
                if fallback_ai:
                    logger.info(f"Trying fallback AI provider: {fallback_ai}")
                    fallback_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                        connector_type=fallback_ai,
                        tenant_id=self.tenant_id
                    )

                    if hasattr(fallback_connector, 'chat_completion'):
                        response = await fallback_connector.chat_completion(
                            messages=[
                                {"role": "system", "content": "You are an expert SEO strategist."},
                                {"role": "user", "content": analysis_prompt}
                            ],
                            temperature=0.7
                        )

                        if isinstance(response, dict) and 'content' in response:
                            return response['content']
                        return str(response)

                raise e

        except Exception as e:
            logger.error(f"Competitor content analysis failed: {str(e)}")
            raise SEOContentGenerationError(f"Content analysis failed: {str(e)}")

    async def _generate_initial_content(
        self,
        title: str,
        seo_analysis: str,
        ai_provider: str,
        fallback_ai: Optional[str],
        previous_content: Optional[str] = None,
        validation_feedback: Optional[str] = None
    ) -> str:
        """
        Generate blog content using AI.

        This replicates your generate_blog_post function.

        Args:
            title: Content title
            seo_analysis: SEO analysis from competitor research
            ai_provider: Primary AI provider
            fallback_ai: Fallback AI provider
            previous_content: Previous version for iteration
            validation_feedback: Feedback for improvement

        Returns:
            Generated blog content
        """
        try:
            # Your original blog generation prompt
            blog_prompt = f"""
Title: {title}

You are an **expert SEO blog writer**. Your task is to produce a complete, ready-to-publish blog post that is 100% SEO optimized for the topic provided by the title above, using the latest SEO analysis and the provided validation feedback.

Please ensure that:
- The content is entirely on-topic and directly relevant to the title: "{title}".
- You generate detailed, actionable content with real-world advice, concrete steps, and measurable recommendations that a reader can immediately apply.
- The output is a fully written blog post, not just a list of suggestions or improvement tips.
- If there is any previous blog post content provided, retain and enhance its good elements while fixing only the identified SEO issues.
- Follow the mandatory SEO enhancements strictly to improve keyword optimization, content structure, schema markup, linking, engagement elements, and on-page/mobile SEO without removing any previous improvements.

---
### **SEO Analysis:**
{seo_analysis}

---
### **Previous Blog Post (Use this as the base and improve it)**
{previous_content if previous_content else "No previous version, this is the first draft."}

---
### **Validation Feedback (Fix these SEO issues only)**
{validation_feedback if validation_feedback else "No feedback yet. Optimize based on SEO best practices."}

---
## **Mandatory SEO Enhancements**
To **outperform competitors**, improve the blog using these advanced SEO tactics:

✅ **1. Keyword Optimization**
   - Ensure **primary and secondary keywords** are in **title, intro, headings, and alt text**.
   - Use **long-tail keyword variations** for **Google Featured Snippets**.
   - Maintain **proper keyword density** (avoid stuffing).
   - Integrate **LSI keywords** naturally.

✅ **2. Content Structure & Readability**
   - Follow an **H1 → H2 → H3 hierarchy**.
   - Add a **Table of Contents with jump links**.
   - Use **short paragraphs (2-3 sentences max) for scannability**.
   - Improve readability using **bulleted lists, numbered steps, key takeaways**.

✅ **3. Schema Markup & Metadata**
   - Implement **FAQ Schema, Recipe Schema, and HowTo Schema**.
   - Ensure **Google Discover best practices** for mobile-first ranking.
   - Add **Pinterest & Facebook metadata** for better social sharing.
   - Optimize **meta title and description (160 chars max, keyword-rich)**.

✅ **4. Internal & External Linking**
   - Add **3+ internal links** to related content.
   - Include **2+ external links** to authoritative sources (BBC Good Food, etc.).
   - Use **keyword-rich anchor text**.

✅ **5. Engagement & Interactive Elements**
   - Include **star ratings, polls, or interactive content**.
   - Add an **FAQ section** to capture **voice search & People Also Ask queries**.
   - Encourage user interaction (comments, sharing).
   - Embed **images, videos, or step-by-step visuals**.

✅ **6. On-Page SEO & Mobile Friendliness**
   - Ensure **title tag is compelling and keyword-rich**.
   - Optimize **image alt text** with **SEO-friendly filenames**.
   - Ensure the blog is **fast-loading & mobile-friendly (Core Web Vitals)**.
   - Implement **canonical tags to prevent duplicate content issues**.

---
- **Now, using the title "{title}" improve this blog post for maximum SEO performance.**
- **Produce a complete and cohesive blog post that is fully optimized for SEO and ready for immediate publication.**
- **Do not generate generic suggestions—deliver a finished blog post with all required content.**
- **Fix ONLY the missing SEO elements.**
- **Retain good elements from the previous version.**
- **Do not remove previous improvements.**
- **Make it engaging, informative, and actionable.**
- **Use a friendly and approachable tone.**
- **Avoid jargon and complex terms.**
- **Make it easy to read and understand.**
- **Use a conversational style.**
- **Use emojis to enhance engagement.**
"""

            # Get AI content generation
            ai_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                connector_type=ai_provider,
                tenant_id=self.tenant_id
            )

            try:
                if hasattr(ai_connector, 'chat_completion'):
                    response = await ai_connector.chat_completion(
                        messages=[{"role": "user", "content": blog_prompt}],
                        temperature=0.7
                    )

                    if isinstance(response, dict) and 'content' in response:
                        return response['content']
                    return str(response)

            except Exception as e:
                logger.warning(f"Primary AI provider {ai_provider} failed: {str(e)}")
                if fallback_ai:
                    logger.info(f"Trying fallback AI provider: {fallback_ai}")
                    fallback_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                        connector_type=fallback_ai,
                        tenant_id=self.tenant_id
                    )

                    if hasattr(fallback_connector, 'chat_completion'):
                        response = await fallback_connector.chat_completion(
                            messages=[{"role": "user", "content": blog_prompt}],
                            temperature=0.7
                        )

                        if isinstance(response, dict) and 'content' in response:
                            return response['content']
                        return str(response)

                raise e

        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise SEOContentGenerationError(f"Content generation failed: {str(e)}")

    async def _validate_content_quality(
        self,
        title: str,
        content: str,
        ai_provider: str,
        fallback_ai: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate blog content quality and SEO score.

        This replicates your validate_blog_post function.

        Args:
            title: Content title
            content: Blog content to validate
            ai_provider: Primary AI provider
            fallback_ai: Fallback AI provider

        Returns:
            Validation result with score and recommendations
        """
        try:
            # Your original validation prompt
            validation_prompt = f"""
You are an **SEO quality control specialist** and **Google ranking expert**. Your task is to analyze the blog post below and assign an SEO **score from 0 to 100** based on compliance with key ranking factors.

### **Scoring Criteria (Total: 100 Points)**
✅ **1. Keyword Optimization (20 points)**
   - Are **primary and secondary keywords** naturally integrated into the **title, introduction, subheadings, and body text**?
   - Are **long-tail keyword variations** used effectively for **featured snippets**?
   - Does the blog avoid **keyword stuffing** while maintaining **optimal keyword density**?

✅ **2. Content Structure & Readability (15 points)**
   - Is the **H1, H2, and H3 hierarchy** correctly structured?
   - Does the blog include a **Table of Contents (TOC) with jump links** for better UX and Google crawling?
   - Are **paragraphs short and easy to skim** (2-3 sentences per paragraph)?
   - Are there **bulleted lists, numbered steps, and key takeaways** to enhance readability?

✅ **3. Schema Markup & Metadata (15 points)**
   - Does the blog **implement structured data (FAQ Schema, Recipe Schema, HowTo Schema, or JSON-LD)?**
   - Is the **meta title and meta description optimized for Google CTR** (contains target keywords & a CTA)?
   - Are **alt text and image file names optimized** for **Google Image Search**?
   - Does the blog have **Pinterest & Facebook metadata** for **social media sharing**?

✅ **4. Internal & External Links (15 points)**
   - Does the blog contain **at least 3 internal links** to related content for **topic authority**?
   - Are there **2+ external links** to **high-authority sources** (e.g., BBC Good Food, AllRecipes)?
   - Are the **internal & external links using descriptive, keyword-rich anchor text**?
   - Does the blog have **structured breadcrumbs** to improve crawlability?

✅ **5. Engagement & Interactive Elements (15 points)**
   - Does the blog include a **star rating system, voting, or poll** to increase CTR?
   - Is there an **FAQ section** to capture **voice search & "People Also Ask" queries**?
   - Does the blog **encourage user interaction** (e.g., comment section, share prompts)?
   - Does it include **interactive elements like videos, step-by-step images, or GIFs**?

✅ **6. On-Page SEO & Mobile Friendliness (20 points)**
   - Is the **title tag compelling, keyword-rich, and formatted for higher CTR**?
   - Is the **meta description under 160 characters with a strong call-to-action**?
   - Does the blog meet **Google Core Web Vitals** for fast loading and mobile-friendliness?
   - Are all **canonical tags properly set up** to prevent duplicate content issues?

---

### **Blog Content to Analyze:**
{content}

---
### **Final Evaluation (Return as JSON Output)**

1️⃣ **Assign a numerical SEO Score (0-100).**
2️⃣ **If the score is <95, return "FAIL" with missing SEO elements.**
3️⃣ **If the score is >=95, return "PASS".**
4️⃣ **Format response as JSON:**

{{
   "title": "{title}",
   "score": 85,
   "status": "FAIL",
   "issues": ["Schema Markup", "Engagement"],
   "recommendations": {{
       "Schema Markup": {{ "issue": "...", "fix": "..." }},
       "Engagement": {{ "issue": "...", "fix": "..." }}
   }}
}}
"""

            # Get AI validation
            ai_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                connector_type=ai_provider,
                tenant_id=self.tenant_id
            )

            try:
                if hasattr(ai_connector, 'chat_completion'):
                    response = await ai_connector.chat_completion(
                        messages=[{"role": "user", "content": validation_prompt}],
                        temperature=0.3  # Lower temperature for consistent scoring
                    )

                    response_text = response['content'] if isinstance(response, dict) else str(response)

                    # Clean and parse JSON response
                    return self._parse_validation_response(response_text, title)

            except Exception as e:
                logger.warning(f"Primary AI validation failed: {str(e)}")
                if fallback_ai:
                    logger.info(f"Trying fallback AI for validation")
                    fallback_connector = await self.connector_service.create_sdk_connector_instance_by_type(
                        connector_type=fallback_ai,
                        tenant_id=self.tenant_id
                    )

                    if hasattr(fallback_connector, 'chat_completion'):
                        response = await fallback_connector.chat_completion(
                            messages=[{"role": "user", "content": validation_prompt}],
                            temperature=0.3
                        )

                        response_text = response['content'] if isinstance(response, dict) else str(response)
                        return self._parse_validation_response(response_text, title)

                raise e

        except Exception as e:
            logger.error(f"Content validation failed: {str(e)}")
            # Return default failure response
            return {
                "title": title,
                "score": 0,
                "status": "ERROR",
                "issues": ["Validation failed"],
                "recommendations": {},
                "error": str(e)
            }

    def _parse_validation_response(self, response_text: str, title: str) -> Dict[str, Any]:
        """
        Parse AI validation response into structured format.

        Args:
            response_text: Raw AI response
            title: Content title

        Returns:
            Parsed validation result
        """
        try:
            # Remove markdown formatting if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            # Parse JSON
            validation_result = json.loads(response_text.strip())

            # Ensure required fields exist
            if "score" not in validation_result:
                logger.warning("Missing 'score' field in validation response")
                validation_result["score"] = 0

            if "status" not in validation_result:
                validation_result["status"] = "PASS" if validation_result["score"] >= 95 else "FAIL"

            return validation_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation JSON: {str(e)}")
            return {
                "title": title,
                "score": 0,
                "status": "ERROR",
                "issues": ["JSON parsing error"],
                "recommendations": {},
                "raw_response": response_text
            }

    async def _improve_content_quality(
        self,
        title: str,
        initial_content: str,
        seo_analysis: str,
        ai_provider: str,
        fallback_ai: Optional[str],
        progress_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], Awaitable[None]]] = None
    ) -> Tuple[str, int]:
        """
        Iteratively improve content quality until SEO score threshold is met.

        Args:
            title: Content title
            initial_content: Initial generated content
            seo_analysis: SEO analysis from competitor research
            ai_provider: Primary AI provider
            fallback_ai: Fallback AI provider

        Returns:
            Tuple of (final_content, final_score)
        """
        async def emit(stage: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
            if progress_callback:
                await progress_callback(stage, message, data or {})

        current_content = initial_content
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Content quality iteration {iteration} for '{title}'")
            await emit(
                "quality.iteration_start",
                f"Running SEO validation iteration {iteration}...",
                {"iteration": iteration}
            )

            # Validate current content
            validation_result = await self._validate_content_quality(
                title, current_content, ai_provider, fallback_ai
            )

            score = validation_result.get("score", 0)
            status = validation_result.get("status", "FAIL")

            logger.info(f"Content score: {score}/100, Status: {status}")
            await emit(
                "quality.validation_result",
                f"Iteration {iteration} scored {score}/100 ({status}).",
                {
                    "iteration": iteration,
                    "score": score,
                    "status": status,
                    "issues": validation_result.get("issues"),
                }
            )

            # Check if quality threshold is met
            if score >= self.min_seo_score or status == "PASS":
                logger.info(f"Quality threshold met after {iteration} iterations")
                await emit(
                    "quality.threshold_met",
                    f"SEO score target met after {iteration} iterations.",
                    {"iteration": iteration, "score": score, "status": status}
                )
                return current_content, score

            # Generate improved content if score is too low
            if iteration < self.max_iterations:
                logger.info(f"Improving content (score: {score}/{self.min_seo_score})")
                await emit(
                    "quality.refine",
                    f"Refining content for iteration {iteration + 1}...",
                    {
                        "iteration": iteration,
                        "score": score,
                        "remaining_iterations": self.max_iterations - iteration
                    }
                )
                validation_feedback = json.dumps(validation_result, indent=2)
                improved_content = await self._generate_initial_content(
                    title=title,
                    seo_analysis=seo_analysis,
                    ai_provider=ai_provider,
                    fallback_ai=fallback_ai,
                    previous_content=current_content,
                    validation_feedback=validation_feedback
                )

                current_content = improved_content
            else:
                logger.warning(f"Max iterations reached, accepting content with score: {score}")
                await emit(
                    "quality.max_iterations",
                    "Max iterations reached. Accepting current content.",
                    {"iteration": iteration, "score": score}
                )
                return current_content, score

        # Final validation
        final_validation = await self._validate_content_quality(
            title, current_content, ai_provider, fallback_ai
        )
        final_score = final_validation.get("score", score)
        await emit(
            "quality.final_validation",
            "Completed final SEO validation.",
            {"score": final_score}
        )

        return current_content, final_score

    async def _save_to_content_broadcaster(
        self,
        title: str,
        content: str,
        created_by: str,
        metadata: Dict[str, Any]
    ) -> ContentItem:
        """
        Save generated content to Content Broadcaster for review/approval.

        Args:
            title: Content title
            content: Generated content
            created_by: User ID who requested the content
            metadata: Additional metadata about the generation process

        Returns:
            Created ContentItem
        """
        try:
            async with get_async_session() as session:
                content_item = ContentItem(
                    id=str(uuid4()),
                    tenant_id=self.tenant_id,
                    title=title,
                    body=content,
                    state=ContentState.IN_REVIEW.value,
                    approval_status=ApprovalStatus.PENDING.value,
                    created_by=created_by,
                    content_metadata=metadata,
                    tags=["ai-generated", "seo-optimized", "pending-review"]
                )

                session.add(content_item)
                await session.commit()
                await session.refresh(content_item)

                logger.info(f"Saved content to Content Broadcaster: {content_item.id}")
                return content_item

        except Exception as e:
            logger.error(f"Failed to save content to Content Broadcaster: {str(e)}")
            raise SEOContentGenerationError(f"Failed to save content: {str(e)}")


# Factory function for automation templates
async def create_seo_content_generator(
    tenant_id: str = "global",
    **config
) -> SEOContentGenerator:
    """
    Factory function to create SEO content generator.

    Args:
        tenant_id: Tenant ID for multi-tenant isolation
        **config: Additional configuration

    Returns:
        Configured SEOContentGenerator instance
    """
    generator = SEOContentGenerator(tenant_id)

    # Apply configuration overrides
    if "min_seo_score" in config:
        generator.min_seo_score = config["min_seo_score"]
    if "max_iterations" in config:
        generator.max_iterations = config["max_iterations"]

    return generator
