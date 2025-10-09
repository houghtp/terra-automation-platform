from fastapi import APIRouter
from .form_routes import router as form_router
from .crud_routes import router as crud_router
from .api_routes import router as api_router
from .dashboard_routes import router as dashboard_router

# Create main router that combines all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(form_router)
router.include_router(crud_router)
router.include_router(api_router)
router.include_router(dashboard_router)