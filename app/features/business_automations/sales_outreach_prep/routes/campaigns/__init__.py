"""Campaign routes for Sales Outreach Prep."""

from fastapi import APIRouter
from .form_routes import router as form_router
from .crud_routes import router as crud_router
from .research_routes import router as research_router
from .streaming_routes import router as streaming_router

router = APIRouter()
router.include_router(form_router)
router.include_router(crud_router)
router.include_router(research_router)
router.include_router(streaming_router)

__all__ = ["router"]
