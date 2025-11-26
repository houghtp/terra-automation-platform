"""
Firecrawl API client for LinkedIn prospect discovery.

Uses Firecrawl's search API to find LinkedIn profiles matching
target criteria (title, company, location).
"""

import httpx
from typing import List, Dict, Optional, Any
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class FirecrawlClient:
    """Client for Firecrawl API to discover prospects via LinkedIn search."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key from secrets management
        """
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v0"
        self.timeout = 30.0

        if not self.api_key:
            logger.warning("Firecrawl API key not provided")

    async def search_linkedin_profiles(
        self,
        company_name: Optional[str] = None,
        job_titles: Optional[List[str]] = None,
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for LinkedIn profiles matching criteria.

        Args:
            company_name: Company name to filter
            job_titles: List of job titles (e.g., ["CTO", "VP Engineering"])
            location: Location filter (e.g., "Boston, MA")
            max_results: Max results to return

        Returns:
            List of prospect dictionaries with LinkedIn data

        Example result:
            [
                {
                    "full_name": "John Doe",
                    "job_title": "CTO",
                    "company_name": "Acme Corp",
                    "location": "Boston, MA",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                    "snippet": "Bio text..."
                },
                ...
            ]
        """
        if not self.api_key:
            logger.error("Firecrawl API key not configured")
            return []

        try:
            # Build LinkedIn search query
            query_parts = []

            if company_name:
                query_parts.append(f'"{company_name}"')

            if job_titles:
                title_str = " OR ".join(f'"{title}"' for title in job_titles)
                query_parts.append(f"({title_str})")

            if location:
                query_parts.append(f'"{location}"')

            query_parts.append("site:linkedin.com/in")
            search_query = " ".join(query_parts)

            logger.info(
                "Searching LinkedIn profiles",
                query=search_query,
                max_results=max_results
            )

            # Call Firecrawl search API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "query": search_query,
                        "limit": max_results,
                        "lang": "en"
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()
                data = response.json()

            # Parse results
            prospects = []
            for result in data.get("data", [])[:max_results]:
                prospect = self._parse_linkedin_result(result)
                if prospect:
                    prospects.append(prospect)

            logger.info(
                "LinkedIn search completed",
                query=search_query,
                results_found=len(prospects)
            )

            return prospects

        except httpx.HTTPStatusError as e:
            logger.error(
                "Firecrawl API error",
                status_code=e.response.status_code,
                error=str(e)
            )
            return []
        except Exception as e:
            logger.error("Firecrawl search failed", error=str(e), exc_info=True)
            return []

    def _parse_linkedin_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Firecrawl search result into prospect data.

        Args:
            result: Raw Firecrawl result

        Returns:
            Prospect dict or None if parsing fails
        """
        try:
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            # Extract name from LinkedIn URL or title
            # LinkedIn profile URLs: https://linkedin.com/in/john-doe
            full_name = ""
            if "/in/" in url:
                username = url.split("/in/")[1].split("?")[0].strip("/")
                full_name = username.replace("-", " ").title()

            # Try to extract name from title (usually "Name - Title - Company | LinkedIn")
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 1:
                    full_name = parts[0].strip()

            if not full_name:
                logger.debug("Could not extract name from LinkedIn result", url=url)
                return None

            # Extract job title and company (heuristic from title/snippet)
            job_title = None
            company_name = None

            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    job_title = parts[1].strip()
                if len(parts) >= 3:
                    company_part = parts[2].split("|")[0].strip()
                    company_name = company_part

            return {
                "full_name": full_name,
                "job_title": job_title,
                "linkedin_url": url,
                "linkedin_snippet": snippet[:500] if snippet else None,
                "discovered_via": "firecrawl",
            }

        except Exception as e:
            logger.debug("Failed to parse LinkedIn result", error=str(e))
            return None

    async def scrape_linkedin_profile(self, profile_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a LinkedIn profile for detailed information.

        Args:
            profile_url: LinkedIn profile URL

        Returns:
            Detailed profile data or None if scraping fails

        Note: This is a placeholder for future enhancement.
        LinkedIn scraping may require additional tools or proxies.
        """
        logger.warning(
            "LinkedIn profile scraping not fully implemented",
            url=profile_url
        )
        return None
