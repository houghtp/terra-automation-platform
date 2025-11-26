"""
Campaign form routes for Sales Outreach Prep.

Handles:
- GET /partials/form - Render campaign form (create/edit)
- POST / - Create new campaign
- PUT /{campaign_id} - Update existing campaign
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_campaign_service
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.schemas import CampaignCreate, CampaignUpdate
from app.features.business_automations.sales_outreach_prep.tasks import discover_prospects_task

logger = get_logger(__name__)
router = APIRouter()


@router.get("/partials/form")
async def get_campaign_form(
    request: Request,
    campaign_id: Optional[str] = None,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Render campaign create/edit form partial.

    Args:
        request: FastAPI request
        campaign_id: Campaign ID for edit, None for create
        service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with form HTML
    """
    try:
        campaign = None
        if campaign_id:
            campaign = await service.get_campaign_by_id(campaign_id)
            if not campaign:
                logger.warning("Campaign not found for form", campaign_id=campaign_id)
                raise HTTPException(status_code=404, detail="Campaign not found")

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/campaigns/partials/form.html",
            {
                "request": request,
                "campaign": campaign,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_campaign_form", e)
        raise HTTPException(status_code=500, detail="Failed to load form")


@router.get("/{campaign_id}/edit")
async def get_campaign_edit_form(
    request: Request,
    campaign_id: str,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Render campaign edit form (standard pattern from users slice).

    Args:
        request: FastAPI request
        campaign_id: Campaign ID to edit
        service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with form HTML
    """
    try:
        campaign = await service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/campaigns/partials/form.html",
            {
                "request": request,
                "campaign": campaign,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_campaign_edit_form", e)
        raise HTTPException(status_code=500, detail="Failed to load edit form")


@router.get("/partials/research_results")
async def get_research_results(
    request: Request,
    campaign_id: str,
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Render AI research results partial.

    Args:
        request: FastAPI request
        campaign_id: Campaign ID to show research results for
        service: Campaign service
        current_user: Current user

    Returns:
        TemplateResponse with research results HTML
    """
    try:
        campaign = await service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/campaigns/partials/research_results.html",
            {
                "request": request,
                "campaign": campaign,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_research_results", e)
        raise HTTPException(status_code=500, detail="Failed to load research results")


@router.post("/")
async def create_campaign(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    discovery_type: str = Form("company_discovery"),
    research_prompt: Optional[str] = Form(None),
    target_industry: Optional[str] = Form(None),
    target_geography: Optional[str] = Form(None),
    target_roles: Optional[str] = Form(None),
    target_seniority: Optional[str] = Form(None),
    status: str = Form("draft"),
    auto_enrich_on_discovery: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new campaign.

    Args:
        request: FastAPI request
        name: Campaign name
        description: Campaign description
        discovery_type: Discovery method
        research_prompt: AI research prompt
        target_industry: Target industry
        target_geography: Target geography
        target_roles: Target roles
        target_seniority: Target seniority
        status: Campaign status
        auto_enrich_on_discovery: Auto-enrich flag
        db: Database session
        service: Campaign service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        # Build campaign data dict
        campaign_data = {
            "name": name,
            "description": description or None,
            "discovery_type": discovery_type,
            "research_prompt": research_prompt or None,
            "target_industry": target_industry or None,
            "target_geography": target_geography or None,
            "target_roles": target_roles or None,
            "target_seniority": target_seniority or None,
            "status": status,
            "auto_enrich_on_discovery": auto_enrich_on_discovery
        }

        campaign = await service.create_campaign(campaign_data, current_user)
        await commit_transaction(db, "create_campaign")

        logger.info(
            "✅ Campaign created via form",
            campaign_id=campaign.id,
            name=campaign.name,
            discovery_type=campaign.discovery_type,
            has_research_prompt=bool(campaign.research_prompt),
            user_id=current_user.id
        )

        # Auto-trigger AI research for ai_research campaigns
        task_id = None
        if campaign.discovery_type == "ai_research" and campaign.research_prompt:
            logger.info(
                "🚀 TRIGGERING AI research task...",
                campaign_id=campaign.id,
                research_prompt_preview=campaign.research_prompt[:100]
            )

            task = discover_prospects_task.delay(
                campaign_id=campaign.id,
                company_ids=None,  # None means AI research discovery
                max_results_per_company=20
            )
            task_id = task.id

            logger.info(
                "AI research task started",
                campaign_id=campaign.id,
                task_id=task_id,
                user_id=current_user.id
            )
        else:
            logger.info(
                "Skipping AI research (not ai_research type or no prompt)",
                campaign_id=campaign.id,
                discovery_type=campaign.discovery_type,
                has_prompt=bool(campaign.research_prompt)
            )

        # Return success with HX-Trigger to close modal and refresh table
        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("create_campaign", e)
        raise HTTPException(status_code=500, detail="Failed to create campaign")


@router.put("/{campaign_id}")
async def update_campaign(
    request: Request,
    campaign_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    discovery_type: Optional[str] = Form(None),
    research_prompt: Optional[str] = Form(None),
    target_industry: Optional[str] = Form(None),
    target_geography: Optional[str] = Form(None),
    target_roles: Optional[str] = Form(None),
    target_seniority: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    auto_enrich_on_discovery: Optional[bool] = Form(None),
    db: AsyncSession = Depends(get_db),
    service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing campaign.

    Args:
        request: FastAPI request
        campaign_id: Campaign ID
        name: Campaign name
        description: Campaign description
        discovery_type: Discovery method
        research_prompt: AI research prompt
        target_industry: Target industry
        target_geography: Target geography
        target_roles: Target roles
        target_seniority: Target seniority
        status: Campaign status
        auto_enrich_on_discovery: Auto-enrich flag
        db: Database session
        service: Campaign service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        # Build update dict (only include provided values)
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description or None
        if discovery_type is not None:
            update_data["discovery_type"] = discovery_type
        if research_prompt is not None:
            update_data["research_prompt"] = research_prompt or None
        if target_industry is not None:
            update_data["target_industry"] = target_industry or None
        if target_geography is not None:
            update_data["target_geography"] = target_geography or None
        if target_roles is not None:
            update_data["target_roles"] = target_roles or None
        if target_seniority is not None:
            update_data["target_seniority"] = target_seniority or None
        if status is not None:
            update_data["status"] = status
        if auto_enrich_on_discovery is not None:
            update_data["auto_enrich_on_discovery"] = auto_enrich_on_discovery

        campaign = await service.update_campaign(
            campaign_id,
            update_data,
            current_user
        )

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        await commit_transaction(db, "update_campaign")

        logger.info(
            "Campaign updated via form",
            campaign_id=campaign.id,
            user_id=current_user.id
        )

        # Return success with HX-Trigger to close modal and refresh table
        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("update_campaign", e)
        raise HTTPException(status_code=500, detail="Failed to update campaign")
