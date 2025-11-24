from fastapi import APIRouter
from .form_routes import router as form_router
from .crud_routes import router as crud_router

router = APIRouter(prefix="/messages", tags=["community-messages"])
router.include_router(form_router)
router.include_router(crud_router)
