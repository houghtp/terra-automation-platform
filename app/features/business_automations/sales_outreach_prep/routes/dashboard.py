"""
Dashboard route for Sales Outreach Prep.

Main landing page showing campaigns overview and stats.
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_campaign_service
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
@router.get("/dashboard")
async def sales_outreach_dashboard(
    request: Request,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Sales Outreach Prep dashboard showing campaigns overview.

    Args:
        request: FastAPI request
        service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with dashboard
    """
    try:
        # Get campaign statistics
        stats = await service.get_campaign_stats()

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "stats": stats
            }
        )

    except Exception as e:
        handle_route_error("sales_outreach_dashboard", e)
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@router.get("/campaigns")
async def campaigns_list_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Campaigns list page.

    Args:
        request: FastAPI request
        current_user: Current user

    Returns:
        TemplateResponse with campaigns list
    """
    try:
        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/campaigns/list.html",
            {
                "request": request,
                "current_user": current_user
            }
        )

    except Exception as e:
        handle_route_error("campaigns_list_page", e)
        raise HTTPException(status_code=500, detail="Failed to load page")


@router.get("/prospects")
async def prospects_list_page(
    request: Request,
    campaign_id: Optional[str] = None,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Prospects list page.

    Args:
        request: FastAPI request
        campaign_id: Optional campaign filter
        service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with prospects list
    """
    try:
        campaign = None
        if campaign_id:
            campaign = await service.get_campaign_by_id(campaign_id)

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/prospects/list.html",
            {
                "request": request,
                "current_user": current_user,
                "campaign": campaign,
                "campaign_id": campaign_id
            }
        )

    except Exception as e:
        handle_route_error("prospects_list_page", e)
        raise HTTPException(status_code=500, detail="Failed to load page")


@router.get("/companies")
async def companies_list_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Companies list page.

    Args:
        request: FastAPI request
        current_user: Current user

    Returns:
        TemplateResponse with companies list
    """
    try:
        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/companies/list.html",
            {
                "request": request,
                "current_user": current_user
            }
        )

    except Exception as e:
        handle_route_error("companies_list_page", e)
        raise HTTPException(status_code=500, detail="Failed to load page")
