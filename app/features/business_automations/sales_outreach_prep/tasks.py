"""
Celery background tasks for Sales Outreach Prep.

Handles:
- Prospect discovery via Firecrawl (LinkedIn search)
- Email enrichment via Hunter.io
- Campaign statistics updates
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.features.core.celery_app import celery_app
from app.features.core.database import async_session
from app.features.core.sqlalchemy_imports import get_logger

from app.features.business_automations.sales_outreach_prep.models import (
    Campaign,
    Company,
    Prospect,
    EnrichmentLog
)
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService
from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService
from app.features.business_automations.sales_outreach_prep.utils import (
    FirecrawlClient,
    HunterClient,
    get_firecrawl_api_key,
    get_hunter_api_key
)

logger = get_logger(__name__)


async def _ai_research_discovery(db, campaign, campaign_service) -> Dict[str, Any]:
    """
    Execute AI-powered research discovery workflow.

    Args:
        db: Database session
        campaign: Campaign object
        campaign_service: Campaign service instance

    Returns:
        Task result summary
    """
    from app.features.business_automations.sales_outreach_prep.services.prospect_research_service import ProspectResearchService
    from sqlalchemy import update

    tenant_id = campaign.tenant_id
    campaign_id = campaign.id

    # Check for research prompt
    if not campaign.research_prompt:
        logger.error("No research prompt provided for AI research", campaign_id=campaign_id)
        return {"success": False, "error": "Research prompt is required for AI research discovery"}

    logger.info(
        "Starting AI research",
        campaign_id=campaign_id,
        prompt=campaign.research_prompt[:100]
    )

    try:
        # Initialize research service
        research_service = ProspectResearchService(tenant_id=tenant_id)

        # Run NEW AI research workflow that returns prospects directly
        research_result = await research_service.research_prospects(
            prompt=campaign.research_prompt,
            db_session=db,
            accessed_by_user=None  # Background task
        )

        # Store research results in campaign.research_data and update status to active
        stmt = (
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(
                research_data=research_result,
                status="active"  # Mark campaign as active (research complete, ready for review)
            )
        )
        await db.execute(stmt)
        await db.commit()

        prospects_found = len(research_result.get("prospects", []))
        strategy_used = research_result.get("metadata", {}).get("strategy_used", "unknown")

        logger.info(
            "AI prospect research completed and stored",
            campaign_id=campaign_id,
            prospects_found=prospects_found,
            strategy_used=strategy_used
        )

        # User can now review prospects and click "Import All" to create Prospect records
        result = {
            "success": True,
            "discovery_type": "ai_research",
            "campaign_id": campaign_id,
            "research_completed": True,
            "prospects_found": prospects_found,
            "strategy_used": strategy_used,
            "message": f"AI research complete - found {prospects_found} prospects using {strategy_used} strategy"
        }

        return result

    except Exception as e:
        logger.exception(
            "AI research discovery failed",
            campaign_id=campaign_id
        )
        return {
            "success": False,
            "error": str(e)
        }


# NOTE: Old auto-creation code removed (lines 121-268)
# AI research now ONLY stores results - companies/prospects created via approve endpoints


@celery_app.task(name="sales_outreach_prep.discover_prospects")
def discover_prospects_task(
    campaign_id: str,
    company_ids: Optional[List[str]] = None,
    max_results_per_company: int = 20
) -> Dict[str, Any]:
    """
    Discover prospects for a campaign using Firecrawl.

    Args:
        campaign_id: Campaign ID
        company_ids: Optional list of company IDs to search (None = all companies)
        max_results_per_company: Max prospects per company

    Returns:
        Task result summary
    """
    import asyncio
    return asyncio.run(_discover_prospects_async(
        campaign_id,
        company_ids,
        max_results_per_company
    ))


async def _discover_prospects_async(
    campaign_id: str,
    company_ids: Optional[List[str]],
    max_results_per_company: int
) -> Dict[str, Any]:
    """Async implementation of prospect discovery."""
    try:
        async with async_session() as db:
            # Get campaign
            campaign_service = CampaignCrudService(db)
            campaign = await campaign_service.get_campaign_by_id(campaign_id)

            if not campaign:
                logger.error("Campaign not found for discovery", campaign_id=campaign_id)
                return {"success": False, "error": "Campaign not found"}

            tenant_id = campaign.tenant_id

            # Route based on discovery type
            if campaign.discovery_type == "ai_research":
                logger.info("Using AI research discovery", campaign_id=campaign_id)
                return await _ai_research_discovery(db, campaign, campaign_service)
            elif campaign.discovery_type == "manual_import":
                logger.info("Manual import discovery", campaign_id=campaign_id)
                return {"success": False, "error": "Manual import not yet implemented"}
            else:
                # Default: company_discovery (existing logic)
                logger.info("Using company discovery", campaign_id=campaign_id)

            # Get companies to search
            company_service = CompanyCrudService(db, tenant_id)
            prospect_service = ProspectCrudService(db, tenant_id)

            if company_ids:
                # Search specific companies
                companies = []
                for company_id in company_ids:
                    company = await company_service.get_company_by_id(company_id)
                    if company:
                        companies.append(company)
            else:
                # Search all companies (limited for MVP)
                companies, _ = await company_service.list_companies(limit=50)

            if not companies:
                logger.warning("No companies found for discovery", campaign_id=campaign_id)
                return {"success": True, "prospects_created": 0, "message": "No companies to search"}

            # Get Firecrawl API key from secrets management
            firecrawl_api_key = await get_firecrawl_api_key(db, tenant_id)
            if not firecrawl_api_key:
                logger.error("Firecrawl API key not configured", campaign_id=campaign_id)
                return {"success": False, "error": "Firecrawl API key not configured in secrets management"}

            # Initialize Firecrawl client
            firecrawl = FirecrawlClient(api_key=firecrawl_api_key)

            total_prospects = 0
            companies_searched = 0

            # Search each company
            for company in companies:
                try:
                    logger.info(
                        "Searching for prospects",
                        campaign_id=campaign_id,
                        company_name=company.name
                    )

                    # Build search criteria from campaign
                    job_titles = None
                    if campaign.target_roles:
                        job_titles = [role.strip() for role in campaign.target_roles.split(',')]

                    # Search LinkedIn profiles
                    results = await firecrawl.search_linkedin_profiles(
                        company_name=company.name,
                        job_titles=job_titles,
                        location=campaign.target_geography,
                        max_results=max_results_per_company
                    )

                    # Create prospect records
                    for result in results:
                        try:
                            prospect_data = {
                                "campaign_id": campaign_id,
                                "company_id": company.id,
                                "full_name": result.get("full_name"),
                                "job_title": result.get("job_title"),
                                "linkedin_url": result.get("linkedin_url"),
                                "linkedin_snippet": result.get("linkedin_snippet"),
                                "discovered_via": "firecrawl",
                                "discovery_query": f"{company.name} {job_titles if job_titles else ''}",
                            }

                            prospect = await prospect_service.create_prospect(
                                prospect_data,
                                user=None  # Background task
                            )

                            total_prospects += 1

                            logger.info(
                                "Prospect created",
                                prospect_id=prospect.id,
                                name=prospect.full_name
                            )

                        except Exception as e:
                            logger.error(
                                "Failed to create prospect",
                                company=company.name,
                                result=result,
                                error=str(e)
                            )

                    companies_searched += 1

                except Exception as e:
                    logger.error(
                        "Failed to search company",
                        company=company.name,
                        error=str(e)
                    )

            # Commit transaction
            await db.commit()

            # Update campaign stats
            await campaign_service.update_campaign_stats(campaign_id)
            await db.commit()

            logger.info(
                "Prospect discovery completed",
                campaign_id=campaign_id,
                companies_searched=companies_searched,
                prospects_created=total_prospects
            )

            result = {
                "success": True,
                "campaign_id": campaign_id,
                "companies_searched": companies_searched,
                "prospects_created": total_prospects
            }

            # Optionally trigger auto-enrichment
            if campaign.auto_enrich_on_discovery and total_prospects > 0:
                logger.info(
                    "Auto-enrich enabled, triggering enrichment task",
                    campaign_id=campaign_id,
                    prospects_count=total_prospects
                )

                # Trigger enrichment task asynchronously
                from app.features.business_automations.sales_outreach_prep.tasks import enrich_prospects_task
                enrich_task = enrich_prospects_task.delay(campaign_id, max_prospects=total_prospects)

                result["enrichment_triggered"] = True
                result["enrichment_task_id"] = enrich_task.id

                logger.info(
                    "Enrichment task triggered",
                    campaign_id=campaign_id,
                    enrichment_task_id=enrich_task.id
                )
            else:
                result["enrichment_triggered"] = False
                if not campaign.auto_enrich_on_discovery:
                    logger.info(
                        "Auto-enrich disabled, skipping enrichment",
                        campaign_id=campaign_id
                    )

            return result

    except Exception as e:
        logger.error(
            "Prospect discovery failed",
            campaign_id=campaign_id,
            error=str(e),
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="sales_outreach_prep.enrich_prospects")
def enrich_prospects_task(
    campaign_id: str,
    prospect_ids: Optional[List[str]] = None,
    max_prospects: int = 50
) -> Dict[str, Any]:
    """
    Enrich prospects with email addresses using Hunter.io.

    Args:
        campaign_id: Campaign ID
        prospect_ids: Optional list of prospect IDs (None = auto-select)
        max_prospects: Max prospects to enrich

    Returns:
        Task result summary
    """
    import asyncio
    return asyncio.run(_enrich_prospects_async(
        campaign_id,
        prospect_ids,
        max_prospects
    ))


async def _enrich_prospects_async(
    campaign_id: str,
    prospect_ids: Optional[List[str]],
    max_prospects: int
) -> Dict[str, Any]:
    """Async implementation of prospect enrichment."""
    try:
        async with async_session() as db:
            # Get campaign
            campaign_service = CampaignCrudService(db)
            campaign = await campaign_service.get_campaign_by_id(campaign_id)

            if not campaign:
                logger.error("Campaign not found for enrichment", campaign_id=campaign_id)
                return {"success": False, "error": "Campaign not found"}

            tenant_id = campaign.tenant_id
            prospect_service = ProspectCrudService(db, tenant_id)

            # Get prospects to enrich
            if prospect_ids:
                prospects = []
                for prospect_id in prospect_ids:
                    prospect = await prospect_service.get_prospect_by_id(prospect_id)
                    if prospect:
                        prospects.append(prospect)
            else:
                # Auto-select prospects ready for enrichment
                prospects = await prospect_service.get_prospects_for_enrichment(
                    campaign_id,
                    limit=max_prospects
                )

            if not prospects:
                logger.info("No prospects to enrich", campaign_id=campaign_id)
                return {"success": True, "enriched": 0, "message": "No prospects to enrich"}

            # Get Hunter.io API key from secrets management
            hunter_api_key = await get_hunter_api_key(db, tenant_id)
            if not hunter_api_key:
                logger.error("Hunter.io API key not configured", campaign_id=campaign_id)
                return {"success": False, "error": "Hunter.io API key not configured in secrets management"}

            # Initialize Hunter.io client
            hunter = HunterClient(api_key=hunter_api_key)

            enriched_count = 0
            failed_count = 0

            # Enrich each prospect
            for prospect in prospects:
                try:
                    # Need company domain for email finding
                    if not prospect.company_id:
                        logger.debug(
                            "Prospect has no company, skipping enrichment",
                            prospect_id=prospect.id
                        )
                        continue

                    # Get company
                    company_service = CompanyCrudService(db, tenant_id)
                    company = await company_service.get_company_by_id(prospect.company_id)

                    if not company or not company.domain:
                        logger.debug(
                            "Company has no domain, skipping enrichment",
                            prospect_id=prospect.id,
                            company_id=prospect.company_id
                        )
                        continue

                    # Log enrichment attempt
                    log = EnrichmentLog(
                        tenant_id=tenant_id,
                        prospect_id=prospect.id,
                        enrichment_type="email",
                        provider="hunter.io",
                        status="in_progress",
                        attempted_at=datetime.now()
                    )
                    db.add(log)
                    await db.flush()

                    # Find email
                    email_data = await hunter.find_email(
                        first_name=prospect.first_name or prospect.full_name.split()[0],
                        last_name=prospect.last_name or prospect.full_name.split()[-1],
                        domain=company.domain
                    )

                    if email_data and email_data.get("email"):
                        # Update prospect with email
                        enrichment_result = {
                            "email": email_data["email"],
                            "email_confidence": email_data.get("confidence"),
                            "email_status": email_data.get("status"),
                            "enrichment_status": "enriched",
                            "enrichment_source": "hunter.io"
                        }

                        await prospect_service.update_prospect_enrichment(
                            prospect.id,
                            enrichment_result
                        )

                        # Update log
                        log.status = "success"
                        log.completed_at = datetime.now()
                        log.confidence_score = email_data.get("confidence")
                        log.result_data = email_data

                        enriched_count += 1

                        logger.info(
                            "Prospect enriched",
                            prospect_id=prospect.id,
                            email=email_data["email"],
                            confidence=email_data.get("confidence")
                        )

                    else:
                        # No email found
                        log.status = "failed"
                        log.completed_at = datetime.now()
                        log.error_message = "No email found"

                        failed_count += 1

                        logger.info(
                            "No email found for prospect",
                            prospect_id=prospect.id
                        )

                except Exception as e:
                    failed_count += 1
                    logger.error(
                        "Failed to enrich prospect",
                        prospect_id=prospect.id,
                        error=str(e)
                    )

            # Commit transaction
            await db.commit()

            # Update campaign stats
            await campaign_service.update_campaign_stats(campaign_id)
            await db.commit()

            logger.info(
                "Prospect enrichment completed",
                campaign_id=campaign_id,
                enriched=enriched_count,
                failed=failed_count
            )

            return {
                "success": True,
                "campaign_id": campaign_id,
                "enriched": enriched_count,
                "failed": failed_count,
                "total_processed": enriched_count + failed_count
            }

    except Exception as e:
        logger.error(
            "Prospect enrichment failed",
            campaign_id=campaign_id,
            error=str(e),
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e)
        }
