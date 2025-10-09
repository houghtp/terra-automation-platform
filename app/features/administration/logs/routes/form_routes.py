# Gold Standard Route Imports - Logs Forms
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException,
    HTMLResponse, AsyncSession, get_db, templates,
    tenant_dependency, get_current_user, User,
    get_logger
)
from datetime import datetime
from ..services import LogManagementService

router = APIRouter(tags=["logs-forms"])
logger = get_logger(__name__)


async def get_log_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> LogManagementService:
    """Get log service dependency."""
    return LogManagementService(db, tenant_id)

# --- UI ROUTES (Jinja + HTMX) ---

@router.get("/", response_class=HTMLResponse, name="logs_dashboard")
async def logs_dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    log_service: LogManagementService = Depends(get_log_service)
):
    """Render the application logs dashboard."""
    try:
        # Get log statistics
        stats = await log_service.get_logs_stats()

        # Get recent logs for display
        recent_logs = await log_service.get_application_logs(
            limit=20,
            sort_by="timestamp",
            sort_order="desc"
        )

        context = {
            "request": request,
            "user": current_user,
            "page_title": "Application Logs",
            "page_description": "View and filter application logs by tenant",
            "stats": stats,
            "recent_logs": recent_logs,
        }

        return templates.TemplateResponse(
            "administration/logs/logs_dashboard.html",
            context
        )

    except Exception as e:
        logger.exception("Failed to render logs dashboard")
        raise HTTPException(status_code=500, detail="Failed to load logs dashboard")


@router.get("/partials/log_details", response_class=HTMLResponse, name="log_details_partial")
async def get_log_details_partial(
    request: Request,
    log_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    log_service: LogManagementService = Depends(get_log_service)
):
    """Get application log details partial for modal display."""
    try:
        log = await log_service.get_application_log_by_id(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Application log not found")

        context = {
            "request": request,
            "log": log
        }

        return templates.TemplateResponse(
            "administration/logs/partials/log_details.html",
            context
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get log details")
        raise HTTPException(status_code=500, detail="Failed to load log details")
