"""
Dashboard routes for analytics and chart data
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.templates import templates
from app.features.dashboard.services import DashboardService
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    session: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_active_user)
):
    """Render the main dashboard page with charts"""
    try:
        # Get summary statistics
        summary = await DashboardService.get_dashboard_summary(session, tenant)

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
        print(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "dashboard/dashboard.html",
            {
                "request": request,
                "summary": {},
                "page_title": "Dashboard",
                "error": "Failed to load dashboard data"
            }
        )


# API endpoints for chart data and summary stats
@router.get("/api/summary")
async def dashboard_summary(
    session: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency)
):
    """Get dashboard summary statistics."""
    summary = await DashboardService.get_dashboard_summary(session, tenant)
    return summary

@router.get("/api/status-breakdown")
async def status_breakdown(
    session: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency)
):
    """Get breakdown of demo items by status."""
    data = await DashboardService.get_user_status_breakdown(session, tenant)
    return data


@router.get("/api/enabled-breakdown")
async def enabled_breakdown(
    session: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency)
):
    """Get breakdown of demo items by enabled status."""
    data = await DashboardService.get_user_enabled_breakdown(session, tenant)
    return data


@router.get("/api/items-timeline")
async def items_timeline(
    session: AsyncSession = Depends(get_db)
):
    """Get timeline of demo items creation."""
    data = await DashboardService.get_user_items_over_time(session)
    return data


@router.get("/api/tags-distribution")
async def tags_distribution(
    session: AsyncSession = Depends(get_db)
):
    """Get distribution of tags used in demo items."""
    data = await DashboardService.get_user_tag_distribution(session)
    return data
