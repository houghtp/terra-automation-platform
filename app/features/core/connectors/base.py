"""
Base connector interface for all SDK-based integrations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class ConnectorType(str, Enum):
    """Connector type classifications."""
    AI_LLM = "ai_llm"
    AI_EMBEDDING = "ai_embedding"
    WEB_SCRAPING = "web_scraping"
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    CRM = "crm"
    MARKETING = "marketing"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    DATABASE = "database"
    API = "api"
    WEBHOOK = "webhook"


class ConnectorError(Exception):
    """Base exception for connector operations."""

    def __init__(self, message: str, code: str = "CONNECTOR_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConnectorResult(BaseModel, Generic[T]):
    """Standard result wrapper for connector operations."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConnectorConfig(BaseModel):
    """Base configuration for connectors."""
    name: str
    connector_type: ConnectorType
    enabled: bool = True
    rate_limit_per_minute: Optional[int] = None
    timeout_seconds: int = 30
    retry_attempts: int = 3
    api_base_url: Optional[str] = None
    version: str = "1.0.0"


class BaseConnector(ABC):
    """
    Abstract base class for all SDK-based connectors.

    This provides a common interface for interacting with external services
    using their official SDKs where possible, with fallback to REST APIs.
    """

    def __init__(self, config: ConnectorConfig, credentials: Dict[str, Any]):
        """
        Initialize the connector with configuration and credentials.

        Args:
            config: Connector configuration
            credentials: Authentication credentials (API keys, tokens, etc.)
        """
        self.config = config
        self.credentials = credentials
        self.logger = structlog.get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._client = None

    @property
    def name(self) -> str:
        """Get connector name."""
        return self.config.name

    @property
    def connector_type(self) -> ConnectorType:
        """Get connector type."""
        return self.config.connector_type

    @abstractmethod
    async def initialize(self) -> ConnectorResult[bool]:
        """
        Initialize the connector and authenticate with the service.

        Returns:
            ConnectorResult indicating success/failure of initialization
        """
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectorResult[bool]:
        """
        Test the connection to the external service.

        Returns:
            ConnectorResult indicating if the connection is working
        """
        pass

    @abstractmethod
    async def get_schema(self) -> ConnectorResult[Dict[str, Any]]:
        """
        Get the configuration schema for this connector.

        Returns:
            ConnectorResult containing the JSON schema for connector configuration
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up resources when the connector is no longer needed.
        """
        if hasattr(self._client, 'close'):
            try:
                await self._client.close()
            except Exception as e:
                self.logger.warning(f"Error closing client: {e}")
        self._client = None

    def _handle_error(self, error: Exception, operation: str) -> ConnectorResult[Any]:
        """
        Standard error handling for connector operations.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed

        Returns:
            ConnectorResult with error information
        """
        error_msg = f"Error in {operation}: {str(error)}"
        self.logger.exception(error_msg)

        # Map common SDK errors to our error codes
        error_code = "CONNECTOR_ERROR"
        if "authentication" in str(error).lower() or "unauthorized" in str(error).lower():
            error_code = "AUTH_ERROR"
        elif "rate limit" in str(error).lower() or "too many requests" in str(error).lower():
            error_code = "RATE_LIMIT_ERROR"
        elif "timeout" in str(error).lower():
            error_code = "TIMEOUT_ERROR"
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            error_code = "NETWORK_ERROR"

        return ConnectorResult[Any](
            success=False,
            error=error_msg,
            error_code=error_code,
            metadata={"operation": operation, "error_type": type(error).__name__}
        )


class LLMConnector(BaseConnector):
    """Base class for Large Language Model connectors."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> ConnectorResult[str]:
        """
        Generate text using the LLM.

        Args:
            prompt: Input prompt
            model: Model name (if supported)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            ConnectorResult containing generated text
        """
        pass

    @abstractmethod
    async def get_models(self) -> ConnectorResult[List[Dict[str, Any]]]:
        """
        Get available models for this LLM service.

        Returns:
            ConnectorResult containing list of available models
        """
        pass


class EmbeddingConnector(BaseConnector):
    """Base class for embedding/vector connectors."""

    @abstractmethod
    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> ConnectorResult[List[List[float]]]:
        """
        Create embeddings for the given texts.

        Args:
            texts: List of texts to embed
            model: Model name (if supported)

        Returns:
            ConnectorResult containing list of embedding vectors
        """
        pass


class WebScrapingConnector(BaseConnector):
    """Base class for web scraping connectors."""

    @abstractmethod
    async def scrape_url(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ConnectorResult[Dict[str, Any]]:
        """
        Scrape content from a URL.

        Args:
            url: URL to scrape
            options: Scraping options (selectors, wait time, etc.)

        Returns:
            ConnectorResult containing scraped content
        """
        pass

    @abstractmethod
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
        pass
