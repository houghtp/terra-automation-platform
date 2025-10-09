# Gold Standard Route Imports - Secrets Forms
"""
Secrets form routes - UI forms, validation, and dashboard pages.
"""
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Form, Response,
    HTMLResponse, AsyncSession, get_db, templates, FormHandler,
    tenant_dependency, get_current_user, get_global_admin_user, User,
    Optional, List, Dict, Any, structlog, get_logger
)

from app.features.administration.secrets.models import (
    SecretCreate,
    SecretUpdate,
    SecretType
)
from ..services import SecretsManagementService

router = APIRouter(tags=["secrets-forms"])
logger = get_logger(__name__)


async def get_secrets_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> SecretsManagementService:
    """Get secrets service dependency."""
    return SecretsManagementService(db, tenant_id)


# --- UI ROUTES (Jinja + HTMX) ---

@router.get("/", response_class=HTMLResponse, name="secrets_dashboard")
async def secrets_dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """Secrets management dashboard."""
    try:
        context = {
            "request": request,
            "user": current_user,
            "page_title": "Secrets Management",
            "page_description": "Securely store and manage API keys, tokens, and other sensitive data",
            "tenant_id": tenant_id
        }

        return templates.TemplateResponse(
            "administration/secrets/secrets_dashboard.html",
            context
        )

    except Exception as e:
        logger.exception("Failed to load secrets dashboard")
        raise HTTPException(status_code=500, detail=f"Failed to load secrets dashboard: {str(e)}")


@router.get("/partials/form", response_class=HTMLResponse)
async def secret_form_partial(
    request: Request,
    secret_id: Optional[int] = None,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Secret form partial for modals."""
    try:
        secret = None
        if secret_id:
            secret = await secrets_service.get_secret_by_id(secret_id)
            if not secret:
                raise HTTPException(status_code=404, detail="Secret not found")

        # Check if current user is global admin
        is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Get available tenants for global admins
        available_tenants = []
        if is_global_admin:
            available_tenants = await secrets_service.get_available_tenants_for_secrets_forms()

        return templates.TemplateResponse(
            "administration/secrets/partials/form.html",
            {
                "request": request,
                "secret": secret,
                "secret_types": [t.value for t in SecretType],
                "is_global_admin": is_global_admin,
                "available_tenants": available_tenants
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load secret form")
        raise HTTPException(status_code=500, detail="Failed to load secret form")


@router.get("/{secret_id}/edit", response_class=HTMLResponse)
async def secret_edit_form(
    request: Request,
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Secret edit form modal."""
    try:
        secret = await secrets_service.get_secret_by_id(secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        # Check if current user is global admin
        is_global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Get available tenants for global admins
        available_tenants = []
        if is_global_admin:
            available_tenants = await secrets_service.get_available_tenants_for_secrets_forms()

        return templates.TemplateResponse(
            "administration/secrets/partials/form.html",
            {
                "request": request,
                "secret": secret,
                "secret_types": [t.value for t in SecretType],
                "is_global_admin": is_global_admin,
                "available_tenants": available_tenants
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to load edit form for secret {secret_id}")
        raise HTTPException(status_code=500, detail="Failed to load edit form")


@router.get("/partials/secret_details", response_class=HTMLResponse)
async def get_secret_details_partial(
    request: Request,
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Get secret details partial for modal display."""
    try:
        secret = await secrets_service.get_secret_by_id(secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        context = {
            "request": request,
            "secret": secret
        }

        return templates.TemplateResponse(
            "administration/secrets/partials/secret_details.html",
            context
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get secret details")
        raise HTTPException(status_code=500, detail="Failed to load secret details")


@router.post("/")
async def secret_create(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Create a new secret via form submission."""
    try:
        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        # Validate required fields
        required_fields = ['name', 'value']
        form_handler.validate_required_fields(required_fields)

        # Additional validation
        name = form_handler.form_data.get('name')
        value = form_handler.form_data.get('value')
        description = form_handler.form_data.get('description')
        secret_type_str = form_handler.form_data.get('secret_type', SecretType.OTHER.value)

        # Convert string to enum
        try:
            secret_type = SecretType(secret_type_str)
        except ValueError:
            secret_type = SecretType.OTHER

        secret_data = SecretCreate(
            name=name,
            description=description,
            secret_type=secret_type,
            value=value
        )

        secret = await secrets_service.create_secret(
            secret_data=secret_data,
            created_by_user=current_user
        )

        await db.commit()
        return Response(status_code=204)

    except ValidationError as e:
        logger.warning("Secret validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.warning("Invalid secret data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create secret")
        raise HTTPException(status_code=500, detail=f"Failed to create secret: {str(e)}")


@router.put("/{secret_id}")
async def secret_update(
    request: Request,
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Update a secret via form submission."""
    try:
        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        # Get form fields (all optional for updates)
        name = form_handler.form_data.get('name')
        description = form_handler.form_data.get('description')
        secret_type_str = form_handler.form_data.get('secret_type')
        value = form_handler.form_data.get('value')
        is_active = form_handler.form_data.get('is_active')

        # Convert string to enum if provided
        secret_type = None
        if secret_type_str:
            try:
                secret_type = SecretType(secret_type_str)
            except ValueError:
                secret_type = None

        # Convert is_active string to boolean if provided
        if is_active is not None and isinstance(is_active, str):
            is_active = is_active.lower() in ('true', '1', 'on', 'yes')

        update_data = SecretUpdate(
            name=name,
            description=description,
            secret_type=secret_type,
            value=value,
            is_active=is_active
        )

        secret = await secrets_service.update_secret(
            secret_id=secret_id,
            update_data=update_data,
            updated_by_user=current_user
        )

        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()
        return Response(status_code=204)

    except ValidationError as e:
        logger.warning("Secret validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Invalid secret update data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to update secret")
        raise HTTPException(status_code=500, detail=f"Failed to update secret: {str(e)}")


# --- HTMX Validation Endpoints ---

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(
    request: Request,
    name: str = Form(...),
    secret_id: Optional[int] = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Validate secret name field in real-time via HTMX."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Secret name is required</span>')

        name = name.strip()

        if len(name) < 3:
            return HTMLResponse('<span class="invalid-feedback d-block">Secret name must be at least 3 characters</span>')

        if len(name) > 255:
            return HTMLResponse('<span class="invalid-feedback d-block">Secret name must be less than 255 characters</span>')

        # Check for duplicate names within tenant (excluding current secret if editing)
        if await secrets_service.secret_name_exists(name, exclude_id=secret_id):
            return HTMLResponse('<span class="invalid-feedback d-block">A secret with this name already exists</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Secret name is available</span>')

    except Exception as e:
        logger.exception("Error validating secret name")
        return HTMLResponse('<span class="invalid-feedback d-block">Validation error occurred</span>')


@router.post("/validate/value", response_class=HTMLResponse)
async def validate_value_field(request: Request, value: str = Form(...)):
    """Validate secret value field in real-time via HTMX."""
    try:
        if not value or not value.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value is required</span>')

        value = value.strip()

        if len(value) < 8:
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value must be at least 8 characters for security</span>')

        # Check for common weak patterns
        weak_patterns = ['password', '123456', 'admin', 'test', 'default', 'secret', 'key']
        if any(pattern in value.lower() for pattern in weak_patterns):
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value appears to contain common words - consider a more secure value</span>')

        # Check for basic complexity
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])

        if complexity_score < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Consider adding uppercase, lowercase, numbers, or special characters for better security</span>')

        # Valid value
        strength_indicator = "Good" if complexity_score >= 3 else "Fair"
        return HTMLResponse(f'<span class="valid-feedback d-block"><i class="ti ti-shield-check text-success me-1"></i>Secret value strength: {strength_indicator}</span>')

    except Exception as e:
        logger.exception("Error validating secret value")
        return HTMLResponse('<span class="invalid-feedback d-block">Validation error occurred</span>')


@router.post("/validate/description", response_class=HTMLResponse)
async def validate_description_field(request: Request, description: str = Form("")):
    """Validate secret description field in real-time via HTMX."""
    try:
        if len(description) > 1000:
            return HTMLResponse('<span class="invalid-feedback d-block">Description must be less than 1000 characters</span>')

        if description and len(description.strip()) > 0:
            return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Description looks good</span>')

        # Empty description is ok
        return HTMLResponse('')

    except Exception as e:
        logger.exception("Error validating secret description")
        return HTMLResponse('<span class="invalid-feedback d-block">Validation error occurred</span>')
