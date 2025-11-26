"""
Prospect CRUD API routes for Sales Outreach Prep.

Handles:
- GET /api/list - List prospects (for Tabulator)
- GET /{prospect_id} - Get prospect details
- DELETE /{prospect_id} - Delete prospect
- POST /bulk/update-status - Bulk update prospect status
"""

from typing import List
from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_prospect_service
from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/list")
async def list_prospects_api(
    request: Request,
    campaign_id: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    enrichment_status: Optional[str] = None,
    seniority_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    List prospects for Tabulator table.

    Args:
        request: FastAPI request
        campaign_id: Filter by campaign
        search: Search term
        status: Filter by status
        enrichment_status: Filter by enrichment status
        seniority_level: Filter by seniority level
        page: Page number
        size: Page size
        service: Prospect service
        current_user: Current user

    Returns:
        JSON response with prospects and pagination
    """
    try:
        offset = (page - 1) * size
        prospects, total = await service.list_prospects(
            campaign_id=campaign_id,
            search=search,
            status=status,
            enrichment_status=enrichment_status,
            seniority_level=seniority_level,
            limit=size,
            offset=offset
        )

        return {
            "data": [prospect.to_dict() for prospect in prospects],
            "last_page": (total + size - 1) // size if total > 0 else 1,
            "total": total
        }

    except Exception as e:
        handle_route_error("list_prospects_api", e)
        raise HTTPException(status_code=500, detail="Failed to list prospects")


@router.get("/{prospect_id}")
async def get_prospect(
    prospect_id: str,
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get prospect by ID.

    Args:
        prospect_id: Prospect ID
        service: Prospect service
        current_user: Current user

    Returns:
        Prospect JSON
    """
    try:
        prospect = await service.get_prospect_by_id(prospect_id)

        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        return prospect.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_prospect", e)
        raise HTTPException(status_code=500, detail="Failed to get prospect")


@router.delete("/{prospect_id}")
async def delete_prospect(
    prospect_id: str,
    db: AsyncSession = Depends(get_db),
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    Delete prospect.

    Args:
        prospect_id: Prospect ID
        db: Database session
        service: Prospect service
        current_user: Current user

    Returns:
        Success response
    """
    try:
        deleted = await service.delete_prospect(prospect_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Prospect not found")

        await commit_transaction(db, "delete_prospect")

        logger.info(
            "Prospect deleted via API",
            prospect_id=prospect_id,
            user_id=current_user.id
        )

        return {"success": True, "message": "Prospect deleted"}

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("delete_prospect", e)
        raise HTTPException(status_code=500, detail="Failed to delete prospect")


@router.post("/bulk/update-status")
async def bulk_update_prospect_status(
    request: Request,
    prospect_ids: List[str],
    new_status: str,
    db: AsyncSession = Depends(get_db),
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk update prospect status.

    Args:
        request: FastAPI request
        prospect_ids: List of prospect IDs
        new_status: New status
        db: Database session
        service: Prospect service
        current_user: Current user

    Returns:
        Success response with count
    """
    try:
        count = await service.bulk_update_status(
            prospect_ids,
            new_status,
            current_user
        )

        await commit_transaction(db, "bulk_update_prospect_status")

        logger.info(
            "Bulk prospect status update",
            count=count,
            new_status=new_status,
            user_id=current_user.id
        )

        return {"success": True, "count": count, "message": f"{count} prospects updated"}

    except Exception as e:
        handle_route_error("bulk_update_prospect_status", e)
        raise HTTPException(status_code=500, detail="Failed to update prospects")


@router.post("/enrich")
async def trigger_enrichment(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger email enrichment for campaign prospects.

    Args:
        request: FastAPI request
        db: Database session
        tenant_id: Current tenant ID
        current_user: Current user

    Returns:
        Task ID and success message

    Raises:
        HTTPException: If campaign not found or enrichment fails
    """
    try:
        # Parse request body
        body = await request.json()
        campaign_id = body.get("campaign_id")

        if not campaign_id:
            raise HTTPException(status_code=400, detail="campaign_id is required")

        # Verify campaign exists and user has access
        from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
        campaign_service = CampaignCrudService(db, tenant_id)
        campaign = await campaign_service.get_campaign_by_id(campaign_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Trigger enrichment task
        from app.features.business_automations.sales_outreach_prep.tasks import enrich_prospects_task
        task = enrich_prospects_task.delay(campaign_id, max_prospects=100)

        logger.info(
            "Manual enrichment triggered",
            campaign_id=campaign_id,
            task_id=task.id,
            user_id=current_user.id
        )

        return {
            "success": True,
            "message": "Enrichment task started",
            "task_id": task.id,
            "campaign_id": campaign_id
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("trigger_enrichment", e)
        raise HTTPException(status_code=500, detail="Failed to trigger enrichment")
