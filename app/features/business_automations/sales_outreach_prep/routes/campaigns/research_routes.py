"""
Research-related routes for AI-powered campaign discovery.

Handles:
- POST /{campaign_id}/start-research - Start AI research discovery for campaign
- POST /{campaign_id}/approve-organization - Approve single organization from research
- POST /{campaign_id}/approve-all-organizations - Approve all organizations and start discovery
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import (
    get_campaign_service,
    get_company_service
)
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService
from app.features.business_automations.sales_outreach_prep.tasks import discover_prospects_task

logger = get_logger(__name__)
router = APIRouter()


@router.post("/{campaign_id}/start-research")
async def start_research(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    campaign_service: CampaignCrudService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    """
    Start AI research discovery for a campaign.

    Triggers the Celery task to run AI research and store results.

    Args:
        campaign_id: Campaign ID
        db: Database session
        campaign_service: Campaign service
        current_user: Current user

    Returns:
        Success response with task ID
    """
    try:
        # Get campaign
        campaign = await campaign_service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Validate it's an AI research campaign
        if campaign.discovery_type != "ai_research":
            raise HTTPException(
                status_code=400,
                detail="This endpoint is only for AI research campaigns"
            )

        # Validate research prompt exists
        if not campaign.research_prompt:
            raise HTTPException(
                status_code=400,
                detail="Campaign must have a research prompt"
            )

        # Trigger discovery task (will run AI research)
        task = discover_prospects_task.delay(
            campaign_id=campaign_id,
            company_ids=None,  # None means AI research discovery
            max_results_per_company=20
        )

        logger.info(
            "AI research task triggered",
            campaign_id=campaign_id,
            task_id=task.id,
            user_id=current_user.id
        )

        # Return HTMX response
        return Response(
            status_code=200,
            headers={"HX-Trigger": "refreshTable"}
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("start_research", e)
        raise HTTPException(status_code=500, detail="Failed to start research")


@router.post("/{campaign_id}/approve-organization")
async def approve_organization(
    campaign_id: str,
    org_index: int = Form(..., description="Index of organization in research_data.organizations array"),
    db: AsyncSession = Depends(get_db),
    campaign_service: CampaignCrudService = Depends(get_campaign_service),
    company_service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Approve single organization from AI research results.

    Creates Company record and optionally triggers contact discovery.

    Args:
        campaign_id: Campaign ID
        org_index: Index of organization in research_data.organizations array
        db: Database session
        campaign_service: Campaign service
        company_service: Company service
        current_user: Current user

    Returns:
        Success response with company ID
    """
    try:
        # Get campaign
        campaign = await campaign_service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Validate research data exists
        if not campaign.research_data or not campaign.research_data.get("organizations"):
            raise HTTPException(status_code=400, detail="No research data available")

        # Get organization by index
        organizations = campaign.research_data.get("organizations", [])
        if org_index < 0 or org_index >= len(organizations):
            raise HTTPException(status_code=400, detail="Invalid organization index")

        org = organizations[org_index]

        # Extract domain from website URL
        domain = None
        if org.get("website"):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(org["website"])
                domain = parsed.netloc.replace("www.", "")
            except Exception as e:
                logger.warning("Failed to parse domain from URL", url=org.get("website"), error=str(e))

        # Create Company record
        company_data = {
            "name": org.get("name", "Unknown Organization"),
            "website_url": org.get("website"),
            "domain": domain,
            "description": org.get("context", "")
        }

        company = await company_service.create_company(company_data, current_user)

        # Link company to campaign
        from app.features.business_automations.sales_outreach_prep.models import CampaignCompany
        campaign_company = CampaignCompany(
            campaign_id=campaign_id,
            company_id=company.id,
            research_status="approved",
            ai_insights=[f"Discovered via AI research: {org.get('source', 'unknown')}"]
        )
        db.add(campaign_company)

        await commit_transaction(db, "approve_organization")

        logger.info(
            "Organization approved from AI research",
            campaign_id=campaign_id,
            company_id=company.id,
            org_name=org.get("name"),
            user_id=current_user.id
        )

        # Return updated button HTML for HTMX swap
        button_html = f"""
            <button class="btn btn-sm btn-outline-secondary" disabled>
                <i class="ti ti-check icon"></i>
                Approved
            </button>
        """

        return Response(
            content=button_html,
            media_type="text/html",
            headers={"HX-Trigger": "showToast"}
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("approve_organization", e)
        raise HTTPException(status_code=500, detail="Failed to approve organization")


@router.post("/{campaign_id}/approve-all-organizations")
async def approve_all_organizations(
    campaign_id: str,
    start_discovery: bool = Form(True, description="Whether to start contact discovery immediately"),
    db: AsyncSession = Depends(get_db),
    campaign_service: CampaignCrudService = Depends(get_campaign_service),
    company_service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Approve all organizations from AI research results.

    Creates Company records for all organizations and optionally starts contact discovery.

    Args:
        campaign_id: Campaign ID
        start_discovery: Whether to start contact discovery immediately
        db: Database session
        campaign_service: Campaign service
        company_service: Company service
        current_user: Current user

    Returns:
        Success response with count of approved organizations
    """
    try:
        # Get campaign
        campaign = await campaign_service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Validate research data exists
        if not campaign.research_data or not campaign.research_data.get("organizations"):
            raise HTTPException(status_code=400, detail="No research data available")

        organizations = campaign.research_data.get("organizations", [])
        approved_companies = []

        # Create Company records for all organizations
        for org in organizations:
            try:
                # Extract domain from website URL
                domain = None
                if org.get("website"):
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(org["website"])
                        domain = parsed.netloc.replace("www.", "")
                    except Exception as e:
                        logger.warning("Failed to parse domain", url=org.get("website"), error=str(e))

                # Create Company
                company_data = {
                    "name": org.get("name", "Unknown Organization"),
                    "website_url": org.get("website"),
                    "domain": domain,
                    "description": org.get("context", "")
                }

                company = await company_service.create_company(company_data, current_user)

                # Link to campaign
                from app.features.business_automations.sales_outreach_prep.models import CampaignCompany
                campaign_company = CampaignCompany(
                    campaign_id=campaign_id,
                    company_id=company.id,
                    research_status="approved",
                    ai_insights=[
                        f"Discovered via AI research: {org.get('source', 'unknown')}",
                        f"Confidence: {org.get('confidence', 'unknown')}"
                    ]
                )
                db.add(campaign_company)

                approved_companies.append(company.id)

                logger.info(
                    "Organization approved (batch)",
                    campaign_id=campaign_id,
                    company_id=company.id,
                    org_name=org.get("name")
                )

            except Exception as e:
                logger.warning(
                    "Failed to approve organization",
                    org_name=org.get("name"),
                    error=str(e)
                )
                continue

        await commit_transaction(db, "approve_all_organizations")

        # Optionally trigger contact discovery
        task_id = None
        if start_discovery and approved_companies:
            task = discover_prospects_task.delay(
                campaign_id=campaign_id,
                company_ids=approved_companies,
                max_results_per_company=20
            )
            task_id = task.id

            logger.info(
                "Contact discovery triggered after batch approval",
                campaign_id=campaign_id,
                company_count=len(approved_companies),
                task_id=task_id
            )

        # Return HTMX response to close modal and refresh table
        return Response(
            status_code=200,
            headers={
                "HX-Trigger": "closeModal, refreshTable"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("approve_all_organizations", e)
        raise HTTPException(status_code=500, detail="Failed to approve organizations")


@router.post("/{campaign_id}/import-all-prospects")
async def import_all_prospects(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    campaign_service: CampaignCrudService = Depends(get_campaign_service),
    company_service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Import all prospects from AI research results.

    Creates Company and Prospect records from research_data.prospects.

    Args:
        campaign_id: Campaign ID
        db: Database session
        campaign_service: Campaign service
        company_service: Company service
        current_user: Current user

    Returns:
        Success response with counts
    """
    try:
        from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService
        from urllib.parse import urlparse

        # Get campaign
        campaign = await campaign_service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Validate research data exists
        if not campaign.research_data or not campaign.research_data.get("prospects"):
            raise HTTPException(status_code=400, detail="No prospect data available")

        prospects_data = campaign.research_data.get("prospects", [])
        prospect_service = ProspectCrudService(db, campaign.tenant_id)

        companies_created = 0
        prospects_created = 0
        prospects_skipped = 0
        companies_cache = {}  # Cache companies by name to avoid duplicates

        logger.info(
            "Starting prospect import",
            campaign_id=campaign_id,
            total_prospects=len(prospects_data)
        )

        for prospect_data in prospects_data:
            try:
                company_name = prospect_data.get("company_name", "Unknown Company")

                logger.debug(
                    "Processing prospect",
                    name=prospect_data.get("full_name"),
                    company=company_name
                )

                # Get or create company
                if company_name in companies_cache:
                    company = companies_cache[company_name]
                else:
                    # Check if company already exists by name
                    from sqlalchemy import select
                    from app.features.business_automations.sales_outreach_prep.models import Company

                    stmt = select(Company).where(
                        Company.name == company_name,
                        Company.tenant_id == campaign.tenant_id
                    )
                    result = await db.execute(stmt)
                    company = result.scalar_one_or_none()

                    if not company:
                        # Extract domain from website
                        domain = None
                        website_url = prospect_data.get("company_website")
                        if website_url:
                            try:
                                parsed = urlparse(website_url)
                                domain = parsed.netloc.replace("www.", "")
                            except Exception:
                                pass

                        # Create new company
                        company_create_data = {
                            "name": company_name,
                            "website_url": website_url,
                            "domain": domain
                        }

                        company = await company_service.create_company(
                            company_create_data,
                            current_user
                        )
                        companies_created += 1

                        logger.info(
                            "Company created from AI research",
                            company_id=company.id,
                            company_name=company_name
                        )

                    # Cache it
                    companies_cache[company_name] = company

                # Check if prospect already exists (by LinkedIn URL or name + campaign)
                from app.features.business_automations.sales_outreach_prep.models import Prospect

                linkedin_url = prospect_data.get("linkedin_url")
                full_name = prospect_data.get("full_name", "Unknown")

                # Try to find existing prospect
                existing_prospect = None
                if linkedin_url:
                    # Check by LinkedIn URL (most reliable)
                    stmt = select(Prospect).where(
                        Prospect.linkedin_url == linkedin_url,
                        Prospect.campaign_id == campaign_id
                    )
                    result = await db.execute(stmt)
                    existing_prospect = result.scalar_one_or_none()

                if not existing_prospect:
                    # Check by full name + campaign (fallback)
                    stmt = select(Prospect).where(
                        Prospect.full_name == full_name,
                        Prospect.campaign_id == campaign_id
                    )
                    result = await db.execute(stmt)
                    existing_prospect = result.scalar_one_or_none()

                if existing_prospect:
                    logger.debug(
                        "Prospect already exists, skipping",
                        prospect_id=existing_prospect.id,
                        name=full_name
                    )
                    prospects_skipped += 1
                    continue  # Skip this prospect

                # Create new prospect
                prospect_create_data = {
                    "campaign_id": campaign_id,
                    "company_id": company.id,
                    "full_name": full_name,
                    "job_title": prospect_data.get("job_title"),
                    "linkedin_url": linkedin_url,
                    "discovered_via": "ai_research",
                    "discovery_query": f"AI Research: {campaign.research_prompt[:100]}"
                }

                prospect = await prospect_service.create_prospect(
                    prospect_create_data,
                    user=current_user
                )

                prospects_created += 1

                logger.debug(
                    "Prospect imported",
                    prospect_id=prospect.id,
                    name=prospect.full_name,
                    company=company_name
                )

            except Exception as e:
                logger.warning(
                    "Failed to import prospect",
                    prospect_name=prospect_data.get("full_name"),
                    error=str(e)
                )
                continue

        await commit_transaction(db, "import_all_prospects")

        # Update campaign stats
        await campaign_service.update_campaign_stats(campaign_id)
        await db.commit()

        logger.info(
            "Prospect import completed",
            campaign_id=campaign_id,
            companies_created=companies_created,
            prospects_created=prospects_created,
            prospects_skipped=prospects_skipped
        )

        # Return HTMX response to close modal and refresh table with success message
        import json

        # Build success message
        message_parts = []
        if prospects_created > 0:
            message_parts.append(f"imported {prospects_created} new prospects")
        if prospects_skipped > 0:
            message_parts.append(f"skipped {prospects_skipped} duplicates")
        if companies_created > 0:
            message_parts.append(f"created {companies_created} companies")

        success_message = "Successfully " + ", ".join(message_parts) + "!"

        hx_trigger = json.dumps({
            "closeModal": None,
            "refreshTable": None,
            "showToast": {
                "message": success_message,
                "level": "success"
            }
        })

        return Response(
            status_code=200,
            headers={
                "HX-Trigger": hx_trigger
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("import_all_prospects", e)
        raise HTTPException(status_code=500, detail="Failed to import prospects")
