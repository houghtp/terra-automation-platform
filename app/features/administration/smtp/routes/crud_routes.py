# Gold Standard Route Imports - SMTP CRUD
from app.features.core.route_imports import (
    # Core FastAPI components
    APIRouter, Depends,
    # Database and dependencies
    AsyncSession, get_db,
    # Tenant and auth
    tenant_dependency, get_current_user, get_global_admin_user, User, is_global_admin,
    # Request/Response types
    Request, HTTPException, Body, Response,
    # Response types
    HTMLResponse, JSONResponse,
    # Template rendering
    templates,
    # Logging and error handling
    get_logger, handle_route_error,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Form handling
    FormHandler
)

from app.features.administration.smtp.services import SMTPConfigurationService
from app.features.administration.smtp.models import SMTPStatus
from app.features.administration.smtp.schemas import (
    SMTPSearchFilter,
    SMTPConfigurationCreate,
    SMTPConfigurationUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["smtp-crud"])

# --- TABULATOR CRUD ROUTES ---

@router.patch("/{config_id}/field")
async def update_smtp_field_api(config_id: str, field_update: dict = Body(...), db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    field = field_update.get("field")
    value = field_update.get("value")

    # Coerce known field types coming from the client
    if field in ['enabled', 'is_active', 'use_tls', 'use_ssl', 'is_verified'] and isinstance(value, str):
        # Handle boolean fields from toggle switches
        value = value.lower() == 'true'

    # Handle port field
    if field == 'port' and isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Port must be a number")

    # Handle tags field - if it's a JSON string, parse it
    if field == 'tags' and isinstance(value, str) and value:
        if value.startswith('[') or value.startswith('{'):
            try:
                import json
                value = json.loads(value)
            except Exception:
                # keep string value if parse fails
                pass

    service = SMTPConfigurationService(db, tenant_id)
    updated_config = await service.update_smtp_field(config_id, field, value, updated_by_user=current_user)
    if not updated_config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    await db.commit()  # Route handles transaction commit
    return {"success": True}

# List content (for HTMX updates)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def smtp_list_content(request: Request, search: str = "", status: str = "", db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Get the list content partial for HTMX updates."""
    service = SMTPConfigurationService(db, tenant_id)

    # Build search filters
    filters = SMTPSearchFilter()
    if search:
        filters.search = search
    if status and status != "all":
        filters.status = SMTPStatus(status)

    configurations = await service.list_smtp_configurations(filters)

    return templates.TemplateResponse("administration/smtp/partials/list_content.html", {
        "request": request,
        "configurations": configurations
    })

# API endpoint for Tabulator
@router.get("/api/list", response_class=JSONResponse)
async def get_smtp_configurations_api(search: str = "", status: str = "", db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Get SMTP configurations as JSON for Tabulator."""
    service = SMTPConfigurationService(db, tenant_id)

    # Build search filters
    filters = SMTPSearchFilter()
    if search:
        filters.search = search
    if status and status != "all":
        filters.status = SMTPStatus(status)

    # Global admins see all configurations across all tenants (if service supports it)
    if is_global_admin(current_user):
        # For now, use regular service (TODO: implement global service method if needed)
        configurations = await service.list_smtp_configurations(filters)
    else:
        configurations = await service.list_smtp_configurations(filters)

    # Return array directly for Tabulator compatibility
    # Handle both Pydantic models and dicts consistently
    result = []
    for config in configurations:
        if hasattr(config, 'model_dump'):
            result.append(config.model_dump())
        else:
            result.append(config)  # Already a dict

    # If global admin, add tenant_name to each config
    if is_global_admin(current_user):
        from app.features.administration.tenants.services import TenantManagementService
        tenant_service = TenantManagementService(service.db)

        # Get all tenants
        tenants = await tenant_service.list_tenants()

        # Build tenant map - handle both string and TenantResponse objects
        tenant_map = {}
        for tenant in tenants:
            # Handle both dict and TenantResponse objects
            if hasattr(tenant, 'id'):
                tenant_id = tenant.id
                tenant_name = tenant.name
            else:
                tenant_id = tenant.get('id')
                tenant_name = tenant.get('name')
            tenant_map[str(tenant_id)] = tenant_name

        logger.info(f"Built tenant map with {len(tenant_map)} tenants: {tenant_map}")

        # Add tenant_name to each config
        for config in result:
            config_tenant_id = str(config.get('tenant_id'))
            config['tenant_name'] = tenant_map.get(config_tenant_id, f'Unknown ({config_tenant_id})')
            logger.info(f"Config {config.get('name')} has tenant_id: {config_tenant_id}, mapped to: {config['tenant_name']}")

    return result

# Delete SMTP configuration (accept both DELETE and POST for compatibility)
@router.delete("/{config_id}/delete")
@router.post("/{config_id}/delete")
async def smtp_delete_api(config_id: str, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Delete SMTP configuration by ID. Accepts both DELETE and POST for frontend compatibility."""
    service = SMTPConfigurationService(db, tenant_id)

    # Get config name for response message
    config = await service.get_configuration_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    config_name = config.name
    success = await service.delete_smtp_configuration(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    await db.commit()
    return {"status": "ok"}

# Create SMTP configuration
@router.post("/")
async def smtp_create(request: Request, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Create a new SMTP configuration via form submission."""
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
        required_fields = ['name', 'host', 'port', 'from_email']
        logger.info(f"Validating required fields: {required_fields}")
        form_handler.validate_required_fields(required_fields)

        # Validate email format
        form_handler.validate_email_field('from_email')

        # Validate password fields (complexity + confirmation)
        form_handler.validate_password_fields('password', 'confirm_password')

        # Check for any validation errors
        if form_handler.has_errors():
            logger.error(f"Form validation errors: {form_handler.errors}")
            logger.error(f"First error: {form_handler.get_first_error()}")

            # Get tenant data for form redisplay
            available_tenants = []
            if global_admin:
                service = SMTPConfigurationService(db, tenant_id)
                available_tenants = await service.get_available_tenants_for_smtp_forms()

            # Return the form with error messages
            return templates.TemplateResponse("administration/smtp/partials/form.html", {
                "request": request,
                "config": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data,
                "is_global_admin": global_admin,
                "available_tenants": available_tenants
            }, status_code=400)

        # Handle form-specific data processing
        tags = form_handler.get_list_values("tags")
        enabled = form_handler.form_data.get("enabled") == "true"
        use_tls = form_handler.form_data.get("use_tls") == "true"
        use_ssl = form_handler.form_data.get("use_ssl") == "true"

        # Convert port to integer
        try:
            port = int(form_handler.form_data.get("port", "587"))
        except ValueError:
            form_handler.add_error('port', 'Port must be a valid number')
            # Return form with error
            available_tenants = []
            if global_admin:
                service = SMTPConfigurationService(db, tenant_id)
                available_tenants = await service.get_available_tenants_for_smtp_forms()
            return templates.TemplateResponse("administration/smtp/partials/form.html", {
                "request": request,
                "config": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data,
                "is_global_admin": global_admin,
                "available_tenants": available_tenants
            }, status_code=400)

        logger.info(f"Tags: {tags}, Enabled: {enabled}")

        # Create SMTPConfigurationCreate schema
        config_data = SMTPConfigurationCreate(
            name=form_handler.form_data.get("name"),
            description=form_handler.form_data.get("description"),
            host=form_handler.form_data.get("host"),
            port=port,
            use_tls=use_tls,
            use_ssl=use_ssl,
            username=form_handler.form_data.get("username"),
            password=form_handler.form_data.get("password"),
            confirm_password=form_handler.form_data.get("confirm_password"),
            from_email=form_handler.form_data.get("from_email"),
            from_name=form_handler.form_data.get("from_name"),
            reply_to=form_handler.form_data.get("reply_to") or None,
            status=SMTPStatus(form_handler.form_data.get("status", "inactive")),
            enabled=enabled,
            tags=tags
        )

        logger.info(f"SMTP config data to create: {config_data}")

        # Create configuration with optional cross-tenant assignment
        service = SMTPConfigurationService(db, tenant_id)
        new_config = await service.create_smtp_configuration(config_data, created_by_user=current_user, target_tenant_id=target_tenant_id)
        await commit_transaction(db, "create_smtp_configuration")
        logger.info(f"SMTP configuration created successfully: {new_config.id}")
        return create_success_response()

    except ValueError as e:
        # Handle service-layer validation errors (password complexity, duplicates)
        await db.rollback()
        error_message = str(e)
        logger.error(f"Service validation error: {error_message}")

        # Check if current user is global admin for form context
        global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Get tenant data for form redisplay
        available_tenants = []
        if global_admin:
            service = SMTPConfigurationService(db, tenant_id)
            available_tenants = await service.get_available_tenants_for_smtp_forms()

        # Map service errors for consistent response
        errors = {}
        if "name" in error_message.lower():
            errors["name"] = [error_message]
        elif "email" in error_message.lower():
            errors["from_email"] = [error_message]
        elif "password" in error_message.lower():
            errors["password"] = [error_message]
        else:
            errors["general"] = [error_message]

        # Return form with error messages
        return templates.TemplateResponse("administration/smtp/partials/form.html", {
            "request": request,
            "config": None,
            "errors": errors,
            "form_data": form_handler.form_data if 'form_handler' in locals() else {},
            "is_global_admin": global_admin,
            "available_tenants": available_tenants
        }, status_code=400)

    except Exception as e:
        # Catch any unexpected errors
        await db.rollback()
        logger.exception(f"Unexpected error during SMTP configuration creation: {str(e)}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# Update SMTP configuration
@router.put("/{config_id}")
async def smtp_update(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant_id: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Update an existing SMTP configuration via form submission."""
    try:
        logger.info(f"Starting SMTP configuration update process for ID: {config_id}")

        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        logger.info(f"Raw form data: {dict(form_handler.raw_form)}")
        logger.info(f"Parsed form data: {form_handler.form_data}")

        # Validate required fields
        required_fields = ['name', 'host', 'username', 'from_email', 'from_name']
        logger.info(f"Validating required fields: {required_fields}")
        form_handler.validate_required_fields(required_fields)

        # Validate email format
        form_handler.validate_email_field('from_email')
        if form_handler.form_data.get('reply_to'):
            form_handler.validate_email_field('reply_to')

        # Validate password fields if provided
        password = form_handler.form_data.get("password")
        if password:
            form_handler.validate_password_fields('password', 'confirm_password')

        # Validate port
        port_str = form_handler.form_data.get("port", "587")
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                form_handler.add_error("port", "Port must be between 1 and 65535")
        except ValueError:
            form_handler.add_error("port", "Port must be a valid number")

        # Check for any validation errors
        if form_handler.has_errors():
            logger.error(f"Form validation errors: {form_handler.errors}")
            logger.error(f"First error: {form_handler.get_first_error()}")

            # Get current config for form context
            service = SMTPConfigurationService(db, tenant_id)
            config = await service.get_configuration_by_id(config_id)

            # Return the form with error messages
            return templates.TemplateResponse("administration/smtp/partials/form.html", {
                "request": request,
                "config": config,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        # Handle form-specific data processing
        tags = form_handler.get_list_values("tags")
        enabled = form_handler.form_data.get("enabled") == "true"
        use_tls = form_handler.form_data.get("use_tls") == "true"
        use_ssl = form_handler.form_data.get("use_ssl") == "true"

        # Validate TLS/SSL combination
        if use_tls and use_ssl:
            form_handler.add_error("use_ssl", "Cannot use both TLS and SSL")
            service = SMTPConfigurationService(db, tenant_id)
            config = await service.get_configuration_by_id(config_id)
            return templates.TemplateResponse("administration/smtp/partials/form.html", {
                "request": request,
                "config": config,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        logger.info(f"Tags: {tags}, Enabled: {enabled}, TLS: {use_tls}, SSL: {use_ssl}")

        # Create SMTPConfigurationUpdate schema
        update_data = {
            "name": form_handler.form_data.get("name"),
            "description": form_handler.form_data.get("description"),
            "host": form_handler.form_data.get("host"),
            "port": port,
            "use_tls": use_tls,
            "use_ssl": use_ssl,
            "username": form_handler.form_data.get("username"),
            "from_email": form_handler.form_data.get("from_email"),
            "from_name": form_handler.form_data.get("from_name"),
            "reply_to": form_handler.form_data.get("reply_to") or None,
            "status": SMTPStatus(form_handler.form_data.get("status", "inactive")),
            "enabled": enabled,
            "tags": tags
        }

        # Only include password if provided
        if password:
            update_data["password"] = password

        config_data = SMTPConfigurationUpdate(**update_data)

        logger.info(f"SMTP config data to update: {config_data}")

        # Check if current user is global admin
        global_admin = current_user.role == "global_admin" and current_user.tenant_id == "global"

        # Update configuration using service
        service = SMTPConfigurationService(db, tenant_id)
        updated_config = await service.update_smtp_configuration(config_id, config_data, updated_by_user=current_user)

        if not updated_config:
            raise HTTPException(status_code=404, detail="SMTP configuration not found")

        # Handle tenant reassignment for global admins
        if global_admin:
            target_tenant_id = form_handler.form_data.get("target_tenant_id")
            if target_tenant_id:
                logger.info(f"Global admin updating SMTP config {config_id} tenant to {target_tenant_id}")
                updated_config = await service.update_smtp_field_global(config_id, "tenant_id", target_tenant_id, updated_by_user=current_user)

        logger.info(f"Successfully updated SMTP configuration with ID: {config_id}")

        # Commit the transaction
        await db.commit()

        # Return success response with HTMX redirect
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/features/administration/smtp/"
        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        # Get current config for form context
        service = SMTPConfigurationService(db, tenant_id)
        config = await service.get_configuration_by_id(config_id)
        # Return form with error message
        return templates.TemplateResponse("administration/smtp/partials/form.html", {
            "request": request,
            "config": config,
            "errors": {"general": [str(e)]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=400)
    except Exception as e:
        logger.error(f"Failed to update SMTP configuration: {e}")
        await db.rollback()
        # Get current config for form context
        service = SMTPConfigurationService(db, tenant_id)
        config = await service.get_configuration_by_id(config_id)
        # Return form with error message
        return templates.TemplateResponse("administration/smtp/partials/form.html", {
            "request": request,
            "config": config,
            "errors": {"general": [f"Failed to update configuration: {str(e)}"]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=500)
