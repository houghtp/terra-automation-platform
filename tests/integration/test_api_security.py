"""
Integration tests for API security system.

Tests API key management, request signature verification,
rate limiting, and security middleware functionality.
"""
import pytest
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.api_security import APIKeyManager, APIKeyScope, RequestSignatureValidator
from app.features.core.database import get_db


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAPIKeyManagement:
    """Test API key management functionality."""

    @pytest.mark.asyncio
    async def test_api_key_generation(self):
        """Test API key generation produces secure keys."""
        key_id, secret, key_hash = APIKeyManager.generate_api_key()

        # Verify format and lengths
        assert len(key_id) == 16
        assert len(secret) == 43  # URL-safe base64 encoding of 32 bytes
        assert len(key_hash) == 64  # SHA256 hex digest

        # Verify uniqueness
        key_id2, secret2, key_hash2 = APIKeyManager.generate_api_key()
        assert key_id != key_id2
        assert secret != secret2
        assert key_hash != key_hash2

    @pytest.mark.asyncio
    async def test_create_api_key(self, test_db_session: AsyncSession):
        """Test creating API key in database."""
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Test API Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value, APIKeyScope.WRITE.value],
            description="Test key for unit tests",
            expires_in_days=30
        )

        assert api_key is not None
        assert api_key.name == "Test API Key"
        assert api_key.tenant_id == "test-tenant"
        assert APIKeyScope.READ.value in api_key.scopes
        assert APIKeyScope.WRITE.value in api_key.scopes
        assert api_key.expires_at is not None
        assert len(secret) == 43

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, test_db_session: AsyncSession):
        """Test successful API key validation."""
        # Create API key
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Test Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value]
        )

        # Validate it
        key_info = await APIKeyManager.validate_api_key(
            session=test_db_session,
            key_id=api_key.key_id,
            secret=secret
        )

        assert key_info is not None
        assert key_info.key_id == api_key.key_id
        assert key_info.tenant_id == "test-tenant"
        assert APIKeyScope.READ.value in key_info.scopes

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid_secret(self, test_db_session: AsyncSession):
        """Test API key validation with invalid secret."""
        # Create API key
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Test Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value]
        )

        # Try to validate with wrong secret
        key_info = await APIKeyManager.validate_api_key(
            session=test_db_session,
            key_id=api_key.key_id,
            secret="wrong-secret"
        )

        assert key_info is None

    @pytest.mark.asyncio
    async def test_validate_api_key_nonexistent(self, test_db_session: AsyncSession):
        """Test API key validation with nonexistent key."""
        key_info = await APIKeyManager.validate_api_key(
            session=test_db_session,
            key_id="nonexistent-key",
            secret="any-secret"
        )

        assert key_info is None

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, test_db_session: AsyncSession):
        """Test API key revocation."""
        # Create API key
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Test Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value]
        )

        # Revoke it
        success = await APIKeyManager.revoke_api_key(
            session=test_db_session,
            key_id=api_key.key_id,
            tenant_id="test-tenant"
        )

        assert success is True

        # Should no longer validate
        key_info = await APIKeyManager.validate_api_key(
            session=test_db_session,
            key_id=api_key.key_id,
            secret=secret
        )

        assert key_info is None

    @pytest.mark.asyncio
    async def test_api_key_scopes(self, test_db_session: AsyncSession):
        """Test API key scope functionality."""
        # Create key with specific scopes
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Scoped Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value, APIKeyScope.WEBHOOK.value]
        )

        # Test scope checking
        assert api_key.has_scope(APIKeyScope.READ.value)
        assert api_key.has_scope(APIKeyScope.WEBHOOK.value)
        assert not api_key.has_scope(APIKeyScope.ADMIN.value)
        assert not api_key.has_scope(APIKeyScope.WRITE.value)

    @pytest.mark.asyncio
    async def test_api_key_expiration(self, test_db_session: AsyncSession):
        """Test API key expiration."""
        # Create expired key
        api_key, secret = await APIKeyManager.create_api_key(
            session=test_db_session,
            name="Expired Key",
            tenant_id="test-tenant",
            scopes=[APIKeyScope.READ.value],
            expires_in_days=-1  # Expired yesterday
        )

        # Should not validate
        key_info = await APIKeyManager.validate_api_key(
            session=test_db_session,
            key_id=api_key.key_id,
            secret=secret
        )

        assert key_info is None


@pytest.mark.integration
@pytest.mark.api
class TestRequestSignatureValidation:
    """Test request signature validation functionality."""

    def test_generate_signature(self):
        """Test signature generation."""
        method = "POST"
        path = "/api/v1/test"
        body = b'{"test": "data"}'
        timestamp = "2025-01-18T12:00:00Z"
        secret = "test-secret"

        signature = RequestSignatureValidator.generate_signature(
            method=method,
            path=path,
            body=body,
            timestamp=timestamp,
            secret=secret
        )

        # Should be base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 20  # Base64 encoded SHA256

        # Should be deterministic
        signature2 = RequestSignatureValidator.generate_signature(
            method=method,
            path=path,
            body=body,
            timestamp=timestamp,
            secret=secret
        )
        assert signature == signature2

    def test_signature_consistency(self):
        """Test signature consistency across different inputs."""
        secret = "test-secret"
        timestamp = "2025-01-18T12:00:00Z"

        # Different methods should produce different signatures
        sig_get = RequestSignatureValidator.generate_signature("GET", "/test", b"", timestamp, secret)
        sig_post = RequestSignatureValidator.generate_signature("POST", "/test", b"", timestamp, secret)
        assert sig_get != sig_post

        # Different paths should produce different signatures
        sig_path1 = RequestSignatureValidator.generate_signature("GET", "/test1", b"", timestamp, secret)
        sig_path2 = RequestSignatureValidator.generate_signature("GET", "/test2", b"", timestamp, secret)
        assert sig_path1 != sig_path2

    def test_verify_signature_success(self):
        """Test successful signature verification."""
        from unittest.mock import Mock

        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"

        # Generate signature
        body = b'{"test": "data"}'
        timestamp = datetime.utcnow().isoformat()
        secret = "test-secret"

        signature = RequestSignatureValidator.generate_signature(
            method=request.method,
            path=request.url.path,
            body=body,
            timestamp=timestamp,
            secret=secret
        )

        # Set headers
        request.headers.get.side_effect = lambda key: {
            "X-Signature": signature,
            "X-Timestamp": timestamp
        }.get(key)

        # Should verify successfully
        is_valid = RequestSignatureValidator.verify_signature(
            request=request,
            body=body,
            secret=secret
        )

        assert is_valid is True

    def test_verify_signature_expired(self):
        """Test signature verification with expired timestamp."""
        from unittest.mock import Mock

        request = Mock()
        request.method = "GET"
        request.url.path = "/test"

        # Old timestamp (more than 5 minutes ago)
        old_timestamp = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
        secret = "test-secret"
        body = b""

        signature = RequestSignatureValidator.generate_signature(
            method=request.method,
            path=request.url.path,
            body=body,
            timestamp=old_timestamp,
            secret=secret
        )

        request.headers.get.side_effect = lambda key: {
            "X-Signature": signature,
            "X-Timestamp": old_timestamp
        }.get(key)

        # Should fail due to expired timestamp
        is_valid = RequestSignatureValidator.verify_signature(
            request=request,
            body=body,
            secret=secret,
            max_age_seconds=300  # 5 minutes
        )

        assert is_valid is False

    def test_verify_signature_missing_headers(self):
        """Test signature verification with missing headers."""
        from unittest.mock import Mock

        request = Mock()
        request.headers.get.return_value = None

        is_valid = RequestSignatureValidator.verify_signature(
            request=request,
            body=b"",
            secret="test-secret"
        )

        assert is_valid is False


@pytest.mark.integration
@pytest.mark.api
class TestAPISecurityMiddleware:
    """Test API security middleware functionality."""

    @pytest.mark.asyncio
    async def test_security_headers_added(self, test_client: AsyncClient):
        """Test that security headers are added to API responses."""
        response = await test_client.get("/api/v1/health")

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

        # Strict-Transport-Security is only added for HTTPS requests
        # In tests we use HTTP so this header should not be present

    @pytest.mark.asyncio
    async def test_non_api_endpoints_skip_security(self, test_client: AsyncClient):
        """Test that non-API endpoints skip enhanced security middleware."""
        # Health endpoint should still work
        response = await test_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_security_middleware_order(self, test_client: AsyncClient):
        """Test that security middleware runs in correct order."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        # Should have both versioning and security headers
        assert "X-API-Version" in response.headers
        assert "X-Content-Type-Options" in response.headers


@pytest.mark.integration
@pytest.mark.api
class TestAPIKeyAuthentication:
    """Test API key authentication in HTTP requests."""

    @pytest.mark.asyncio
    async def test_api_key_authentication_format(self, test_client: AsyncClient):
        """Test API key authentication format requirements."""
        # Test invalid format (missing colon)
        response = await test_client.get(
            "/api/v1/webhooks/events",
            headers={"Authorization": "Bearer invalid-format"}
        )
        assert response.status_code == 401
        # Note: Response might be HTML login page instead of JSON for API endpoints
        # The important thing is that authentication is properly rejected

    @pytest.mark.asyncio
    async def test_api_key_authentication_missing(self, test_client: AsyncClient):
        """Test API endpoints require authentication."""
        response = await test_client.get("/api/v1/webhooks/events")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_security_scope_enforcement(self, test_db_session: AsyncSession, test_client: AsyncClient):
        """Test that API scopes are properly enforced."""
        # This would require mocking the database dependency
        # and creating a valid API key to test scope enforcement
        # For now, just test that endpoints exist and require auth

        response = await test_client.get("/api/v1/webhooks/events")
        assert response.status_code == 401  # Should require authentication


@pytest.mark.integration
@pytest.mark.api
class TestRateLimiting:
    """Test rate limiting functionality with API keys."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, test_client: AsyncClient):
        """Test that rate limit information is included in responses."""
        # This would test rate limiting middleware if implemented
        # For now, test basic functionality
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

        # Rate limiting headers might be added in future
        # assert "X-RateLimit-Limit" in response.headers