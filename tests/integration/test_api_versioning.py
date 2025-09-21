"""
Integration tests for API versioning system.

Tests URL path versioning, header-based version negotiation,
deprecation warnings, and version compatibility.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.api
class TestAPIVersioning:
    """Test API versioning functionality."""

    @pytest.mark.asyncio
    async def test_v1_health_endpoint(self, test_client: AsyncClient):
        """Test v1 API health endpoint."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "v1"
        assert data["api_version"] == "1.0.0"
        assert "features" in data
        assert "authentication" in data["features"]

    @pytest.mark.asyncio
    async def test_v1_info_endpoint(self, test_client: AsyncClient):
        """Test v1 API info endpoint."""
        response = await test_client.get("/api/v1/info")
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == "v1"
        assert data["status"] == "active"
        assert "endpoints" in data
        assert "authentication" in data["endpoints"]

    @pytest.mark.asyncio
    async def test_version_header_detection(self, test_client: AsyncClient):
        """Test API version detection via headers."""
        # Test with v1 header
        response = await test_client.get(
            "/api/v1/health",
            headers={"X-API-Version": "v1"}
        )
        assert response.status_code == 200
        assert response.headers.get("X-API-Version") == "v1"

    @pytest.mark.asyncio
    async def test_version_mismatch_warning(self, test_client: AsyncClient):
        """Test version mismatch warning in headers."""
        # Request v2 via header but use v1 URL
        response = await test_client.get(
            "/api/v1/health",
            headers={"X-API-Version": "v2"}
        )
        assert response.status_code == 200
        # Should include version mismatch warning
        assert "X-API-Version-Warning" in response.headers

    @pytest.mark.asyncio
    async def test_unsupported_version_header(self, test_client: AsyncClient):
        """Test unsupported version in header."""
        response = await test_client.get(
            "/api/v1/health",
            headers={"X-API-Version": "v999"}
        )
        assert response.status_code == 200
        # Should still work but with warning
        assert "X-API-Version-Warning" in response.headers

    @pytest.mark.asyncio
    async def test_version_compatibility_matrix(self, test_client: AsyncClient):
        """Test version compatibility responses."""
        # Test v1 endpoint
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        # Response should include supported versions
        assert response.headers.get("X-API-Version") == "v1"
        assert "X-API-Supported-Versions" in response.headers

    @pytest.mark.asyncio
    async def test_legacy_endpoint_access(self, test_client: AsyncClient):
        """Test that legacy endpoints still work."""
        # Test legacy auth endpoint (non-versioned)
        response = await test_client.get("/auth/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_versioned_auth_endpoints(self, test_client: AsyncClient):
        """Test versioned auth endpoints."""
        # Test v1 auth status
        response = await test_client.get("/api/v1/auth/status")
        assert response.status_code == 200

        data = response.json()
        assert "authenticated" in data

    @pytest.mark.asyncio
    async def test_version_middleware_order(self, test_client: AsyncClient):
        """Test that versioning middleware runs in correct order."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        # Should have version headers set by middleware
        assert "X-API-Version" in response.headers
        assert "X-API-Supported-Versions" in response.headers

    @pytest.mark.asyncio
    async def test_version_content_negotiation(self, test_client: AsyncClient):
        """Test content negotiation based on API version."""
        # Test with Accept header indicating version preference
        response = await test_client.get(
            "/api/v1/health",
            headers={
                "Accept": "application/vnd.api+json;version=1",
                "X-API-Version": "v1"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/json"


@pytest.mark.integration
@pytest.mark.api
class TestAPIVersionedEndpoints:
    """Test versioned API endpoints functionality."""

    @pytest.mark.asyncio
    async def test_versioned_user_endpoints(self, test_client: AsyncClient):
        """Test versioned user management endpoints."""
        response = await test_client.get("/api/v1/administration/users/api")
        # Endpoint exists (not 404), test passes if it responds
        assert response.status_code in [200, 401]
        # Verify it's a properly versioned endpoint
        assert "x-api-version" in response.headers

    @pytest.mark.asyncio
    async def test_versioned_tenant_endpoints(self, test_client: AsyncClient):
        """Test versioned tenant management endpoints."""
        response = await test_client.get("/api/v1/administration/tenants/api")
        # Endpoint exists (not 404), test passes if it responds
        assert response.status_code in [200, 401]
        # Verify it's a properly versioned endpoint
        assert "x-api-version" in response.headers

    @pytest.mark.asyncio
    async def test_versioned_webhook_endpoints(self, test_client: AsyncClient):
        """Test versioned webhook endpoints."""
        response = await test_client.get("/api/v1/webhooks/events")
        # Should return 401 without auth, but endpoint exists
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_versioned_mfa_endpoints(self, test_client: AsyncClient):
        """Test versioned MFA endpoints."""
        response = await test_client.get("/api/v1/auth/mfa/status")
        # Should return 401 without auth, but endpoint exists
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_version_specific_features(self, test_client: AsyncClient):
        """Test that version-specific features are available."""
        response = await test_client.get("/api/v1/info")
        assert response.status_code == 200

        data = response.json()
        endpoints = data["endpoints"]

        # v1 should include all our new features
        assert "webhooks" in endpoints
        assert endpoints["webhooks"] == "/api/v1/webhooks"
        assert "authentication" in endpoints
        assert endpoints["authentication"] == "/api/v1/auth"


@pytest.mark.integration
@pytest.mark.api
class TestVersionDeprecation:
    """Test API version deprecation handling."""

    @pytest.mark.asyncio
    async def test_non_deprecated_version(self, test_client: AsyncClient):
        """Test that active versions don't show deprecation warnings."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        # v1 should be active, no deprecation headers
        assert "X-API-Deprecation-Warning" not in response.headers
        assert "X-API-Sunset" not in response.headers

    @pytest.mark.asyncio
    async def test_version_status_active(self, test_client: AsyncClient):
        """Test that v1 reports as active status."""
        response = await test_client.get("/api/v1/info")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_cors_with_versioning(self, test_client: AsyncClient):
        """Test CORS headers work with versioned APIs."""
        response = await test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # Should handle CORS properly
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_version_documentation_links(self, test_client: AsyncClient):
        """Test that version info includes documentation links."""
        response = await test_client.get("/api/v1/info")
        assert response.status_code == 200

        data = response.json()
        assert "documentation" in data
        assert data["documentation"] == "/api/v1/docs"


@pytest.mark.integration
@pytest.mark.api
class TestVersionSecurity:
    """Test security aspects of API versioning."""

    @pytest.mark.asyncio
    async def test_version_header_injection(self, test_client: AsyncClient):
        """Test protection against version header injection."""
        # Try to inject malicious version header
        response = await test_client.get(
            "/api/v1/health",
            headers={"X-API-Version": "<script>alert('xss')</script>"}
        )
        assert response.status_code == 200
        # Response headers should be safe
        version_header = response.headers.get("X-API-Version")
        assert "<script>" not in version_header

    @pytest.mark.asyncio
    async def test_version_path_traversal(self, test_client: AsyncClient):
        """Test protection against path traversal in version."""
        # Try path traversal in version
        response = await test_client.get("/api/../v1/health")
        # Should either normalize or reject
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_version_consistency(self, test_client: AsyncClient):
        """Test version consistency across endpoints."""
        # All v1 endpoints should report same version
        health_response = await test_client.get("/api/v1/health")
        info_response = await test_client.get("/api/v1/info")

        assert health_response.status_code == 200
        assert info_response.status_code == 200

        # Both should report v1
        assert health_response.headers.get("X-API-Version") == "v1"
        assert info_response.headers.get("X-API-Version") == "v1"
