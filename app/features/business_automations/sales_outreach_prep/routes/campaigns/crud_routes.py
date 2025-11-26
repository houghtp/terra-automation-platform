"""
Campaign CRUD API routes for Sales Outreach Prep.

Handles:
- GET /api/list - List campaigns (for Tabulator)
- GET /{campaign_id} - Get campaign details
- DELETE /{campaign_id} - Delete campaign
- GET /stats - Get campaign statistics
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_campaign_service
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/list")
async def list_campaigns_api(
    request: Request,
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    List campaigns for Tabulator table.

    Args:
        request: FastAPI request
        search: Search term
        status: Filter by status
        page: Page number
        size: Page size
        service: Campaign service
        current_user: Current user

    Returns:
        JSON response with campaigns and pagination
    """
    try:
        offset = (page - 1) * size
        campaigns, total = await service.list_campaigns(
            search=search,
            status=status,
            limit=size,
            offset=offset
        )

        return {
            "data": [campaign.to_dict() for campaign in campaigns],
            "last_page": (total + size - 1) // size if total > 0 else 1,
            "total": total
        }

    except Exception as e:
        handle_route_error("list_campaigns_api", e)
        raise HTTPException(status_code=500, detail="Failed to list campaigns")


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get campaign by ID.

    Args:
        campaign_id: Campaign ID
        service: Campaign service
        current_user: Current user

    Returns:
        Campaign JSON
    """
    try:
        campaign = await service.get_campaign_by_id(campaign_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return campaign.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_campaign", e)
        raise HTTPException(status_code=500, detail="Failed to get campaign")


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Delete campaign.

    Args:
        campaign_id: Campaign ID
        db: Database session
        service: Campaign service
        current_user: Current user

    Returns:
        Success response
    """
    try:
        deleted = await service.delete_campaign(campaign_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Campaign not found")

        await commit_transaction(db, "delete_campaign")

        logger.info(
            "Campaign deleted via API",
            campaign_id=campaign_id,
            user_id=current_user.id
        )

        return {"success": True, "message": "Campaign deleted"}

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("delete_campaign", e)
        raise HTTPException(status_code=500, detail="Failed to delete campaign")


@router.get("/stats")
async def get_campaign_stats(
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get campaign statistics.

    Args:
        service: Campaign service
        current_user: Current user

    Returns:
        Statistics JSON
    """
    try:
        stats = await service.get_campaign_stats()
        return stats

    except Exception as e:
        handle_route_error("get_campaign_stats", e)
        raise HTTPException(status_code=500, detail="Failed to get statistics")
