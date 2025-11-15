# Gold Standard Route Imports - SMTP Forms
from app.features.core.route_imports import (
    # Core FastAPI components
    APIRouter, Depends,
    # Database and dependencies
    AsyncSession, get_db,
    # Tenant and auth
    tenant_dependency, get_current_user, get_global_admin_user, User,
    # Request/Response types
    Request, Form, HTTPException, Response,
    # Response types
    HTMLResponse,
    # Template rendering
    templates,
    # Logging and error handling
    get_logger, handle_route_error,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Form handling
    FormHandler,
    # Typing
    Optional
)

from app.features.administration.smtp.services import SMTPConfigurationService
from app.features.administration.smtp.models import SMTPStatus
from app.features.administration.smtp.schemas import (
    SMTPConfigurationCreate,
    SMTPConfigurationUpdate,
)
import re

logger = get_logger(__name__)

router = APIRouter(tags=["smtp-forms"])

# --- UI ROUTES (Jinja + HTMX) ---

# List page
@router.get("/", response_class=HTMLResponse)
async def smtp_list(request: Request, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

    return templates.TemplateResponse("administration/smtp/list.html", {
        "request": request,
        "is_global_admin": is_global_admin
    })

# Modal form (add/edit)
@router.get("/partials/form", response_class=HTMLResponse)
async def smtp_form_partial(request: Request, config_id: str = None, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    config = None
    if config_id:
        service = SMTPConfigurationService(db, tenant_id)
        config = await service.get_configuration_by_id(config_id)

    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

    # Get available tenants for global admins
    available_tenants = []
    if is_global_admin:
        service = SMTPConfigurationService(db, tenant_id)
        available_tenants = await service.get_available_tenants_for_smtp_forms()

    return templates.TemplateResponse("administration/smtp/partials/form.html", {
        "request": request,
        "config": config,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    })

# Modal edit endpoint
@router.get("/{config_id}/edit", response_class=HTMLResponse)
async def smtp_edit_form(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = SMTPConfigurationService(db, tenant_id)
    config = await service.get_configuration_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    # Check if current user is global admin
    is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

    # Get available tenants for global admins
    available_tenants = []
    if is_global_admin:
        available_tenants = await service.get_available_tenants_for_smtp_forms()

    return templates.TemplateResponse("administration/smtp/partials/form.html", {
        "request": request,
        "config": config,
        "is_global_admin": is_global_admin,
        "available_tenants": available_tenants
    })



# --- HTMX VALIDATION ENDPOINTS ---

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_smtp_name(request: Request, name: str = Form(...), config_id: Optional[str] = Form(None), db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate SMTP configuration name."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Configuration name is required</span>')

        name = name.strip()

        if len(name) < 3:
            return HTMLResponse('<span class="invalid-feedback d-block">Configuration name must be at least 3 characters</span>')

        if len(name) > 255:
            return HTMLResponse('<span class="invalid-feedback d-block">Configuration name must be less than 255 characters</span>')

        # Check for duplicate names within tenant (excluding current config if editing)
        smtp_service = SMTPConfigurationService(db, tenant_id)
        existing = await smtp_service.get_configuration_by_name(name)

        if existing and (not config_id or existing.id != config_id):
            return HTMLResponse('<span class="invalid-feedback d-block">A configuration with this name already exists</span>')

        return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Configuration name is available</span>')
    except Exception as e:
        logger.exception("Error validating SMTP name", error=str(e))
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating configuration name</span>')

@router.post("/validate/host", response_class=HTMLResponse)
async def validate_smtp_host(request: Request, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate SMTP host."""
    try:
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        host = form_handler.form_data.get("host", "").strip()
        if not host:
            return HTMLResponse('<span class="invalid-feedback d-block">SMTP host is required</span>')

        # Basic host validation
        host_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$'
        if not re.match(host_pattern, host):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid hostname format</span>')

        return HTMLResponse('<span class="valid-feedback d-block">Host format looks good</span>')
    except Exception:
        return HTMLResponse("")

@router.post("/validate/password", response_class=HTMLResponse)
async def validate_smtp_password(request: Request, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate SMTP password."""
    try:
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        password = form_handler.form_data.get("password", "")
        confirm_password = form_handler.form_data.get("confirm_password", "")

        if not password:
            return HTMLResponse('<span class="invalid-feedback d-block">Password is required</span>')

        if len(password) < 8:
            return HTMLResponse('<span class="invalid-feedback d-block">Password must be at least 8 characters</span>')

        if confirm_password and password != confirm_password:
            return HTMLResponse('<span class="invalid-feedback d-block">Passwords do not match</span>')

        return HTMLResponse('<span class="valid-feedback d-block">Password looks good</span>')
    except Exception:
        return HTMLResponse("")

@router.post("/validate/from_email", response_class=HTMLResponse)
async def validate_smtp_from_email(request: Request, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate from email address."""
    try:
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        from_email = form_handler.form_data.get("from_email", "").strip()
        if not from_email:
            return HTMLResponse('<span class="invalid-feedback d-block">From email is required</span>')

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, from_email):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid email format</span>')

        return HTMLResponse('<span class="valid-feedback d-block">Email format looks good</span>')
    except Exception:
        return HTMLResponse("")
