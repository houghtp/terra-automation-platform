# Gold Standard Route Imports - Audit Forms
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Query,
    HTMLResponse, AsyncSession, get_db, templates,
    tenant_dependency, get_current_user, User,
    Optional, get_logger
)
from datetime import datetime
from ..services import AuditManagementService

router = APIRouter(tags=["audit-forms"])
logger = get_logger(__name__)


async def get_audit_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> AuditManagementService:
    """Get audit service dependency."""
    return AuditManagementService(db, tenant_id)

# --- UI ROUTES (Jinja + HTMX) ---

@router.get("/", response_class=HTMLResponse, name="audit_dashboard")
async def audit_dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    audit_service: AuditManagementService = Depends(get_audit_service)
):
    """Render the audit logs dashboard."""
    try:
        # Get audit statistics
        stats = await audit_service.get_audit_stats()

        # Get recent audit logs for display
        recent_logs = await audit_service.get_audit_logs(
            limit=20,
            sort_by="timestamp",
            sort_order="desc"
        )

        context = {
            "request": request,
            "title": "Audit Logs",
            "stats": stats,
            "recent_logs": recent_logs,
        }

        return templates.TemplateResponse(
            "audit_dashboard.html",
            context
        )

    except Exception as e:
        logger.exception("Failed to render audit dashboard")
        raise HTTPException(status_code=500, detail="Failed to load audit dashboard")

@router.get("/partials/filtered_list", response_class=HTMLResponse, name="audit_filtered_list_partial")
async def get_filtered_list_partial(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    audit_service: AuditManagementService = Depends(get_audit_service)
):
    """Get filtered audit logs partial for HTMX updates."""
    try:
        # Parse date filters
        date_from_dt = None
        date_to_dt = None

        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")

        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")

        # Get filtered audit logs
        logs = await audit_service.get_audit_logs(
            limit=100,  # Show more for filtered view
            offset=0,
            category_filter=category,
            severity_filter=severity,
            user_filter=user,
            action_filter=action,
            date_from=date_from_dt,
            date_to=date_to_dt,
            sort_by="timestamp",
            sort_order="desc"
        )

        context = {
            "request": request,
            "logs": logs,
            "filters": {
                "category": category,
                "severity": severity,
                "user": user,
                "action": action,
                "date_from": date_from,
                "date_to": date_to
            }
        }

        return templates.TemplateResponse(
            "partials/filtered_table.html",
            context
        )

    except Exception as e:
        logger.exception("Failed to get filtered audit logs partial")
        raise HTTPException(status_code=500, detail="Failed to load filtered audit logs")

@router.get("/partials/log_details", response_class=HTMLResponse, name="audit_log_details_partial")
async def get_log_details_partial(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    log_id: int = Query(...),
    audit_service: AuditManagementService = Depends(get_audit_service)
):
    """Get audit log details partial for modal display."""
    try:
        log = await audit_service.get_audit_log_by_id(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")

        context = {
            "request": request,
            "log": log
        }

        return templates.TemplateResponse(
            "partials/log_details.html",
            context
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get audit log details partial for {log_id}")
        raise HTTPException(status_code=500, detail="Failed to load audit log details")
