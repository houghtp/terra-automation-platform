from fastapi import APIRouter, Depends, Request, Form, HTTPException, Body, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.templates import templates
from app.features.core.database import get_db
from app.features.core.validation import FormHandler, ValidationError
from app.features.administration.users.services import UserManagementService
from app.features.administration.users.models import (
    UserCreate, UserUpdate, UserResponse, UserSearchFilter,
    UserStatus, UserRole
)
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from typing import List, Optional
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/administration/users", tags=["users"])

@router.patch("/{user_id}/field")
async def update_user_field_api(user_id: str, field_update: dict = Body(...), db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    field = field_update.get("field")
    value = field_update.get("value")

    # Coerce known field types coming from the client
    if field in ['enabled', 'is_active'] and isinstance(value, str):
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

    service = UserManagementService(db, tenant)
    updated_user = await service.update_user_field(user_id, field, value)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.commit()  # Route handles transaction commit
    return {"success": True}

# --- UI ROUTES (Jinja + HTMX) ---

# List page
@router.get("/", response_class=HTMLResponse)
async def user_list(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("administration/users/list.html", {"request": request})

# Modal form (add/edit)
@router.get("/partials/form", response_class=HTMLResponse)
async def user_form_partial(request: Request, user_id: str = None, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    user = None
    if user_id:
        service = UserManagementService(db, tenant)
        user = await service.get_user_by_id(user_id)

    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": user
    })

# Modal edit endpoint
@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(request: Request, user_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = UserManagementService(db, tenant)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse("administration/users/partials/form.html", {
        "request": request,
        "user": user
    })

# Create user
@router.post("/")
async def user_create(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Create a new user via form submission."""
    try:
        logger.info("Starting user creation process")

        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        logger.info(f"Raw form data: {dict(form_handler.raw_form)}")
        logger.info(f"Parsed form data: {form_handler.form_data}")

        # Validate required fields
        required_fields = ['name', 'email', 'password', 'confirm_password']
        logger.info(f"Validating required fields: {required_fields}")
        form_handler.validate_required_fields(required_fields)

        # Validate email format
        form_handler.validate_email_field('email')

        # Validate password fields (complexity + confirmation)
        form_handler.validate_password_fields('password', 'confirm_password')

        # Check for any validation errors
        if form_handler.has_errors():
            logger.error(f"Form validation errors: {form_handler.errors}")
            logger.error(f"First error: {form_handler.get_first_error()}")
            # Return the form with error messages
            return templates.TemplateResponse("administration/users/partials/form.html", {
                "request": request,
                "user": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        # Handle form-specific data processing
        tags = form_handler.get_list_values("tags")
        enabled = form_handler.form_data.get("enabled") == "true"

        logger.info(f"Tags: {tags}, Enabled: {enabled}")

        # Create UserCreate schema
        user_data = UserCreate(
            name=form_handler.form_data.get("name"),
            email=form_handler.form_data.get("email"),
            password=form_handler.form_data.get("password"),
            confirm_password=form_handler.form_data.get("confirm_password"),
            description=form_handler.form_data.get("description"),
            status=UserStatus(form_handler.form_data.get("status", "active")),
            role=UserRole(form_handler.form_data.get("role", "user")),
            enabled=enabled,
            tags=tags
        )

        logger.info(f"User data to create: {user_data}")

        # Create user using service
        service = UserManagementService(db, tenant)
        user = await service.create_user(user_data)
        await db.commit()
        logger.info(f"User created successfully: {user.id}")
        return Response(status_code=204)

    except ValueError as e:
        # Handle service-layer validation errors (password complexity, duplicates)
        await db.rollback()
        error_message = str(e)
        logger.error(f"Service validation error: {error_message}")

        # Map service errors to form handler for consistent response
        errors = {}
        if "password" in error_message.lower():
            errors["password"] = [error_message]
        elif "email" in error_message.lower():
            errors["email"] = [error_message]
        else:
            errors["general"] = [error_message]

        # Return the form with error messages
        return templates.TemplateResponse("administration/users/partials/form.html", {
            "request": request,
            "user": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=400)

    except Exception as e:
        # Catch any unexpected errors
        await db.rollback()
        logger.exception(f"Unexpected error during user creation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# Update user
@router.put("/{user_id}")
async def user_edit(request: Request, user_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Update a user via form submission."""
    form = await request.form()

    # Handle tags - getlist() gets multiple values from multi-select
    tags = form.getlist("tags") if form.getlist("tags") else []

    # Handle enabled toggle - checkbox will send 'true' if checked, nothing if unchecked
    enabled = form.get("enabled") == "true"

    # Create update schema
    user_data = UserUpdate(
        name=form.get("name") if form.get("name") else None,
        email=form.get("email") if form.get("email") else None,
        description=form.get("description") if form.get("description") else None,
        status=UserStatus(form.get("status")) if form.get("status") else None,
        role=UserRole(form.get("role")) if form.get("role") else None,
        enabled=enabled,
        tags=tags
    )

    service = UserManagementService(db, tenant)
    updated_user = await service.update_user(user_id, user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.commit()  # Route handles transaction commit
    # Return empty response - client will handle table refresh and modal close
    return Response(status_code=204)

# --- API ROUTES (Tabulator) ---

# List content partial (for HTMX table refresh)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def user_list_partial(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = UserManagementService(db, tenant)
    filters = UserSearchFilter()
    users = await service.list_users(filters)
    return templates.TemplateResponse("administration/users/partials/list_content.html", {"request": request, "users": users})

# API endpoint for Tabulator
@router.get("/api", response_class=JSONResponse)
async def get_users_api(db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = UserManagementService(db, tenant)
    filters = UserSearchFilter()
    users = await service.list_users(filters)
    # Return array directly for Tabulator compatibility
    return [user.model_dump() for user in users]

# Delete user (accept both DELETE and POST for compatibility)
@router.delete("/{user_id}/delete")
@router.post("/{user_id}/delete")
async def user_delete_api(user_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Delete a user by ID. Accepts both DELETE and POST for frontend compatibility."""
    service = UserManagementService(db, tenant)
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()  # Route handles transaction commit
    return {"status": "ok"}

# HTMX Validation Endpoints
@router.post("/validate/email", response_class=HTMLResponse)
async def validate_email_field(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate email field in real-time via HTMX."""
    try:
        # Check if email format is valid using existing validation
        from app.features.core.validation import FormValidator
        validator = FormValidator()

        if not email or not email.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Email is required</span>')

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid email format</span>')

        # Check for duplicate email in tenant
        service = UserManagementService(db, tenant)
        existing = await service.get_user_by_email(email)
        if existing:
            return HTMLResponse('<span class="invalid-feedback d-block">Email already exists</span>')

        # Valid - return empty or success message
        return HTMLResponse('<span class="valid-feedback d-block">Email is available</span>')

    except Exception as e:
        logger.error(f"Email validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating email</span>')

@router.post("/validate/password", response_class=HTMLResponse)
async def validate_password_field(request: Request, password: str = Form(...)):
    """Validate password complexity in real-time via HTMX."""
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
        logger.error(f"Password validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating password</span>')

@router.post("/validate/confirm-password", response_class=HTMLResponse)
async def validate_confirm_password_field(request: Request, password: str = Form(...), confirm_password: str = Form(...)):
    """Validate password confirmation in real-time via HTMX."""
    try:
        if not confirm_password:
            return HTMLResponse('<span class="invalid-feedback d-block">Please confirm your password</span>')

        if password != confirm_password:
            return HTMLResponse('<span class="invalid-feedback d-block">Passwords do not match</span>')

        # Valid confirmation
        return HTMLResponse('<span class="valid-feedback d-block">Passwords match</span>')

    except Exception as e:
        logger.error(f"Password confirmation validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating password confirmation</span>')

@router.post("/validate/name", response_class=HTMLResponse)
async def validate_name_field(request: Request, name: str = Form(...)):
    """Validate name field in real-time via HTMX."""
    try:
        if not name or not name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Name is required</span>')

        if len(name.strip()) < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Name must be at least 2 characters</span>')

        # Valid name
        return HTMLResponse('<span class="valid-feedback d-block">Name looks good</span>')

    except Exception as e:
        logger.error(f"Name validation error: {e}")
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating name</span>')
