# Use centralized imports for consistency
from app.features.core.route_imports import *
from app.features.administration.users.services import UserManagementService
from app.features.administration.users.models import (
    UserSearchFilter, UserCreate, UserUpdate, UserStatus, UserRole
)

logger = get_logger(__name__)

router = APIRouter(tags=["users-crud"])

# --- TABULATOR CRUD ROUTES ---

@router.patch("/{user_id}/field")
async def update_user_field_api(
    user_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Update single user field using gold standard patterns."""
    try:
        field = field_update.get("field")
        value = field_update.get("value")

        # Standardized field type coercion
        if field in ['enabled', 'is_active'] and isinstance(value, str):
            value = value.lower() == 'true'

        # Handle tags field JSON parsing
        if field == 'tags' and isinstance(value, str) and value:
            if value.startswith('[') or value.startswith('{'):
                try:
                    import json
                    value = json.loads(value)
                except Exception:
                    pass  # Keep string value if parse fails

        service = UserManagementService(db, tenant)
        updated_user = await service.update_user_field(user_id, field, value)

        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")

        await commit_transaction(db, "update_user_field")
        return {"success": True}

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        handle_route_error("update_user_field_api", e, user_id=user_id, field=field)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user field")

# List content partial (for HTMX table refresh)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def user_list_partial(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get users list partial using standardized patterns."""
    try:
        service = UserManagementService(db, tenant)
        filters = UserSearchFilter()

        # Use centralized global admin check
        if is_global_admin(current_user):
            users = await service.list_users_global(filters)
        else:
            users = await service.list_users(filters)

        return templates.TemplateResponse(
            "administration/users/partials/list_content.html",
            {"request": request, "users": users}
        )

    except Exception as e:
        handle_route_error("user_list_partial", e)
        raise HTTPException(status_code=500, detail="Failed to load user list")

# API endpoint for Tabulator
@router.get("/api/list", response_class=JSONResponse)
async def get_users_api(
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get users list for Tabulator API using standardized patterns."""
    try:
        service = UserManagementService(db, tenant)
        filters = UserSearchFilter()

        # Use centralized global admin check
        if is_global_admin(current_user):
            users = await service.list_users_global(filters)
        else:
            users = await service.list_users(filters)

        # Standardized response formatting
        result = []
        for user in users:
            if hasattr(user, 'model_dump'):
                result.append(user.model_dump())
            else:
                result.append(user)  # Already a dict

        return result

    except Exception as e:
        handle_route_error("get_users_api", e)
        raise HTTPException(status_code=500, detail="Failed to fetch users")

# Delete user (accept both DELETE and POST for compatibility)
@router.delete("/{user_id}/delete")
@router.post("/{user_id}/delete")
async def user_delete_api(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Delete user using gold standard patterns."""
    try:
        service = UserManagementService(db, tenant)
        success = await service.delete_user(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        await commit_transaction(db, "delete_user")
        return {"status": "ok"}

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        handle_route_error("user_delete_api", e, user_id=user_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")

# --- FORM SUBMISSION CRUD OPERATIONS ---

# Create user
@router.post("/")
async def user_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Create user using gold standard patterns."""
    try:
        logger.info("Starting user creation process")

        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        # Use centralized global admin check
        global_admin = is_global_admin(current_user)
        target_tenant_id = None

        if global_admin:
            # For global admins, target_tenant_id is required
            target_tenant_id = form_handler.form_data.get("target_tenant_id")
            if not target_tenant_id:
                form_handler.add_error('target_tenant_id', 'Target tenant is required for global admin')

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

            # Get tenant data for form redisplay
            available_tenants = []
            if global_admin:
                service = UserManagementService(db, tenant)
                available_tenants = await service.get_available_tenants_for_user_forms()

            # Return the form with error messages
            return templates.TemplateResponse("administration/users/partials/form.html", {
                "request": request,
                "user": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data,
                "is_global_admin": global_admin,
                "available_tenants": available_tenants
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

        # Create user with optional cross-tenant assignment
        service = UserManagementService(db, tenant)
        user = await service.create_user(user_data, target_tenant_id)
        await commit_transaction(db, "create_user")
        logger.info(f"User created successfully: {user.id}")
        return create_success_response()

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

        # Get tenant data for form redisplay
        available_tenants = []
        global_admin = is_global_admin(current_user)
        if global_admin:
            service = UserManagementService(db, tenant)
            available_tenants = await service.get_available_tenants_for_user_forms()

        # Return the form with error messages
        return templates.TemplateResponse("administration/users/partials/form.html", {
            "request": request,
            "user": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {},
            "is_global_admin": global_admin,
            "available_tenants": available_tenants
        }, status_code=400)

    except Exception as e:
        # Standardized unexpected error handling
        await db.rollback()
        handle_route_error("user_create", e)
        return create_error_response("Internal server error", status_code=500)

# Update user
@router.put("/{user_id}")
async def user_edit(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Update user using gold standard patterns."""
    try:
        form = await request.form()

        # Handle tags - getlist() gets multiple values from multi-select
        tags = form.getlist("tags") if form.getlist("tags") else []

        # Handle enabled toggle - checkbox will send 'true' if checked, nothing if unchecked
        enabled = form.get("enabled") == "true"

        # Use centralized global admin check
        global_admin = is_global_admin(current_user)
        target_tenant_id = form.get("target_tenant_id") if global_admin else None

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

        # Handle tenant reassignment for global admins
        if global_admin and target_tenant_id:
            # Update tenant_id directly if global admin is changing it
            updated_user = await service.update_user_field_global(user_id, "tenant_id", target_tenant_id)
            if not updated_user:
                raise HTTPException(status_code=404, detail="User not found")

        # Apply other updates
        if global_admin:
            updated_user = await service.update_user_global(user_id, user_data)
        else:
            updated_user = await service.update_user(user_id, user_data)

        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")

        await commit_transaction(db, "update_user")
        return create_success_response()

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        handle_route_error("user_edit", e, user_id=user_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")
