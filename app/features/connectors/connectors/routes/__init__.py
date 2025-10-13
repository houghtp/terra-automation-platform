"""
Connectors routes aggregation.

Combines API, dashboard, and form routes into a single router.
"""

from fastapi import APIRouter
from .api_routes import router as api_router
from .dashboard_routes import router as dashboard_router
from .form_routes import router as form_router

# Main router for connectors feature
router = APIRouter()

# Include sub-routers
router.include_router(api_router)
router.include_router(dashboard_router)
router.include_router(form_router)

__all__ = ["router"]
