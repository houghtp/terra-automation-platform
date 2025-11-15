# Gold Standard Route Imports - Tenants Forms
from app.features.core.route_imports import (
    APIRouter, Depends, Request, Form, HTTPException, Response,
    HTMLResponse, AsyncSession, get_db, templates, FormHandler,
    Optional, get_logger
)
from app.features.administration.tenants.services import TenantManagementService
from app.features.auth.dependencies import get_global_admin_user
from app.features.auth.models import User
from app.features.administration.tenants.schemas import TenantCreate, TenantUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["tenants-forms"])

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
        from fastapi.responses import JSONResponse
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

# --- HTMX VALIDATION ENDPOINTS ---

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(request: Request, name: str = Form(...), tenant_id: Optional[str] = Form(None), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Validate tenant name field in real-time via HTMX."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name is required</span>')

        name = name.strip()

        if len(name) < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name must be at least 2 characters</span>')

        if len(name) > 255:
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name must be less than 255 characters</span>')

        # Check for duplicate tenant name (global scope, excluding current if editing)
        service = TenantManagementService(db)
        existing = await service.get_tenant_by_name(name)

        if existing and (not tenant_id or existing.id != tenant_id):
            return HTMLResponse('<span class="invalid-feedback d-block">Tenant name already exists</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Tenant name is available</span>')

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
