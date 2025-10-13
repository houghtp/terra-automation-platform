# Use centralized imports for consistency
from app.features.core.route_imports import *
from app.features.administration.users.services import UserManagementService
from app.features.administration.users.models import (
    UserCreate, UserUpdate, UserStatus, UserRole
)

logger = get_logger(__name__)

router = APIRouter(tags=["users-forms"])

# --- UI ROUTES (Jinja + HTMX) ---

# List page
@router.get("/", response_class=HTMLResponse)
async def user_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Users list page using standardized patterns."""
    try:
        return templates.TemplateResponse("administration/users/list.html", {
            "request": request,
            "is_global_admin": is_global_admin(current_user)
        })
    except Exception as e:
        handle_route_error("user_list", e)
        raise HTTPException(status_code=500, detail="Failed to load user list page")

# Modal form (add/edit)
@router.get("/partials/form", response_class=HTMLResponse)
async def user_form_partial(
    request: Request,
    user_id: str = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """User form partial using standardized patterns."""
    try:
        user = None
        if user_id:
            service = UserManagementService(db, tenant_id)
            user = await service.get_user_by_id(user_id)

        # Use centralized global admin check
        available_tenants = []
        global_admin = is_global_admin(current_user)

        if global_admin:
            service = UserManagementService(db, tenant_id)
            available_tenants = await service.get_available_tenants_for_user_forms()

        return templates.TemplateResponse("administration/users/partials/form.html", {
            "request": request,
            "user": user,
            "is_global_admin": global_admin,
            "available_tenants": available_tenants
        })

    except Exception as e:
        handle_route_error("user_form_partial", e, user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to load user form")

# Modal edit endpoint
@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(request: Request, user_id: str, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = UserManagementService(db, tenant_id)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
    available_tenants = []

    if is_global_admin:
        # Get available tenants for global admin
        available_tenants = await service.get_available_tenants_for_user_forms()

    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": user,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    })

# --- HTMX VALIDATION ENDPOINTS ---

@router.post("/validate/email", response_class=HTMLResponse)
async def validate_email_field(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Validate email field in real-time via HTMX using gold standard patterns."""
    try:
        if not email or not email.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Email is required</span>')

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid email format</span>')

        # Check for duplicate email in tenant
        service = UserManagementService(db, tenant_id)
        existing = await service.get_user_by_email(email)
        if existing:
            return HTMLResponse('<span class="invalid-feedback d-block">Email already exists</span>')

        # Valid - return empty or success message
        return HTMLResponse('<span class="valid-feedback d-block">Email is available</span>')

    except Exception as e:
        handle_route_error("validate_email_field", e, email=email)
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating email</span>')

@router.post("/validate/password", response_class=HTMLResponse)
async def validate_password_field(request: Request, password: str = Form(...)):
    """Validate password complexity in real-time via HTMX using gold standard patterns."""
    try:
        from app.features.core.security import validate_password_complexity

        if not password:
            return HTMLResponse('<span class="invalid-feedback d-block">Password is required</span>')

        # Check password complexity
        password_errors = validate_password_complexity(password)
        if password_errors:
            error_html = '<div class="invalid-feedback d-block">'
            for error in password_errors:
                error_html += f'<div>• {error}</div>'
            error_html += '</div>'
            return HTMLResponse(error_html)

        # Valid password
        return HTMLResponse('<span class="valid-feedback d-block">Password meets requirements</span>')

    except Exception as e:
        handle_route_error("validate_password_field", e)
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating password</span>')

@router.post("/validate/confirm-password", response_class=HTMLResponse)
async def validate_confirm_password_field(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Validate password confirmation in real-time via HTMX using gold standard patterns."""
    try:
        if not confirm_password:
            return HTMLResponse('<span class="invalid-feedback d-block">Please confirm your password</span>')

        if password != confirm_password:
            return HTMLResponse('<span class="invalid-feedback d-block">Passwords do not match</span>')

        # Valid confirmation
        return HTMLResponse('<span class="valid-feedback d-block">Passwords match</span>')

    except Exception as e:
        handle_route_error("validate_confirm_password_field", e)
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating password confirmation</span>')

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(request: Request, name: str = Form(...)):
    """Validate name field in real-time via HTMX using gold standard patterns."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Name is required</span>')

        if len(name.strip()) < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Name must be at least 2 characters</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block">Name looks good</span>')

    except Exception as e:
        handle_route_error("validate_name_field", e, name=name)
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating name</span>')
