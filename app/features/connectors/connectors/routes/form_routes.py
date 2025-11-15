"""
Form routes for connectors (HTMX form handling).

Provides HTMX-powered form submission and inline validation.
"""

from app.features.core.route_imports import *
from app.features.connectors.connectors.services.connector_service import ConnectorService
from app.features.connectors.connectors.models import ConnectorStatus
from app.features.connectors.connectors.schemas import ConnectorCreate, ConnectorUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/forms", tags=["connectors-forms"])


@router.get("/create", response_class=HTMLResponse)
async def get_create_form(
    request: Request,
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Load create connector form modal.

    Query Parameters:
        catalog_id: Catalog connector ID to install

    Returns:
        HTML modal with dynamic form fields based on JSON Schema
    """
    try:
        service = ConnectorService(db, tenant_id)
        catalog = await service.get_catalog_by_id(catalog_id)

        if not catalog:
            raise HTTPException(status_code=404, detail="Connector type not found")

        return templates.TemplateResponse(
            "connectors/partials/modal_create.html",
            {
                "request": request,
                "catalog": catalog,
                "connector": None,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_create_form", e)
        raise HTTPException(status_code=500, detail="Failed to load form")


@router.get("/edit/{connector_id}", response_class=HTMLResponse)
async def get_edit_form(
    request: Request,
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Load edit connector form modal.

    Path Parameters:
        connector_id: Connector ID to edit

    Returns:
        HTML modal with pre-filled form
    """
    try:
        service = ConnectorService(db, tenant_id)
        connector = await service.get_by_id_with_enrichment(connector_id)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        # Get catalog for schema
        catalog = await service.get_catalog_by_id(connector.catalog_id)

        return templates.TemplateResponse(
            "connectors/partials/modal_edit.html",
            {
                "request": request,
                "catalog": catalog,
                "connector": connector,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_edit_form", e)
        raise HTTPException(status_code=500, detail="Failed to load form")


@router.post("/create", response_class=HTMLResponse)
async def submit_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Submit create connector form (HTMX).

    Returns:
        Success: HX-Redirect to refresh page
        Error: Form with validation errors
    """
    try:
        # Parse form data
        form_data = await request.form()

        catalog_id = form_data.get("catalog_id")
        name = form_data.get("name", "").strip()

        # Parse config JSON (dynamic based on schema)
        config = {}
        auth = {}

        # Extract all form fields and categorize them
        for key, value in form_data.items():
            if key.startswith("config_"):
                field_name = key.replace("config_", "")
                config[field_name] = value
            elif key.startswith("auth_"):
                field_name = key.replace("auth_", "")
                auth[field_name] = value

        # Parse tags
        tags_str = form_data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        # Validate required fields
        if not catalog_id:
            return templates.TemplateResponse(
                "connectors/partials/modal_create.html",
                {
                    "request": request,
                    "error": "Connector type is required",
                    "form_data": dict(form_data),
                },
                status_code=400
            )

        if not name:
            service = ConnectorService(db, tenant_id)
            catalog = await service.get_catalog_by_id(catalog_id)
            return templates.TemplateResponse(
                "connectors/partials/modal_create.html",
                {
                    "request": request,
                    "catalog": catalog,
                    "error": "Connector name is required",
                    "form_data": dict(form_data),
                },
                status_code=400
            )

        # Create connector
        service = ConnectorService(db, tenant_id)
        connector_data = ConnectorCreate(
            catalog_id=catalog_id,
            name=name,
            config=config,
            auth=auth,
            tags=tags
        )

        connector = await service.install_connector(
            connector_data,
            created_by_id=current_user.id,
            created_by_name=current_user.name
        )

        await commit_transaction(db, "submit_create_form")

        logger.info("Connector created via form",
                   connector_id=connector.id,
                   name=connector.name,
                   tenant_id=tenant_id)

        # Return HX-Redirect to refresh page
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/features/connectors/?tab=installed"
        return response

    except ValueError as e:
        # Validation error - return form with error
        service = ConnectorService(db, tenant_id)
        catalog = await service.get_catalog_by_id(catalog_id) if catalog_id else None

        return templates.TemplateResponse(
            "connectors/partials/modal_create.html",
            {
                "request": request,
                "catalog": catalog,
                "error": str(e),
                "form_data": dict(form_data),
            },
            status_code=400
        )

    except Exception as e:
        await db.rollback()
        handle_route_error("submit_create_form", e)

        return templates.TemplateResponse(
            "connectors/partials/modal_create.html",
            {
                "request": request,
                "error": f"Failed to create connector: {str(e)}",
                "form_data": dict(form_data),
            },
            status_code=500
        )


@router.post("/edit/{connector_id}", response_class=HTMLResponse)
async def submit_edit_form(
    request: Request,
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Submit edit connector form (HTMX).

    Path Parameters:
        connector_id: Connector ID

    Returns:
        Success: HX-Redirect to refresh page
        Error: Form with validation errors
    """
    try:
        # Parse form data
        form_data = await request.form()

        name = form_data.get("name", "").strip()
        status = form_data.get("status")

        # Parse config and auth
        config = {}
        auth = {}

        for key, value in form_data.items():
            if key.startswith("config_"):
                field_name = key.replace("config_", "")
                config[field_name] = value
            elif key.startswith("auth_"):
                field_name = key.replace("auth_", "")
                # Only update auth if value provided (allow keeping existing)
                if value:
                    auth[field_name] = value

        # Parse tags
        tags_str = form_data.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        # Update connector
        service = ConnectorService(db, tenant_id)

        update_data = ConnectorUpdate(
            name=name if name else None,
            config=config if config else None,
            auth=auth if auth else None,
            status=ConnectorStatus(status) if status else None,
            tags=tags
        )

        connector = await service.update_connector(connector_id, update_data)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await commit_transaction(db, "submit_edit_form")

        logger.info("Connector updated via form",
                   connector_id=connector_id,
                   tenant_id=tenant_id)

        # Return HX-Redirect to refresh page
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/features/connectors/?tab=installed"
        return response

    except ValueError as e:
        # Validation error - return form with error
        service = ConnectorService(db, tenant_id)
        connector = await service.get_by_id_with_enrichment(connector_id)
        catalog = await service.get_catalog_by_id(connector.catalog_id) if connector else None

        return templates.TemplateResponse(
            "connectors/partials/modal_edit.html",
            {
                "request": request,
                "catalog": catalog,
                "connector": connector,
                "error": str(e),
                "form_data": dict(form_data),
            },
            status_code=400
        )

    except Exception as e:
        await db.rollback()
        handle_route_error("submit_edit_form", e)

        return templates.TemplateResponse(
            "connectors/partials/modal_edit.html",
            {
                "request": request,
                "error": f"Failed to update connector: {str(e)}",
                "form_data": dict(form_data),
            },
            status_code=500
        )


@router.post("/validate-name", response_class=HTMLResponse)
async def validate_name(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Validate connector name uniqueness (inline validation).

    Returns:
        HTML feedback message
    """
    try:
        form_data = await request.form()
        name = form_data.get("name", "").strip()
        connector_id = form_data.get("connector_id")  # For edit mode

        if not name:
            return HTMLResponse('<span class="invalid-feedback d-block">Name is required</span>')

        if len(name) < 2:
            return HTMLResponse('<span class="invalid-feedback d-block">Name must be at least 2 characters</span>')

        # Check uniqueness
        service = ConnectorService(db, tenant_id)

        # Check if name exists (excluding current connector in edit mode)
        from sqlalchemy import select, and_
        from app.features.connectors.connectors.models import Connector

        stmt = select(Connector).where(
            and_(
                Connector.name == name,
                Connector.tenant_id == tenant_id
            )
        )

        if connector_id:
            stmt = stmt.where(Connector.id != connector_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return HTMLResponse('<span class="invalid-feedback d-block">A connector with this name already exists</span>')

        return HTMLResponse('<span class="valid-feedback d-block"><i class="ti ti-check text-success me-1"></i>Name is available</span>')

    except Exception as e:
        logger.error("Name validation error", error=str(e))
        return HTMLResponse("")


@router.delete("/{connector_id}", response_class=HTMLResponse)
async def delete_connector_form(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Delete connector (HTMX).

    Path Parameters:
        connector_id: Connector ID

    Returns:
        Empty response with HX-Redirect
    """
    try:
        service = ConnectorService(db, tenant_id)
        deleted = await service.delete_connector(connector_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Connector not found")

        await commit_transaction(db, "delete_connector_form")

        logger.info("Connector deleted via form",
                   connector_id=connector_id,
                   tenant_id=tenant_id)

        # Return HX-Redirect to refresh page
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/features/connectors/?tab=installed"
        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        handle_route_error("delete_connector_form", e)
        raise HTTPException(status_code=500, detail="Failed to delete connector")
