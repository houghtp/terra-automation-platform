from fastapi import APIRouter

from .connections import router as connections_router
from .metrics import router as metrics_router
from .insights import router as insights_router
from .reports import router as reports_router
from .ui import router as ui_router
from .auth import router as auth_router
from .clients import router as clients_router

router = APIRouter(tags=["marketing-intelligence-hub"])
router.include_router(ui_router)
router.include_router(auth_router)
router.include_router(clients_router)
router.include_router(connections_router)
router.include_router(metrics_router)
router.include_router(insights_router)
router.include_router(reports_router)

__all__ = ["router"]
