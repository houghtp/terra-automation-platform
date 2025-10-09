# Gold Standard Route Imports - Logs API
from app.features.core.route_imports import (
    APIRouter, Depends, AsyncSession, get_db,
    tenant_dependency, get_current_user, User,
    get_logger
)

logger = get_logger(__name__)

router = APIRouter(tags=["logs-api"])

# --- EXTERNAL API ROUTES ---
# Note: Logs module currently has no external API endpoints
# This file is reserved for future external API routes if needed
