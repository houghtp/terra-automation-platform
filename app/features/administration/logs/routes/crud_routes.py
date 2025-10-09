# Gold Standard Route Imports - Logs CRUD
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Query,
    JSONResponse, AsyncSession, get_db,
    tenant_dependency, get_current_user, User,
    Optional, get_logger
)
from app.features.core.rate_limiter import rate_limit_api
from datetime import datetime
from ..services import LogManagementService

router = APIRouter(tags=["logs-crud"])
logger = get_logger(__name__)


async def get_log_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> LogManagementService:
    """Get log service dependency."""
    return LogManagementService(db, tenant_id)

# --- TABULATOR CRUD ROUTES ---

@router.get("/api/list", response_class=JSONResponse)
async def get_logs_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger_name: Optional[str] = Query(None, description="Filter by logger name"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    sort: Optional[str] = Query("timestamp"),
    order: Optional[str] = Query("desc"),
    log_service: LogManagementService = Depends(get_log_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """Get logs list for Tabulator API using standardized patterns."""
    try:
        # Get logs (let Tabulator handle pagination like audit does)
        logs = await log_service.get_application_logs(
            level_filter=level,
            logger_filter=logger_name,
            user_filter=user_id,
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

    except Exception as e:
        logger.exception("Failed to get logs list")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/{log_id}", name="log_detail")
async def get_log_detail(
    log_id: int,
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    log_service: LogManagementService = Depends(get_log_service)
):
    """Get detailed information about a specific application log."""
    try:
        log_entry = await log_service.get_log_by_id(log_id)

        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")

        return JSONResponse(content=log_entry.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get log {log_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log")
