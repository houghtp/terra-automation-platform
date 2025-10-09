# Gold Standard Route Imports - Tenants Dashboard
from app.features.core.route_imports import (
    APIRouter, Depends, AsyncSession, get_db, get_logger
)
from app.features.auth.dependencies import get_global_admin_user
from app.features.auth.models import User

logger = get_logger(__name__)

router = APIRouter(tags=["tenants-dashboard"])

# --- DASHBOARD ROUTES ---
# Note: Tenants module currently has no dashboard-specific endpoints
# This file is reserved for future dashboard routes like charts, stats cards, etc.
