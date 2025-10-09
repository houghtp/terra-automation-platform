# Gold Standard Route Imports - Secrets CRUD
"""
Secrets CRUD routes - Database operations and API endpoints.
"""
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Body, Query,
    JSONResponse, Response, AsyncSession, get_db,
    tenant_dependency, get_current_user, get_global_admin_user, User,
    Optional, List, Dict, Any, structlog, get_logger,
    # Template rendering
    templates,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Form handling
    FormHandler,
    # Rate limiting
    rate_limit_api
)

from app.features.administration.secrets.models import (
    SecretCreate,
    SecretUpdate,
    SecretResponse,
    SecretValue,
    SecretType
)
from ..services import SecretsManagementService

router = APIRouter(tags=["secrets-crud"])
logger = get_logger(__name__)


async def get_secrets_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency)
) -> SecretsManagementService:
    """Get secrets service dependency."""
    return SecretsManagementService(db, tenant_id)


# --- API ROUTES (Database Operations) ---

@router.get("/api/list")
async def get_secrets_list(
    secret_type: Optional[SecretType] = None,
    include_inactive: bool = False,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    _rate_limit: dict = Depends(rate_limit_api)
):
    """Get secrets list for Tabulator (returns simple array)."""
    try:
        secrets = await secrets_service.list_secrets(
            secret_type=secret_type,
            include_inactive=include_inactive
        )

        # Return simple array format for Tabulator compatibility
        result = [secret.model_dump() for secret in secrets]
        return result

    except Exception as e:
        logger.exception("Failed to get secrets list")
        raise HTTPException(status_code=500, detail="Failed to retrieve secrets")


@router.get("/api/stats")
async def get_secrets_stats(
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Get secrets statistics for dashboard."""
    try:
        stats = await secrets_service.get_secrets_stats()
        return stats

    except Exception as e:
        logger.exception("Failed to get secrets stats")
        raise HTTPException(status_code=500, detail="Failed to get secrets stats")


@router.get("/api/{secret_id}")
async def get_secret_details(
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Get detailed information for a specific secret."""
    try:
        secret = await secrets_service.get_secret_by_id(secret_id)

        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        return secret.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get secret details for {secret_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret details")


# Create secret via form submission
@router.post("/")
async def create_secret_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Create a new secret via form submission."""
    try:
        # Initialize form handler
        form_handler = FormHandler(await request.form())

        # Check if current user is global admin
        global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"
        target_tenant_id = None

        if global_admin:
            # For global admins, target_tenant_id is required
            target_tenant_id = form_handler.form_data.get("target_tenant_id")
            if not target_tenant_id:
                form_handler.add_error('target_tenant_id', 'Target tenant is required for global admin')

        # Validate required fields
        required_fields = ['name', 'secret_type', 'value']
        logger.info(f"Validating required fields: {required_fields}")
        form_handler.validate_required_fields(required_fields)

        # Check for any validation errors
        if form_handler.has_errors():
            logger.error(f"Form validation errors: {form_handler.errors}")
            logger.error(f"First error: {form_handler.get_first_error()}")

            # Get tenant data for form redisplay
            available_tenants = []
            if global_admin:
                secrets_service = SecretsManagementService(db, tenant_id)
                available_tenants = await secrets_service.get_available_tenants_for_secrets_forms()

            # Return the form with error messages
            return templates.TemplateResponse("administration/secrets/partials/form.html", {
                "request": request,
                "secret": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data,
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "secret_types": [t.value for t in SecretType]
            }, status_code=400)

        # Handle form-specific data processing
        tags = form_handler.get_list_values("tags")
        is_active = form_handler.form_data.get("is_active") == "true"

        logger.info(f"Tags: {tags}, Is Active: {is_active}")

        # Create SecretCreate schema
        secret_data = SecretCreate(
            name=form_handler.form_data.get("name"),
            description=form_handler.form_data.get("description"),
            secret_type=SecretType(form_handler.form_data.get("secret_type")),
            value=form_handler.form_data.get("value"),
            is_active=is_active,
            tags=tags
        )

        logger.info(f"Secret data to create: {secret_data}")

        # Create secret with optional cross-tenant assignment
        secrets_service = SecretsManagementService(db, tenant_id)
        new_secret = await secrets_service.create_secret(
            secret_data=secret_data,
            created_by_user=current_user,
            target_tenant_id=target_tenant_id
        )
        await commit_transaction(db, "create_secret")
        logger.info(f"Secret created successfully: {new_secret.id}")
        return create_success_response()

    except ValueError as e:
        # Handle service-layer validation errors (duplicates, validation)
        await db.rollback()
        error_message = str(e)
        logger.error(f"Service validation error: {error_message}")

        # Check if current user is global admin for form context
        global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Get tenant data for form redisplay
        available_tenants = []
        if global_admin:
            secrets_service = SecretsManagementService(db, tenant_id)
            available_tenants = await secrets_service.get_available_tenants_for_secrets_forms()

        # Map service errors for consistent response
        errors = {}
        if "name" in error_message.lower():
            errors["name"] = [error_message]
        elif "value" in error_message.lower():
            errors["value"] = [error_message]
        else:
            errors["general"] = [error_message]

        # Return form with error messages
        return templates.TemplateResponse("administration/secrets/partials/form.html", {
            "request": request,
            "secret": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {},
            "is_global_admin": global_admin,
            "available_tenants": available_tenants,
            "secret_types": [t.value for t in SecretType]
        }, status_code=400)

    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to create secret via form")

        # Check if current user is global admin for form context
        global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Get tenant data for form redisplay
        available_tenants = []
        if global_admin:
            secrets_service = SecretsManagementService(db, tenant_id)
            available_tenants = await secrets_service.get_available_tenants_for_secrets_forms()

        errors = {"general": ["An unexpected error occurred while creating the secret"]}
        return templates.TemplateResponse("administration/secrets/partials/form.html", {
            "request": request,
            "secret": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {},
            "is_global_admin": global_admin,
            "available_tenants": available_tenants,
            "secret_types": [t.value for t in SecretType]
        }, status_code=500)


@router.post("/api", response_model=SecretResponse)
async def create_secret_api(
    secret_data: SecretCreate,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Create a new secret via API (JSON)."""
    try:
        secret = await secrets_service.create_secret(
            secret_data=secret_data,
            created_by_user=current_user
        )
        await db.commit()
        return secret

    except ValueError as e:
        logger.warning("Invalid secret data via API", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create secret via API")
        raise HTTPException(status_code=500, detail=f"Failed to create secret: {str(e)}")


@router.patch("/{secret_id}/field")
async def update_secret_field(
    secret_id: int,
    field_update: dict = Body(...),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Update a single field of a secret."""
    try:
        field = field_update.get("field")
        value = field_update.get("value")

        # Coerce known field types coming from the client
        if field in ['is_active'] and isinstance(value, str):
            value = value.lower() == 'true'

        # Handle tags field - if it's a JSON string, parse it
        if field == 'tags' and isinstance(value, str) and value:
            if value.startswith('[') or value.startswith('{'):
                try:
                    import json
                    value = json.loads(value)
                except Exception:
                    pass

        updated_secret = await secrets_service.update_secret_field(secret_id, field, value)
        if not updated_secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update secret field {field}")
        raise HTTPException(status_code=500, detail="Failed to update secret field")


@router.put("/{secret_id}")
async def update_secret_api(
    secret_id: int,
    update_data: SecretUpdate,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Update a secret via API (JSON)."""
    try:
        secret = await secrets_service.update_secret(
            secret_id=secret_id,
            update_data=update_data,
            updated_by_user=current_user
        )

        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()
        return secret.model_dump()

    except ValueError as e:
        logger.warning("Invalid secret update data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update secret via API")
        raise HTTPException(status_code=500, detail=f"Failed to update secret: {str(e)}")


@router.delete("/{secret_id}")
@router.post("/{secret_id}/delete")
async def delete_secret(
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
    db: AsyncSession = Depends(get_db),
):
    """Delete a secret by ID. Accepts both DELETE and POST for frontend compatibility."""
    try:
        success = await secrets_service.delete_secret(
            secret_id=secret_id,
            deleted_by_user=current_user
        )

        if not success:
            raise HTTPException(status_code=404, detail="Secret not found")

        await db.commit()
        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete secret")
        raise HTTPException(status_code=500, detail=f"Failed to delete secret: {str(e)}")


@router.get("/{secret_id}", response_model=SecretResponse)
async def get_secret(
    secret_id: int,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    secrets_service: SecretsManagementService = Depends(get_secrets_service),
):
    """Get secret metadata by ID."""
    try:
        secret = await secrets_service.get_secret_by_id(secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")

        return secret

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get secret {secret_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret")
