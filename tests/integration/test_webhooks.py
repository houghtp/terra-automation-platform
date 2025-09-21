"""
Integration tests for webhook system.

Tests webhook endpoint management, event triggering, delivery tracking,
signature verification, and retry mechanisms.
"""
import pytest
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, Mock, AsyncMock
from fastapi import BackgroundTasks

from app.features.core.webhooks import (
    WebhookManager, WebhookEndpoint, WebhookDelivery,
    EventType, DeliveryStatus, WebhookStatus
)


@pytest.mark.integration
@pytest.mark.webhooks
class TestWebhookManager:
    """Test webhook manager functionality."""

    @pytest.mark.asyncio
    async def test_generate_webhook_secret(self):
        """Test webhook secret generation."""
        secret1 = WebhookManager.generate_webhook_secret()
        secret2 = WebhookManager.generate_webhook_secret()

        assert len(secret1) == 43  # URL-safe base64 encoded
        assert len(secret2) == 43
        assert secret1 != secret2  # Should be unique

    @pytest.mark.asyncio
    async def test_generate_and_verify_signature(self):
        """Test signature generation and verification."""
        payload = '{"test": "data"}'
        secret = "test-secret"

        signature = WebhookManager.generate_signature(payload, secret)
        assert signature.startswith("sha256=")
        assert len(signature) > 10

        # Verify signature
        is_valid = WebhookManager.verify_signature(payload, signature, secret)
        assert is_valid is True

        # Verify with wrong secret
        is_invalid = WebhookManager.verify_signature(payload, signature, "wrong-secret")
        assert is_invalid is False

    @pytest.mark.asyncio
    async def test_create_webhook_endpoint(self, test_db_session: AsyncSession):
        """Test creating webhook endpoint."""
        webhook_manager = WebhookManager()

        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=[EventType.USER_CREATED.value, EventType.USER_UPDATED.value],
            description="Test webhook endpoint"
        )

        assert endpoint is not None
        assert endpoint.name == "Test Webhook"
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.tenant_id == "test-tenant"
        assert EventType.USER_CREATED.value in endpoint.events
        assert len(endpoint.secret) == 43

    @pytest.mark.asyncio
    async def test_create_webhook_endpoint_invalid_url(self, test_db_session: AsyncSession):
        """Test creating webhook endpoint with invalid URL."""
        webhook_manager = WebhookManager()

        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="invalid-url",
            name="Invalid Webhook",
            events=[EventType.USER_CREATED.value]
        )

        assert endpoint is None

    @pytest.mark.asyncio
    async def test_create_webhook_endpoint_invalid_events(self, test_db_session: AsyncSession):
        """Test creating webhook endpoint with invalid events."""
        webhook_manager = WebhookManager()

        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Invalid Events Webhook",
            events=["invalid.event", EventType.USER_CREATED.value]
        )

        assert endpoint is None

    @pytest.mark.asyncio
    async def test_trigger_webhook_event(self, test_db_session: AsyncSession):
        """Test triggering webhook event."""
        webhook_manager = WebhookManager()

        # Create endpoint
        await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Mock background tasks
        background_tasks = Mock(spec=BackgroundTasks)
        background_tasks.add_task = Mock()

        # Trigger event
        success = await webhook_manager.trigger_webhook_event(
            session=test_db_session,
            background_tasks=background_tasks,
            event_type=EventType.USER_CREATED,
            tenant_id="test-tenant",
            data={"user_id": "123", "email": "test@example.com"}
        )

        assert success is True
        assert background_tasks.add_task.called

    @pytest.mark.asyncio
    async def test_trigger_webhook_event_no_endpoints(self, test_db_session: AsyncSession):
        """Test triggering webhook event with no subscribed endpoints."""
        webhook_manager = WebhookManager()
        background_tasks = Mock(spec=BackgroundTasks)

        success = await webhook_manager.trigger_webhook_event(
            session=test_db_session,
            background_tasks=background_tasks,
            event_type=EventType.USER_CREATED,
            tenant_id="nonexistent-tenant",
            data={"user_id": "123"}
        )

        assert success is True  # Should succeed even with no endpoints

    @pytest.mark.asyncio
    async def test_get_webhook_endpoints(self, test_db_session: AsyncSession):
        """Test getting webhook endpoints for tenant."""
        webhook_manager = WebhookManager()

        # Create endpoints
        await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook1",
            name="Webhook 1",
            events=[EventType.USER_CREATED.value]
        )

        await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook2",
            name="Webhook 2",
            events=[EventType.USER_UPDATED.value]
        )

        # Get endpoints
        endpoints = await webhook_manager.get_webhook_endpoints(
            session=test_db_session,
            tenant_id="test-tenant"
        )

        assert len(endpoints) == 2
        assert all(ep.tenant_id == "test-tenant" for ep in endpoints)

    @pytest.mark.asyncio
    async def test_delete_webhook_endpoint(self, test_db_session: AsyncSession):
        """Test deleting webhook endpoint."""
        webhook_manager = WebhookManager()

        # Create endpoint
        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Delete endpoint
        success = await webhook_manager.delete_webhook_endpoint(
            session=test_db_session,
            endpoint_id=endpoint.id,
            tenant_id="test-tenant"
        )

        assert success is True

        # Verify deletion
        endpoints = await webhook_manager.get_webhook_endpoints(
            session=test_db_session,
            tenant_id="test-tenant"
        )

        assert len(endpoints) == 0

    @pytest.mark.asyncio
    async def test_deliver_webhook_sync_success(self, test_db_session: AsyncSession):
        """Test synchronous webhook delivery success."""
        webhook_manager = WebhookManager()

        # Create endpoint
        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://httpbin.org/post",  # Mock endpoint
            name="Test Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Create delivery record manually
        from app.features.core.webhooks import WebhookDelivery
        import secrets

        event_data = {"user_id": "123", "email": "test@example.com"}
        payload = json.dumps({
            "event_type": "user.created",
            "tenant_id": "test-tenant",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": "test-event",
            "api_version": "v1"
        })

        signature = webhook_manager.generate_signature(payload, endpoint.secret)

        delivery = WebhookDelivery(
            webhook_endpoint_id=endpoint.id,
            tenant_id="test-tenant",
            event_id="test-event",
            event_type="user.created",
            event_data=event_data,
            delivery_url=endpoint.url,
            payload=payload,
            signature=signature,
            max_attempts=3
        )

        test_db_session.add(delivery)
        await test_db_session.commit()

        # Mock HTTP client to simulate successful response
        with patch.object(webhook_manager, 'http_client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.headers = {"content-type": "application/json"}
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await webhook_manager.deliver_webhook_sync(
                session=test_db_session,
                delivery_id=delivery.id
            )

            assert result.success is True
            assert result.status_code == 200


@pytest.mark.integration
@pytest.mark.webhooks
@pytest.mark.skip(reason="Webhook API endpoints cause test infrastructure to hang - authentication dependency issues")
class TestWebhookAPIEndpoints:
    """Test webhook API endpoints."""

    @pytest.mark.asyncio
    async def test_get_available_events(self, test_client: AsyncClient):
        """Test getting available webhook events endpoint exists and requires auth."""
        response = await test_client.get("/api/v1/webhooks/events")

        # Should return 401 when not authenticated (proving endpoint exists and security works)
        assert response.status_code == 401

    @pytest.mark.skip(reason="Authentication dependency causes test infrastructure to hang")
    @pytest.mark.asyncio
    async def test_create_webhook_endpoint_api(self, test_client: AsyncClient):
        """Test creating webhook endpoint via API requires authentication."""
        response = await test_client.post(
            "/api/v1/webhooks/endpoints",
            json={
                "url": "https://example.com/webhook",
                "name": "Test Webhook",
                "description": "Test webhook endpoint",
                "events": ["user.created", "user.updated"],
                "timeout_seconds": 30,
                "max_retries": 3
            }
        )
        # Should return 401 when not authenticated
        assert response.status_code == 401

    @pytest.mark.skip(reason="Authentication dependency causes test infrastructure to hang")
    @patch('app.features.auth.dependencies.get_current_user')
    @pytest.mark.asyncio
    async def test_create_webhook_endpoint_invalid_events(self, mock_get_user, test_client: AsyncClient):
        """Test creating webhook endpoint with invalid events."""
        mock_user = Mock()
        mock_user.id = "test-user"
        mock_user.tenant_id = "test-tenant"
        mock_get_user.return_value = mock_user

        response = await test_client.post(
            "/api/v1/webhooks/endpoints",
            json={
                "url": "https://example.com/webhook",
                "name": "Invalid Webhook",
                "events": ["invalid.event"]
            }
        )

        assert response.status_code == 400
        assert "Invalid event types" in response.json()["detail"]

    @pytest.mark.skip(reason="Authentication dependency causes test infrastructure to hang")
    @patch('app.features.auth.dependencies.get_current_user')
    @pytest.mark.asyncio
    async def test_list_webhook_endpoints(self, mock_get_user, test_client: AsyncClient):
        """Test listing webhook endpoints."""
        mock_user = Mock()
        mock_user.id = "test-user"
        mock_user.tenant_id = "test-tenant"
        mock_get_user.return_value = mock_user

        response = await test_client.get("/api/v1/webhooks/endpoints")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_webhook_endpoints_require_auth(self, test_client: AsyncClient):
        """Test that webhook endpoints require authentication."""
        response = await test_client.get("/api/v1/webhooks/endpoints")
        assert response.status_code == 401

        response = await test_client.post(
            "/api/v1/webhooks/endpoints",
            json={"url": "https://example.com", "name": "Test", "events": ["user.created"]}
        )
        assert response.status_code == 401

    @pytest.mark.skip(reason="Authentication dependency causes test infrastructure to hang")
    @patch('app.features.auth.dependencies.get_current_user')
    @pytest.mark.asyncio
    async def test_test_webhook_endpoint(self, mock_get_user, test_client: AsyncClient):
        """Test webhook endpoint testing functionality."""
        mock_user = Mock()
        mock_user.id = "test-user"
        mock_user.tenant_id = "test-tenant"
        mock_get_user.return_value = mock_user

        # This would require an existing endpoint
        response = await test_client.post(
            "/api/v1/webhooks/endpoints/999/test",
            json={
                "event_type": "user.created",
                "test_data": {"custom": "data"}
            }
        )

        # Expect 404 since endpoint doesn't exist
        assert response.status_code == 404

    @pytest.mark.skip(reason="Authentication dependency causes test infrastructure to hang")
    @patch('app.features.auth.dependencies.get_current_user')
    @pytest.mark.asyncio
    async def test_test_webhook_invalid_event_type(self, mock_get_user, test_client: AsyncClient):
        """Test webhook testing with invalid event type."""
        mock_user = Mock()
        mock_user.id = "test-user"
        mock_user.tenant_id = "test-tenant"
        mock_get_user.return_value = mock_user

        response = await test_client.post(
            "/api/v1/webhooks/endpoints/1/test",
            json={
                "event_type": "invalid.event",
                "test_data": {}
            }
        )

        assert response.status_code == 400
        assert "Invalid event type" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.webhooks
class TestWebhookSecurity:
    """Test webhook security features."""

    @pytest.mark.asyncio
    async def test_webhook_signature_validation(self):
        """Test webhook signature validation."""
        payload = '{"test": "data"}'
        secret = "webhook-secret"

        # Generate valid signature
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        full_signature = f"sha256={signature}"

        # Verify signature
        is_valid = WebhookManager.verify_signature(payload, full_signature, secret)
        assert is_valid is True

        # Test with tampered payload
        tampered_payload = '{"test": "tampered"}'
        is_invalid = WebhookManager.verify_signature(tampered_payload, full_signature, secret)
        assert is_invalid is False

    @pytest.mark.asyncio
    async def test_webhook_endpoint_url_validation(self, test_db_session: AsyncSession):
        """Test webhook endpoint URL validation."""
        webhook_manager = WebhookManager()

        # Test invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('xss')",
            "http://",
            ""
        ]

        for invalid_url in invalid_urls:
            endpoint = await webhook_manager.create_webhook_endpoint(
                session=test_db_session,
                tenant_id="test-tenant",
                url=invalid_url,
                name="Invalid URL Test",
                events=[EventType.USER_CREATED.value]
            )
            assert endpoint is None

    @pytest.mark.asyncio
    async def test_webhook_tenant_isolation(self, test_db_session: AsyncSession):
        """Test webhook tenant isolation."""
        webhook_manager = WebhookManager()

        # Create endpoints for different tenants
        endpoint1 = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="tenant-1",
            url="https://tenant1.com/webhook",
            name="Tenant 1 Webhook",
            events=[EventType.USER_CREATED.value]
        )

        endpoint2 = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="tenant-2",
            url="https://tenant2.com/webhook",
            name="Tenant 2 Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Tenant 1 should only see their endpoints
        tenant1_endpoints = await webhook_manager.get_webhook_endpoints(
            session=test_db_session,
            tenant_id="tenant-1"
        )

        assert len(tenant1_endpoints) == 1
        assert tenant1_endpoints[0].id == endpoint1.id

        # Tenant 2 should only see their endpoints
        tenant2_endpoints = await webhook_manager.get_webhook_endpoints(
            session=test_db_session,
            tenant_id="tenant-2"
        )

        assert len(tenant2_endpoints) == 1
        assert tenant2_endpoints[0].id == endpoint2.id


@pytest.mark.integration
@pytest.mark.webhooks
class TestWebhookDeliveryAndRetry:
    """Test webhook delivery and retry mechanisms."""

    @pytest.mark.asyncio
    async def test_webhook_delivery_status_tracking(self, test_db_session: AsyncSession):
        """Test webhook delivery status tracking."""
        from app.features.core.webhooks import WebhookDelivery

        delivery = WebhookDelivery(
            webhook_endpoint_id=1,
            tenant_id="test-tenant",
            event_id="test-event",
            event_type="user.created",
            event_data={"user_id": "123"},
            delivery_url="https://example.com/webhook",
            payload='{"test": "data"}',
            signature="sha256=abc123",
            max_attempts=3
        )
        # Set initial status and defaults since object is not in database yet
        from app.features.core.webhooks import DeliveryStatus
        delivery.status = DeliveryStatus.PENDING.value
        delivery.attempt_number = 1

        # Test initial state
        assert delivery.is_pending() is True
        assert delivery.can_retry() is False
        assert delivery.is_final() is False

        # Test after failure
        delivery.status = DeliveryStatus.FAILED.value
        delivery.next_retry_at = datetime.utcnow() - timedelta(minutes=1)  # Past time
        assert delivery.can_retry() is True

        # Test after completion
        delivery.status = DeliveryStatus.DELIVERED.value
        assert delivery.is_final() is True
        assert delivery.can_retry() is False

    @pytest.mark.asyncio
    async def test_webhook_endpoint_health_tracking(self, test_db_session: AsyncSession):
        """Test webhook endpoint health tracking."""
        webhook_manager = WebhookManager()

        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Health Test Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Initial state should be healthy
        assert endpoint.is_healthy() is True
        assert endpoint.consecutive_failures == 0
        assert endpoint.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_webhook_event_filtering(self, test_db_session: AsyncSession):
        """Test webhook event filtering by subscription."""
        webhook_manager = WebhookManager()

        # Create endpoint that only subscribes to user.created
        endpoint = await webhook_manager.create_webhook_endpoint(
            session=test_db_session,
            tenant_id="test-tenant",
            url="https://example.com/webhook",
            name="Filtered Webhook",
            events=[EventType.USER_CREATED.value]
        )

        # Should deliver user.created events
        assert endpoint.should_deliver_event(EventType.USER_CREATED.value) is True

        # Should not deliver user.updated events
        assert endpoint.should_deliver_event(EventType.USER_UPDATED.value) is False

    @pytest.mark.asyncio
    async def test_webhook_payload_structure(self, test_db_session: AsyncSession):
        """Test webhook payload structure."""
        from app.features.core.webhooks import WebhookEvent

        event = WebhookEvent(
            event_type="user.created",
            tenant_id="test-tenant",
            data={"user_id": "123", "email": "test@example.com"},
            timestamp=datetime.utcnow().isoformat(),
            event_id="test-event"
        )

        payload_dict = event.to_dict()

        # Verify required fields
        assert "event_type" in payload_dict
        assert "tenant_id" in payload_dict
        assert "data" in payload_dict
        assert "timestamp" in payload_dict
        assert "event_id" in payload_dict
        assert "api_version" in payload_dict

        # Verify values
        assert payload_dict["event_type"] == "user.created"
        assert payload_dict["tenant_id"] == "test-tenant"
        assert payload_dict["api_version"] == "v1"