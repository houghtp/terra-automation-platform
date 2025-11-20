"""
AI Generation Service - OpenAI-powered content creation.

This service handles:
1. Generating SEO-optimized blog posts
2. Creating per-channel content variants
3. Iterative content refinement based on feedback

Ported from SEO Blog Generator.py (lines 163-246)
"""

import json
from typing import Optional, Dict, Any, List
from jinja2 import Template
from openai import AsyncOpenAI, AuthenticationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.sqlalchemy_imports import get_logger
from app.features.administration.ai_prompts.services import AIPromptService
from .prompt_templates import PROMPT_DEFAULTS

logger = get_logger(__name__)


class AIGenerationService:
    """
    Service for AI-powered content generation using OpenAI.

    Uses GPT-4 for high-quality, SEO-optimized content creation.
    Now uses dynamic AI prompts from database with Jinja2 templates.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str = "global"):
        """
        Initialize generation service.

        Args:
            db_session: Database session for fetching prompts
            tenant_id: Tenant ID for tenant-specific prompt overrides
        """
        self.db = db_session
        self.tenant_id = tenant_id
        self.prompt_service = AIPromptService(db_session)

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
        tone: str = "professional",
        prompt_settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate SEO-optimized blog post using AI with dynamic prompts from database.

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

        Now uses dynamic AI prompts from database with Jinja2 templates.
        """
        try:
            prompt_settings = prompt_settings or {}

            await self.prompt_service.ensure_system_prompt(
                "seo_blog_generation",
                PROMPT_DEFAULTS["seo_blog_generation"]
            )

            # Prepare variables for Jinja2 template rendering
            variables = {
                "title": title,
                "description": description or "",
                "target_audience": target_audience or "general readers",
                "keywords": ", ".join(keywords) if keywords else "",
                "seo_analysis": seo_analysis or "",
                "previous_content": previous_content or "No previous version, this is the first draft.",
                "validation_feedback": validation_feedback or "No feedback yet. Optimize based on SEO best practices.",
                "tone": tone,
                "has_seo_analysis": bool(seo_analysis),
                "has_description": bool(description),
                "has_target_audience": bool(target_audience),
                "has_keywords": bool(keywords),
                "professionalism_level": prompt_settings.get("professionalism_level", 4),
                "humor_level": prompt_settings.get("humor_level", 1),
                "creativity_level": prompt_settings.get("creativity_level", 3),
            }

            # Fetch and render prompt from database
            blog_prompt = await self.prompt_service.render_prompt(
                prompt_key="seo_blog_generation",
                variables=variables,
                tenant_id=self.tenant_id,
                track_usage=True
            )

            if not blog_prompt:
                logger.error("Failed to load prompt 'seo_blog_generation' from database")
                blog_prompt = Template(
                    PROMPT_DEFAULTS["seo_blog_generation"]["prompt_template"]
                ).render(**variables)

            logger.info(
                "Generating blog post with dynamic prompt",
                title=title,
                has_previous=bool(previous_content),
                has_feedback=bool(validation_feedback),
                prompt_length=len(blog_prompt)
            )

            # === COMMENTED OUT: Original hardcoded prompt ===
            # blog_prompt = f"""
            # Title: {title}
            #
            # You are an **expert SEO blog writer**. Your task is to produce a complete, ready-to-publish blog post...
            # [Full hardcoded prompt preserved as comment for reference]
            # """
            # === END COMMENTED OUT SECTION ===

            # Call OpenAI with the rendered prompt
            client = AsyncOpenAI(api_key=openai_api_key)

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": blog_prompt}],
                temperature=0.7
            )

            content = response.choices[0].message.content

            # Track successful usage
            await self.prompt_service.track_usage(
                prompt_key="seo_blog_generation",
                tenant_id=self.tenant_id,
                success=True
            )

            logger.info(
                "Blog post generated successfully with dynamic prompt",
                title=title,
                content_length=len(content),
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None
            )

            return content

        except AuthenticationError as auth_error:
            try:
                await self.prompt_service.track_usage(
                    prompt_key="seo_blog_generation",
                    tenant_id=self.tenant_id,
                    success=False
                )
            except Exception as track_error:
                logger.warning(f"Failed to track usage failure: {track_error}")

            logger.error(
                "OpenAI authentication failed while generating blog post",
                title=title
            )
            raise ValueError(
                "OpenAI API key is invalid or expired. Update the secret in Secrets Management and try again."
            ) from auth_error
        except Exception as e:
            # Track failed usage
            try:
                await self.prompt_service.track_usage(
                    prompt_key="seo_blog_generation",
                    tenant_id=self.tenant_id,
                    success=False
                )
            except Exception as track_error:
                logger.warning(f"Failed to track usage failure: {track_error}")

            logger.error(f"Failed to generate blog post: {e}", title=title)
            raise ValueError(f"Content generation failed: {str(e)}")

    async def generate_variants_per_channel(
        self,
        content: str,
        title: str,
        channels: List[str],
        openai_api_key: str,
        prompt_settings: Optional[Dict[str, Any]] = None
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

        prompt_settings = prompt_settings or {}
        variants = []

        for channel in channels:
            constraints = channel_constraints.get(channel, {
                "max_chars": 1000,
                "format": "plain text",
                "tone": "professional",
                "instructions": f"Adapt content for {channel}"
            })

            try:
                prompt_key = f"channel_variant_{channel}"
                template_defaults = PROMPT_DEFAULTS.get(prompt_key)
                if not template_defaults:
                    prompt_key = "channel_variant_twitter"
                    template_defaults = PROMPT_DEFAULTS["channel_variant_twitter"]

                await self.prompt_service.ensure_system_prompt(prompt_key, template_defaults)

                variables = {
                    "title": title,
                    "content": content,
                    "constraints": constraints,
                    "professionalism_level": prompt_settings.get("professionalism_level", 4),
                    "humor_level": prompt_settings.get("humor_level", 1),
                    "creativity_level": prompt_settings.get("creativity_level", 3),
                }

                variant_prompt = await self.prompt_service.render_prompt(
                    prompt_key=prompt_key,
                    variables=variables,
                    tenant_id=self.tenant_id,
                    track_usage=True
                )

                if not variant_prompt:
                    variant_prompt = Template(template_defaults["prompt_template"]).render(**variables)

                client = AsyncOpenAI(api_key=openai_api_key)

                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
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

    async def validate_content(
        self,
        title: str,
        content: str,
        openai_api_key: str,
        prompt_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate content for SEO quality and assign a score (0-100).

        Args:
            title: Content title
            content: Content body to validate
            openai_api_key: OpenAI API key

        Returns:
            Dict with score, status, issues, and recommendations
        """
        try:
            client = AsyncOpenAI(api_key=openai_api_key)
            await self.prompt_service.ensure_system_prompt(
                "seo_content_validation",
                PROMPT_DEFAULTS["seo_content_validation"]
            )

            settings = prompt_settings or {}
            variables = {
                "title": title,
                "content": content,
                "target_score": settings.get("target_score", 95),
                "strictness_level": settings.get("strictness_level", 4),
            }

            validation_prompt = await self.prompt_service.render_prompt(
                prompt_key="seo_content_validation",
                variables=variables,
                tenant_id=self.tenant_id,
                track_usage=True
            )

            if not validation_prompt:
                validation_prompt = Template(
                    PROMPT_DEFAULTS["seo_content_validation"]["prompt_template"]
                ).render(**variables)

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.3  # Lower temperature for consistent scoring
            )

            validation_text = response.choices[0].message.content

            # Parse JSON response
            validation_result = json.loads(validation_text)

            # Ensure required fields
            target_score = variables.get("target_score", 95)
            validation_result.setdefault("score", 0)
            validation_result.setdefault("status", "FAIL" if validation_result["score"] < target_score else "PASS")
            validation_result.setdefault("issues", [])
            validation_result.setdefault("recommendations", [])
            validation_result.setdefault("strengths", [])
            sub_scores = validation_result.get("sub_scores") or {}
            default_sub_keys = [
                "keyword_coverage",
                "structure",
                "readability",
                "engagement",
                "technical"
            ]
            for key in default_sub_keys:
                sub_scores.setdefault(key, 0)
            validation_result["sub_scores"] = sub_scores

            sub_score_details = validation_result.get("sub_score_details") or {}
            for key in default_sub_keys:
                sub_score_details.setdefault(key, "")
            validation_result["sub_score_details"] = sub_score_details

            metadata = validation_result.get("metadata") or {}
            word_count = len(content.split()) if content else 0
            metadata.setdefault("word_count", word_count)
            metadata.setdefault("reading_level", "Unknown")
            metadata.setdefault("tone_alignment", "")
            metadata.setdefault("schema_opportunities", "")
            metadata.setdefault("link_opportunities", "")

            primary_keywords = metadata.get("primary_keywords_used") or []
            secondary_keywords = metadata.get("secondary_keywords_used") or []
            if not isinstance(primary_keywords, list):
                primary_keywords = [primary_keywords]
            if not isinstance(secondary_keywords, list):
                secondary_keywords = [secondary_keywords]
            metadata["primary_keywords_used"] = primary_keywords
            metadata["secondary_keywords_used"] = secondary_keywords

            validation_result["metadata"] = metadata

            logger.info(
                "Content validation completed",
                title=title,
                score=validation_result["score"],
                status=validation_result["status"],
                issue_count=len(validation_result["issues"])
            )

            return validation_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation JSON: {e}")
            return {
                "score": 0,
                "status": "ERROR",
                "issues": ["Validation failed - could not parse AI response"],
                "recommendations": [],
                "strengths": []
            }
        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return {
                "score": 0,
                "status": "ERROR",
                "issues": [f"Validation error: {str(e)}"],
                "recommendations": [],
                "strengths": []
            }

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
