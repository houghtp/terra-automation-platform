# Gold Standard Route Imports - Tenants API
from app.features.core.route_imports import (
    APIRouter, Depends, AsyncSession, get_db, get_logger
)
from app.features.auth.dependencies import get_global_admin_user
from app.features.auth.models import User

logger = get_logger(__name__)

router = APIRouter(tags=["tenants-api"])

# --- EXTERNAL API ROUTES ---
# Note: Tenants module currently has no external API endpoints
# This file is reserved for future external API routes if needed
