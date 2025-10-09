# Gold Standard Route Imports - Logs Dashboard
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException,
    JSONResponse, AsyncSession, get_db,
    tenant_dependency, get_current_user, User,
    get_logger
)
from app.features.core.rate_limiter import rate_limit_api
from ..services import LogManagementService

router = APIRouter(tags=["logs-dashboard"])
logger = get_logger(__name__)


async def get_log_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> LogManagementService:
    """Get log service dependency."""
    return LogManagementService(db, tenant_id)

# --- DASHBOARD ROUTES ---

@router.get("/api/stats", response_class=JSONResponse, name="logs_stats_api")
async def get_logs_stats(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    log_service: LogManagementService = Depends(get_log_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """Get log statistics for dashboard."""
    try:
        return await log_service.get_logs_stats()
    except Exception as e:
        logger.exception("Failed to get logs stats")
        raise HTTPException(status_code=500, detail="Failed to retrieve log statistics")
