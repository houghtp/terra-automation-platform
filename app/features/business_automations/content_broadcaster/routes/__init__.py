from fastapi import APIRouter
from .form_routes import router as form_router
from .api_routes import router as api_router
from .dashboard_routes import router as dashboard_router
from .planning_routes import router as planning_router
from .crud_routes import router as crud_router

# Create main router that combines all sub-routers
router = APIRouter(tags=["Content Broadcaster"])

# Include all sub-routers
router.include_router(form_router)
router.include_router(api_router)
router.include_router(dashboard_router)
router.include_router(planning_router)
# Keep CRUD routes last so the dynamic /api/{content_id} path doesn't shadow more specific routes.
router.include_router(crud_router)
