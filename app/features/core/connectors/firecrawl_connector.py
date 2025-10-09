"""
Firecrawl SDK-based connector for web scraping and crawling operations.
"""

from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
from ..base import WebScrapingConnector, ConnectorResult, ConnectorType, ConnectorConfig
from ..utils import with_rate_limit, with_metrics, with_retry, ConnectorAuth
import logging

logger = logging.getLogger(__name__)


class FirecrawlConnector(WebScrapingConnector):
    """
    Firecrawl connector for web scraping using the Firecrawl API.

    Note: Firecrawl doesn't have an official Python SDK yet, so we'll use their REST API
    with an async HTTP client for better performance.
    """

    def __init__(self, config: ConnectorConfig, credentials: Dict[str, Any]):
        """Initialize Firecrawl connector."""
        super().__init__(config, credentials)
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key: Optional[str] = None
        self._base_url = self.config.api_base_url or "https://api.firecrawl.dev/v0"

    async def initialize(self) -> ConnectorResult[bool]:
        """Initialize the Firecrawl client."""
        try:
            self._api_key = ConnectorAuth.get_api_key(self.credentials, "api_key")

            # Create aiohttp session with default headers
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "TerraAutomationPlatform/1.0"
            }

            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )

            # Test the connection
            test_result = await self.test_connection()
            if not test_result.success:
                return test_result

            self.logger.info("Firecrawl connector initialized successfully")
            return ConnectorResult[bool](success=True, data=True)

        except Exception as e:
            return self._handle_error(e, "initialize")

    @with_metrics("test_connection")
    @with_retry(max_attempts=2)
    async def test_connection(self) -> ConnectorResult[bool]:
        """Test connection to Firecrawl API."""
        try:
            if not self._session:
                return ConnectorResult[bool](
                    success=False,
                    error="Session not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            # Test with a simple scrape call to a known URL
            test_url = "https://httpbin.org/status/200"

            async with self._session.post(
                f"{self._base_url}/scrape",
                json={"url": test_url}
            ) as response:
                if response.status == 200:
                    return ConnectorResult[bool](
                        success=True,
                        data=True,
                        metadata={"status_code": response.status}
                    )
                else:
                    error_text = await response.text()
                    return ConnectorResult[bool](
                        success=False,
                        error=f"API test failed: {response.status} - {error_text}",
                        error_code="API_ERROR"
                    )

        except Exception as e:
            return self._handle_error(e, "test_connection")

    async def get_schema(self) -> ConnectorResult[Dict[str, Any]]:
        """Get configuration schema for Firecrawl connector."""
        schema = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "Firecrawl API key",
                    "format": "password"
                },
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "description": "Firecrawl API base URL (optional)",
                    "default": "https://api.firecrawl.dev/v0",
                    "format": "uri"
                },
                "default_options": {
                    "type": "object",
                    "title": "Default Scraping Options",
                    "description": "Default options for scraping operations",
                    "properties": {
                        "formats": {
                            "type": "array",
                            "title": "Output Formats",
                            "description": "Formats to return (markdown, html, rawHtml, etc.)",
                            "items": {"type": "string"},
                            "default": ["markdown"]
                        },
                        "onlyMainContent": {
                            "type": "boolean",
                            "title": "Only Main Content",
                            "description": "Extract only main content, excluding navigation/ads",
                            "default": true
                        },
                        "includeTags": {
                            "type": "array",
                            "title": "Include Tags",
                            "description": "HTML tags to include in extraction",
                            "items": {"type": "string"}
                        },
                        "excludeTags": {
                            "type": "array",
                            "title": "Exclude Tags",
                            "description": "HTML tags to exclude from extraction",
                            "items": {"type": "string"}
                        },
                        "waitFor": {
                            "type": "integer",
                            "title": "Wait For (ms)",
                            "description": "Time to wait before scraping (milliseconds)",
                            "minimum": 0,
                            "maximum": 10000
                        }
                    }
                }
            },
            "required": ["api_key"],
            "additionalProperties": False
        }

        return ConnectorResult[Dict[str, Any]](success=True, data=schema)

    @with_metrics("scrape_url")
    @with_rate_limit(requests_per_minute=30)  # Firecrawl has rate limits
    @with_retry(max_attempts=3)
    async def scrape_url(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult[Dict[str, Any]]:
        """
        Scrape content from a URL using Firecrawl.

        Args:
            url: URL to scrape
            options: Scraping options (formats, selectors, etc.)

        Returns:
            ConnectorResult containing scraped content
        """
        try:
            if not self._session:
                return ConnectorResult[Dict[str, Any]](
                    success=False,
                    error="Session not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            if not url:
                return ConnectorResult[Dict[str, Any]](
                    success=False,
                    error="URL is required",
                    error_code="INVALID_INPUT"
                )

            # Prepare request payload
            payload = {"url": url}

            # Add scraping options
            if options:
                payload.update(options)

            # Set default options if not provided
            if "formats" not in payload:
                payload["formats"] = ["markdown", "html"]
            if "onlyMainContent" not in payload:
                payload["onlyMainContent"] = True

            # Make the API call
            async with self._session.post(
                f"{self._base_url}/scrape",
                json=payload
            ) as response:

                if response.status == 200:
                    result = await response.json()

                    return ConnectorResult[Dict[str, Any]](
                        success=True,
                        data=result,
                        metadata={
                            "url": url,
                            "status_code": response.status,
                            "options_used": payload
                        }
                    )
                else:
                    error_text = await response.text()
                    return ConnectorResult[Dict[str, Any]](
                        success=False,
                        error=f"Scraping failed: {response.status} - {error_text}",
                        error_code="SCRAPE_ERROR",
                        metadata={"url": url, "status_code": response.status}
                    )

        except Exception as e:
            return self._handle_error(e, "scrape_url")

    @with_metrics("scrape_batch")
    @with_rate_limit(requests_per_minute=20)  # Lower rate for batch operations
    async def scrape_batch(
        self,
        urls: List[str],
        options: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult[List[Dict[str, Any]]]:
        """
        Scrape content from multiple URLs.

        Args:
            urls: List of URLs to scrape
            options: Scraping options

        Returns:
            ConnectorResult containing list of scraped content
        """
        try:
            if not urls:
                return ConnectorResult[List[Dict[str, Any]]](
                    success=False,
                    error="URLs list is empty",
                    error_code="INVALID_INPUT"
                )

            # Limit batch size to prevent API abuse
            max_batch_size = getattr(self.config, 'max_batch_size', 10)
            if len(urls) > max_batch_size:
                return ConnectorResult[List[Dict[str, Any]]](
                    success=False,
                    error=f"Batch size {len(urls)} exceeds maximum {max_batch_size}",
                    error_code="BATCH_SIZE_EXCEEDED"
                )

            # Process URLs concurrently with a semaphore to control concurrency
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

            async def scrape_single(url: str) -> Dict[str, Any]:
                async with semaphore:
                    result = await self.scrape_url(url, options)
                    return {
                        "url": url,
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                        "error_code": result.error_code
                    }

            # Execute all scraping tasks
            tasks = [scrape_single(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            processed_results = []
            successful_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "url": urls[i],
                        "success": False,
                        "data": None,
                        "error": str(result),
                        "error_code": "EXECUTION_ERROR"
                    })
                else:
                    processed_results.append(result)
                    if result["success"]:
                        successful_count += 1

            return ConnectorResult[List[Dict[str, Any]]](
                success=True,  # Overall success if at least some URLs were processed
                data=processed_results,
                metadata={
                    "total_urls": len(urls),
                    "successful_count": successful_count,
                    "failed_count": len(urls) - successful_count,
                    "success_rate": successful_count / len(urls) if urls else 0
                }
            )

        except Exception as e:
            return self._handle_error(e, "scrape_batch")

    @with_metrics("search")
    @with_rate_limit(requests_per_minute=20)  # Rate limit for search
    async def search(
        self,
        query: str,
        limit: int = 10,
        options: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult[List[Dict[str, Any]]]:
        """
        Search for content using Firecrawl's search endpoint.

        Args:
            query: Search query
            limit: Maximum number of results to return
            options: Additional search options

        Returns:
            ConnectorResult containing search results
        """
        try:
            if not self._session:
                return ConnectorResult[List[Dict[str, Any]]](
                    success=False,
                    error="Session not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            if not query or not query.strip():
                return ConnectorResult[List[Dict[str, Any]]](
                    success=False,
                    error="Search query is required",
                    error_code="INVALID_INPUT"
                )

            # Prepare search payload
            payload = {
                "query": query.strip(),
                "limit": min(limit, 20)  # Cap at 20 results
            }

            if options:
                payload.update(options)

            # Make the search API call
            async with self._session.post(
                f"{self._base_url}/search",
                json=payload
            ) as response:

                if response.status == 200:
                    result = await response.json()

                    # Extract search results and format consistently
                    search_results = []
                    if isinstance(result, dict) and "data" in result:
                        results_data = result["data"]
                    elif isinstance(result, list):
                        results_data = result
                    else:
                        results_data = []

                    for item in results_data:
                        search_results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", item.get("snippet", "")),
                            "source": "firecrawl"
                        })

                    return ConnectorResult[List[Dict[str, Any]]](
                        success=True,
                        data=search_results,
                        metadata={
                            "query": query,
                            "total_results": len(search_results),
                            "limit": limit
                        }
                    )
                else:
                    error_text = await response.text()
                    return ConnectorResult[List[Dict[str, Any]]](
                        success=False,
                        error=f"Search failed: {response.status} - {error_text}",
                        error_code="SEARCH_ERROR",
                        metadata={"query": query}
                    )

        except Exception as e:
            return self._handle_error(e, "search")

    @with_metrics("crawl_website")
    @with_rate_limit(requests_per_minute=10)  # Very low rate for crawling
    async def crawl_website(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult[Dict[str, Any]]:
        """
        Crawl an entire website using Firecrawl's crawl endpoint.

        Args:
            url: Starting URL to crawl
            options: Crawling options (maxDepth, limit, etc.)

        Returns:
            ConnectorResult containing crawl job information
        """
        try:
            if not self._session:
                return ConnectorResult[Dict[str, Any]](
                    success=False,
                    error="Session not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            # Prepare crawl payload
            payload = {"url": url}

            if options:
                payload.update(options)

            # Set reasonable defaults for crawling
            if "maxDepth" not in payload:
                payload["maxDepth"] = 2
            if "limit" not in payload:
                payload["limit"] = 10

            # Start the crawl job
            async with self._session.post(
                f"{self._base_url}/crawl",
                json=payload
            ) as response:

                if response.status == 200:
                    result = await response.json()

                    return ConnectorResult[Dict[str, Any]](
                        success=True,
                        data=result,
                        metadata={
                            "url": url,
                            "crawl_options": payload
                        }
                    )
                else:
                    error_text = await response.text()
                    return ConnectorResult[Dict[str, Any]](
                        success=False,
                        error=f"Crawl failed: {response.status} - {error_text}",
                        error_code="CRAWL_ERROR"
                    )

        except Exception as e:
            return self._handle_error(e, "crawl_website")

    async def cleanup(self) -> None:
        """Clean up aiohttp session."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                self.logger.warning(f"Error closing Firecrawl session: {e}")
            finally:
                self._session = None


# Configuration for Firecrawl connector
FIRECRAWL_CONFIG = ConnectorConfig(
    name="firecrawl",
    display_name="Firecrawl",
    description="Advanced web scraping and crawling with AI-powered content extraction",
    connector_type=ConnectorType.WEB_SCRAPING,
    version="1.0.0",
    rate_limit_per_minute=30,
    timeout_seconds=60,  # Web scraping can take longer
    retry_attempts=3,
    api_base_url="https://api.firecrawl.dev/v0",
    supports_streaming=False,
    supports_batch=True,
    max_batch_size=10,  # Reasonable limit for web scraping
    max_content_length=10 * 1024 * 1024  # 10MB limit for scraped content
)
