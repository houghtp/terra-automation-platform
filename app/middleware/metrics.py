"""
Metrics middleware for FastAPI applications.
Automatically tracks HTTP requests, response times, and other performance metrics.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.features.core.metrics import metrics

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect metrics for all HTTP requests.
    Integrates with tenant context and provides comprehensive request tracking.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        logger.info(f"Metrics middleware initialized (enabled: {self.enabled})")

    def _extract_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from request context."""
        try:
            # Try to get tenant from middleware context variables
            from app.middleware.tenant import tenant_ctx_var
            tenant_id = tenant_ctx_var.get(None)
            if tenant_id:
                return tenant_id
        except Exception:
            pass

        # Fallback to header
        return request.headers.get("X-Tenant-ID", "unknown")

    def _extract_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern for consistent metrics grouping."""
        path = request.url.path

        # Group similar endpoints to avoid metric explosion
        # Replace IDs with placeholders
        import re

        # Replace UUIDs with {id}
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)

        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)

        # Common patterns
        if path.startswith('/static/'):
            return '/static/{file}'
        elif path.startswith('/api/'):
            # Keep API paths more detailed
            return path
        elif path == '/':
            return '/'

        return path

    def _should_skip_metrics(self, request: Request) -> bool:
        """Determine if metrics collection should be skipped for this request."""
        path = request.url.path

        # Skip the metrics endpoint itself to avoid recursion
        if path == '/metrics':
            return True

        # Skip health checks (they have their own detailed metrics)
        if path in ['/health', '/health/db', '/health/detailed']:
            return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Main middleware dispatch method."""
        if not self.enabled or self._should_skip_metrics(request):
            return await call_next(request)

        # Extract request information
        method = request.method
        endpoint = self._extract_endpoint_pattern(request)
        tenant_id = self._extract_tenant_id(request)

        # Track request in flight
        start_time = time.time()

        async with metrics.track_request_in_flight():
            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics
                metrics.record_http_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    duration=duration,
                    tenant_id=tenant_id
                )

                # Add metrics headers to response (optional, for debugging)
                if hasattr(response, 'headers'):
                    response.headers['X-Request-Duration'] = f"{duration:.3f}s"
                    response.headers['X-Tenant-ID'] = tenant_id

                return response

            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time

                metrics.record_http_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=500,
                    duration=duration,
                    tenant_id=tenant_id
                )

                # Record as security event if it looks suspicious
                error_msg = str(e).lower()
                if any(term in error_msg for term in ['unauthorized', 'forbidden', 'invalid', 'malicious']):
                    metrics.record_security_event(
                        event_type="request_error",
                        severity="medium",
                        tenant_id=tenant_id
                    )

                logger.error(f"Request error: {method} {endpoint} - {e}")
                raise


def create_metrics_middleware(enabled: bool = None) -> MetricsMiddleware:
    """
    Factory function to create metrics middleware with optional configuration.

    Args:
        enabled: Whether to enable metrics collection (defaults to env var or True)

    Returns:
        Configured MetricsMiddleware instance
    """
    if enabled is None:
        import os
        enabled = os.getenv("METRICS_ENABLED", "true").lower() in ("true", "1", "yes")

    return lambda app: MetricsMiddleware(app, enabled=enabled)
