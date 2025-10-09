"""
Enterprise webhook system for real-time integrations.

Provides secure, reliable webhook delivery with retry mechanisms,
signature verification, and comprehensive monitoring.
"""
import json
import hmac
import hashlib
import secrets
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

import httpx
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import BackgroundTasks
import structlog

from app.features.core.database import Base

logger = structlog.get_logger(__name__)


class WebhookStatus(Enum):
    """Webhook endpoint status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"


class EventType(Enum):
    """Available webhook event types."""
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    AUDIT_LOG_CREATED = "audit.log_created"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    MFA_ENABLED = "mfa.enabled"
    MFA_DISABLED = "mfa.disabled"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"


class DeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"


@dataclass
class WebhookEvent:
    """Webhook event payload structure."""
    event_type: str
    tenant_id: str
    data: Dict[str, Any]
    timestamp: str
    event_id: str
    api_version: str = "v1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class DeliveryResult:
    """Result of webhook delivery attempt."""
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    delivery_time_ms: Optional[float] = None


class WebhookEndpoint(Base):
    """
    Webhook endpoint configuration.

    Stores customer webhook endpoints and their settings.
    """
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Endpoint configuration
    url = Column(String(2048), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Security
    secret = Column(String(255), nullable=False)  # For HMAC signature

    # Event filtering
    events = Column(JSON, nullable=False)  # List of subscribed event types

    # Status and health
    status = Column(String(20), default=WebhookStatus.ACTIVE.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Delivery settings
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Health tracking
    last_delivery_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    total_deliveries = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)

    @property
    def success_rate(self) -> float:
        """Calculate delivery success rate."""
        if self.total_deliveries == 0:
            return 100.0
        return (self.successful_deliveries / self.total_deliveries) * 100

    def is_healthy(self) -> bool:
        """Check if endpoint is considered healthy."""
        # Consider unhealthy if too many consecutive failures
        return self.consecutive_failures < 5 and self.status == WebhookStatus.ACTIVE.value

    def should_deliver_event(self, event_type: str) -> bool:
        """Check if endpoint should receive this event type."""
        return self.is_active and event_type in (self.events or [])


class WebhookDelivery(Base):
    """
    Webhook delivery attempt tracking.

    Records all delivery attempts for monitoring and debugging.
    """
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_endpoint_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Event details
    event_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)

    # Delivery details
    delivery_url = Column(String(2048), nullable=False)
    http_method = Column(String(10), default="POST", nullable=False)
    headers = Column(JSON, nullable=True)
    payload = Column(Text, nullable=False)
    signature = Column(String(255), nullable=True)

    # Response tracking
    status = Column(String(20), default=DeliveryStatus.PENDING.value, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Response details
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    scheduled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    attempted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    delivery_time_ms = Column(Float, nullable=True)

    # Retry scheduling
    next_retry_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def is_pending(self) -> bool:
        """Check if delivery is pending."""
        return self.status == DeliveryStatus.PENDING.value

    def can_retry(self) -> bool:
        """Check if delivery can be retried."""
        return (
            self.status in [DeliveryStatus.FAILED.value, DeliveryStatus.RETRYING.value] and
            self.attempt_number < self.max_attempts and
            self.next_retry_at and
            datetime.now(timezone.utc) >= self.next_retry_at
        )

    def is_final(self) -> bool:
        """Check if delivery is in final state (no more retries)."""
        return self.status in [DeliveryStatus.DELIVERED.value, DeliveryStatus.EXHAUSTED.value]


class WebhookManager:
    """
    Manages webhook operations and delivery.

    Features:
    - Endpoint registration and management
    - Event triggering and delivery
    - Retry mechanisms with exponential backoff
    - Signature verification
    - Health monitoring and automatic disabling
    """

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.http_client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    @staticmethod
    def generate_webhook_secret() -> str:
        """Generate secure webhook secret."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        expected_signature = WebhookManager.generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)

    async def create_webhook_endpoint(
        self,
        session: AsyncSession,
        tenant_id: str,
        url: str,
        name: str,
        events: List[str],
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3
    ) -> Optional[WebhookEndpoint]:
        """Create a new webhook endpoint."""
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL format")

            if parsed_url.scheme not in ["http", "https"]:
                raise ValueError("URL must use HTTP or HTTPS")

            # Validate events
            valid_events = [e.value for e in EventType]
            invalid_events = [e for e in events if e not in valid_events]
            if invalid_events:
                raise ValueError(f"Invalid event types: {invalid_events}")

            # Generate secret
            secret = self.generate_webhook_secret()

            # Create endpoint
            endpoint = WebhookEndpoint(
                tenant_id=tenant_id,
                url=url,
                name=name,
                description=description,
                secret=secret,
                events=events,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                created_by=created_by
            )

            session.add(endpoint)
            await session.commit()

            logger.info(f"Created webhook endpoint {endpoint.id} for tenant {tenant_id}")
            return endpoint

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create webhook endpoint: {e}")
            return None

    async def trigger_webhook_event(
        self,
        session: AsyncSession,
        background_tasks: BackgroundTasks,
        event_type: EventType,
        tenant_id: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> bool:
        """Trigger webhook event to all subscribed endpoints."""
        try:
            # Generate event ID if not provided
            if not event_id:
                event_id = secrets.token_urlsafe(16)

            # Create event payload
            event = WebhookEvent(
                event_type=event_type.value,
                tenant_id=tenant_id,
                data=data,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=event_id
            )

            # Get all active endpoints for this tenant that subscribe to this event
            stmt = select(WebhookEndpoint).where(
                WebhookEndpoint.tenant_id == tenant_id,
                WebhookEndpoint.is_active == True
            )
            result = await session.execute(stmt)
            endpoints = result.scalars().all()

            # Filter endpoints that should receive this event
            relevant_endpoints = [
                ep for ep in endpoints
                if ep.should_deliver_event(event_type.value)
            ]

            if not relevant_endpoints:
                logger.debug(f"No endpoints for event {event_type.value} in tenant {tenant_id}")
                return True

            # Schedule deliveries
            for endpoint in relevant_endpoints:
                await self._schedule_delivery(
                    session=session,
                    endpoint=endpoint,
                    event=event,
                    background_tasks=background_tasks
                )

            await session.commit()
            logger.info(f"Scheduled {len(relevant_endpoints)} deliveries for event {event_id}")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to trigger webhook event: {e}")
            return False

    async def _schedule_delivery(
        self,
        session: AsyncSession,
        endpoint: WebhookEndpoint,
        event: WebhookEvent,
        background_tasks: BackgroundTasks
    ):
        """Schedule webhook delivery."""
        try:
            # Create payload
            payload = json.dumps(event.to_dict(), separators=(',', ':'))

            # Generate signature
            signature = self.generate_signature(payload, endpoint.secret)

            # Create delivery record
            delivery = WebhookDelivery(
                webhook_endpoint_id=endpoint.id,
                tenant_id=endpoint.tenant_id,
                event_id=event.event_id,
                event_type=event.event_type,
                event_data=event.data,
                delivery_url=endpoint.url,
                payload=payload,
                signature=signature,
                max_attempts=endpoint.max_retries
            )

            session.add(delivery)
            await session.flush()  # Get the ID

            # Schedule background delivery
            background_tasks.add_task(
                self._deliver_webhook,
                delivery.id
            )

            logger.debug(f"Scheduled delivery {delivery.id} to {endpoint.url}")

        except Exception as e:
            logger.error(f"Failed to schedule delivery: {e}")
            raise

    async def _deliver_webhook(self, delivery_id: int, session: Optional[AsyncSession] = None):
        """Deliver webhook (background task)."""
        # Note: In a real implementation, you'd get a new session here
        # For now, this is a placeholder for the delivery logic
        logger.info(f"Processing webhook delivery {delivery_id}")

        # This would:
        # 1. Load delivery from database
        # 2. Make HTTP request
        # 3. Update delivery status
        # 4. Schedule retry if needed
        # 5. Update endpoint health metrics

    async def deliver_webhook_sync(
        self,
        session: AsyncSession,
        delivery_id: int
    ) -> DeliveryResult:
        """Synchronously deliver webhook (for testing/manual retry)."""
        try:
            # Get delivery record
            stmt = select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
            result = await session.execute(stmt)
            delivery = result.scalar_one_or_none()

            if not delivery:
                return DeliveryResult(
                    success=False,
                    error_message="Delivery not found"
                )

            # Mark as attempting
            delivery.attempted_at = datetime.now(timezone.utc)
            delivery.status = DeliveryStatus.RETRYING.value if delivery.attempt_number > 1 else DeliveryStatus.PENDING.value

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": delivery.signature,
                "X-Webhook-Event-Type": delivery.event_type,
                "X-Webhook-Event-ID": delivery.event_id,
                "User-Agent": "FastAPI-Webhooks/1.0"
            }

            # Make HTTP request
            start_time = datetime.now(timezone.utc)
            try:
                response = await self.http_client.post(
                    delivery.delivery_url,
                    data=delivery.payload,
                    headers=headers,
                    timeout=30.0
                )

                end_time = datetime.now(timezone.utc)
                delivery_time_ms = (end_time - start_time).total_seconds() * 1000

                # Update delivery record
                delivery.response_status_code = response.status_code
                delivery.response_headers = dict(response.headers)
                delivery.response_body = response.text[:1000]  # Limit size
                delivery.delivery_time_ms = delivery_time_ms
                delivery.completed_at = end_time

                # Check if successful
                if 200 <= response.status_code < 300:
                    delivery.status = DeliveryStatus.DELIVERED.value
                    await self._update_endpoint_success(session, delivery.webhook_endpoint_id)

                    await session.commit()
                    return DeliveryResult(
                        success=True,
                        status_code=response.status_code,
                        response_body=response.text,
                        delivery_time_ms=delivery_time_ms
                    )
                else:
                    # HTTP error
                    delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    await self._handle_delivery_failure(session, delivery)

                    return DeliveryResult(
                        success=False,
                        status_code=response.status_code,
                        response_body=response.text,
                        error_message=delivery.error_message,
                        delivery_time_ms=delivery_time_ms
                    )

            except httpx.TimeoutException:
                delivery.error_message = "Request timeout"
                await self._handle_delivery_failure(session, delivery)

                return DeliveryResult(
                    success=False,
                    error_message="Request timeout"
                )

            except Exception as e:
                delivery.error_message = f"Request failed: {str(e)}"
                await self._handle_delivery_failure(session, delivery)

                return DeliveryResult(
                    success=False,
                    error_message=str(e)
                )

        except Exception as e:
            logger.error(f"Failed to deliver webhook {delivery_id}: {e}")
            return DeliveryResult(
                success=False,
                error_message=f"Delivery failed: {str(e)}"
            )

    async def _handle_delivery_failure(self, session: AsyncSession, delivery: WebhookDelivery):
        """Handle failed webhook delivery."""
        delivery.attempt_number += 1

        if delivery.attempt_number >= delivery.max_attempts:
            # No more retries
            delivery.status = DeliveryStatus.EXHAUSTED.value
            delivery.completed_at = datetime.now(timezone.utc)
            await self._update_endpoint_failure(session, delivery.webhook_endpoint_id)
        else:
            # Schedule retry with exponential backoff
            delay_minutes = 2 ** (delivery.attempt_number - 1)  # 1, 2, 4, 8...
            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
            delivery.status = DeliveryStatus.FAILED.value

        await session.commit()

    async def _update_endpoint_success(self, session: AsyncSession, endpoint_id: int):
        """Update endpoint metrics for successful delivery."""
        stmt = update(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id
        ).values(
            last_delivery_at=datetime.now(timezone.utc),
            last_success_at=datetime.now(timezone.utc),
            consecutive_failures=0,
            total_deliveries=WebhookEndpoint.total_deliveries + 1,
            successful_deliveries=WebhookEndpoint.successful_deliveries + 1
        )
        await session.execute(stmt)

    async def _update_endpoint_failure(self, session: AsyncSession, endpoint_id: int):
        """Update endpoint metrics for failed delivery."""
        stmt = update(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id
        ).values(
            last_delivery_at=datetime.now(timezone.utc),
            consecutive_failures=WebhookEndpoint.consecutive_failures + 1,
            total_deliveries=WebhookEndpoint.total_deliveries + 1
        )
        await session.execute(stmt)

        # Check if endpoint should be disabled
        endpoint_stmt = select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id)
        result = await session.execute(endpoint_stmt)
        endpoint = result.scalar_one_or_none()

        if endpoint and endpoint.consecutive_failures >= 10:
            # Disable endpoint after too many failures
            endpoint.status = WebhookStatus.FAILED.value
            endpoint.is_active = False
            logger.warning(f"Disabled webhook endpoint {endpoint_id} due to consecutive failures")

    async def get_webhook_endpoints(
        self,
        session: AsyncSession,
        tenant_id: str,
        include_inactive: bool = False
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints for a tenant."""
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.tenant_id == tenant_id
        )

        if not include_inactive:
            stmt = stmt.where(WebhookEndpoint.is_active == True)

        result = await session.execute(stmt)
        return result.scalars().all()

    async def delete_webhook_endpoint(
        self,
        session: AsyncSession,
        endpoint_id: int,
        tenant_id: str
    ) -> bool:
        """Delete webhook endpoint."""
        try:
            stmt = delete(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.tenant_id == tenant_id
            )
            result = await session.execute(stmt)
            await session.commit()

            success = result.rowcount > 0
            if success:
                logger.info(f"Deleted webhook endpoint {endpoint_id}")

            return success

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete webhook endpoint {endpoint_id}: {e}")
            return False
