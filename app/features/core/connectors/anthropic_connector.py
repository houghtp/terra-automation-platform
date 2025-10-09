"""
Anthropic Claude SDK-based connector for LLM operations.
"""

from typing import Dict, Any, List, Optional
import anthropic
from anthropic import AsyncAnthropic
from ..base import LLMConnector, ConnectorResult, ConnectorType, ConnectorConfig
from ..utils import with_rate_limit, with_metrics, with_retry, ConnectorAuth
import structlog

logger = structlog.get_logger(__name__)


class AnthropicConnector(LLMConnector):
    """
    Anthropic Claude connector using the official Anthropic Python SDK.

    Supports Claude models for text generation and conversation.
    """

    def __init__(self, config: ConnectorConfig, credentials: Dict[str, Any]):
        """Initialize Anthropic connector."""
        super().__init__(config, credentials)
        self._client: Optional[AsyncAnthropic] = None
        self._default_model = "claude-3-haiku-20240307"
        self._available_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

    async def initialize(self) -> ConnectorResult[bool]:
        """Initialize the Anthropic client."""
        try:
            api_key = ConnectorAuth.get_api_key(self.credentials, "api_key")

            # Initialize Anthropic client
            client_kwargs = {
                "api_key": api_key,
                "timeout": self.config.timeout_seconds,
            }

            # Support custom base URL if needed
            if self.config.api_base_url:
                client_kwargs["base_url"] = self.config.api_base_url

            self._client = AsyncAnthropic(**client_kwargs)

            # Test the connection
            test_result = await self.test_connection()
            if not test_result.success:
                return test_result

            self.logger.info("Anthropic connector initialized successfully")
            return ConnectorResult[bool](success=True, data=True)

        except Exception as e:
            return self._handle_error(e, "initialize")

    @with_metrics("test_connection")
    @with_retry(max_attempts=2)
    async def test_connection(self) -> ConnectorResult[bool]:
        """Test connection to Anthropic API."""
        try:
            if not self._client:
                return ConnectorResult[bool](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            # Test with a simple message to verify API key works
            test_message = await self._client.messages.create(
                model=self._default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )

            return ConnectorResult[bool](
                success=True,
                data=True,
                metadata={
                    "model": self._default_model,
                    "usage": test_message.usage.model_dump() if test_message.usage else {}
                }
            )

        except Exception as e:
            return self._handle_error(e, "test_connection")

    async def get_schema(self) -> ConnectorResult[Dict[str, Any]]:
        """Get configuration schema for Anthropic connector."""
        schema = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "Anthropic API key",
                    "format": "password"
                },
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "description": "Custom base URL for Anthropic API (optional)",
                    "format": "uri"
                },
                "default_model": {
                    "type": "string",
                    "title": "Default Model",
                    "description": "Default Claude model to use",
                    "default": "claude-3-haiku-20240307",
                    "enum": self._available_models
                },
                "default_max_tokens": {
                    "type": "integer",
                    "title": "Default Max Tokens",
                    "description": "Default maximum tokens for responses",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 4096
                },
                "system_prompt": {
                    "type": "string",
                    "title": "System Prompt",
                    "description": "Default system prompt for conversations (optional)"
                }
            },
            "required": ["api_key"],
            "additionalProperties": False
        }

        return ConnectorResult[Dict[str, Any]](success=True, data=schema)

    @with_metrics("generate_text")
    @with_rate_limit(requests_per_minute=50)  # Anthropic rate limits
    @with_retry(max_attempts=3)
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> ConnectorResult[str]:
        """
        Generate text using Anthropic's Claude model.

        Args:
            prompt: Input prompt
            model: Model name (defaults to configured default)
            **kwargs: Additional parameters (temperature, max_tokens, system, etc.)

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

            # Validate model
            if model_name not in self._available_models:
                return ConnectorResult[str](
                    success=False,
                    error=f"Model {model_name} not available. Available models: {self._available_models}",
                    error_code="INVALID_MODEL"
                )

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Set parameters
            params = {
                "model": model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
            }

            # Add optional parameters
            if "temperature" in kwargs:
                params["temperature"] = kwargs["temperature"]
            if "top_p" in kwargs:
                params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                params["top_k"] = kwargs["top_k"]
            if "system" in kwargs:
                params["system"] = kwargs["system"]

            # Make the API call
            response = await self._client.messages.create(**params)

            # Extract the generated text
            generated_text = ""
            for content_block in response.content:
                if content_block.type == "text":
                    generated_text += content_block.text

            return ConnectorResult[str](
                success=True,
                data=generated_text,
                metadata={
                    "model": model_name,
                    "usage": response.usage.model_dump() if response.usage else {},
                    "stop_reason": response.stop_reason,
                    "stop_sequence": response.stop_sequence
                }
            )

        except Exception as e:
            return self._handle_error(e, "generate_text")

    @with_metrics("get_models")
    async def get_models(self) -> ConnectorResult[List[Dict[str, Any]]]:
        """Get available Claude models."""
        try:
            # Return the static list of available models
            # Anthropic doesn't have a models API endpoint like OpenAI
            models = []
            for model_id in self._available_models:
                model_info = {
                    "id": model_id,
                    "object": "model",
                    "owned_by": "anthropic"
                }

                # Add model-specific information
                if "opus" in model_id:
                    model_info.update({
                        "description": "Most powerful model, best for complex tasks",
                        "context_window": 200000,
                        "max_output": 4096
                    })
                elif "sonnet" in model_id:
                    model_info.update({
                        "description": "Balanced performance and speed",
                        "context_window": 200000,
                        "max_output": 4096
                    })
                elif "haiku" in model_id:
                    model_info.update({
                        "description": "Fastest model, good for simple tasks",
                        "context_window": 200000,
                        "max_output": 4096
                    })

                models.append(model_info)

            return ConnectorResult[List[Dict[str, Any]]](
                success=True,
                data=models,
                metadata={"total_models": len(models)}
            )

        except Exception as e:
            return self._handle_error(e, "get_models")

    @with_metrics("create_conversation")
    @with_rate_limit(requests_per_minute=40)
    @with_retry(max_attempts=3)
    async def create_conversation(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> ConnectorResult[str]:
        """
        Create a conversation with multiple messages.

        Args:
            messages: List of messages with role and content
            model: Model name (defaults to configured default)
            **kwargs: Additional parameters

        Returns:
            ConnectorResult containing conversation response
        """
        try:
            if not self._client:
                return ConnectorResult[str](
                    success=False,
                    error="Client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED"
                )

            if not messages:
                return ConnectorResult[str](
                    success=False,
                    error="Messages list is empty",
                    error_code="INVALID_INPUT"
                )

            # Use provided model or default
            model_name = model or self._default_model

            # Validate messages format for Anthropic
            formatted_messages = []
            for msg in messages:
                if "role" not in msg or "content" not in msg:
                    return ConnectorResult[str](
                        success=False,
                        error="Each message must have 'role' and 'content' fields",
                        error_code="INVALID_MESSAGE_FORMAT"
                    )

                # Anthropic only supports 'user' and 'assistant' roles in messages
                if msg["role"] not in ["user", "assistant"]:
                    continue

                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Set parameters
            params = {
                "model": model_name,
                "messages": formatted_messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
            }

            # Add optional parameters
            if "temperature" in kwargs:
                params["temperature"] = kwargs["temperature"]
            if "system" in kwargs:
                params["system"] = kwargs["system"]

            # Make the API call
            response = await self._client.messages.create(**params)

            # Extract the response text
            response_text = ""
            for content_block in response.content:
                if content_block.type == "text":
                    response_text += content_block.text

            return ConnectorResult[str](
                success=True,
                data=response_text,
                metadata={
                    "model": model_name,
                    "usage": response.usage.model_dump() if response.usage else {},
                    "stop_reason": response.stop_reason,
                    "message_count": len(formatted_messages)
                }
            )

        except Exception as e:
            return self._handle_error(e, "create_conversation")

    async def cleanup(self) -> None:
        """Clean up Anthropic client resources."""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                self.logger.warning(f"Error closing Anthropic client: {e}")
            finally:
                self._client = None


# Configuration for Anthropic connector
ANTHROPIC_CONFIG = ConnectorConfig(
    name="anthropic",
    display_name="Anthropic Claude",
    description="Anthropic Claude models for advanced text generation and conversation",
    connector_type=ConnectorType.AI_LLM,
    version="1.0.0",
    rate_limit_per_minute=50,
    timeout_seconds=30,
    retry_attempts=3,
    api_base_url="https://api.anthropic.com",
    supports_streaming=True,
    supports_batch=False,  # Anthropic doesn't support batch operations yet
    max_content_length=200000  # Claude's context window
)
