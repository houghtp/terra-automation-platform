"""
ScrapingDog Connector for web scraping services.

Provides access to ScrapingDog's web scraping API for Google search results,
website content extraction, and social media scraping.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
import aiohttp
import structlog
from urllib.parse import urlencode, quote_plus

from .base import BaseConnector, ConnectorError, RateLimitError, AuthenticationError
from .utils import handle_rate_limit, validate_required_fields

logger = structlog.get_logger(__name__)


class ScrapingDogError(ConnectorError):
    """ScrapingDog-specific error."""
    pass


class ScrapingDogConnector(BaseConnector):
    """
    ScrapingDog connector for web scraping services.

    Features:
    - Google search results scraping
    - Website content extraction
    - Social media scraping
    - Instagram, Twitter, LinkedIn data
    - Proxy rotation and CAPTCHA solving

    Rate Limits:
    - Depends on plan (1k-1M requests/month)
    - 100 requests per minute on basic plans
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize ScrapingDog connector.

        Args:
            api_key: ScrapingDog API key
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = "https://api.scrapingdog.com"

        # Service endpoints
        self.endpoints = {
            "google": f"{self.base_url}/google",
            "scrape": f"{self.base_url}/scrape",
            "instagram": f"{self.base_url}/instagram",
            "twitter": f"{self.base_url}/twitter",
            "linkedin": f"{self.base_url}/linkedin",
        }

        logger.info("ScrapingDog connector initialized")

    async def google_search(
        self,
        query: str,
        num_results: int = 10,
        country: str = "US",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search Google using ScrapingDog's Google API.

        Args:
            query: Search query
            num_results: Number of results to return (max 100)
            country: Country code (US, UK, CA, etc.)
            language: Language code (en, es, fr, etc.)
            **kwargs: Additional parameters (safe_search, etc.)

        Returns:
            Dictionary containing search results

        Raises:
            ScrapingDogError: If the search fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ScrapingDogError("Search query cannot be empty")

            # Prepare parameters
            params = {
                "api_key": self.api_key,
                "query": query.strip(),
                "num": min(num_results, 100),
                "country": country.upper(),
                "lang": language.lower(),
                **kwargs
            }

            logger.info(f"Searching Google via ScrapingDog: '{query}' (num={num_results})")

            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoints["google"], params=params, timeout=30) as response:
                    if response.status == 429:
                        raise RateLimitError("ScrapingDog rate limit exceeded")
                    elif response.status == 401:
                        raise AuthenticationError("Invalid ScrapingDog API key")
                    elif response.status == 403:
                        raise AuthenticationError("ScrapingDog API access forbidden")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ScrapingDogError(f"ScrapingDog error {response.status}: {error_text}")

                    data = await response.json()

            # Validate response structure
            if not isinstance(data, dict):
                raise ScrapingDogError("Invalid response format from ScrapingDog")

            logger.info(f"Retrieved {len(data.get('organic_results', []))} search results")
            return data

        except aiohttp.ClientError as e:
            raise ScrapingDogError(f"Network error: {str(e)}")
        except asyncio.TimeoutError:
            raise ScrapingDogError("Request timeout")
        except Exception as e:
            if isinstance(e, (ScrapingDogError, RateLimitError, AuthenticationError)):
                raise
            raise ScrapingDogError(f"Unexpected error: {str(e)}")

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
            results = await self.google_search(
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
                    "position": result.get("position", len(cleaned_results) + 1),
                    "displayed_link": result.get("displayed_link", ""),
                }
                cleaned_results.append(cleaned_result)

            return cleaned_results

        except Exception as e:
            if isinstance(e, (ScrapingDogError, RateLimitError, AuthenticationError)):
                raise
            raise ScrapingDogError(f"Error getting organic results: {str(e)}")

    async def scrape_website(
        self,
        url: str,
        premium: bool = False,
        dynamic: bool = False,
        **kwargs
    ) -> str:
        """
        Scrape content from a website URL.

        Args:
            url: URL to scrape
            premium: Use premium proxy (better success rate)
            dynamic: Enable JavaScript rendering
            **kwargs: Additional parameters

        Returns:
            Raw HTML content

        Raises:
            ScrapingDogError: If scraping fails
        """
        try:
            if not url or not url.strip():
                raise ScrapingDogError("URL cannot be empty")

            # Prepare parameters
            params = {
                "api_key": self.api_key,
                "url": url.strip(),
                **kwargs
            }

            if premium:
                params["premium"] = "true"
            if dynamic:
                params["dynamic"] = "true"

            logger.info(f"Scraping website via ScrapingDog: {url}")

            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoints["scrape"], params=params, timeout=60) as response:
                    if response.status == 429:
                        raise RateLimitError("ScrapingDog rate limit exceeded")
                    elif response.status == 401:
                        raise AuthenticationError("Invalid ScrapingDog API key")
                    elif response.status == 403:
                        raise AuthenticationError("ScrapingDog API access forbidden")
                    elif response.status == 404:
                        raise ScrapingDogError(f"Page not found: {url}")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ScrapingDogError(f"ScrapingDog error {response.status}: {error_text}")

                    content = await response.text()

            logger.info(f"Successfully scraped {len(content)} characters from {url}")
            return content

        except aiohttp.ClientError as e:
            raise ScrapingDogError(f"Network error: {str(e)}")
        except asyncio.TimeoutError:
            raise ScrapingDogError("Request timeout")
        except Exception as e:
            if isinstance(e, (ScrapingDogError, RateLimitError, AuthenticationError)):
                raise
            raise ScrapingDogError(f"Unexpected error: {str(e)}")

    async def search_for_competitor_analysis(
        self,
        query: str,
        num_results: int = 5,
        **kwargs
    ) -> List[Dict[str, str]]:
        """
        Get search results formatted for competitor content analysis.

        This matches the format your original script expects.

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
            logger.error(f"Error in competitor analysis search: {str(e)}")
            # Return error results for graceful degradation
            return [{
                "title": f"Error fetching results: {str(e)}",
                "url": "N/A",
                "snippet": "",
                "position": i + 1
            } for i in range(num_results)]

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the ScrapingDog connection.

        Returns:
            Dictionary with connection test results
        """
        try:
            # Simple test search
            results = await self.google_search(
                query="test search",
                num_results=1
            )

            return {
                "success": True,
                "message": "ScrapingDog connection successful",
                "account_info": {
                    "has_results": len(results.get("organic_results", [])) > 0,
                    "service": "google_search"
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
def create_scrapingdog_connector(credentials: Dict[str, Any], **kwargs) -> ScrapingDogConnector:
    """
    Factory function to create ScrapingDog connector instance.

    Args:
        credentials: Dictionary containing 'api_key'
        **kwargs: Additional configuration options

    Returns:
        Configured ScrapingDogConnector instance

    Raises:
        ValueError: If required credentials are missing
    """
    required_fields = ["api_key"]
    validate_required_fields(credentials, required_fields)

    return ScrapingDogConnector(
        api_key=credentials["api_key"],
        **kwargs
    )


# Connector metadata for registration
CONNECTOR_METADATA = {
    "name": "ScrapingDog",
    "description": "Web scraping and Google search via ScrapingDog",
    "category": "scraping",
    "required_credentials": ["api_key"],
    "optional_credentials": [],
    "factory": create_scrapingdog_connector,
    "test_connection": lambda connector: connector.test_connection()
}
