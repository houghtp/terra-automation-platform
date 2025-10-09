"""
Connector management routes for the automation platform.
Provides endpoints for managing both available connectors and tenant-specific instances.
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Body, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.templates import templates
from app.features.core.database import get_db
from app.features.core.validation import FormHandler, ValidationError
from app.features.connectors.connectors.services import ConnectorService
from app.features.connectors.connectors.models import (
    TenantConnectorCreate, TenantConnectorUpdate, TenantConnectorResponse, ConnectorSearchFilter,
    ConnectorStatus, ConnectorCategory, AvailableConnectorResponse
)
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from typing import List, Optional
import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["connectors"])


# Main Page Routes
@router.get("/", response_class=HTMLResponse)
async def connectors_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Main connectors management page."""
    return templates.TemplateResponse("connectors/list.html", {
        "request": request,
        "title": "Connectors",
        "tenant": tenant,
        "user": current_user
    })


@router.get("/partials/form", response_class=HTMLResponse)
async def connector_form_modal(
    request: Request,
    connector_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Load connector form modal (add/edit)."""
    service = ConnectorService(db, tenant)

    connector = None
    if connector_id:
        connector = await service.get_tenant_connector_by_id(connector_id)
        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

    # Get available connectors for the picker
    available_connectors = await service.list_available_connectors()

    return templates.TemplateResponse("connectors/partials/form.html", {
        "request": request,
        "connector": connector,
        "available_connectors": available_connectors,
        "is_edit": connector is not None
    })


# API Routes for Table Data
@router.get("/api/list")
async def list_connectors_api(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """API endpoint for Tabulator table data."""
    try:
        service = ConnectorService(db, tenant)

        # Build filters
        filters = ConnectorSearchFilter(
            search=search,
            category=ConnectorCategory(category) if category else None,
            status=ConnectorStatus(status) if status else None,
            is_enabled=is_enabled,
            limit=limit,
            offset=offset
        )

        connectors = await service.list_tenant_connectors(filters)

        # Format for Tabulator
        table_data = []
        for connector in connectors:
            row = {
                "id": connector.id,
                "instance_name": connector.instance_name,
                "description": connector.description or "",
                "connector_display_name": connector.connector_display_name or "",
                "connector_category": connector.connector_category or "",
                "status": connector.status,
                "is_enabled": connector.is_enabled,
                "last_sync": connector.last_sync,
                "created_at": connector.created_at,
                "connector_icon_url": connector.connector_icon_url,
                "connector_icon_class": connector.connector_icon_class,
                "connector_brand_color": connector.connector_brand_color,
                "tags": connector.tags or []
            }
            table_data.append(row)

        return {"data": table_data}

    except Exception as e:
        logger.error(f"Failed to list connectors: {e}")
        raise HTTPException(status_code=500, detail="Failed to load connectors")


@router.get("/api/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard summary statistics."""
    try:
        service = ConnectorService(db, tenant)
        stats = await service.get_dashboard_stats()

        return {
            "total_connectors": stats.total_connectors,
            "active_connectors": stats.active_connectors,
            "error_connectors": stats.error_connectors,
            "pending_setup_connectors": stats.pending_setup_connectors
        }

    except Exception as e:
        logger.error(f"Failed to get connector summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to load summary")


@router.get("/api/available")
async def list_available_connectors_api(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API endpoint for available connectors picker."""
    try:
        service = ConnectorService(db)  # No tenant for available connectors

        category_filter = ConnectorCategory(category) if category else None
        connectors = await service.list_available_connectors(category_filter)

        return {"data": [connector.model_dump() for connector in connectors]}

    except Exception as e:
        logger.error(f"Failed to list available connectors: {e}")
        raise HTTPException(status_code=500, detail="Failed to load available connectors")


# CRUD Operations
@router.post("/api")
async def create_connector(
    connector_data: TenantConnectorCreate,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Create a new tenant connector."""
    try:
        service = ConnectorService(db, tenant)
        connector = await service.create_tenant_connector(connector_data, current_user.id)
        await db.commit()

        logger.info(f"Created connector: {connector.instance_name} (ID: {connector.id})")
        return connector.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(status_code=500, detail="Failed to create connector")


@router.get("/api/{connector_id}")
async def get_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get a specific connector by ID."""
    service = ConnectorService(db, tenant)
    connector = await service.get_tenant_connector_by_id(connector_id)

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    return connector.model_dump()


@router.put("/api/{connector_id}")
async def update_connector(
    connector_id: str,
    connector_data: TenantConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Update a connector."""
    try:
        service = ConnectorService(db, tenant)
        connector = await service.update_tenant_connector(connector_id, connector_data)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await db.commit()

        logger.info(f"Updated connector: {connector.instance_name} (ID: {connector.id})")
        return connector.model_dump()

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update connector {connector_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update connector")


@router.delete("/api/{connector_id}")
async def delete_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Delete a connector."""
    try:
        service = ConnectorService(db, tenant)
        success = await service.delete_tenant_connector(connector_id)

        if not success:
            raise HTTPException(status_code=404, detail="Connector not found")

        await db.commit()

        logger.info(f"Deleted connector: {connector_id}")
        return {"success": True, "message": "Connector deleted successfully"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete connector {connector_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete connector")


# Field Updates
@router.patch("/api/{connector_id}/field")
async def update_connector_field(
    connector_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Update a single field of a connector."""
    try:
        field = field_update.get("field")
        value = field_update.get("value")

        if not field:
            raise HTTPException(status_code=400, detail="Field name is required")

        # Handle boolean fields
        if field in ['is_enabled'] and isinstance(value, str):
            value = value.lower() == 'true'

        # Handle JSON fields
        if field in ['configuration', 'secrets_references', 'tags'] and isinstance(value, str):
            try:
                import json
                value = json.loads(value)
            except:
                pass  # Keep as string if parse fails

        service = ConnectorService(db, tenant)
        updated_connector = await service._update_connector_field(connector_id, field, value)

        if not updated_connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await db.commit()

        return updated_connector.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update connector field: {e}")
        raise HTTPException(status_code=500, detail="Failed to update field")


# Status Management
@router.post("/api/{connector_id}/enable")
async def enable_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Enable a connector."""
    try:
        service = ConnectorService(db, tenant)
        connector = await service.enable_connector(connector_id)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await db.commit()
        return connector.model_dump()

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to enable connector {connector_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable connector")


@router.post("/api/{connector_id}/disable")
async def disable_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Disable a connector."""
    try:
        service = ConnectorService(db, tenant)
        connector = await service.disable_connector(connector_id)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await db.commit()
        return connector.model_dump()

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to disable connector {connector_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable connector")
    if not updated_config:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    await db.commit()  # Route handles transaction commit
    return {"success": True}

# --- CONNECTORS Configuration Action Routes ---

@router.post("/validate/name")
async def validate_connectors_name(request: Request, instance_name: str = Form(...), connector_id: Optional[str] = Form(None), db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate connector instance name."""
    try:
        if not instance_name or not instance_name.strip():
            return HTMLResponse('<span class="invalid-feedback d-block">Connector name is required</span>')

        instance_name = instance_name.strip()

        if len(instance_name) < 3:
            return HTMLResponse('<span class="invalid-feedback d-block">Connector name must be at least 3 characters</span>')

        if len(instance_name) > 255:
            return HTMLResponse('<span class="invalid-feedback d-block">Connector name must be less than 255 characters</span>')

        # Check for duplicate names within tenant (excluding current connector if editing)
        connectors_service = ConnectorsService(db, tenant)
        existing = await connectors_service.get_tenant_connector_by_name(instance_name)

        if existing and (not connector_id or existing.id != connector_id):
            return HTMLResponse('<span class="invalid-feedback d-block">A connector with this name already exists</span>')

        return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Connector name is available</span>')
    except Exception as e:
        logger.exception("Error validating connector name", error=str(e))
        return HTMLResponse('<span class="invalid-feedback d-block">Error validating connector name</span>')

@router.post("/validate/host")
async def validate_connectors_host(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate CONNECTORS host."""
    try:
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        host = form_handler.form_data.get("host", "").strip()
        if not host:
            return HTMLResponse('<span class="invalid-feedback d-block">CONNECTORS host is required</span>')

        # Basic host validation
        host_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$'
        if not re.match(host_pattern, host):
            return HTMLResponse('<span class="invalid-feedback d-block">Invalid hostname format</span>')

        return HTMLResponse('<span class="valid-feedback d-block">Host format looks good</span>')
    except Exception:
        return HTMLResponse("")

@router.post("/validate/password")
async def validate_connectors_password(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Validate CONNECTORS password."""
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

@router.post("/validate/from_email")
async def validate_connectors_from_email(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
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
        return HTMLResponse("")@router.post("/{config_id}/activate")
async def activate_connectors_configuration(config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Activate CONNECTORS configuration."""
    service = CONNECTORSConfigurationService(db, tenant)
    config = await service.activate_connectors_configuration(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    await db.commit()
    return {"success": True, "message": f"CONNECTORS configuration '{config.name}' activated"}

@router.post("/{config_id}/deactivate")
async def deactivate_connectors_configuration(config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Deactivate CONNECTORS configuration."""
    service = CONNECTORSConfigurationService(db, tenant)
    config = await service.deactivate_connectors_configuration(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    await db.commit()
    return {"success": True, "message": f"CONNECTORS configuration '{config.name}' deactivated"}

@router.post("/{config_id}/test")
async def test_connectors_configuration(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Test CONNECTORS configuration."""
    try:
        # Parse form data for test email
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        test_email = form_handler.form_data.get("test_email")

        service = CONNECTORSConfigurationService(db, tenant)
        test_result = await service.test_connectors_configuration(config_id, test_email)

        await db.commit()  # Save test results

        if test_result.success:
            return JSONResponse({
                "success": True,
                "message": test_result.message,
                "details": test_result.details
            })
        else:
            return JSONResponse({
                "success": False,
                "message": test_result.message
            }, status_code=400)

    except Exception as e:
        logger.error(f"Failed to test CONNECTORS configuration: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Test failed: {str(e)}"
        }, status_code=500)


@router.post("/send-test-email")
async def send_test_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Send a test email using the email service."""
    try:
        from app.features.core.email_service import get_email_service

        # Parse form data
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        test_email = form_handler.form_data.get("test_email")
        email_type = form_handler.form_data.get("email_type", "welcome")

        if not test_email:
            return JSONResponse({
                "success": False,
                "message": "Test email address is required"
            }, status_code=400)

        # Get email service
        email_service = await get_email_service(db, tenant)

        # Send test email based on type
        if email_type == "welcome":
            result = await email_service.send_welcome_email(
                user_email=test_email,
                user_name="Test User"
            )
        elif email_type == "password_reset":
            result = await email_service.send_password_reset_email(
                user_email=test_email,
                user_name="Test User",
                reset_token="test-token-123"
            )
        elif email_type == "admin_alert":
            result = await email_service.send_admin_alert(
                alert_type="system",
                message="This is a test admin alert email",
                severity="info",
                admin_emails=[test_email]
            )
        else:
            # Custom email
            result = await email_service.send_email(
                to_emails=test_email,
                subject=f"Test Email from {tenant}",
                html_body=f"""
                <h2>Test Email</h2>
                <p>This is a test email sent from the {tenant} email service.</p>
                <p>If you received this email, the email service is working correctly!</p>
                """,
                text_body=f"Test email from {tenant}. If you received this, the email service is working!"
            )

        if result.success:
            return JSONResponse({
                "success": True,
                "message": result.message,
                "sent_at": result.sent_at.isoformat()
            })
        else:
            return JSONResponse({
                "success": False,
                "message": result.message,
                "error": result.error
            }, status_code=400)

    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Test email failed: {str(e)}"
        }, status_code=500)

# --- UI ROUTES (Jinja + HTMX) ---

# List page
@router.get("/", response_class=HTMLResponse)
async def connectors_list(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("administration/connectors/list.html", {"request": request})

# Modal form (add/edit)
@router.get("/partials/form", response_class=HTMLResponse)
async def connectors_form_partial(request: Request, config_id: str = None, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    config = None
    if config_id:
        service = CONNECTORSConfigurationService(db, tenant)
        config = await service.get_configuration_by_id(config_id)

    return templates.TemplateResponse("administration/connectors/partials/form.html", {
        "request": request,
        "config": config
    })

# Modal edit endpoint
@router.get("/{config_id}/edit", response_class=HTMLResponse)
async def connectors_edit_form(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    service = CONNECTORSConfigurationService(db, tenant)
    config = await service.get_configuration_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    return templates.TemplateResponse("administration/connectors/partials/form.html", {
        "request": request,
        "config": config
    })

# Create CONNECTORS configuration
@router.post("/")
async def connectors_create(request: Request, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Create a new CONNECTORS configuration via form submission."""
    try:
        logger.info("Starting CONNECTORS configuration creation process")

        # Use centralized form handler
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        logger.info(f"Raw form data: {dict(form_handler.raw_form)}")
        logger.info(f"Parsed form data: {form_handler.form_data}")

        # Validate required fields
        required_fields = ['name', 'host', 'username', 'password', 'confirm_password', 'from_email', 'from_name']
        logger.info(f"Validating required fields: {required_fields}")
        form_handler.validate_required_fields(required_fields)

        # Validate email format
        form_handler.validate_email_field('from_email')
        if form_handler.form_data.get('reply_to'):
            form_handler.validate_email_field('reply_to')

        # Validate password fields (complexity + confirmation)
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
            # Return the form with error messages
            return templates.TemplateResponse("administration/connectors/partials/form.html", {
                "request": request,
                "config": None,
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
            return templates.TemplateResponse("administration/connectors/partials/form.html", {
                "request": request,
                "config": None,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        logger.info(f"Tags: {tags}, Enabled: {enabled}, TLS: {use_tls}, SSL: {use_ssl}")

        # Create CONNECTORSConfigurationCreate schema
        config_data = CONNECTORSConfigurationCreate(
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
            status=CONNECTORSStatus(form_handler.form_data.get("status", "inactive")),
            enabled=enabled,
            tags=tags
        )

        logger.info(f"CONNECTORS config data to create: {config_data}")

        # Create configuration using service
        service = CONNECTORSConfigurationService(db, tenant)
        new_config = await service.create_connectors_configuration(config_data)

        logger.info(f"Successfully created CONNECTORS configuration with ID: {new_config.id}")

        # Commit the transaction
        await db.commit()

        # Return success response with HTMX redirect
        response = Response(status_code=201)
        response.headers["HX-Redirect"] = "/features/administration/connectors/"
        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        # Return form with error message
        return templates.TemplateResponse("administration/connectors/partials/form.html", {
            "request": request,
            "config": None,
            "errors": {"general": [str(e)]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=400)
    except Exception as e:
        logger.error(f"Failed to create CONNECTORS configuration: {e}")
        await db.rollback()
        # Return form with error message
        return templates.TemplateResponse("administration/connectors/partials/form.html", {
            "request": request,
            "config": None,
            "errors": {"general": [f"Failed to create configuration: {str(e)}"]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=500)

# Update CONNECTORS configuration
@router.post("/{config_id}")
async def connectors_update(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Update an existing CONNECTORS configuration via form submission."""
    try:
        logger.info(f"Starting CONNECTORS configuration update process for ID: {config_id}")

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
            service = CONNECTORSConfigurationService(db, tenant)
            config = await service.get_configuration_by_id(config_id)

            # Return the form with error messages
            return templates.TemplateResponse("administration/connectors/partials/form.html", {
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
            service = CONNECTORSConfigurationService(db, tenant)
            config = await service.get_configuration_by_id(config_id)
            return templates.TemplateResponse("administration/connectors/partials/form.html", {
                "request": request,
                "config": config,
                "errors": form_handler.errors,
                "form_data": form_handler.form_data
            }, status_code=400)

        logger.info(f"Tags: {tags}, Enabled: {enabled}, TLS: {use_tls}, SSL: {use_ssl}")

        # Create CONNECTORSConfigurationUpdate schema
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
            "status": CONNECTORSStatus(form_handler.form_data.get("status", "inactive")),
            "enabled": enabled,
            "tags": tags
        }

        # Only include password if provided
        if password:
            update_data["password"] = password

        config_data = CONNECTORSConfigurationUpdate(**update_data)

        logger.info(f"CONNECTORS config data to update: {config_data}")

        # Update configuration using service
        service = CONNECTORSConfigurationService(db, tenant)
        updated_config = await service.update_connectors_configuration(config_id, config_data)

        if not updated_config:
            raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

        logger.info(f"Successfully updated CONNECTORS configuration with ID: {config_id}")

        # Commit the transaction
        await db.commit()

        # Return success response with HTMX redirect
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/features/administration/connectors/"
        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        # Get current config for form context
        service = CONNECTORSConfigurationService(db, tenant)
        config = await service.get_configuration_by_id(config_id)
        # Return form with error message
        return templates.TemplateResponse("administration/connectors/partials/form.html", {
            "request": request,
            "config": config,
            "errors": {"general": [str(e)]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=400)
    except Exception as e:
        logger.error(f"Failed to update CONNECTORS configuration: {e}")
        await db.rollback()
        # Get current config for form context
        service = CONNECTORSConfigurationService(db, tenant)
        config = await service.get_configuration_by_id(config_id)
        # Return form with error message
        return templates.TemplateResponse("administration/connectors/partials/form.html", {
            "request": request,
            "config": config,
            "errors": {"general": [f"Failed to update configuration: {str(e)}"]},
            "form_data": form_handler.form_data if 'form_handler' in locals() else {}
        }, status_code=500)

# Delete CONNECTORS configuration
@router.delete("/{config_id}")
async def connectors_delete(config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Delete CONNECTORS configuration."""
    service = CONNECTORSConfigurationService(db, tenant)

    # Get config name for response message
    config = await service.get_configuration_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    config_name = config.name
    success = await service.delete_connectors_configuration(config_id)

    if not success:
        raise HTTPException(status_code=404, detail="CONNECTORS configuration not found")

    await db.commit()
    return {"success": True, "message": f"CONNECTORS configuration '{config_name}' deleted"}

# API endpoint for Tabulator
@router.get("/api/list", response_class=JSONResponse)
async def get_connectors_configurations_api(search: str = "", status: str = "", db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Get CONNECTORS configurations as JSON for Tabulator."""
    service = CONNECTORSConfigurationService(db, tenant)

    # Build search filters
    filters = CONNECTORSSearchFilter()
    if search:
        filters.search = search
    if status and status != "all":
        filters.status = CONNECTORSStatus(status)

    configurations = await service.list_connectors_configurations(filters)
    # Return array directly for Tabulator compatibility
    return [config.model_dump() for config in configurations]

# List content (for HTMX updates)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def connectors_list_content(request: Request, search: str = "", status: str = "", db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Get the list content partial for HTMX updates."""
    service = CONNECTORSConfigurationService(db, tenant)

    # Build search filters
    filters = CONNECTORSSearchFilter()
    if search:
        filters.search = search
    if status and status != "all":
        filters.status = CONNECTORSStatus(status)

    configurations = await service.list_connectors_configurations(filters)

    return templates.TemplateResponse("administration/connectors/partials/list_content.html", {
        "request": request,
        "configurations": configurations
    })


# --- SDK Connector Integration Routes ---

@router.post("/{connector_id}/test-connection")
async def test_connector_connection(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Test connection for a tenant connector using SDK."""
    try:
        service = ConnectorService(db, tenant)
        result = await service.test_connector_connection(connector_id)

        if result["success"]:
            logger.info(f"Connection test successful for connector {connector_id}")
        else:
            logger.warning(f"Connection test failed for connector {connector_id}: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Error testing connector {connector_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_code": "TEST_ERROR"
        }


@router.get("/{connector_id}/credentials")
async def get_connector_credentials(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get resolved credentials for a connector (for debugging - sensitive!)."""
    try:
        service = ConnectorService(db, tenant)
        credentials = await service.get_connector_credentials(connector_id)

        if not credentials:
            raise HTTPException(status_code=404, detail="Connector or credentials not found")

        # Mask sensitive values for security
        masked_credentials = {}
        for key, value in credentials.items():
            if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password']):
                masked_credentials[key] = f"***{str(value)[-4:]}" if len(str(value)) > 4 else "***"
            else:
                masked_credentials[key] = value

        return {
            "connector_id": connector_id,
            "credentials": masked_credentials,
            "credential_count": len(credentials)
        }

    except Exception as e:
        logger.error(f"Error getting credentials for connector {connector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{connector_id}/create-sdk-instance")
async def create_sdk_connector_instance(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Create and initialize an SDK connector instance."""
    try:
        service = ConnectorService(db, tenant)
        sdk_connector = await service.create_sdk_connector_instance(connector_id)

        # Initialize the connector
        init_result = await sdk_connector.initialize()

        # Get connector info
        result = {
            "success": init_result.success,
            "connector_name": sdk_connector.name,
            "connector_type": sdk_connector.connector_type.value,
            "initialized": init_result.success,
            "error": init_result.error,
            "error_code": init_result.error_code
        }

        # Test basic functionality if initialization was successful
        if init_result.success:
            try:
                schema_result = await sdk_connector.get_schema()
                result["has_schema"] = schema_result.success

                if hasattr(sdk_connector, 'get_models'):
                    models_result = await sdk_connector.get_models()
                    result["available_models"] = len(models_result.data) if models_result.success else 0
            except Exception as e:
                logger.warning(f"Could not get additional info for connector {connector_id}: {e}")

        # Clean up
        await sdk_connector.cleanup()

        return result

    except Exception as e:
        logger.error(f"Error creating SDK instance for connector {connector_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_code": "SDK_CREATION_ERROR"
        }
