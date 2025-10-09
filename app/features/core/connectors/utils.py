"""
Connector utilities for authentication, rate limiting, and configuration.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from functools import wraps
import structlog
from collections import defaultdict, deque
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ConnectorAuth:
    """Authentication utilities for connectors."""

    @staticmethod
    def get_api_key(credentials: Dict[str, Any], key_name: str = "api_key") -> str:
        """Extract API key from credentials."""
        api_key = credentials.get(key_name)
        if not api_key:
            raise ValueError(f"Missing {key_name} in credentials")
        return api_key

    @staticmethod
    def get_bearer_token(credentials: Dict[str, Any], token_name: str = "access_token") -> str:
        """Extract bearer token from credentials."""
        token = credentials.get(token_name)
        if not token:
            raise ValueError(f"Missing {token_name} in credentials")
        return f"Bearer {token}"

    @staticmethod
    def validate_oauth_credentials(credentials: Dict[str, Any]) -> Dict[str, str]:
        """Validate and extract OAuth credentials."""
        required_fields = ["client_id", "client_secret"]
        missing_fields = [field for field in required_fields if not credentials.get(field)]

        if missing_fields:
            raise ValueError(f"Missing OAuth credentials: {missing_fields}")

        return {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "access_token": credentials.get("access_token"),
            "refresh_token": credentials.get("refresh_token")
        }


class RateLimiter:
    """
    Rate limiter for connector operations.
    Uses token bucket algorithm for smooth rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        self.bucket_size = min(requests_per_minute, 100)  # Max burst size
        self.tokens = self.bucket_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the rate limiter.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if rate limited
        """
        async with self._lock:
            now = time.time()
            time_passed = now - self.last_update
            self.last_update = now

            # Add tokens based on time passed
            tokens_to_add = time_passed * self.requests_per_second
            self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens needed
        """
        while not await self.acquire(tokens):
            # Calculate wait time based on current deficit
            wait_time = max(0.1, tokens / self.requests_per_second)
            await asyncio.sleep(wait_time)


class ConnectorMetrics:
    """Metrics collection for connector operations."""

    def __init__(self):
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.response_times = defaultdict(list)
        self.last_requests = defaultdict(lambda: deque(maxlen=100))

    def record_request(self, connector_name: str, operation: str, response_time: float, success: bool):
        """Record a connector request for metrics."""
        key = f"{connector_name}.{operation}"
        self.request_counts[key] += 1
        self.response_times[key].append(response_time)
        self.last_requests[key].append({
            "timestamp": time.time(),
            "response_time": response_time,
            "success": success
        })

        if not success:
            self.error_counts[key] += 1

    def get_metrics(self, connector_name: str) -> Dict[str, Any]:
        """Get metrics for a specific connector."""
        prefix = f"{connector_name}."

        metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "operations": {}
        }

        for key, count in self.request_counts.items():
            if key.startswith(prefix):
                operation = key[len(prefix):]
                response_times = self.response_times[key]
                error_count = self.error_counts[key]

                metrics["total_requests"] += count
                metrics["total_errors"] += error_count

                metrics["operations"][operation] = {
                    "request_count": count,
                    "error_count": error_count,
                    "error_rate": error_count / count if count > 0 else 0,
                    "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                    "min_response_time": min(response_times) if response_times else 0,
                    "max_response_time": max(response_times) if response_times else 0
                }

        return metrics


# Global metrics instance
connector_metrics = ConnectorMetrics()


def with_rate_limit(requests_per_minute: int = 60):
    """
    Decorator to add rate limiting to connector methods.

    Args:
        requests_per_minute: Rate limit for the decorated method
    """
    rate_limiter = RateLimiter(requests_per_minute)

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            await rate_limiter.wait_for_tokens()
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


def with_metrics(operation: str):
    """
    Decorator to add metrics collection to connector methods.

    Args:
        operation: Name of the operation for metrics
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            success = False

            try:
                result = await func(self, *args, **kwargs)
                success = getattr(result, 'success', True)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                response_time = time.time() - start_time
                connector_metrics.record_request(
                    connector_name=self.name,
                    operation=operation,
                    response_time=response_time,
                    success=success
                )
        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, backoff_factor: float = 1.0):
    """
    Decorator to add retry logic to connector methods.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff factor
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry authentication errors
                    if "unauthorized" in str(e).lower() or "authentication" in str(e).lower():
                        raise

                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Retry attempt {attempt + 1} for {func.__name__} after {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All retry attempts failed for {func.__name__}: {e}")

            raise last_exception
        return wrapper
    return decorator


class ConnectorConfig(BaseModel):
    """Enhanced connector configuration with validation."""

    name: str = Field(..., description="Connector name")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Connector description")
    version: str = Field(default="1.0.0", description="Connector version")

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(default=60, description="Requests per minute limit")
    burst_limit: Optional[int] = Field(default=10, description="Burst request limit")

    # Timeouts and retries
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_backoff_factor: float = Field(default=1.0, description="Exponential backoff factor")

    # API configuration
    api_base_url: Optional[str] = Field(default=None, description="Base API URL")
    api_version: Optional[str] = Field(default=None, description="API version")

    # Features
    supports_streaming: bool = Field(default=False, description="Supports streaming responses")
    supports_batch: bool = Field(default=False, description="Supports batch operations")

    # Resource limits
    max_batch_size: Optional[int] = Field(default=None, description="Maximum batch size")
    max_content_length: Optional[int] = Field(default=None, description="Maximum content length")

    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow additional fields for connector-specific config
