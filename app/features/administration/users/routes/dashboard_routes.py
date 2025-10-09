# Gold Standard Route Imports - Users Dashboard
from app.features.core.route_imports import (
    # Core FastAPI components
    APIRouter,
    # Database and dependencies
    AsyncSession, get_db,
    # Tenant and auth
    tenant_dependency, get_current_user, User,
    # Request/Response types
    Request, Form, HTTPException,
    # Response types
    HTMLResponse, RedirectResponse,
    # Template rendering
    templates,
    # Logging and error handling
    get_logger, handle_route_error,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Auth utilities
    is_global_admin
)

logger = get_logger(__name__)

router = APIRouter(tags=["users-dashboard"])

# --- DASHBOARD ROUTES ---
# Note: Users module currently has no dashboard-specific endpoints
# This file is reserved for future dashboard routes like charts, stats cards, etc.
