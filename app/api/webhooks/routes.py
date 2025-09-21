"""
Webhook API endpoints for integration management.

Provides webhook endpoint configuration, monitoring, and testing capabilities.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.webhooks import WebhookManager, WebhookEndpoint, WebhookDelivery, EventType
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# Initialize webhook manager
webhook_manager = WebhookManager()


# Request/Response Models
class WebhookEndpointRequest(BaseModel):
    """Request to create webhook endpoint."""
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    name: str = Field(..., min_length=1, max_length=255, description="Endpoint name")
    description: Optional[str] = Field(None, max_length=1000, description="Endpoint description")
    events: List[str] = Field(..., min_items=1, description="List of event types to subscribe to")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")


class WebhookEndpointResponse(BaseModel):
    """Webhook endpoint information."""
    id: int
    url: str
    name: str
    description: Optional[str]
    events: List[str]
    status: str
    is_active: bool
    timeout_seconds: int
    max_retries: int
    secret: str  # Only shown on creation/retrieval
    last_delivery_at: Optional[str]
    last_success_at: Optional[str]
    consecutive_failures: int
    total_deliveries: int
    successful_deliveries: int
    success_rate: float
    created_at: str
    updated_at: str


class WebhookEndpointListResponse(BaseModel):
    """Webhook endpoint list item (without secret)."""
    id: int
    url: str
    name: str
    description: Optional[str]
    events: List[str]
    status: str
    is_active: bool
    last_delivery_at: Optional[str]
    last_success_at: Optional[str]
    consecutive_failures: int
    total_deliveries: int
    successful_deliveries: int
    success_rate: float
    created_at: str


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery information."""
    id: int
    event_id: str
    event_type: str
    status: str
    attempt_number: int
    max_attempts: int
    response_status_code: Optional[int]
    error_message: Optional[str]
    delivery_time_ms: Optional[float]
    scheduled_at: str
    attempted_at: Optional[str]
    completed_at: Optional[str]
    next_retry_at: Optional[str]


class TestWebhookRequest(BaseModel):
    """Request to test webhook endpoint."""
    event_type: str = Field(..., description="Event type to test")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Custom test data")


class AvailableEventsResponse(BaseModel):
    """Available webhook event types."""
    events: Dict[str, str]


# Webhook Endpoint Management
@router.get("/events", response_model=AvailableEventsResponse)
async def get_available_events(current_user: User = Depends(get_current_user)):
    """Get list of available webhook event types."""
    events = {event.value: event.name for event in EventType}
    return AvailableEventsResponse(events=events)


@router.post("/endpoints", response_model=WebhookEndpointResponse)
async def create_webhook_endpoint(
    request: WebhookEndpointRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create a new webhook endpoint."""
    try:
        # Validate event types
        valid_events = [e.value for e in EventType]
        invalid_events = [e for e in request.events if e not in valid_events]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event types: {invalid_events}"
            )

        endpoint = await webhook_manager.create_webhook_endpoint(
            session=session,
            tenant_id=current_user.tenant_id,
            url=str(request.url),
            name=request.name,
            events=request.events,
            description=request.description,
            created_by=current_user.id,
            timeout_seconds=request.timeout_seconds,
            max_retries=request.max_retries
        )

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create webhook endpoint"
            )

        return WebhookEndpointResponse(
            id=endpoint.id,
            url=endpoint.url,
            name=endpoint.name,
            description=endpoint.description,
            events=endpoint.events,
            status=endpoint.status,
            is_active=endpoint.is_active,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            secret=endpoint.secret,
            last_delivery_at=endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
            last_success_at=endpoint.last_success_at.isoformat() if endpoint.last_success_at else None,
            consecutive_failures=endpoint.consecutive_failures,
            total_deliveries=endpoint.total_deliveries,
            successful_deliveries=endpoint.successful_deliveries,
            success_rate=endpoint.success_rate,
            created_at=endpoint.created_at.isoformat(),
            updated_at=endpoint.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create webhook endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook endpoint"
        )


@router.get("/endpoints", response_model=List[WebhookEndpointListResponse])
async def list_webhook_endpoints(
    include_inactive: bool = Query(False, description="Include inactive endpoints"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """List webhook endpoints for the current tenant."""
    try:
        endpoints = await webhook_manager.get_webhook_endpoints(
            session=session,
            tenant_id=current_user.tenant_id,
            include_inactive=include_inactive
        )

        return [
            WebhookEndpointListResponse(
                id=endpoint.id,
                url=endpoint.url,
                name=endpoint.name,
                description=endpoint.description,
                events=endpoint.events,
                status=endpoint.status,
                is_active=endpoint.is_active,
                last_delivery_at=endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
                last_success_at=endpoint.last_success_at.isoformat() if endpoint.last_success_at else None,
                consecutive_failures=endpoint.consecutive_failures,
                total_deliveries=endpoint.total_deliveries,
                successful_deliveries=endpoint.successful_deliveries,
                success_rate=endpoint.success_rate,
                created_at=endpoint.created_at.isoformat()
            )
            for endpoint in endpoints
        ]

    except Exception as e:
        logger.error(f"Failed to list webhook endpoints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhook endpoints"
        )


@router.get("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def get_webhook_endpoint(
    endpoint_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get webhook endpoint details including secret."""
    try:
        from sqlalchemy import select
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.tenant_id == current_user.tenant_id
        )
        result = await session.execute(stmt)
        endpoint = result.scalar_one_or_none()

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )

        return WebhookEndpointResponse(
            id=endpoint.id,
            url=endpoint.url,
            name=endpoint.name,
            description=endpoint.description,
            events=endpoint.events,
            status=endpoint.status,
            is_active=endpoint.is_active,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            secret=endpoint.secret,
            last_delivery_at=endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
            last_success_at=endpoint.last_success_at.isoformat() if endpoint.last_success_at else None,
            consecutive_failures=endpoint.consecutive_failures,
            total_deliveries=endpoint.total_deliveries,
            successful_deliveries=endpoint.successful_deliveries,
            success_rate=endpoint.success_rate,
            created_at=endpoint.created_at.isoformat(),
            updated_at=endpoint.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook endpoint {endpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook endpoint"
        )


@router.delete("/endpoints/{endpoint_id}")
async def delete_webhook_endpoint(
    endpoint_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Delete webhook endpoint."""
    try:
        success = await webhook_manager.delete_webhook_endpoint(
            session=session,
            endpoint_id=endpoint_id,
            tenant_id=current_user.tenant_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )

        return {"message": "Webhook endpoint deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook endpoint {endpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook endpoint"
        )


@router.post("/endpoints/{endpoint_id}/test")
async def test_webhook_endpoint(
    endpoint_id: int,
    request: TestWebhookRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Send test webhook to endpoint."""
    try:
        # Validate event type
        try:
            event_type = EventType(request.event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {request.event_type}"
            )

        # Check endpoint exists and belongs to tenant
        from sqlalchemy import select
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.tenant_id == current_user.tenant_id
        )
        result = await session.execute(stmt)
        endpoint = result.scalar_one_or_none()

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )

        # Create test data
        test_data = {
            "test": True,
            "user_id": current_user.id,
            "message": "This is a test webhook event",
            **request.test_data
        }

        # Trigger test event
        success = await webhook_manager.trigger_webhook_event(
            session=session,
            background_tasks=background_tasks,
            event_type=event_type,
            tenant_id=current_user.tenant_id,
            data=test_data
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger test webhook"
            )

        return {
            "message": "Test webhook scheduled successfully",
            "event_type": event_type.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook endpoint {endpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test webhook endpoint"
        )


# Delivery Monitoring
@router.get("/endpoints/{endpoint_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    endpoint_id: int,
    limit: int = Query(50, ge=1, le=100, description="Number of deliveries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get webhook delivery history for an endpoint."""
    try:
        # Verify endpoint belongs to tenant
        from sqlalchemy import select
        endpoint_stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.tenant_id == current_user.tenant_id
        )
        endpoint_result = await session.execute(endpoint_stmt)
        endpoint = endpoint_result.scalar_one_or_none()

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )

        # Get deliveries
        deliveries_stmt = select(WebhookDelivery).where(
            WebhookDelivery.webhook_endpoint_id == endpoint_id
        ).order_by(WebhookDelivery.created_at.desc()).limit(limit).offset(offset)

        deliveries_result = await session.execute(deliveries_stmt)
        deliveries = deliveries_result.scalars().all()

        return [
            WebhookDeliveryResponse(
                id=delivery.id,
                event_id=delivery.event_id,
                event_type=delivery.event_type,
                status=delivery.status,
                attempt_number=delivery.attempt_number,
                max_attempts=delivery.max_attempts,
                response_status_code=delivery.response_status_code,
                error_message=delivery.error_message,
                delivery_time_ms=delivery.delivery_time_ms,
                scheduled_at=delivery.scheduled_at.isoformat(),
                attempted_at=delivery.attempted_at.isoformat() if delivery.attempted_at else None,
                completed_at=delivery.completed_at.isoformat() if delivery.completed_at else None,
                next_retry_at=delivery.next_retry_at.isoformat() if delivery.next_retry_at else None
            )
            for delivery in deliveries
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook deliveries for endpoint {endpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook deliveries"
        )


@router.post("/deliveries/{delivery_id}/retry")
async def retry_webhook_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Manually retry a failed webhook delivery."""
    try:
        # Get delivery and verify access
        from sqlalchemy import select
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.tenant_id == current_user.tenant_id
        )
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()

        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook delivery not found"
            )

        if delivery.is_final():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot retry completed or exhausted delivery"
            )

        # Perform delivery
        delivery_result = await webhook_manager.deliver_webhook_sync(
            session=session,
            delivery_id=delivery_id
        )

        return {
            "message": "Delivery retry completed",
            "success": delivery_result.success,
            "status_code": delivery_result.status_code,
            "error_message": delivery_result.error_message,
            "delivery_time_ms": delivery_result.delivery_time_ms
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry webhook delivery {delivery_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry webhook delivery"
        )