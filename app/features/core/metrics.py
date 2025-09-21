"""
Prometheus metrics collection for FastAPI applications.
Provides comprehensive monitoring of application performance, security, and business metrics.
"""
import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import asynccontextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Enum, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)


class ApplicationMetrics:
    """
    Central metrics collector for FastAPI application.
    Tracks performance, security, and business metrics.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""

        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code', 'tenant_id'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'tenant_id'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        self.http_requests_in_flight = Gauge(
            'http_requests_in_flight',
            'Number of HTTP requests currently being processed',
            registry=self.registry
        )

        # Authentication Metrics
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['method', 'status', 'tenant_id'],  # method: login/register, status: success/failure
            registry=self.registry
        )

        self.active_sessions = Gauge(
            'active_sessions_total',
            'Number of currently active user sessions',
            ['tenant_id'],
            registry=self.registry
        )

        # Rate Limiting Metrics
        self.rate_limit_hits_total = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits (requests blocked)',
            ['scope', 'rule_type', 'tenant_id'],  # scope: global/tenant/user/ip/endpoint
            registry=self.registry
        )

        self.rate_limit_usage = Histogram(
            'rate_limit_usage_ratio',
            'Rate limit usage as ratio (0.0 to 1.0)',
            ['scope', 'rule_type', 'tenant_id'],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
            registry=self.registry
        )

        # Database Metrics
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )

        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'tenant_id'],  # query_type: select/insert/update/delete
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )

        self.database_errors_total = Counter(
            'database_errors_total',
            'Total database errors',
            ['error_type', 'tenant_id'],
            registry=self.registry
        )

        # Business Metrics (customize based on your application)
        self.tenant_activity = Counter(
            'tenant_activity_total',
            'Total tenant activity events',
            ['tenant_id', 'activity_type'],  # activity_type: login, api_call, feature_usage
            registry=self.registry
        )

        self.feature_usage = Counter(
            'feature_usage_total',
            'Feature usage counter',
            ['feature_name', 'tenant_id', 'user_role'],
            registry=self.registry
        )

        # Security Metrics
        self.security_events_total = Counter(
            'security_events_total',
            'Total security events',
            ['event_type', 'severity', 'tenant_id'],  # event_type: suspicious_login, brute_force, etc.
            registry=self.registry
        )

        # Application Health Metrics
        self.application_info = Info(
            'application',
            'Application information',
            registry=self.registry
        )

        self.application_health = Enum(
            'application_health_status',
            'Application health status',
            states=['healthy', 'degraded', 'unhealthy'],
            registry=self.registry
        )

        # Secrets Management Metrics
        self.secrets_access_total = Counter(
            'secrets_access_total',
            'Total secrets access attempts',
            ['backend', 'status'],  # backend: env_file/aws/azure, status: success/failure
            registry=self.registry
        )

        # Set initial application info
        import os
        self.application_info.info({
            'version': os.getenv('APP_VERSION', 'dev'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
        })

        self.application_health.state('healthy')

        # Use print for initialization instead of logger to avoid circular imports
        print("✅ Prometheus metrics initialized")

    def record_http_request(self, method: str, endpoint: str, status_code: int,
                          duration: float, tenant_id: str = "unknown"):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            tenant_id=tenant_id
        ).inc()

        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            tenant_id=tenant_id
        ).observe(duration)

    @asynccontextmanager
    async def track_request_in_flight(self):
        """Context manager to track requests currently being processed."""
        self.http_requests_in_flight.inc()
        try:
            yield
        finally:
            self.http_requests_in_flight.dec()

    def record_auth_attempt(self, method: str, success: bool, tenant_id: str = "unknown"):
        """Record authentication attempt."""
        status = "success" if success else "failure"
        self.auth_attempts_total.labels(
            method=method,
            status=status,
            tenant_id=tenant_id
        ).inc()

    def record_rate_limit_hit(self, scope: str, rule_type: str, usage_ratio: float,
                             tenant_id: str = "unknown"):
        """Record rate limit hit and usage."""
        self.rate_limit_hits_total.labels(
            scope=scope,
            rule_type=rule_type,
            tenant_id=tenant_id
        ).inc()

        self.rate_limit_usage.labels(
            scope=scope,
            rule_type=rule_type,
            tenant_id=tenant_id
        ).observe(usage_ratio)

    def record_database_query(self, query_type: str, duration: float,
                             tenant_id: str = "unknown", error: Optional[str] = None):
        """Record database query metrics."""
        self.database_query_duration.labels(
            query_type=query_type,
            tenant_id=tenant_id
        ).observe(duration)

        if error:
            self.database_errors_total.labels(
                error_type=error,
                tenant_id=tenant_id
            ).inc()

    def record_feature_usage(self, feature_name: str, tenant_id: str = "unknown",
                           user_role: str = "user"):
        """Record feature usage."""
        self.feature_usage.labels(
            feature_name=feature_name,
            tenant_id=tenant_id,
            user_role=user_role
        ).inc()

        self.tenant_activity.labels(
            tenant_id=tenant_id,
            activity_type="feature_usage"
        ).inc()

    def record_security_event(self, event_type: str, severity: str = "medium",
                            tenant_id: str = "unknown"):
        """Record security event."""
        self.security_events_total.labels(
            event_type=event_type,
            severity=severity,
            tenant_id=tenant_id
        ).inc()

    def record_secrets_access(self, backend: str, success: bool):
        """Record secrets access attempt."""
        status = "success" if success else "failure"
        self.secrets_access_total.labels(
            backend=backend,
            status=status
        ).inc()

    def set_application_health(self, status: str):
        """Set application health status."""
        if status in ['healthy', 'degraded', 'unhealthy']:
            self.application_health.state(status)

    def update_active_sessions(self, tenant_id: str, count: int):
        """Update active sessions count for a tenant."""
        self.active_sessions.labels(tenant_id=tenant_id).set(count)

    def update_database_connections(self, count: int):
        """Update active database connections count."""
        self.database_connections.set(count)

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
metrics = ApplicationMetrics()


def track_time(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to track execution time of functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if hasattr(metrics, metric_name):
                    metric = getattr(metrics, metric_name)
                    if labels:
                        metric.labels(**labels).observe(duration)
                    else:
                        metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if hasattr(metrics, metric_name):
                    metric = getattr(metrics, metric_name)
                    if labels:
                        metric.labels(**labels).observe(duration)
                    else:
                        metric.observe(duration)

        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Utility functions for easy metric recording
def record_request(method: str, endpoint: str, status_code: int, duration: float,
                  tenant_id: str = "unknown"):
    """Convenience function to record HTTP request metrics."""
    metrics.record_http_request(method, endpoint, status_code, duration, tenant_id)


def record_auth(method: str, success: bool, tenant_id: str = "unknown"):
    """Convenience function to record authentication metrics."""
    metrics.record_auth_attempt(method, success, tenant_id)


def record_feature(feature_name: str, tenant_id: str = "unknown", user_role: str = "user"):
    """Convenience function to record feature usage."""
    metrics.record_feature_usage(feature_name, tenant_id, user_role)


def record_security(event_type: str, severity: str = "medium", tenant_id: str = "unknown"):
    """Convenience function to record security events."""
    metrics.record_security_event(event_type, severity, tenant_id)
