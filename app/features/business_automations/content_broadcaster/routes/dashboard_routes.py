"""
Content Broadcaster dashboard routes for statistics and analytics.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_db
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from .api_routes import get_content_service
from ..services import ContentBroadcasterService
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["content-broadcaster-dashboard"])

# --- DASHBOARD ROUTES ---

@router.get("/api/summary", response_class=JSONResponse)
async def get_summary_stats(
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get summary statistics for stats cards."""
    logger.info(f"Summary stats called for tenant: {tenant_id}")
    try:
        # Create service directly without using dependency
        service = ContentBroadcasterService(session, tenant_id)
        stats = await service.get_dashboard_stats()

        logger.info(f"Stats retrieved successfully: {stats}")

        # Format for stats cards
        result = {
            "total_content": stats.get("total_content", 0),
            "pending_approvals": stats.get("pending_approvals", 0),
            "scheduled_count": stats.get("content_by_state", {}).get("scheduled", 0),
            "published_count": stats.get("content_by_state", {}).get("published", 0)
        }
        logger.info(f"Returning formatted result: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to get summary stats")
        raise HTTPException(status_code=500, detail="Failed to get stats")

@router.get("/api/approvals/pending")
async def get_pending_approvals(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """API endpoint to get content pending approval."""
    try:
        from ..models import ApprovalStatus

        result = await service.get_content_list(
            limit=limit,
            offset=offset,
            approval_status=ApprovalStatus.pending
        )
        return result

    except Exception as e:
        logger.exception("Failed to get pending approvals")
        raise HTTPException(status_code=500, detail="Failed to retrieve pending approvals")
