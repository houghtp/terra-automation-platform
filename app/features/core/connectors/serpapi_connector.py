"""
SerpAPI Connector for Google search results.

Provides access to Google search data via SerpAPI's REST API.
Supports organic results, People Also Ask, Knowledge Graphs, and more.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from serpapi import GoogleSearch
import aiohttp
import structlog

from .base import BaseConnector, ConnectorError, RateLimitError, AuthenticationError
from .utils import handle_rate_limit, validate_required_fields

logger = structlog.get_logger(__name__)


class SerpAPIError(ConnectorError):
    """SerpAPI-specific error."""
    pass


class SerpAPIConnector(BaseConnector):
    """
    SerpAPI connector for Google search results.

    Features:
    - Organic search results
    - People Also Ask questions
    - Knowledge Graph data
    - Related searches
    - Shopping results
    - News results

    Rate Limits:
    - Depends on plan (100-40k searches/month)
    - No per-second limits, but has monthly quotas
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize SerpAPI connector.

        Args:
            api_key: SerpAPI API key
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

        # Default parameters
        self.default_params = {
            "engine": "google",
            "hl": "en",  # Language
            "gl": "us",  # Country
            "google_domain": "google.com"
        }

        logger.info("SerpAPI connector initialized")

    async def get_search_results(
        self,
        query: str,
        num_results: int = 10,
        country: str = "us",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get Google search results for a query.

        Args:
            query: Search query
            num_results: Number of results to return (max 100)
            country: Country code (us, uk, ca, etc.)
            language: Language code (en, es, fr, etc.)
            **kwargs: Additional SerpAPI parameters

        Returns:
            Dictionary containing search results

        Raises:
            SerpAPIError: If the search fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise SerpAPIError("Search query cannot be empty")

            if num_results > 100:
                logger.warning("SerpAPI max results is 100, limiting to 100")
                num_results = 100

            # Prepare parameters
            params = {
                **self.default_params,
                "q": query.strip(),
                "num": min(num_results, 100),
                "gl": country,
                "hl": language,
                "api_key": self.api_key,
                **kwargs
            }

            logger.info(f"Searching SerpAPI for: '{query}' (num={num_results})")

            # Use async HTTP client
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 429:
                        raise RateLimitError("SerpAPI rate limit exceeded")
                    elif response.status == 401:
                        raise AuthenticationError("Invalid SerpAPI key")
                    elif response.status != 200:
                        raise SerpAPIError(f"SerpAPI error: {response.status}")

                    data = await response.json()

            # Check for API errors
            if "error" in data:
                error_msg = data["error"]
                if "Invalid API key" in error_msg:
                    raise AuthenticationError(f"SerpAPI authentication failed: {error_msg}")
                elif "rate limit" in error_msg.lower():
                    raise RateLimitError(f"SerpAPI rate limit: {error_msg}")
                else:
                    raise SerpAPIError(f"SerpAPI error: {error_msg}")

            logger.info(f"Retrieved {len(data.get('organic_results', []))} search results")
            return data

        except aiohttp.ClientError as e:
            raise SerpAPIError(f"Network error: {str(e)}")
        except Exception as e:
            if isinstance(e, (SerpAPIError, RateLimitError, AuthenticationError)):
                raise
            raise SerpAPIError(f"Unexpected error: {str(e)}")

    async def get_organic_results(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get organic search results only.

        Args:
            query: Search query
            num_results: Number of results to return
            **kwargs: Additional parameters

        Returns:
            List of organic search results
        """
        try:
            results = await self.get_search_results(
                query=query,
                num_results=num_results,
                **kwargs
            )

            organic_results = results.get("organic_results", [])

            # Clean and standardize results
            cleaned_results = []
            for result in organic_results[:num_results]:
                cleaned_result = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0),
                    "displayed_link": result.get("displayed_link", ""),
                }

                # Add optional fields if present
                if "rich_snippet" in result:
                    cleaned_result["rich_snippet"] = result["rich_snippet"]
                if "sitelinks" in result:
                    cleaned_result["sitelinks"] = result["sitelinks"]

                cleaned_results.append(cleaned_result)

            return cleaned_results

        except Exception as e:
            if isinstance(e, (SerpAPIError, RateLimitError, AuthenticationError)):
                raise
            raise SerpAPIError(f"Error getting organic results: {str(e)}")

    async def get_people_also_ask(
        self,
        query: str,
        **kwargs
    ) -> List[Dict[str, str]]:
        """
        Get "People Also Ask" questions for a query.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            List of questions and snippets
        """
        try:
            results = await self.get_search_results(query=query, **kwargs)

            paa_results = results.get("people_also_ask", [])

            cleaned_paa = []
            for paa in paa_results:
                cleaned_paa.append({
                    "question": paa.get("question", ""),
                    "snippet": paa.get("snippet", ""),
                    "title": paa.get("title", ""),
                    "link": paa.get("link", "")
                })

            return cleaned_paa

        except Exception as e:
            if isinstance(e, (SerpAPIError, RateLimitError, AuthenticationError)):
                raise
            raise SerpAPIError(f"Error getting People Also Ask: {str(e)}")

    async def get_related_searches(
        self,
        query: str,
        **kwargs
    ) -> List[str]:
        """
        Get related search suggestions.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            List of related search queries
        """
        try:
            results = await self.get_search_results(query=query, **kwargs)

            related_searches = results.get("related_searches", [])

            # Extract just the query strings
            queries = []
            for related in related_searches:
                if isinstance(related, dict) and "query" in related:
                    queries.append(related["query"])
                elif isinstance(related, str):
                    queries.append(related)

            return queries

        except Exception as e:
            if isinstance(e, (SerpAPIError, RateLimitError, AuthenticationError)):
                raise
            raise SerpAPIError(f"Error getting related searches: {str(e)}")

    async def search_for_competitor_analysis(
        self,
        query: str,
        num_results: int = 5,
        **kwargs
    ) -> List[Dict[str, str]]:
        """
        Get search results formatted for competitor content analysis.

        This is the format your original script expects.

        Args:
            query: Search query
            num_results: Number of results (max 5 for analysis)
            **kwargs: Additional parameters

        Returns:
            List of (title, url) tuples as dicts
        """
        try:
            # Limit to reasonable number for content analysis
            num_results = min(num_results, 5)

            organic_results = await self.get_organic_results(
                query=query,
                num_results=num_results,
                **kwargs
            )

            # Format for your content analysis script
            competitor_results = []
            for result in organic_results:
                competitor_results.append({
                    "title": result.get("title", "No title available"),
                    "url": result.get("link", "N/A"),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0)
                })

            # Ensure we always return the requested number (pad with N/A if needed)
            while len(competitor_results) < num_results:
                competitor_results.append({
                    "title": "No result found",
                    "url": "N/A",
                    "snippet": "",
                    "position": len(competitor_results) + 1
                })

            return competitor_results[:num_results]

        except Exception as e:
            if isinstance(e, (SerpAPIError, RateLimitError, AuthenticationError)):
                raise
            # Return error results for graceful degradation
            return [{
                "title": f"Error fetching results: {str(e)}",
                "url": "N/A",
                "snippet": "",
                "position": i + 1
            } for i in range(num_results)]

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the SerpAPI connection.

        Returns:
            Dictionary with connection test results
        """
        try:
            # Simple test search
            results = await self.get_search_results(
                query="test search",
                num_results=1
            )

            return {
                "success": True,
                "message": "SerpAPI connection successful",
                "account_info": {
                    "has_results": len(results.get("organic_results", [])) > 0,
                    "search_metadata": results.get("search_metadata", {})
                }
            }

        except AuthenticationError as e:
            return {
                "success": False,
                "error": "Authentication failed",
                "message": str(e)
            }
        except RateLimitError as e:
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Connection failed",
                "message": str(e)
            }


# Factory function for the registry
def create_serpapi_connector(credentials: Dict[str, Any], **kwargs) -> SerpAPIConnector:
    """
    Factory function to create SerpAPI connector instance.

    Args:
        credentials: Dictionary containing 'api_key'
        **kwargs: Additional configuration options

    Returns:
        Configured SerpAPIConnector instance

    Raises:
        ValueError: If required credentials are missing
    """
    required_fields = ["api_key"]
    validate_required_fields(credentials, required_fields)

    return SerpAPIConnector(
        api_key=credentials["api_key"],
        **kwargs
    )


# Connector metadata for registration
CONNECTOR_METADATA = {
    "name": "SerpAPI",
    "description": "Google search results via SerpAPI",
    "category": "search",
    "required_credentials": ["api_key"],
    "optional_credentials": [],
    "factory": create_serpapi_connector,
    "test_connection": lambda connector: connector.test_connection()
}
