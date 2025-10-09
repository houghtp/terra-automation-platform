# Gold Standard Route Imports - Audit Dashboard
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Query,
    JSONResponse, AsyncSession, get_db,
    tenant_dependency, get_current_user, User,
    Optional, get_logger
)
from app.features.core.rate_limiter import rate_limit_api
from datetime import datetime
from ..services import AuditManagementService

router = APIRouter(tags=["audit-dashboard"])
logger = get_logger(__name__)


async def get_audit_service(db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency)) -> AuditManagementService:
    """Get audit service dependency."""
    return AuditManagementService(db, tenant_id)

# --- DASHBOARD ROUTES ---

@router.get("/api/stats", name="audit_stats_api")
async def get_audit_stats_api(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    audit_service: AuditManagementService = Depends(get_audit_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """API endpoint for audit statistics."""
    try:
        stats = await audit_service.get_audit_stats()
        return JSONResponse(content=stats)

    except Exception as e:
        logger.exception("Failed to get audit stats via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit statistics")

@router.get("/api/timeline", name="audit_timeline_api")
async def get_audit_timeline_api(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, ge=1, le=90),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    audit_service: AuditManagementService = Depends(get_audit_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """API endpoint for audit activity timeline with filtering support."""
    try:
        logger.info(f"Timeline API called - tenant_id: {tenant_id}, user: {current_user}, days: {days}")
        logger.info(f"Filters - category: {category}, severity: {severity}, user: {user}, action: {action}")

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

        # Get timeline data with filters
        timeline_data = await audit_service.get_audit_timeline(
            days=days,
            category_filter=category,
            severity_filter=severity,
            user_filter=user,
            action_filter=action,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        logger.info(f"Service returned data: {timeline_data}")

        # Transform data for chart widget compatibility
        # Chart widget expects: {categories: [], values: []} for simple line chart
        # or {series: [{name: "", data: []}]} for multi-series

        if not timeline_data:
            logger.info("No timeline data found, returning empty response")
            return JSONResponse(content={
                "categories": [],
                "series": []
            })

        try:
            # Get unique dates and categories
            dates = sorted(list(set(item['date'] for item in timeline_data)))
            categories = sorted(list(set(item['category'] for item in timeline_data)))
            logger.info(f"Processing dates: {dates}, categories: {categories}")

            # Create series data for each category
            series = []
            for category in categories:
                category_data = []
                for date in dates:
                    # Find count for this date/category combination
                    count = 0
                    for item in timeline_data:
                        if item['date'] == date and item['category'] == category:
                            count = item['count']
                            break
                    category_data.append(count)

                series.append({
                    "name": category,
                    "data": category_data
                })

            result = {
                "categories": dates,
                "series": series
            }
            logger.info(f"Returning timeline result: {result}")
            return JSONResponse(content=result)

        except Exception as data_processing_error:
            logger.exception(f"Error processing timeline data: {data_processing_error}")
            raise HTTPException(status_code=500, detail="Failed to process timeline data")

    except Exception as e:
        logger.exception("Failed to get audit timeline via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit timeline")
