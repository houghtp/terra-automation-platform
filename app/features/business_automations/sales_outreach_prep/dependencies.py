"""
Dependency injection for Sales Outreach Prep feature.

Provides factory functions for service instantiation in routes.
Follows platform best practices for dependency injection.
"""

from typing import AsyncGenerator
from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService
from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService

logger = get_logger(__name__)


# Service dependencies

def get_campaign_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> CampaignCrudService:
    """
    Get campaign CRUD service instance.

    Args:
        db: Database session
        tenant_id: Current tenant ID

    Returns:
        CampaignCrudService instance
    """
    return CampaignCrudService(db, tenant_id)


def get_company_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> CompanyCrudService:
    """
    Get company CRUD service instance.

    Args:
        db: Database session
        tenant_id: Current tenant ID

    Returns:
        CompanyCrudService instance
    """
    return CompanyCrudService(db, tenant_id)


def get_prospect_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> ProspectCrudService:
    """
    Get prospect CRUD service instance.

    Args:
        db: Database session
        tenant_id: Current tenant ID

    Returns:
        ProspectCrudService instance
    """
    return ProspectCrudService(db, tenant_id)
