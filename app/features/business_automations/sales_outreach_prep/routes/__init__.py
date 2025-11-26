"""
Routes for Sales Outreach Prep feature.

Aggregates all route modules and provides main router.
"""

from fastapi import APIRouter
from .campaigns import router as campaigns_router
from .prospects import router as prospects_router
from .companies import router as companies_router
from .dashboard import router as dashboard_router

# Main router for Sales Outreach Prep
router = APIRouter(
    prefix="/features/business-automations/sales-outreach-prep",
    tags=["sales-outreach-prep"]
)

# Include sub-routers
router.include_router(
    dashboard_router,
    tags=["sales-outreach-prep-dashboard"]
)

router.include_router(
    campaigns_router,
    prefix="/campaigns",
    tags=["sales-outreach-prep-campaigns"]
)

router.include_router(
    prospects_router,
    prefix="/prospects",
    tags=["sales-outreach-prep-prospects"]
)

router.include_router(
    companies_router,
    prefix="/companies",
    tags=["sales-outreach-prep-companies"]
)

__all__ = ["router"]
