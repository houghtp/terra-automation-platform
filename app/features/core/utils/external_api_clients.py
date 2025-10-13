"""
Centralized API clients for external services (OpenAI, Firecrawl).

These clients accept API keys as parameters (from Secrets Management) and provide
clean async interfaces for external API calls. They can be reused throughout the app.

Usage:
    # Initialize with API key from Secrets Management
    openai_client = OpenAIClient(api_key=secret_value)
    result = await openai_client.chat_completion(messages=[...])

    firecrawl_client = FirecrawlClient(api_key=secret_value)
    results = await firecrawl_client.search(query="...")
"""

import httpx
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """
    Centralized OpenAI API client.

    Provides clean async methods for:
    - Chat completions
    - Embeddings
    - Other OpenAI endpoints
    """

    def __init__(self, api_key: str, default_model: str = "gpt-4"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (from Secrets Management)
            default_model: Default model to use (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.api_key = api_key
        self.default_model = default_model
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to OpenAI

        Returns:
            Generated text response

        Example:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a blog post about Python."}
            ]
            response = await client.chat_completion(messages)
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            content = response.choices[0].message.content

            logger.info(
                "OpenAI chat completion successful",
                model=model or self.default_model,
                tokens_used=response.usage.total_tokens if response.usage else None
            )

            return content

        except Exception as e:
            logger.exception("OpenAI chat completion failed")
            raise

    async def chat_completion_with_metadata(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a chat completion with full response metadata.

        Returns:
            Dict with 'content', 'model', 'tokens_used', 'finish_reason'
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None
            }

        except Exception as e:
            logger.exception("OpenAI chat completion failed")
            raise


class FirecrawlClient:
    """
    Centralized Firecrawl API client.

    Provides clean async methods for:
    - Google search
    - Web scraping
    - Batch operations
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: str, timeout: float = 60.0):
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key (from Secrets Management)
            timeout: Request timeout in seconds (default 60)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        lang: str = "en",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search Google via Firecrawl.

        Args:
            query: Search query
            limit: Number of results to return (max 10)
            lang: Language code (default: en)
            **kwargs: Additional parameters

        Returns:
            List of search results with 'title', 'url', 'markdown' (if available)

        Example:
            results = await client.search("Python web scraping", limit=5)
            for result in results:
                print(result['title'], result['url'])
        """
        url = f"{self.BASE_URL}/search"
        payload = {
            "query": query,
            "limit": limit,
            "lang": lang,
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()

            results = data.get("data", [])

            logger.info(
                "Firecrawl search successful",
                query=query,
                results_count=len(results)
            )

            return results

        except httpx.HTTPError as e:
            logger.error(f"Firecrawl search HTTP error: {e}", query=query)
            raise
        except Exception as e:
            logger.exception("Firecrawl search failed", query=query)
            raise

    async def scrape(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            formats: List of formats to return (default: ["markdown"])
                     Options: "markdown", "html", "rawHtml", "screenshot"
            **kwargs: Additional parameters

        Returns:
            Dict with scraping results containing 'markdown', 'html', etc.

        Example:
            result = await client.scrape("https://example.com")
            markdown = result.get("markdown", "")
        """
        if formats is None:
            formats = ["markdown"]

        scrape_url = f"{self.BASE_URL}/scrape"
        payload = {
            "url": url,
            "formats": formats,
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(scrape_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()

            result = data.get("data", {})

            logger.info(
                "Firecrawl scrape successful",
                url=url,
                formats=formats,
                content_length=len(result.get("markdown", ""))
            )

            return result

        except httpx.HTTPError as e:
            logger.error(f"Firecrawl scrape HTTP error: {e}", url=url)
            raise
        except Exception as e:
            logger.exception("Firecrawl scrape failed", url=url)
            raise

    async def scrape_batch(
        self,
        urls: List[str],
        formats: Optional[List[str]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            formats: List of formats to return
            **kwargs: Additional parameters

        Returns:
            List of scraping results (same order as input URLs)

        Note: This makes parallel requests. For large batches, consider
              using Firecrawl's batch API endpoint instead.
        """
        import asyncio

        tasks = [self.scrape(url, formats, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error dicts
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scrape URL {urls[idx]}: {result}")
                processed_results.append({
                    "url": urls[idx],
                    "error": str(result),
                    "markdown": ""
                })
            else:
                processed_results.append(result)

        return processed_results


# Convenience functions for backward compatibility with existing code
async def get_openai_client_from_secret(
    db_session,
    tenant_id: Optional[str] = None,
    secret_name: str = "OpenAI API Key",
    accessed_by_user = None
) -> OpenAIClient:
    """
    Helper function to get OpenAI client from Secrets Management.

    Args:
        db_session: Database session
        tenant_id: Tenant ID for secrets retrieval
        secret_name: Name of the secret in Secrets Management
        accessed_by_user: User accessing the secret (for audit trail)

    Returns:
        Initialized OpenAIClient

    Example:
        from app.features.core.utils.external_api_clients import get_openai_client_from_secret

        client = await get_openai_client_from_secret(db, tenant_id, accessed_by_user=current_user)
        response = await client.chat_completion(messages=[...])
    """
    from app.features.administration.secrets.services import SecretsManagementService

    secrets_service = SecretsManagementService(db_session, tenant_id)

    # Get secret metadata
    secret = await secrets_service.get_secret_by_name(secret_name)
    if not secret:
        raise ValueError(f"Secret '{secret_name}' not found in Secrets Management")

    # Get decrypted value
    secret_value = await secrets_service.get_secret_value(
        secret_id=secret.id,
        accessed_by_user=accessed_by_user
    )

    return OpenAIClient(api_key=secret_value.value)


async def get_firecrawl_client_from_secret(
    db_session,
    tenant_id: Optional[str] = None,
    secret_name: str = "Firecrawl API Key",
    accessed_by_user = None
) -> FirecrawlClient:
    """
    Helper function to get Firecrawl client from Secrets Management.

    Args:
        db_session: Database session
        tenant_id: Tenant ID for secrets retrieval
        secret_name: Name of the secret in Secrets Management
        accessed_by_user: User accessing the secret (for audit trail)

    Returns:
        Initialized FirecrawlClient

    Example:
        from app.features.core.utils.external_api_clients import get_firecrawl_client_from_secret

        client = await get_firecrawl_client_from_secret(db, tenant_id, accessed_by_user=current_user)
        results = await client.search("Python tutorials")
    """
    from app.features.administration.secrets.services import SecretsManagementService

    secrets_service = SecretsManagementService(db_session, tenant_id)

    # Get secret metadata
    secret = await secrets_service.get_secret_by_name(secret_name)
    if not secret:
        raise ValueError(f"Secret '{secret_name}' not found in Secrets Management")

    # Get decrypted value
    secret_value = await secrets_service.get_secret_value(
        secret_id=secret.id,
        accessed_by_user=accessed_by_user
    )

    return FirecrawlClient(api_key=secret_value.value)
