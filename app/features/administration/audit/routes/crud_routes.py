# Gold Standard Route Imports - Audit CRUD
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Query,
    JSONResponse, AsyncSession, get_db,
    tenant_dependency, get_current_user, User,
    Optional, get_logger
)
from app.features.core.rate_limiter import rate_limit_api
from datetime import datetime
from ..services import AuditManagementService

router = APIRouter(tags=["audit-crud"])
logger = get_logger(__name__)

async def get_audit_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> AuditManagementService:
    """Get audit service dependency."""
    return AuditManagementService(db, tenant_id)

# --- TABULATOR CRUD ROUTES ---

@router.get("/api/list", response_class=JSONResponse)
async def get_audit_logs_list_api(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: Optional[str] = Query("timestamp"),
    order: Optional[str] = Query("desc"),
    audit_service: AuditManagementService = Depends(get_audit_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """Get audit logs list for Tabulator API using standardized patterns."""
    try:
        # Parse date filters
        date_from_dt = None
        date_to_dt = None

        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format")

        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format")

        # Get audit logs (let Tabulator handle pagination)
        logs = await audit_service.get_audit_logs(
            category_filter=category,
            severity_filter=severity,
            user_filter=user,
            action_filter=action,
            date_from=date_from_dt,
            date_to=date_to_dt,
            sort_by=sort or "timestamp",
            sort_order=order or "desc"
        )

        # Standardized response formatting
        result = []
        for log in logs:
            if hasattr(log, 'to_dict'):
                result.append(log.to_dict())
            else:
                result.append(log)  # Already a dict

        # Return simple array like users route for Tabulator compatibility
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get audit logs list via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")

@router.get("/{log_id}", name="audit_log_detail")
async def get_audit_log_detail(
    log_id: int,
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    audit_service: AuditManagementService = Depends(get_audit_service)
):
    """Get detailed information about a specific audit log."""
    try:
        log = await audit_service.get_audit_log_by_id(tenant_id, log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")

        return JSONResponse(content=log.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get audit log {log_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit log")
