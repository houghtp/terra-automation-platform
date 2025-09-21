"""
Tests for monitoring and observability system.

Tests Prometheus metrics, structured logging, health checks, and security event tracking
integrated with the main pytest test suite.
"""

import pytest
import json
import asyncio
from httpx import AsyncClient
from unittest.mock import patch

from tests.utils import ResponseAssertions


@pytest.mark.integration
@pytest.mark.asyncio
class TestMonitoringEndpoints:
    """Test monitoring and health check endpoints."""

    @pytest.mark.asyncio
    async def test_basic_health_endpoint(self, test_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await test_client.get("/health")

        ResponseAssertions.assert_success(response)
        data = ResponseAssertions.assert_json_response(response)

        assert "status" in data
        assert data["status"] == "ok"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self, test_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await test_client.get("/health/detailed")

        ResponseAssertions.assert_success(response)
        data = ResponseAssertions.assert_json_response(response)

        # Verify required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "checks" in data

        # Verify component checks
        checks = data["checks"]
        assert "database" in checks
        assert "secrets" in checks
        assert "rate_limiting" in checks
        assert "application" in checks

        # Database check should be healthy
        db_check = checks["database"]
        assert db_check["status"] == "healthy"
        assert "response_time_ms" in db_check

    @pytest.mark.asyncio
    async def test_kubernetes_liveness_probe(self, test_client: AsyncClient):
        """Test Kubernetes liveness probe endpoint."""
        response = await test_client.get("/health/liveness")

        ResponseAssertions.assert_success(response)
        data = ResponseAssertions.assert_json_response(response)

        assert data["status"] == "alive"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_kubernetes_readiness_probe(self, test_client: AsyncClient):
        """Test Kubernetes readiness probe endpoint."""
        response = await test_client.get("/health/readiness")

        ResponseAssertions.assert_success(response)
        data = ResponseAssertions.assert_json_response(response)

        assert data["status"] == "ready"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_kubernetes_startup_probe(self, test_client: AsyncClient):
        """Test Kubernetes startup probe endpoint."""
        response = await test_client.get("/health/startup")

        ResponseAssertions.assert_success(response)
        data = ResponseAssertions.assert_json_response(response)

        assert data["status"] == "started"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, test_client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await test_client.get("/metrics")

        ResponseAssertions.assert_success(response)

        # Verify content type
        assert "text/plain" in response.headers.get("content-type", "")

        # Verify Prometheus format
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content

        # Verify core metrics are present
        expected_metrics = [
            "http_requests_total",
            "http_request_duration_seconds",
            "auth_attempts_total",
            "rate_limit_hits_total",
            "database_query_duration_seconds"
        ]

        for metric in expected_metrics:
            assert metric in content, f"Missing metric: {metric}"

    @pytest.mark.asyncio
    async def test_metrics_collection_after_requests(self, test_client: AsyncClient):
        """Test that metrics are properly collected after making requests."""
        # Make some requests to generate metrics
        await test_client.get("/health")
        await test_client.get("/health/detailed")
        await test_client.get("/demo/", headers={"X-Tenant-ID": "test-metrics"})

        # Check metrics endpoint
        response = await test_client.get("/metrics")
        ResponseAssertions.assert_success(response)

        content = response.text

        # Should have recorded HTTP requests
        assert "http_requests_total" in content
        assert 'endpoint="/demo/"' in content  # This endpoint should definitely be recorded
        assert 'method="GET"' in content
        assert 'status_code="200"' in content


@pytest.mark.unit
class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_structured_logging_initialization(self):
        """Test that structured logging can be initialized."""
        from app.features.core.structured_logging import setup_structured_logging

        # Should not raise any exceptions
        setup_structured_logging(level="INFO", format_type="console")

    def test_security_logger_functionality(self):
        """Test security event logging."""
        from app.features.core.structured_logging import security_logger

        # Should not raise exceptions
        security_logger.log_auth_attempt(
            username="test_user",
            success=True,
            ip_address="127.0.0.1",
            tenant_id="test"
        )

        security_logger.log_rate_limit_exceeded(
            rule_scope="test_endpoint",
            limit=100,
            window=60,
            ip_address="127.0.0.1"
        )

    def test_audit_logger_functionality(self):
        """Test audit logging."""
        from app.features.core.structured_logging import audit_logger

        # Should not raise exceptions
        audit_logger.log_user_action(
            action="test_action",
            user_id="test_user",
            resource="test_resource",
            details={"key": "value"}
        )

    def test_json_logging_in_production(self):
        """Test JSON logging configuration for production."""
        from app.features.core.structured_logging import setup_structured_logging
        import structlog

        # Configure for production
        setup_structured_logging(
            level="INFO",
            format_type="json",
            enable_json=True
        )

        # Get logger and log a message
        logger = structlog.get_logger("test")

        # Should not raise exceptions
        logger.info("Test message", component="test", environment="production")


@pytest.mark.unit
class TestMetricsSystem:
    """Test Prometheus metrics collection."""

    def test_metrics_initialization(self):
        """Test that metrics system initializes correctly."""
        from app.features.core.metrics import ApplicationMetrics

        metrics = ApplicationMetrics()
        assert metrics is not None

    def test_http_metrics_recording(self):
        """Test HTTP request metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_http_request("GET", "/test", 200, 0.123, "test-tenant")
        metrics.record_http_request("POST", "/api/test", 201, 0.456, "test-tenant")

    def test_auth_metrics_recording(self):
        """Test authentication metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_auth_attempt("test_user", True, "test-tenant")
        metrics.record_auth_attempt("bad_user", False, "test-tenant")

    def test_rate_limit_metrics_recording(self):
        """Test rate limiting metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_rate_limit_hit("global", "test-tenant", 0.75)
        metrics.record_rate_limit_hit("user", "test-tenant", 1.0)

    def test_database_metrics_recording(self):
        """Test database query metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_database_query("SELECT", 0.045, "test-tenant")
        metrics.record_database_query("INSERT", 0.123, "test-tenant")

    def test_security_metrics_recording(self):
        """Test security event metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_security_event("auth_failure", "medium", "test-tenant")
        metrics.record_security_event("rate_limit", "high", "test-tenant")

    def test_feature_metrics_recording(self):
        """Test feature usage metrics recording."""
        from app.features.core.metrics import metrics

        # Should not raise exceptions
        metrics.record_feature_usage("demo_create", "test-tenant")
        metrics.record_feature_usage("api_access", "test-tenant")

    def test_metrics_export(self):
        """Test that metrics can be exported in Prometheus format."""
        from app.features.core.metrics import metrics
        from prometheus_client import generate_latest

        # Record some test data
        metrics.record_http_request("GET", "/test", 200, 0.1, "test")

        # Export metrics
        output = generate_latest().decode('utf-8')

        # Should contain Prometheus format
        assert "# HELP" in output
        assert "# TYPE" in output


@pytest.mark.integration
@pytest.mark.asyncio
class TestMonitoringMiddleware:
    """Test monitoring middleware integration."""

    @pytest.mark.asyncio
    async def test_metrics_middleware_integration(self, test_client: AsyncClient):
        """Test that metrics middleware properly records requests."""
        # Make a test request
        response = await test_client.get("/health")
        ResponseAssertions.assert_success(response)

        # Check that metrics were recorded
        metrics_response = await test_client.get("/metrics")
        ResponseAssertions.assert_success(metrics_response)

        content = metrics_response.text

        # Should have recorded the health check request
        assert 'method="GET"' in content
        assert 'status_code="200"' in content

    @pytest.mark.asyncio
    async def test_request_id_generation(self, test_client: AsyncClient):
        """Test that request IDs are generated and tracked."""
        response = await test_client.get("/health")
        ResponseAssertions.assert_success(response)

        # Request ID should be in response headers
        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_tenant_context_tracking(self, test_client: AsyncClient):
        """Test that tenant context is properly tracked."""
        tenant_id = "test-monitoring"
        headers = {"X-Tenant-ID": tenant_id}

        response = await test_client.get("/dashboard", headers=headers)
        # Dashboard endpoint should redirect to login (302, 307) or return 200 if authenticated
        assert response.status_code in [200, 302, 307]

        # Check metrics include tenant context
        metrics_response = await test_client.get("/metrics")
        content = metrics_response.text

        # Should have tenant-specific metrics
        assert f'tenant_id="{tenant_id}"' in content


@pytest.mark.integration
@pytest.mark.asyncio
class TestMonitoringPerformance:
    """Test monitoring system performance."""

    @pytest.mark.asyncio
    async def test_health_check_performance(self, test_client: AsyncClient):
        """Test that health checks respond quickly."""
        import time

        start_time = time.time()
        response = await test_client.get("/health")
        end_time = time.time()

        ResponseAssertions.assert_success(response)

        # Should respond in under 1 second
        response_time = end_time - start_time
        assert response_time < 1.0, f"Health check took {response_time:.3f}s"

    @pytest.mark.asyncio
    async def test_metrics_endpoint_performance(self, test_client: AsyncClient):
        """Test that metrics endpoint responds reasonably quickly."""
        import time

        # Generate some metrics first
        for i in range(10):
            await test_client.get("/health")

        start_time = time.time()
        response = await test_client.get("/metrics")
        end_time = time.time()

        ResponseAssertions.assert_success(response)

        # Should respond in under 2 seconds even with metrics
        response_time = end_time - start_time
        assert response_time < 2.0, f"Metrics endpoint took {response_time:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, test_client: AsyncClient):
        """Test concurrent health check handling."""
        import asyncio

        async def make_health_request():
            return await test_client.get("/health")

        # Make 5 concurrent requests
        tasks = [make_health_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            ResponseAssertions.assert_success(response)


@pytest.mark.integration
@pytest.mark.asyncio
class TestMonitoringErrorHandling:
    """Test monitoring system error handling."""

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_components(self, test_client: AsyncClient):
        """Test health check behavior when components fail."""
        # The detailed health check should handle component failures gracefully
        response = await test_client.get("/health/detailed")

        # Should still return a response even if some components fail
        assert response.status_code in [200, 503]  # OK or Service Unavailable

    @pytest.mark.asyncio
    async def test_metrics_resilience(self, test_client: AsyncClient):
        """Test that metrics collection doesn't break application."""
        # Make requests that could potentially cause issues
        await test_client.get("/nonexistent-endpoint")  # 404
        await test_client.post("/health")  # Method not allowed

        # Metrics endpoint should still work
        response = await test_client.get("/metrics")
        ResponseAssertions.assert_success(response)

    @pytest.mark.asyncio
    async def test_invalid_health_endpoint(self, test_client: AsyncClient):
        """Test invalid health endpoint paths."""
        response = await test_client.get("/health/invalid")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_monitoring_with_malformed_requests(self, test_client: AsyncClient):
        """Test monitoring handles malformed requests gracefully."""
        # Request with invalid headers
        headers = {"X-Tenant-ID": ""}
        response = await test_client.get("/health", headers=headers)

        # Should handle gracefully
        assert response.status_code in [200, 400]

        # Metrics should still be collectible
        metrics_response = await test_client.get("/metrics")
        ResponseAssertions.assert_success(metrics_response)


# Test categorization for organization
# These tests validate the comprehensive monitoring and observability system
