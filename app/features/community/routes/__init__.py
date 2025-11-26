"""Route aggregation for the community feature."""

from fastapi import APIRouter

from .members import router as members_router
from .partners import router as partners_router
from .pages_routes import router as pages_router
from .groups import router as groups_router
from .messages import router as messages_router
from .events import router as events_router
from .polls import router as polls_router
from .content import router as content_router

router = APIRouter(tags=["Community"])

# Order: pages first (HTML shell), then entity packages
router.include_router(pages_router)
router.include_router(groups_router)
router.include_router(members_router)
router.include_router(partners_router)
router.include_router(messages_router)
router.include_router(events_router)
router.include_router(polls_router)
router.include_router(content_router)

__all__ = ["router"]
