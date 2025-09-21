"""
Rate limiting middleware for FastAPI applications.
Integrates with the tenant system and provides comprehensive rate limiting.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.features.core.rate_limiting import (
    RateLimiter,
    RateLimitStorage,
    MemoryRateLimitStorage,
    RedisRateLimitStorage,
    DEFAULT_RATE_LIMIT_RULES,
    RateLimitRule
)

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that applies rate limits based on various scopes.
    Integrates with tenant context and authentication.
    """

    def __init__(self, app, storage: Optional[RateLimitStorage] = None, rules: Optional[list] = None):
        super().__init__(app)

        # Initialize storage backend
        if storage is None:
            storage = self._create_default_storage()

        # Initialize rules
        if rules is None:
            rules = DEFAULT_RATE_LIMIT_RULES

        self.rate_limiter = RateLimiter(storage=storage, rules=rules)
        self.enabled = self._is_rate_limiting_enabled()

        logger.info(f"Rate limiting middleware initialized (enabled: {self.enabled})")

    def _create_default_storage(self) -> RateLimitStorage:
        """Create default storage backend based on environment."""
        import os

        environment = os.getenv("ENVIRONMENT", "development").lower()
        redis_url = os.getenv("REDIS_URL", os.getenv("RATE_LIMIT_REDIS_URL"))

        if environment == "production" and redis_url:
            try:
                return RedisRateLimitStorage(redis_url)
            except ImportError:
                logger.warning("Redis not available, falling back to memory storage")
                return MemoryRateLimitStorage()
        else:
            return MemoryRateLimitStorage()

    def _is_rate_limiting_enabled(self) -> bool:
        """Check if rate limiting is enabled via environment variables."""
        import os
        return os.getenv("RATE_LIMITING_ENABLED", "true").lower() in ("true", "1", "yes")

    def _extract_context(self, request: Request) -> Dict[str, Any]:
        """Extract context information from the request for rate limiting."""
        context = {}

        # Client IP
        client_ip = request.client.host if request.client else "unknown"
        if hasattr(request, "headers"):
            # Check for forwarded IP headers
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            else:
                real_ip = request.headers.get("X-Real-IP")
                if real_ip:
                    client_ip = real_ip

        context["client_ip"] = client_ip

        # Endpoint information
        context["endpoint"] = request.url.path
        context["method"] = request.method

        # Tenant information (from middleware context variables)
        try:
            from app.middleware.tenant import tenant_ctx_var
            tenant_id = tenant_ctx_var.get(None)
            if tenant_id:
                context["tenant_id"] = tenant_id
        except Exception:
            # Fallback to header
            context["tenant_id"] = request.headers.get("X-Tenant-ID", "unknown")

        # User information (from auth context)
        user_id = None
        try:
            # Try to get user from request state (set by auth dependencies)
            if hasattr(request.state, "current_user"):
                user = request.state.current_user
                if user:
                    user_id = str(user.id)
                    context["user_role"] = getattr(user, "role", "user")
        except Exception:
            pass

        if not user_id:
            # Try to extract from JWT token
            try:
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    from app.features.auth.jwt_utils import JWTUtils
                    token = auth_header.split(" ")[1]
                    token_data = JWTUtils.verify_token(token)
                    if token_data:
                        user_id = token_data.user_id
                        context["user_role"] = token_data.role
            except Exception:
                pass

        context["user_id"] = user_id or f"anon_{client_ip}"

        # Request metadata
        context["user_agent"] = request.headers.get("user-agent", "unknown")
        context["authenticated"] = user_id is not None and not user_id.startswith("anon_")

        return context

    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Determine if rate limiting should be skipped for this request."""
        path = request.url.path

        # Skip health checks
        if path in ["/health", "/health/db", "/health/detailed"]:
            return True

        # Skip static files
        if path.startswith("/static/"):
            return True

        # Skip internal endpoints
        if path.startswith("/_internal/"):
            return True

        return False

    def _create_rate_limit_response(self, context: Dict[str, Any], rate_limit_result) -> JSONResponse:
        """Create a rate limit exceeded response."""
        headers = rate_limit_result.to_headers()

        # Add additional context to response
        response_data = {
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Try again in {rate_limit_result.retry_after} seconds.",
            "details": {
                "remaining": rate_limit_result.remaining,
                "reset_at": rate_limit_result.reset_time.isoformat(),
                "retry_after": rate_limit_result.retry_after
            }
        }

        # Add rule information for debugging (in development)
        import os
        if os.getenv("ENVIRONMENT", "development").lower() == "development" and rate_limit_result.rule_matched:
            response_data["debug"] = {
                "rule_scope": rate_limit_result.rule_matched.scope.value,
                "rule_limit": rate_limit_result.rule_matched.limit,
                "rule_window": rate_limit_result.rule_matched.window,
                "context": {
                    "tenant_id": context.get("tenant_id"),
                    "user_id": context.get("user_id", "").replace(context.get("client_ip", ""), "***") if context.get("user_id", "").startswith("anon_") else context.get("user_id"),
                    "endpoint": context.get("endpoint"),
                    "authenticated": context.get("authenticated")
                }
            }

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=response_data,
            headers=headers
        )

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        # Skip if rate limiting is disabled
        if not self.enabled:
            return await call_next(request)

        # Skip certain endpoints
        if self._should_skip_rate_limiting(request):
            return await call_next(request)

        try:
            # Extract context for rate limiting
            context = self._extract_context(request)

            # Check rate limits
            rate_limit_result = await self.rate_limiter.check_rate_limit(context)

            if not rate_limit_result.allowed:
                # Rate limit exceeded - log security event
                try:
                    from app.features.core.structured_logging import security_logger
                    security_logger.log_rate_limit_exceeded(
                        rule_scope=rate_limit_result.rule_matched.scope.value,
                        limit=rate_limit_result.rule_matched.limit,
                        window=rate_limit_result.rule_matched.window,
                        ip_address=context.get('client_ip'),
                        tenant_id=context.get('tenant_id'),
                        user_id=context.get('user_id'),
                        endpoint=context.get('endpoint'),
                        user_agent=context.get('user_agent')
                    )
                except ImportError:
                    # Fallback to basic logging
                    logger.warning(
                        f"Rate limit exceeded - "
                        f"IP: {context.get('client_ip')}, "
                        f"Tenant: {context.get('tenant_id')}, "
                        f"User: {context.get('user_id')}, "
                        f"Endpoint: {context.get('endpoint')}"
                    )

                # Record metrics
                try:
                    from app.features.core.metrics import metrics
                    usage_ratio = 1.0  # Rate limit exceeded, so usage is at 100%
                    metrics.record_rate_limit_hit(
                        scope=rate_limit_result.rule_matched.scope.value,
                        rule_type=rate_limit_result.rule_matched.algorithm.value,
                        usage_ratio=usage_ratio,
                        tenant_id=context.get('tenant_id', 'unknown')
                    )
                except ImportError:
                    pass

                return self._create_rate_limit_response(context, rate_limit_result)

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful responses
            if hasattr(response, "headers"):
                for header_name, header_value in rate_limit_result.to_headers().items():
                    response.headers[header_name] = header_value

            return response

        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Fail open - allow request if rate limiting fails
            return await call_next(request)


def create_rate_limit_middleware(
    storage: Optional[RateLimitStorage] = None,
    rules: Optional[list] = None
) -> RateLimitMiddleware:
    """
    Factory function to create rate limiting middleware with custom configuration.

    Args:
        storage: Custom storage backend (defaults to auto-detected)
        rules: Custom rate limiting rules (defaults to DEFAULT_RATE_LIMIT_RULES)

    Returns:
        Configured RateLimitMiddleware instance
    """
    return lambda app: RateLimitMiddleware(app, storage=storage, rules=rules)


# Example custom rule configurations for different use cases

def create_strict_rate_limits():
    """Create strict rate limits for high-security environments."""
    from app.features.core.rate_limiting import RateLimitRule, RateLimitScope, RateLimitAlgorithm

    return [
        # Very strict global limits
        RateLimitRule(
            scope=RateLimitScope.GLOBAL,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=5000,  # 5k requests per hour globally
            window=3600
        ),

        # Strict per-tenant limits
        RateLimitRule(
            scope=RateLimitScope.TENANT,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=500,  # 500 requests per hour per tenant
            window=3600,
            burst_allowance=50
        ),

        # Strict per-user limits
        RateLimitRule(
            scope=RateLimitScope.USER,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=100,  # 100 requests per hour per user
            window=3600,
            burst_allowance=20
        ),

        # Very strict per-IP limits
        RateLimitRule(
            scope=RateLimitScope.IP,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=50,  # 50 requests per hour per IP
            window=3600,
            burst_allowance=10
        ),

        # Extremely strict auth endpoints
        RateLimitRule(
            scope=RateLimitScope.ENDPOINT,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=3,  # 3 login attempts per 15 minutes
            window=900,
            identifier="/auth/login"
        ),
    ]


def create_generous_rate_limits():
    """Create generous rate limits for high-volume applications."""
    from app.features.core.rate_limiting import RateLimitRule, RateLimitScope, RateLimitAlgorithm

    return [
        # Generous global limits
        RateLimitRule(
            scope=RateLimitScope.GLOBAL,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=100000,  # 100k requests per hour globally
            window=3600
        ),

        # Generous per-tenant limits
        RateLimitRule(
            scope=RateLimitScope.TENANT,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=10000,  # 10k requests per hour per tenant
            window=3600,
            burst_allowance=1000
        ),

        # Generous per-user limits
        RateLimitRule(
            scope=RateLimitScope.USER,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=1000,  # 1k requests per hour per user
            window=3600,
            burst_allowance=200
        ),

        # Reasonable per-IP limits
        RateLimitRule(
            scope=RateLimitScope.IP,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            limit=500,  # 500 requests per hour per IP
            window=3600,
            burst_allowance=100
        ),
    ]
