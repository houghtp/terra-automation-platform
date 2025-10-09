"""
Web scraping utilities for content extraction.

Provides unified interface for scraping websites using various services
and extracting clean content for analysis.
"""

import asyncio
import aiohttp
from typing import Any, Dict, List, Optional, Union
from bs4 import BeautifulSoup
import structlog

from .base import BaseConnector, ConnectorError
from .registry import get_connector
from ..database import get_async_session
from ...connectors.connectors.services import ConnectorService

logger = structlog.get_logger(__name__)


class WebScrapingError(ConnectorError):
    """Web scraping specific error."""
    pass


class WebScraper:
    """
    Unified web scraping interface using multiple backends.

    Can use Firecrawl, ScrapingBee, ScrapingDog, or direct HTTP requests
    with BeautifulSoup for content extraction.
    """

    def __init__(self, tenant_id: str = "global"):
        """
        Initialize web scraper.

        Args:
            tenant_id: Tenant ID for credential resolution
        """
        self.tenant_id = tenant_id
        self.connector_service = ConnectorService()

    async def scrape_article(
        self,
        url: str,
        preferred_service: str = "firecrawl",
        fallback_services: List[str] = ["scrapingbee", "scrapingdog", "direct"]
    ) -> str:
        """
        Scrape article content from a URL.

        This replicates the functionality from your original script
        but uses our connector infrastructure.

        Args:
            url: URL to scrape
            preferred_service: Preferred scraping service
            fallback_services: Fallback services if preferred fails

        Returns:
            Extracted article text

        Raises:
            WebScrapingError: If all scraping attempts fail
        """
        if url == "N/A" or not url or not url.strip():
            return "⚠ No valid URL for this search result."

        # Try services in order
        services_to_try = [preferred_service] + fallback_services

        for service in services_to_try:
            try:
                if service == "direct":
                    return await self._scrape_direct(url)
                else:
                    return await self._scrape_with_service(url, service)
            except Exception as e:
                logger.warning(f"Scraping failed with {service}: {str(e)}")
                continue

        return f"⚠ Failed to scrape {url}: All services failed"

    async def _scrape_with_service(self, url: str, service: str) -> str:
        """
        Scrape using a specific connector service.

        Args:
            url: URL to scrape
            service: Service name (firecrawl, scrapingbee, scrapingdog)

        Returns:
            Extracted content
        """
        try:
            # Get connector instance with credentials
            connector = await self.connector_service.create_sdk_connector_instance_by_type(
                connector_type=service,
                tenant_id=self.tenant_id
            )

            if service == "firecrawl":
                # Use Firecrawl's scraping capability
                if hasattr(connector, 'scrape_url'):
                    result = await connector.scrape_url(url)
                    # Firecrawl returns structured data
                    if isinstance(result, dict):
                        return result.get('content', result.get('markdown', ''))
                    return str(result)

            elif service in ["scrapingbee", "scrapingdog"]:
                # Use scraping service's website scraping
                if hasattr(connector, 'scrape_website'):
                    html_content = await connector.scrape_website(url)
                    return self._extract_content_from_html(html_content)

            raise WebScrapingError(f"Service {service} not properly configured")

        except Exception as e:
            raise WebScrapingError(f"Service {service} failed: {str(e)}")

    async def _scrape_direct(self, url: str) -> str:
        """
        Scrape directly using aiohttp + BeautifulSoup.

        This replicates your original scraping logic.

        Args:
            url: URL to scrape

        Returns:
            Extracted content
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    html_content = await response.text()

            return self._extract_content_from_html(html_content)

        except Exception as e:
            raise WebScrapingError(f"Direct scraping failed: {str(e)}")

    def _extract_content_from_html(self, html_content: str) -> str:
        """
        Extract clean content from HTML using BeautifulSoup.

        This replicates your original content extraction logic.

        Args:
            html_content: Raw HTML content

        Returns:
            Extracted text content
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text from common content tags (your original logic)
            article_text = ""
            for tag in ["article", "div", "section"]:
                content = soup.find(tag)
                if content:
                    article_text = content.get_text(separator="\n", strip=True)
                    break

            # Fallback to paragraphs if no main content found
            if not article_text:
                paragraphs = soup.find_all("p")
                article_text = "\n".join([p.get_text(strip=True) for p in paragraphs])

            # Check if we got meaningful content
            if len(article_text) > 100:
                return article_text
            else:
                return "⚠ Could not extract meaningful content."

        except Exception as e:
            return f"⚠ Failed to parse HTML: {str(e)}"


class SearchScraper:
    """
    Unified search interface using multiple search backends.

    Can use SerpAPI, ScrapingDog, or ScrapingBee for Google search results.
    """

    def __init__(self, tenant_id: str = "global"):
        """
        Initialize search scraper.

        Args:
            tenant_id: Tenant ID for credential resolution
        """
        self.tenant_id = tenant_id
        self.connector_service = ConnectorService()

    async def get_top_google_results(
        self,
        query: str,
        num_results: int = 5,
        preferred_service: str = "serpapi",
        fallback_services: List[str] = ["firecrawl", "scrapingbee", "scrapingdog"]
    ) -> List[Dict[str, str]]:
        """
        Get top Google search results.

        This replicates the functionality from your original script.

        Args:
            query: Search query
            num_results: Number of results to return
            preferred_service: Preferred search service
            fallback_services: Fallback services if preferred fails

        Returns:
            List of search results with title and URL
        """
        # Try services in order
        services_to_try = [preferred_service] + fallback_services

        for service in services_to_try:
            try:
                return await self._search_with_service(query, num_results, service)
            except Exception as e:
                logger.warning(f"Search failed with {service}: {str(e)}")
                continue

        # Return error results if all services fail
        return [{
            "title": f"Error fetching results for '{query}'",
            "url": "N/A",
            "snippet": "",
            "position": i + 1
        } for i in range(num_results)]

    async def _search_with_service(
        self,
        query: str,
        num_results: int,
        service: str
    ) -> List[Dict[str, str]]:
        """
        Search using a specific service.

        Args:
            query: Search query
            num_results: Number of results
            service: Service name

        Returns:
            List of search results
        """
        try:
            # Get connector instance with credentials
            connector = await self.connector_service.create_sdk_connector_instance_by_type(
                connector_type=service,
                tenant_id=self.tenant_id
            )

            # Special handling for Firecrawl search
            if service == "firecrawl" and hasattr(connector, 'search'):
                result = await connector.search(query, limit=num_results)
                if result.success and result.data:
                    return [{
                        "title": item.get("title", "No title"),
                        "url": item.get("url", "N/A"),
                        "snippet": item.get("snippet", ""),
                        "position": i + 1
                    } for i, item in enumerate(result.data)]
                else:
                    raise WebScrapingError(f"Firecrawl search failed: {result.error}")

            # Use the search_for_competitor_analysis method which returns the right format
            if hasattr(connector, 'search_for_competitor_analysis'):
                return await connector.search_for_competitor_analysis(query, num_results)

            # Fallback to standard search methods
            if hasattr(connector, 'get_organic_results'):
                results = await connector.get_organic_results(query, num_results)
                # Convert to expected format
                return [{
                    "title": result.get("title", "No title"),
                    "url": result.get("link", result.get("url", "N/A")),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", i + 1)
                } for i, result in enumerate(results)]

            raise WebScrapingError(f"Service {service} doesn't support search")

        except Exception as e:
            raise WebScrapingError(f"Search with {service} failed: {str(e)}")


# Convenience functions for backward compatibility with your script
async def get_top_google_results_scrapingbee(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Backward compatibility function for ScrapingBee search.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        List of search results
    """
    scraper = SearchScraper()
    return await scraper.get_top_google_results(
        query=query,
        num_results=num_results,
        preferred_service="scrapingbee",
        fallback_services=["serpapi", "scrapingdog"]
    )


async def get_top_google_results(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Backward compatibility function for ScrapingDog search.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        List of search results
    """
    scraper = SearchScraper()
    return await scraper.get_top_google_results(
        query=query,
        num_results=num_results,
        preferred_service="scrapingdog",
        fallback_services=["serpapi", "scrapingbee"]
    )


async def scrape_article(url: str) -> str:
    """
    Backward compatibility function for article scraping.

    Args:
        url: URL to scrape

    Returns:
        Extracted article content
    """
    scraper = WebScraper()
    return await scraper.scrape_article(url)
