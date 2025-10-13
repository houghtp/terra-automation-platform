"""
AI Generation Service - OpenAI-powered content creation.

This service handles:
1. Generating SEO-optimized blog posts
2. Creating per-channel content variants
3. Iterative content refinement based on feedback

Ported from SEO Blog Generator.py (lines 163-246)
"""

from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class AIGenerationService:
    """
    Service for AI-powered content generation using OpenAI.

    Uses GPT-4 for high-quality, SEO-optimized content creation.
    """

    def __init__(self):
        """Initialize generation service."""
        pass

    async def generate_blog_post(
        self,
        title: str,
        openai_api_key: str,
        description: Optional[str] = None,
        target_audience: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        seo_analysis: Optional[str] = None,
        previous_content: Optional[str] = None,
        validation_feedback: Optional[str] = None,
        tone: str = "professional"
    ) -> str:
        """
        Generate SEO-optimized blog post using AI.

        Args:
            title: Blog post title/topic
            openai_api_key: OpenAI API key
            description: Additional context/instructions (optional)
            target_audience: Target audience description (optional)
            keywords: User-provided keywords (optional)
            seo_analysis: SEO analysis from competitor research (optional - for research mode)
            previous_content: Previous version to improve (optional)
            validation_feedback: Feedback from validation (optional)
            tone: Writing tone (default: "professional")

        Returns:
            Generated blog post content

        Ported from SEO Blog Generator.py (lines 163-246)
        """
        # Build context section based on available information
        context_section = f"Title: {title}\n\n"

        if description:
            context_section += f"**Additional Context:**\n{description}\n\n"

        if target_audience:
            context_section += f"**Target Audience:** {target_audience}\n\n"

        if keywords:
            context_section += f"**Focus Keywords:** {', '.join(keywords)}\n\n"

        blog_prompt = f"""
{context_section}

You are an **expert SEO blog writer**. Your task is to produce a complete, ready-to-publish blog post that is 100% SEO optimized for the topic provided by the title above{', using the latest SEO analysis and competitor insights' if seo_analysis else ' using best SEO practices and the provided context'}.

Please ensure that:
- The content is entirely on-topic and directly relevant to the title: "{title}".
- You generate detailed, actionable content with real-world advice, concrete steps, and measurable recommendations that a reader can immediately apply.
- The output is a fully written blog post, not just a list of suggestions or improvement tips.
- If there is any previous blog post content provided, retain and enhance its good elements while fixing only the identified SEO issues.
- Follow the mandatory SEO enhancements strictly to improve keyword optimization, content structure, schema markup, linking, engagement elements, and on-page/mobile SEO without removing any previous improvements.

---
{f'''### **SEO Analysis (Competitor Research):**
{seo_analysis}

---''' if seo_analysis else ''}

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
- **Use a {tone} tone.**
- **Avoid jargon and complex terms.**
- **Make it easy to read and understand.**
- **Use a conversational style.**
"""

        try:
            client = AsyncOpenAI(api_key=openai_api_key)

            logger.info(
                "Generating blog post",
                title=title,
                has_previous=bool(previous_content),
                has_feedback=bool(validation_feedback)
            )

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": blog_prompt}],
                temperature=0.7
            )

            content = response.choices[0].message.content

            logger.info(
                "Blog post generated",
                title=title,
                content_length=len(content),
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None
            )

            return content

        except Exception as e:
            logger.error(f"Failed to generate blog post: {e}", title=title)
            raise ValueError(f"Content generation failed: {str(e)}")

    async def generate_variants_per_channel(
        self,
        content: str,
        title: str,
        channels: List[str],
        openai_api_key: str
    ) -> List[Dict[str, Any]]:
        """
        Generate channel-specific content variants.

        Args:
            content: Base content to adapt
            title: Content title
            channels: List of channel keys (e.g., ["twitter", "linkedin", "wordpress"])
            openai_api_key: OpenAI API key

        Returns:
            List of variant dicts with 'channel', 'body', 'metadata'
        """
        # Channel-specific constraints
        channel_constraints = {
            "twitter": {
                "max_chars": 280,
                "format": "plain text",
                "tone": "casual and engaging",
                "instructions": "Create a compelling tweet with hashtags"
            },
            "linkedin": {
                "max_chars": 3000,
                "format": "professional text with line breaks",
                "tone": "professional and insightful",
                "instructions": "Create a LinkedIn post that sparks professional discussion"
            },
            "wordpress": {
                "max_chars": None,
                "format": "HTML with proper headings",
                "tone": "informative and comprehensive",
                "instructions": "Full blog post with proper HTML structure"
            },
            "medium": {
                "max_chars": None,
                "format": "Markdown",
                "tone": "storytelling and engaging",
                "instructions": "Medium-style article with narrative flow"
            },
            "facebook": {
                "max_chars": 63206,
                "format": "plain text with emoji",
                "tone": "friendly and conversational",
                "instructions": "Engaging Facebook post with call-to-action"
            }
        }

        variants = []

        for channel in channels:
            constraints = channel_constraints.get(channel, {
                "max_chars": 1000,
                "format": "plain text",
                "tone": "professional",
                "instructions": f"Adapt content for {channel}"
            })

            variant_prompt = f"""
You are a content adaptation specialist. Your task is to adapt the following content for {channel}.

**Original Content:**
Title: {title}

{content[:2000]}

**Channel: {channel.upper()}**
**Constraints:**
- Maximum characters: {constraints['max_chars'] or 'No limit'}
- Format: {constraints['format']}
- Tone: {constraints['tone']}

**Instructions:**
{constraints['instructions']}

**Requirements:**
- Adapt the key message from the original content
- Follow the character limit strictly
- Use appropriate formatting for the channel
- Maintain the core value proposition
- Make it engaging and platform-appropriate

Generate ONLY the adapted content, no explanations.
"""

            try:
                client = AsyncOpenAI(api_key=openai_api_key)

                response = await client.chat.completions.create(
                    model="gpt-4o-mini",  # Use mini for variants (cost optimization)
                    messages=[{"role": "user", "content": variant_prompt}],
                    temperature=0.7
                )

                variant_body = response.choices[0].message.content.strip()

                # Build metadata
                variant_metadata = {
                    "char_count": len(variant_body),
                    "max_chars": constraints.get("max_chars"),
                    "format": constraints["format"],
                    "tone": constraints["tone"],
                    "truncated": False
                }

                # Truncate if needed
                if constraints["max_chars"] and len(variant_body) > constraints["max_chars"]:
                    variant_body = variant_body[:constraints["max_chars"] - 3] + "..."
                    variant_metadata["truncated"] = True

                variants.append({
                    "channel": channel,
                    "body": variant_body,
                    "variant_metadata": variant_metadata
                })

                logger.info(
                    "Generated channel variant",
                    channel=channel,
                    char_count=len(variant_body),
                    truncated=variant_metadata["truncated"]
                )

            except Exception as e:
                logger.error(f"Failed to generate variant for {channel}: {e}")
                # Continue with other channels even if one fails
                continue

        return variants

    async def get_generation_metadata(
        self,
        response_data: Any
    ) -> Dict[str, Any]:
        """
        Extract generation metadata from OpenAI response.

        Args:
            response_data: OpenAI API response object

        Returns:
            Dict with metadata (model, tokens, cost estimate)
        """
        metadata = {
            "model": getattr(response_data, "model", "unknown"),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_estimate": 0.0
        }

        if hasattr(response_data, "usage") and response_data.usage:
            usage = response_data.usage
            metadata["prompt_tokens"] = usage.prompt_tokens
            metadata["completion_tokens"] = usage.completion_tokens
            metadata["total_tokens"] = usage.total_tokens

            # Cost estimation (approximate, as of 2024)
            # GPT-4: $0.03/1K prompt tokens, $0.06/1K completion tokens
            # GPT-4o-mini: $0.00015/1K prompt tokens, $0.0006/1K completion tokens
            if "gpt-4" in metadata["model"].lower():
                if "mini" in metadata["model"].lower():
                    cost = (usage.prompt_tokens * 0.00015 / 1000) + \
                           (usage.completion_tokens * 0.0006 / 1000)
                else:
                    cost = (usage.prompt_tokens * 0.03 / 1000) + \
                           (usage.completion_tokens * 0.06 / 1000)
                metadata["cost_estimate"] = round(cost, 4)

        return metadata
