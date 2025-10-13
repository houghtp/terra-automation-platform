"""
Dashboard routes for analytics and chart data.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.templates import templates
from app.features.dashboard.services import DashboardService
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_active_user)
):
    """Render the main dashboard page with charts."""
    try:
        # Initialize service with tenant context
        service = DashboardService(db, tenant_id)

        # Get summary statistics
        summary = await service.get_dashboard_summary()

        return templates.TemplateResponse(
            "dashboard/dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "summary": summary,
                "page_title": "Dashboard"
            }
        )
    except Exception as e:
        logger.error("Failed to load dashboard", error=str(e), tenant_id=tenant_id)
        return templates.TemplateResponse(
            "dashboard/dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "summary": {},
                "page_title": "Dashboard",
                "error": "Failed to load dashboard data"
            }
        )


# API endpoints for chart data and summary stats
@router.get("/api/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
):
    """Get dashboard summary statistics."""
    try:
        service = DashboardService(db, tenant_id)
        summary = await service.get_dashboard_summary()
        return summary
    except Exception as e:
        logger.error("Failed to get dashboard summary", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load dashboard summary")


@router.get("/api/status-breakdown")
async def status_breakdown(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
):
    """Get breakdown of users by status."""
    try:
        service = DashboardService(db, tenant_id)
        data = await service.get_user_status_breakdown()
        return data
    except Exception as e:
        logger.error("Failed to get status breakdown", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load status breakdown")


@router.get("/api/enabled-breakdown")
async def enabled_breakdown(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
):
    """Get breakdown of users by enabled status."""
    try:
        service = DashboardService(db, tenant_id)
        data = await service.get_user_enabled_breakdown()
        return data
    except Exception as e:
        logger.error("Failed to get enabled breakdown", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load enabled breakdown")


@router.get("/api/items-timeline")
async def items_timeline(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
):
    """Get timeline of user creation over time."""
    try:
        service = DashboardService(db, tenant_id)
        data = await service.get_user_items_over_time()
        return data
    except Exception as e:
        logger.error("Failed to get items timeline", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load items timeline")


@router.get("/api/tags-distribution")
async def tags_distribution(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
):
    """Get distribution of tags used in users."""
    try:
        service = DashboardService(db, tenant_id)
        data = await service.get_user_tag_distribution()
        return data
    except Exception as e:
        logger.error("Failed to get tags distribution", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to load tags distribution")
