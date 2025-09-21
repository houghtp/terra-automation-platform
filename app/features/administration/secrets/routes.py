"""
Tenant-aware secrets management routes following demo slice patterns.
Provides secure CRUD operations for storing API keys, tokens, and other sensitive data.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Response, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.templates import templates
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.administration.secrets.models import (
    SecretCreate,
    SecretUpdate,
    SecretResponse,
    SecretValue,
    SecretType
)
from app.features.administration.secrets.services import SecretsService
from app.features.core.validation import FormHandler, ValidationError
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/administration/secrets", tags=["administration", "secrets"])




@router.patch("/{secret_id}/field")
async def update_secret_field_api(secret_id: int, field_update: dict = Body(...), db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    field = field_update.get("field")
    value = field_update.get("value")

    # Coerce known field types coming from the client
    if field in ['is_active'] and isinstance(value, str):
        # Handle boolean fields from toggle switches
        value = value.lower() == 'true'

    # Handle tags field - if it's a JSON string, parse it
    if field == 'tags' and isinstance(value, str) and value:
        if value.startswith('[') or value.startswith('{'):
            try:
                import json
                value = json.loads(value)
            except Exception:
                # keep string value if parse fails
                pass

    secrets_service = SecretsService(db)
    updated_secret = await secrets_service.update_secret_field(tenant, secret_id, field, value)
    if not updated_secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    await db.commit()  # Route handles transaction commit
    return {"success": True}

# --- UI ROUTES (Jinja + HTMX) ---

# Dashboard (List page)
@router.get("/", response_class=HTMLResponse)
async def secrets_list(
    request: Request,
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secrets management dashboard.
    """
    secrets_service = SecretsService(db)

    try:
        # Get secrets list and stats
        secrets = await secrets_service.list_secrets(tenant, limit=50)
        stats = await secrets_service.get_secrets_stats(tenant)

        return templates.TemplateResponse(
            "administration/secrets/list.html",
            {
                "request": request,
                "title": "Secrets Management",
                "secrets": secrets,
                "stats": stats,
                "secret_types": [t.value for t in SecretType],
                "tenant_id": tenant
            }
        )
    except Exception as e:
        logger.exception("Failed to load secrets dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to load secrets dashboard: {str(e)}")


# Modal form (add/edit) - following demo pattern
@router.get("/partials/form", response_class=HTMLResponse)
async def secret_form_partial(
    request: Request,
    secret_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Secret form partial for modals.
    """
    secret = None
    if secret_id:
        secrets_service = SecretsService(db)
        secret = await secrets_service.get_secret_by_id(tenant, secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

    return templates.TemplateResponse(
        "administration/secrets/partials/form.html",
        {
            "request": request,
            "secret": secret,
            "secret_types": [t.value for t in SecretType]
        }
    )


# Modal edit endpoint - following demo pattern
@router.get("/{secret_id}/edit", response_class=HTMLResponse)
async def secret_edit_form(
    request: Request,
    secret_id: int,
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secret edit form modal.
    """
    secrets_service = SecretsService(db)
    secret = await secrets_service.get_secret_by_id(tenant, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    return templates.TemplateResponse(
        "administration/secrets/partials/form.html",
        {
            "request": request,
            "secret": secret,
            "secret_types": [t.value for t in SecretType]
        }
    )


# Create secret
@router.post("/")
async def secret_create(
    request: Request,
    tenant: str = Depends(tenant_dependency),
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
        name = form_handler.get_field('name')
        value = form_handler.get_field('value')
        description = form_handler.get_field('description')
        secret_type_str = form_handler.get_field('secret_type', SecretType.OTHER.value)

        # Convert string to enum
        try:
            secret_type = SecretType(secret_type_str)
        except ValueError:
            secret_type = SecretType.OTHER

        # Validate field lengths
        if len(name) < 3:
            raise ValidationError("Secret name must be at least 3 characters")
        if len(value) < 8:
            raise ValidationError("Secret value must be at least 8 characters")

        secrets_service = SecretsService(db)
        secret_data = SecretCreate(
            name=name,
            description=description,
            secret_type=secret_type,
            value=value
        )

        secret = await secrets_service.create_secret(
            tenant_id=tenant,
            secret_data=secret_data,
            created_by=current_user
        )

        await db.commit()  # Route handles transaction commit
        # Return empty response - client will handle redirect
        return Response(status_code=204)

    except ValidationError as e:
        logger.warning("Secret validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.warning("Invalid secret data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create secret", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create secret: {str(e)}")


# Update secret
@router.put("/{secret_id}")
async def secret_edit(
    request: Request,
    secret_id: int,
    tenant: str = Depends(tenant_dependency),
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a secret via form submission."""
    try:
        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        # Get form fields (all optional for updates)
        name = form_handler.get_field('name')
        description = form_handler.get_field('description')
        secret_type_str = form_handler.get_field('secret_type')
        value = form_handler.get_field('value')
        is_active = form_handler.get_field('is_active')

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

        # Validate field lengths if provided
        if name and len(name) < 3:
            raise ValidationError("Secret name must be at least 3 characters")
        if value and len(value) < 8:
            raise ValidationError("Secret value must be at least 8 characters")

        secrets_service = SecretsService(db)
        update_data = SecretUpdate(
            name=name,
            description=description,
            secret_type=secret_type,
            value=value,
            is_active=is_active
        )

        secret = await secrets_service.update_secret(
            tenant_id=tenant,
            secret_id=secret_id,
            update_data=update_data,
            updated_by=current_user
        )

        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()  # Route handles transaction commit
        # Return empty response - client will handle redirect
        return Response(status_code=204)

    except ValidationError as e:
        logger.warning("Secret validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions without logging as errors
        raise
    except ValueError as e:
        logger.warning("Invalid secret update data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to update secret", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update secret: {str(e)}")


# Delete secret (accept both DELETE and POST for compatibility)
@router.delete("/{secret_id}")
@router.post("/{secret_id}/delete")
async def secret_delete(
    secret_id: int,
    tenant: str = Depends(tenant_dependency),
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a secret by ID. Accepts both DELETE and POST for frontend compatibility."""
    secrets_service = SecretsService(db)

    try:
        success = await secrets_service.delete_secret(
            tenant_id=tenant,
            secret_id=secret_id,
            deleted_by=current_user
        )

        if not success:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()  # Route handles transaction commit
        return Response(status_code=204)  # Return 204 for HTMX compatibility

    except HTTPException:
        # Re-raise HTTP exceptions without logging as errors
        raise
    except Exception as e:
        logger.exception("Failed to delete secret", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete secret: {str(e)}")


# List content partial for HTMX
@router.get("/partials/list_content", response_class=HTMLResponse)
async def secret_list_partial(
    request: Request,
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List content partial for HTMX."""
    secrets_service = SecretsService(db)

    try:
        secrets = await secrets_service.list_secrets(tenant, limit=50)
        return templates.TemplateResponse(
            "administration/secrets/partials/list_content.html",
            {
                "request": request,
                "secrets": secrets
            }
        )
    except Exception as e:
        logger.exception("Failed to load secrets list content", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to load secrets: {str(e)}")


# --- API ROUTES (Programmatic Access) ---

# List endpoint alias for test compatibility
@router.get("/list", response_model=List[SecretResponse])
async def list_secrets_endpoint(
    secret_type: Optional[SecretType] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """List tenant secrets (test-compatible endpoint)."""
    secrets_service = SecretsService(db)

    try:
        secrets = await secrets_service.list_secrets(
            tenant_id=tenant,
            secret_type=secret_type,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset
        )
        return secrets

    except Exception as e:
        logger.exception("Failed to list secrets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list secrets: {str(e)}")


# Stats endpoint alias for test compatibility
@router.get("/stats/overview")
async def secrets_stats_overview(
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get secrets statistics overview (test-compatible endpoint)."""
    secrets_service = SecretsService(db)

    try:
        stats = await secrets_service.get_secrets_stats(tenant)
        return stats

    except Exception as e:
        logger.exception("Failed to get secrets stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get secrets stats: {str(e)}")


# API endpoint for getting secrets
@router.get("/api", response_class=JSONResponse)
async def get_secrets_api(
    secret_type: Optional[SecretType] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """List tenant secrets with filtering."""
    secrets_service = SecretsService(db)

    try:
        secrets = await secrets_service.list_secrets(
            tenant_id=tenant,
            secret_type=secret_type,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset
        )
        # Return array directly for API compatibility
        return [secret.model_dump() for secret in secrets]

    except Exception as e:
        logger.exception("Failed to list secrets via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list secrets: {str(e)}")


# API endpoint for creating secrets
@router.post("/api", response_model=SecretResponse)
async def create_secret_api(
    secret_data: SecretCreate,
    tenant: str = Depends(tenant_dependency),
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant secret via API (JSON)."""
    secrets_service = SecretsService(db)

    try:
        secret = await secrets_service.create_secret(
            tenant_id=tenant,
            secret_data=secret_data,
            created_by=current_user
        )
        await db.commit()
        return secret

    except ValueError as e:
        logger.warning("Invalid secret data via API", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create secret via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create secret: {str(e)}")


# View secret details (HTMX partial)
@router.get("/{secret_id}/view", response_class=HTMLResponse)
async def view_secret(
    secret_id: int,
    request: Request,
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """View secret details in modal (HTMX partial)."""
    secrets_service = SecretsService(db)

    try:
        secret = await secrets_service.get_secret_by_id(tenant, secret_id)
        return templates.TemplateResponse(
            "administration/secrets/partials/view_details.html",
            {
                "request": request,
                "secret": secret
            }
        )
    except HTTPException as e:
        return templates.TemplateResponse(
            "error/404.html",
            {"request": request, "detail": "Secret not found"},
            status_code=404
        )

# Get secret metadata by ID
@router.get("/{secret_id}", response_model=SecretResponse)
async def get_secret(
    secret_id: int,
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get secret metadata by ID."""
    secrets_service = SecretsService(db)

    secret = await secrets_service.get_secret_by_id(tenant, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    return secret


# Get secret value (dangerous operation)
@router.get("/{secret_id}/value", response_model=SecretValue)
async def get_secret_value(
    secret_id: int,
    tenant: str = Depends(tenant_dependency),
    current_user: Optional[str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get decrypted secret value (use with caution)."""
    secrets_service = SecretsService(db)

    secret_value = await secrets_service.get_secret_value(
        tenant_id=tenant,
        secret_id=secret_id,
        accessed_by=current_user
    )

    if not secret_value:
        raise HTTPException(status_code=404, detail="Secret not found or expired")

    return secret_value


# Get secrets statistics
@router.get("/api/stats", name="secrets_stats")
async def secrets_stats(
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get secrets statistics for the tenant."""
    secrets_service = SecretsService(db)

    try:
        stats = await secrets_service.get_secrets_stats(tenant)
        return stats

    except Exception as e:
        logger.exception("Failed to get secrets stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get secrets stats: {str(e)}")


# Get expiring secrets
@router.get("/api/expiring", response_model=List[SecretResponse])
async def expiring_secrets(
    days_ahead: int = 30,
    tenant: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db)
):
    """Get secrets that will expire soon."""
    secrets_service = SecretsService(db)

    try:
        secrets = await secrets_service.get_expiring_secrets(tenant, days_ahead)
        return secrets

    except Exception as e:
        logger.exception("Failed to get expiring secrets", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get expiring secrets: {str(e)}")


# --- HTMX Validation Endpoints ---

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(request: Request, name: str = Form(...), tenant: str = Depends(tenant_dependency), db: AsyncSession = Depends(get_db)):
    """Validate secret name field in real-time via HTMX."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Secret name is required</span>')

        if len(name.strip()) < 3:
            return HTMLResponse('<span class="invalid-feedback d-block">Secret name must be at least 3 characters</span>')

        # Check for duplicate names within tenant
        secrets_service = SecretsService(db)
        existing_secrets = await secrets_service.list_secrets(tenant, limit=1000)
        if any(secret.name.lower() == name.strip().lower() for secret in existing_secrets):
            return HTMLResponse('<span class="invalid-feedback d-block">A secret with this name already exists</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block">Secret name is available</span>')

    except Exception as e:
        logger.exception("Error validating secret name", error=str(e))
        return HTMLResponse('<span class="invalid-feedback d-block">Validation error occurred</span>')


@router.post("/validate/value", response_class=HTMLResponse)
async def validate_value_field(request: Request, value: str = Form(...)):
    """Validate secret value field in real-time via HTMX."""
    try:
        if not value or not value.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value is required</span>')

        if len(value.strip()) < 8:
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value must be at least 8 characters</span>')

        # Check for common weak patterns
        weak_patterns = ['password', '123456', 'admin', 'test', 'default']
        if any(pattern in value.lower() for pattern in weak_patterns):
            return HTMLResponse('<span class="invalid-feedback d-block">Secret value appears to be weak or common</span>')

        # Valid value
        return HTMLResponse('<span class="valid-feedback d-block">Secret value looks secure</span>')

    except Exception as e:
        logger.exception("Error validating secret value", error=str(e))
        return HTMLResponse('<span class="invalid-feedback d-block">Validation error occurred</span>')
