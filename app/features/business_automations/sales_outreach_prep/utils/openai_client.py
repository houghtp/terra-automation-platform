"""
OpenAI client for competitive analysis and market intelligence.

Uses OpenAI's GPT models to analyze companies, generate insights,
and create competitive positioning analysis.
"""

from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class OpenAIAnalyzer:
    """Client for OpenAI-powered competitive analysis."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key from secrets management
        """
        if not api_key:
            logger.warning("OpenAI API key not provided")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)

        self.model = "gpt-4o-mini"  # Cost-effective for analysis

    async def analyze_company(
        self,
        company_name: str,
        company_description: Optional[str] = None,
        industry: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a company for competitive positioning.

        Args:
            company_name: Company name
            company_description: Company description (optional)
            industry: Industry (optional)

        Returns:
            Analysis dict with market position, insights, etc. or None

        Example result:
            {
                "market_position": {
                    "completeness_of_vision": 7,
                    "ability_to_execute": 8,
                    "innovation_score": 6
                },
                "insights": [
                    "Strong product execution",
                    "Limited market presence"
                ],
                "executive_summary": "Company is a strong player in..."
            }
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return None

        try:
            prompt = self._build_company_analysis_prompt(
                company_name,
                company_description,
                industry
            )

            logger.info("Analyzing company with OpenAI", company=company_name)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst specializing in competitive intelligence."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )

            # Parse response
            content = response.choices[0].message.content
            analysis = self._parse_analysis_response(content)

            logger.info(
                "Company analysis completed",
                company=company_name,
                vision_score=analysis.get("market_position", {}).get("completeness_of_vision")
            )

            return analysis

        except Exception as e:
            logger.error(
                "OpenAI company analysis failed",
                company=company_name,
                error=str(e),
                exc_info=True
            )
            return None

    def _build_company_analysis_prompt(
        self,
        company_name: str,
        company_description: Optional[str],
        industry: Optional[str]
    ) -> str:
        """Build prompt for company analysis."""
        parts = [
            f"Analyze the following company for competitive positioning:\n",
            f"Company: {company_name}"
        ]

        if industry:
            parts.append(f"Industry: {industry}")

        if company_description:
            parts.append(f"Description: {company_description}")

        parts.append("\nProvide:")
        parts.append("1. Completeness of Vision (1-10 score)")
        parts.append("2. Ability to Execute (1-10 score)")
        parts.append("3. Innovation Score (1-10 score)")
        parts.append("4. 2-3 key insights (bullet points)")
        parts.append("5. Brief executive summary (2-3 sentences)")

        return "\n".join(parts)

    def _parse_analysis_response(self, content: str) -> Dict[str, Any]:
        """
        Parse OpenAI response into structured analysis.

        Args:
            content: Raw OpenAI response text

        Returns:
            Structured analysis dict
        """
        # Simple parsing (could be enhanced with JSON mode in production)
        analysis = {
            "market_position": {
                "completeness_of_vision": 5,
                "ability_to_execute": 5,
                "innovation_score": 5
            },
            "insights": [],
            "executive_summary": content[:500] if content else "Analysis unavailable"
        }

        try:
            lines = content.split("\n")
            for line in lines:
                # Extract scores (simple heuristic)
                if "vision" in line.lower() and any(c.isdigit() for c in line):
                    score = int(''.join(filter(str.isdigit, line))[:1])
                    analysis["market_position"]["completeness_of_vision"] = min(score, 10)

                elif "execute" in line.lower() and any(c.isdigit() for c in line):
                    score = int(''.join(filter(str.isdigit, line))[:1])
                    analysis["market_position"]["ability_to_execute"] = min(score, 10)

                elif "innovation" in line.lower() and any(c.isdigit() for c in line):
                    score = int(''.join(filter(str.isdigit, line))[:1])
                    analysis["market_position"]["innovation_score"] = min(score, 10)

                # Extract insights (lines starting with - or •)
                elif line.strip().startswith(("-", "•", "*")):
                    insight = line.strip().lstrip("-•* ")
                    if insight:
                        analysis["insights"].append(insight)

        except Exception as e:
            logger.debug("Failed to parse analysis details", error=str(e))

        return analysis

    async def generate_outreach_message(
        self,
        prospect_name: str,
        prospect_title: str,
        company_name: str,
        campaign_description: str
    ) -> Optional[str]:
        """
        Generate personalized outreach message for a prospect.

        Args:
            prospect_name: Prospect's name
            prospect_title: Prospect's job title
            company_name: Company name
            campaign_description: Campaign description/goal

        Returns:
            Generated email message or None

        Note: This is a placeholder for future enhancement.
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return None

        try:
            prompt = (
                f"Write a professional, personalized cold email to:\n"
                f"Name: {prospect_name}\n"
                f"Title: {prospect_title}\n"
                f"Company: {company_name}\n\n"
                f"Campaign goal: {campaign_description}\n\n"
                f"Keep it concise (3-4 sentences), friendly, and value-focused."
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sales professional writing personalized outreach emails."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=300
            )

            message = response.choices[0].message.content

            logger.info("Outreach message generated", prospect=prospect_name)

            return message

        except Exception as e:
            logger.error(
                "OpenAI message generation failed",
                prospect=prospect_name,
                error=str(e),
                exc_info=True
            )
            return None
