"""Route aggregation for the community feature."""

from fastapi import APIRouter

from .members_routes import router as members_router
from .partners_routes import router as partners_router
from .pages_routes import router as pages_router
from .form_routes import router as form_router
from .groups_routes import router as groups_router
from .messages_routes import router as messaging_router
from .events_routes import router as events_router
from .polls_routes import router as polls_router
from .content_routes import router as content_router

router = APIRouter(tags=["Community"])

# Order: pages first (HTML shell), then API routes
router.include_router(pages_router)
router.include_router(form_router)
router.include_router(groups_router)
router.include_router(members_router)
router.include_router(partners_router)
router.include_router(messaging_router)
router.include_router(events_router)
router.include_router(polls_router)
router.include_router(content_router)

__all__ = ["router"]
