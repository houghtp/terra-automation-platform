"""
Log management routes for viewing and filtering application logs by tenant.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.templates import templates
from .models import ApplicationLog
from .services import LogService
from app.features.auth.dependencies import get_current_user
from app.deps.tenant import tenant_dependency
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/logs", tags=["logs"])


async def get_log_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> LogService:
    """Dependency to get log service with tenant isolation."""
    # Global admins can see logs from all tenants
    if hasattr(current_user, 'role') and current_user.role == 'global_admin':
        return LogService(db, None)  # None = all tenants
    return LogService(db, tenant_id)


@router.get("/", response_class=HTMLResponse)
async def logs_dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
):
    """Display log management dashboard."""
    try:
        return templates.TemplateResponse(
            "administration/logs/logs_dashboard.html",
            {
                "request": request,
                "user": current_user,
                "page_title": "Application Logs",
                "page_description": "View and filter application logs by tenant"
            }
        )
    except Exception as e:
        logger.exception("Failed to render logs dashboard")
        raise HTTPException(status_code=500, detail="Failed to load logs dashboard")


@router.get("/api/list", response_class=JSONResponse)
async def get_logs_list(
    request: Request,
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger_name: Optional[str] = Query(None, description="Filter by logger name"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    log_service: LogService = Depends(get_log_service)
):
    """Get paginated list of logs with filtering."""
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        result = await log_service.get_logs_list(
            level=level,
            logger_name=logger_name,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )

        # Return in audit-compatible format
        return JSONResponse(content={
            "items": result["data"],
            "total": result["total"],
            "page": (offset // limit) + 1,
            "size": limit
        })

    except Exception as e:
        logger.exception("Failed to get logs list via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")
@router.get("/api/summary", response_class=JSONResponse)
async def get_logs_summary(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    log_service: LogService = Depends(get_log_service)
):
    """Get log summary statistics."""
    try:
        return await log_service.get_logs_summary(
            hours=hours
        )

    except Exception as e:
        logger.exception("Failed to get logs summary")
        raise HTTPException(status_code=500, detail="Failed to retrieve log summary")


@router.get("/api/tenants", response_class=JSONResponse)
async def get_tenant_list(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    log_service: LogService = Depends(get_log_service)
):
    """Get list of all tenants that have logs."""
    try:
        tenants = await log_service.get_tenant_list()
        return {"tenants": tenants}

    except Exception as e:
        logger.exception("Failed to get tenant list")
        raise HTTPException(status_code=500, detail="Failed to retrieve tenant list")


@router.get("/api/{log_id}", response_class=JSONResponse)
async def get_log_details(
    log_id: int,
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    log_service: LogService = Depends(get_log_service)
):
    """Get detailed information for a specific log entry."""
    try:
        log_entry = await log_service.get_log_by_id(log_id)

        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")

        return log_entry.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get log details for {log_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log details")


@router.delete("/api/cleanup", response_class=JSONResponse)
async def cleanup_old_logs(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Delete logs older than this many days"),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    log_service: LogService = Depends(get_log_service)
):
    """Clean up old log entries to manage database size."""
    try:
        return await log_service.cleanup_old_logs(days=days)

    except Exception as e:
        logger.exception("Failed to cleanup old logs")
        raise HTTPException(status_code=500, detail="Failed to cleanup logs")
