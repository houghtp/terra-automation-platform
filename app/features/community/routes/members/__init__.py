from fastapi import APIRouter
from .form_routes import router as form_router
from .crud_routes import router as crud_router

router = APIRouter(prefix="/members", tags=["community-members"])
router.include_router(form_router)
router.include_router(crud_router)
