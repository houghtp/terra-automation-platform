from fastapi import APIRouter, Depends, Request, Form, HTTPException, Body, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.templates import templates
from app.features.core.database import get_db
from app.features.core.validation import FormHandler, ValidationError
from app.features.administration.tenants.services import TenantManagementService
from app.features.auth.dependencies import get_global_admin_user
from app.features.auth.models import User
from app.features.administration.tenants.models import (
    TenantCreate, TenantUpdate, TenantResponse, TenantStats,
    TenantSearchFilter, TenantUserResponse,
    UserTenantAssignment, TenantStatus, TenantTier
)
from typing import List, Optional
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/administration/tenants", tags=["tenants"])

@router.patch("/{tenant_id}/field")
async def update_tenant_field_api(tenant_id: int, field_update: dict = Body(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    field = field_update.get("field")
    value = field_update.get("value")

    service = TenantManagementService(db)

    # Create update data with just the field being updated
    update_data = TenantUpdate()
    setattr(update_data, field, value)

    try:
        result = await service.update_tenant(tenant_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Tenant not found")

        await db.commit()  # Route handles transaction commit
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update tenant: {str(e)}")

# --- UI ROUTES (Jinja + HTMX) ---

# List page
@router.get("/", response_class=HTMLResponse)
async def tenant_list(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    return templates.TemplateResponse("administration/tenants/list.html", {"request": request})

# Modal form (add/edit)
@router.get("/partials/form", response_class=HTMLResponse)
async def tenant_form_partial(request: Request, tenant_id: int = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    tenant = None
    if tenant_id:
        service = TenantManagementService(db)
        tenant = await service.get_tenant_by_id(tenant_id)

    return templates.TemplateResponse("administration/tenants/partials/form.html", {
        "request": request,
        "tenant": tenant
    })

# Modal edit endpoint
@router.get("/{tenant_id}/edit", response_class=HTMLResponse)
async def tenant_edit_form(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    service = TenantManagementService(db)
    tenant = await service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return templates.TemplateResponse("administration/tenants/partials/form.html", {
        "request": request,
        "tenant": tenant
    })

# Create tenant
@router.post("/")
async def tenant_create(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Create a new tenant via form submission."""
    try:
        logger.info("Starting tenant creation process")

        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        logger.info(f"Parsed form data: {form_handler.form_data}")

        # Validate required fields
        required_fields = ['name']
        form_handler.validate_required_fields(required_fields)

        # Check for any validation errors
        if form_handler.has_errors():
            logger.error(f"Form validation errors: {form_handler.errors}")
            logger.error(f"First error: {form_handler.get_first_error()}")
            # Return the form with error messages
            return templates.TemplateResponse("administration/tenants/partials/form.html", {
                "request": request,
                "tenant": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        # Handle form-specific data processing
        features = {}
        for key, value in form_handler.form_data.items():
            if key.startswith('features[') and key.endswith(']'):
                feature_key = key[9:-1]  # Remove 'features[' and ']'
                features[feature_key] = value == 'on'

        # Handle optional fields properly - convert empty strings to None
        contact_email = form_handler.form_data.get("contact_email")
        contact_name = form_handler.form_data.get("contact_name")
        website = form_handler.form_data.get("website")
        description = form_handler.form_data.get("description")

        data = {
            "name": form_handler.form_data.get("name"),
            "description": description if description and description.strip() else None,
            "status": form_handler.form_data.get("status", "active"),
            "tier": form_handler.form_data.get("tier", "free"),
            "contact_email": contact_email if contact_email and contact_email.strip() else None,
            "contact_name": contact_name if contact_name and contact_name.strip() else None,
            "website": website if website and website.strip() else None,
            "max_users": int(form_handler.form_data.get("max_users", 10)),
            "features": features
        }

        logger.info(f"Tenant data to create: {data}")

        # Check for duplicate name
        service = TenantManagementService(db)
        if data["name"]:
            existing = await service.get_tenant_by_name(data["name"])
            if existing:
                form_handler.add_error("name", "Tenant name already exists")
                # Return the form with error messages
                return templates.TemplateResponse("administration/tenants/partials/form.html", {
                    "request": request,
                    "tenant": None,
                    "errors": form_handler.errors,
                    "form_data": form_handler.form_data
                }, status_code=400)

        # Create tenant
        logger.info(f"Creating tenant")
        tenant_data = TenantCreate(**data)
        tenant = await service.create_tenant(tenant_data)
        await db.commit()
        logger.info(f"Tenant created successfully: {tenant.id}")
        return Response(status_code=204)

    except ValueError as e:
        # Handle service-layer validation errors (email validation, duplicates)
        await db.rollback()
        error_message = str(e)
        logger.error(f"Service validation error: {error_message}")

        # Map service errors to form handler for consistent response
        errors = {}
        if "contact_email" in error_message.lower() or "email" in error_message.lower():
            errors["contact_email"] = [error_message]
        elif "name" in error_message.lower():
            errors["name"] = [error_message]
        else:
            errors["general"] = [error_message]

        # Return the form with error messages
        return templates.TemplateResponse("administration/tenants/partials/form.html", {
            "request": request,
            "tenant": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=400)

    except Exception as e:
        # Catch any unexpected errors
        await db.rollback()
        logger.exception(f"Unexpected error during tenant creation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# Update tenant
@router.put("/{tenant_id}")
async def tenant_edit(request: Request, tenant_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Update a tenant via form submission."""
    form = await request.form()

    # Parse feature flags from form
    features = {}
    for key, value in form.items():
        if key.startswith('features[') and key.endswith(']'):
            feature_key = key[9:-1]  # Remove 'features[' and ']'
            features[feature_key] = value == 'on'

    # Handle optional fields properly - convert empty strings to None
    contact_email = form.get("contact_email")
    contact_name = form.get("contact_name")
    website = form.get("website")
    description = form.get("description")
    name = form.get("name")

    data = {
        "name": name if name and name.strip() else None,
        "description": description if description and description.strip() else None,
        "status": form.get("status"),
        "tier": form.get("tier"),
        "contact_email": contact_email if contact_email and contact_email.strip() else None,
        "contact_name": contact_name if contact_name and contact_name.strip() else None,
        "website": website if website and website.strip() else None,
        "max_users": int(form.get("max_users", 10)) if form.get("max_users") else None,
        "features": features
    }

    service = TenantManagementService(db)
    update_data = TenantUpdate()
    for key, value in data.items():
        if value is not None:
            setattr(update_data, key, value)

    updated_tenant = await service.update_tenant(tenant_id, update_data)
    if not updated_tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.commit()  # Route handles transaction commit
    # Return empty response - client will handle table refresh and modal close
    return Response(status_code=204)

# --- API ROUTES (Tabulator) ---

# List content partial (for HTMX table refresh)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def tenant_list_partial(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    service = TenantManagementService(db)
    filters = TenantSearchFilter()
    tenants = await service.list_tenants(filters)
    return templates.TemplateResponse("administration/tenants/partials/list_content.html", {"request": request, "tenants": tenants})

# API endpoint for Tabulator
@router.get("/api", response_class=JSONResponse)
async def get_tenants_api(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    service = TenantManagementService(db)
    filters = TenantSearchFilter()
    tenants = await service.list_tenants(filters)
    # Return array directly for Tabulator compatibility
    return [tenant.model_dump() for tenant in tenants]

# Delete tenant (accept both DELETE and POST for compatibility)
@router.delete("/{tenant_id}/delete")
@router.post("/{tenant_id}/delete")
async def tenant_delete_api(tenant_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Delete a tenant by ID. Accepts both DELETE and POST for frontend compatibility."""
    service = TenantManagementService(db)
    success = await service.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.commit()  # Route handles transaction commit
    return {"status": "ok"}

# HTMX Validation Endpoints
@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(request: Request, name: str = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Validate tenant name field in real-time via HTMX."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name is required</span>')

        if len(name.strip()) < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name must be at least 2 characters</span>')

        # Check for duplicate tenant name (global scope)
        service = TenantManagementService(db)
        existing = await service.get_tenant_by_name(name.strip())
        if existing:
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name already exists</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block">Tenant name is available</span>')

    except Exception as e:
        logger.error(f"Name validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating tenant name</span>')

@router.post("/validate/contact_email", response_class=HTMLResponse)
async def validate_contact_email_field(request: Request, contact_email: str = Form(...)):
    """Validate contact email field in real-time via HTMX."""
    try:
        if not contact_email or not contact_email.strip():
            # Contact email is optional, so no error for empty
            return HTMLResponse('')

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, contact_email):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid email format</span>')

        # Valid email
        return HTMLResponse('<span class="valid-feedback d-block">Email format is valid</span>')

    except Exception as e:
        logger.error(f"Contact email validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating email</span>')
