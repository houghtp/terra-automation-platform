"""
Streaming routes for real-time campaign status updates.

Handles:
- GET /stream/{campaign_id} - Server-Sent Events (SSE) for AI research progress
"""

import asyncio
import json
from typing import AsyncIterator
from fastapi.responses import StreamingResponse

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_campaign_service
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService

logger = get_logger(__name__)
router = APIRouter()


async def campaign_progress_generator(
    campaign_id: str,
    service: CampaignCrudService,
    poll_interval: int = 2
) -> AsyncIterator[str]:
    """
    Generate SSE events for campaign AI research progress.

    Follows CSPM pattern for real-time status updates.

    Args:
        campaign_id: Campaign ID to stream
        service: Campaign service instance
        poll_interval: Polling interval in seconds

    Yields:
        SSE formatted progress events
    """
    logger.info("Starting SSE stream for campaign", campaign_id=campaign_id)

    try:
        while True:
            # Get current campaign state (force refresh from database)
            campaign = await service.get_campaign_by_id(campaign_id)

            if not campaign:
                logger.warning("Campaign not found for streaming", campaign_id=campaign_id)
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': 'Campaign not found'})}\n\n"
                break

            # Force SQLAlchemy to refresh from database (avoid stale data)
            await service.db.refresh(campaign)

            # Build status update payload
            event_data = {
                "id": campaign.id,
                "status": campaign.status,
                "discovery_type": campaign.discovery_type,
                "total_prospects": campaign.total_prospects or 0,
                "enriched_prospects": campaign.enriched_prospects or 0,
                "research_data": campaign.research_data
            }

            logger.debug(
                "Streaming poll",
                campaign_id=campaign_id,
                status=campaign.status,
                has_research_data=bool(campaign.research_data),
                total_prospects=campaign.total_prospects
            )

            # Send progress event
            yield f"event: progress\n"
            yield f"data: {json.dumps(event_data, default=str)}\n\n"

            # Check if research is complete (status changed from "draft" to "active")
            # Following CSPM pattern: detect terminal status change
            if campaign.discovery_type == "ai_research" and campaign.status == "active":
                # Send complete event
                yield f"event: complete\n"
                yield f"data: {json.dumps({'campaign_id': campaign_id, 'status': 'active'})}\n\n"
                logger.info("AI research complete, closing stream", campaign_id=campaign_id, status=campaign.status)
                break

            # Poll every N seconds
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info("Stream cancelled by client", campaign_id=campaign_id)
    except Exception as e:
        logger.error("Error in campaign stream", campaign_id=campaign_id, error=str(e))
        yield f"event: error\n"
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.get("/stream/{campaign_id}")
async def stream_campaign_status(
    campaign_id: str,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events endpoint for campaign AI research progress.

    Args:
        campaign_id: Campaign ID to stream
        service: Campaign service
        current_user: Current user

    Returns:
        StreamingResponse with SSE events
    """
    return StreamingResponse(
        campaign_progress_generator(campaign_id, service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
