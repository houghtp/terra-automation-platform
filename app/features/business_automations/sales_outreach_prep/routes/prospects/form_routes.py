"""
Prospect form routes for Sales Outreach Prep.

Handles:
- GET /partials/form - Render prospect form (create/edit)
- POST / - Create new prospect
- PUT /{prospect_id} - Update existing prospect
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_prospect_service, get_campaign_service
from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.schemas import ProspectCreate, ProspectUpdate

logger = get_logger(__name__)
router = APIRouter()


@router.get("/partials/form")
async def get_prospect_form(
    request: Request,
    campaign_id: Optional[str] = None,
    prospect_id: Optional[str] = None,
    service: ProspectCrudService = Depends(get_prospect_service),
    campaign_service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Render prospect create/edit form partial.

    Args:
        request: FastAPI request
        campaign_id: Campaign ID (for create)
        prospect_id: Prospect ID (for edit)
        service: Prospect service
        campaign_service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with form HTML
    """
    try:
        prospect = None
        if prospect_id:
            prospect = await service.get_prospect_by_id(prospect_id)
            if not prospect:
                raise HTTPException(status_code=404, detail="Prospect not found")
            campaign_id = prospect.campaign_id

        # Get campaign for dropdown/context
        campaign = None
        if campaign_id:
            campaign = await campaign_service.get_campaign_by_id(campaign_id)

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/prospects/partials/form.html",
            {
                "request": request,
                "prospect": prospect,
                "campaign": campaign,
                "campaign_id": campaign_id,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_prospect_form", e)
        raise HTTPException(status_code=500, detail="Failed to load form")


@router.post("/")
async def create_prospect(
    request: Request,
    data: ProspectCreate,
    db: AsyncSession = Depends(get_db),
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new prospect.

    Args:
        request: FastAPI request
        data: Prospect creation data
        db: Database session
        service: Prospect service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        prospect = await service.create_prospect(data.dict(), current_user)
        await commit_transaction(db, "create_prospect")

        logger.info(
            "Prospect created via form",
            prospect_id=prospect.id,
            name=prospect.full_name,
            user_id=current_user.id
        )

        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("create_prospect", e)
        raise HTTPException(status_code=500, detail="Failed to create prospect")


@router.put("/{prospect_id}")
async def update_prospect(
    request: Request,
    prospect_id: str,
    data: ProspectUpdate,
    db: AsyncSession = Depends(get_db),
    service: ProspectCrudService = Depends(get_prospect_service),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing prospect.

    Args:
        request: FastAPI request
        prospect_id: Prospect ID
        data: Prospect update data
        db: Database session
        service: Prospect service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        prospect = await service.update_prospect(
            prospect_id,
            data.dict(exclude_unset=True),
            current_user
        )

        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        await commit_transaction(db, "update_prospect")

        logger.info(
            "Prospect updated via form",
            prospect_id=prospect.id,
            user_id=current_user.id
        )

        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("update_prospect", e)
        raise HTTPException(status_code=500, detail="Failed to update prospect")
