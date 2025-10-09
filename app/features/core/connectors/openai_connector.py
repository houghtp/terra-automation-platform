"""
OpenAI SDK-based connector for LLM and embedding operations.
"""

from typing import Dict, Any, List, Optional
import openai
from openai import AsyncOpenAI
from ..base import LLMConnector, EmbeddingConnector, ConnectorResult, ConnectorType, ConnectorConfig
from ..utils import with_rate_limit, with_metrics, with_retry, ConnectorAuth
import structlog

logger = structlog.get_logger(__name__)


class OpenAIConnector(LLMConnector, EmbeddingConnector):
    """
    OpenAI connector using the official OpenAI Python SDK.

    Supports both text generation and embedding creation.
    """

    def __init__(self, config: ConnectorConfig, credentials: Dict[str, Any]):
        """Initialize OpenAI connector."""
        super().__init__(config, credentials)
        self._client: Optional[AsyncOpenAI] = None
        self._default_model = "gpt-3.5-turbo"
        self._default_embedding_model = "text-embedding-ada-002"

    async def initialize(self) -> ConnectorResult[bool]:
        """Initialize the OpenAI client."""
        try:
            api_key = ConnectorAuth.get_api_key(self.credentials, "api_key")

            # Initialize OpenAI client
            client_kwargs = {
                "api_key": api_key,
                "timeout": self.config.timeout_seconds,
            }

            # Support custom base URL for OpenAI-compatible APIs
            if self.config.api_base_url:
                client_kwargs["base_url"] = self.config.api_base_url

            self._client = AsyncOpenAI(**client_kwargs)

            # Test the connection
            test_result = await self.test_connection()
            if not test_result.success:
                return test_result

            self.logger.info("OpenAI connector initialized successfully")
            return ConnectorResult[bool](success=True, data=True)

        except Exception as e:
            return self._handle_error(e, "initialize")

    @with_metrics("test_connection")
    @with_retry(max_attempts=2)
    async def test_connection(self) -> ConnectorResult[bool]:
        """Test connection to OpenAI API."""
        try:
            if not self._client:
                return ConnectorResult[bool](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            # Test with a simple models list call
            models = await self._client.models.list()

            return ConnectorResult[bool](
                success=True,
                data=True,
                metadata={"models_count": len(models.data)}
            )

        except Exception as e:
            return self._handle_error(e, "test_connection")

    async def get_schema(self) -> ConnectorResult[Dict[str, Any]]:
        """Get configuration schema for OpenAI connector."""
        schema = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "OpenAI API key",
                    "format": "password"
                },
                "organization_id": {
                    "type": "string",
                    "title": "Organization ID",
                    "description": "OpenAI organization ID (optional)"
                },
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "description": "Custom base URL for OpenAI-compatible APIs (optional)",
                    "format": "uri"
                },
                "default_model": {
                    "type": "string",
                    "title": "Default Model",
                    "description": "Default model to use for text generation",
                    "default": "gpt-3.5-turbo",
                    "enum": [
                        "gpt-4o",
                        "gpt-4o-mini",
                        "gpt-4-turbo",
                        "gpt-4",
                        "gpt-3.5-turbo"
                    ]
                },
                "default_embedding_model": {
                    "type": "string",
                    "title": "Default Embedding Model",
                    "description": "Default model to use for embeddings",
                    "default": "text-embedding-ada-002",
                    "enum": [
                        "text-embedding-3-large",
                        "text-embedding-3-small",
                        "text-embedding-ada-002"
                    ]
                }
            },
            "required": ["api_key"],
            "additionalProperties": False
        }

        return ConnectorResult[Dict[str, Any]](success=True, data=schema)

    @with_metrics("generate_text")
    @with_rate_limit(requests_per_minute=60)
    @with_retry(max_attempts=3)
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> ConnectorResult[str]:
        """
        Generate text using OpenAI's chat completion API.

        Args:
            prompt: Input prompt
            model: Model name (defaults to configured default)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            ConnectorResult containing generated text
        """
        try:
            if not self._client:
                return ConnectorResult[str](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            # Use provided model or default
            model_name = model or self._default_model

            # Prepare messages format for chat completion
            messages = [{"role": "user", "content": prompt}]

            # Set default parameters
            params = {
                "model": model_name,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 1.0),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
            }

            # Add any additional parameters
            for key, value in kwargs.items():
                if key not in params and value is not None:
                    params[key] = value

            # Make the API call
            response = await self._client.chat.completions.create(**params)

            # Extract the generated text
            generated_text = response.choices[0].message.content

            return ConnectorResult[str](
                success=True,
                data=generated_text,
                metadata={
                    "model": model_name,
                    "usage": response.usage.model_dump() if response.usage else {},
                    "finish_reason": response.choices[0].finish_reason
                }
            )

        except Exception as e:
            return self._handle_error(e, "generate_text")

    @with_metrics("get_models")
    @with_rate_limit(requests_per_minute=30)
    async def get_models(self) -> ConnectorResult[List[Dict[str, Any]]]:
        """Get available models from OpenAI."""
        try:
            if not self._client:
                return ConnectorResult[List[Dict[str, Any]]](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            models_response = await self._client.models.list()

            # Filter and format models
            models = []
            for model in models_response.data:
                models.append({
                    "id": model.id,
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "object": model.object
                })

            # Sort by name for consistency
            models.sort(key=lambda x: x["id"])

            return ConnectorResult[List[Dict[str, Any]]](
                success=True,
                data=models,
                metadata={"total_models": len(models)}
            )

        except Exception as e:
            return self._handle_error(e, "get_models")

    @with_metrics("create_embeddings")
    @with_rate_limit(requests_per_minute=100)
    @with_retry(max_attempts=3)
    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> ConnectorResult[List[List[float]]]:
        """
        Create embeddings for the given texts.

        Args:
            texts: List of texts to embed
            model: Embedding model name (defaults to configured default)

        Returns:
            ConnectorResult containing list of embedding vectors
        """
        try:
            if not self._client:
                return ConnectorResult[List[List[float]]](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            if not texts:
                return ConnectorResult[List[List[float]]](
                    success=False,
                    error="No texts provided for embedding",
                    error_code="INVALID_INPUT"
                )

            # Use provided model or default
            model_name = model or self._default_embedding_model

            # Create embeddings
            response = await self._client.embeddings.create(
                model=model_name,
                input=texts
            )

            # Extract embedding vectors
            embeddings = [embedding.embedding for embedding in response.data]

            return ConnectorResult[List[List[float]]](
                success=True,
                data=embeddings,
                metadata={
                    "model": model_name,
                    "usage": response.usage.model_dump() if response.usage else {},
                    "total_texts": len(texts),
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0
                }
            )

        except Exception as e:
            return self._handle_error(e, "create_embeddings")

    async def cleanup(self) -> None:
        """Clean up OpenAI client resources."""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                self.logger.warning(f"Error closing OpenAI client: {e}")
            finally:
                self._client = None


# Configuration for OpenAI connector
OPENAI_CONFIG = ConnectorConfig(
    name="openai",
    display_name="OpenAI",
    description="OpenAI GPT models for text generation and embeddings",
    connector_type=ConnectorType.AI_LLM,
    version="1.0.0",
    rate_limit_per_minute=60,
    timeout_seconds=30,
    retry_attempts=3,
    api_base_url="https://api.openai.com/v1",
    supports_streaming=True,
    supports_batch=True,
    max_batch_size=2048  # OpenAI's limit for embedding batch size
)
