"""
Dashboard routes for connectors (page rendering).

Provides main HTML pages for catalog and installed connectors views.
"""

from app.features.core.route_imports import *
from app.features.connectors.connectors.services.connector_service import ConnectorService

logger = get_logger(__name__)

router = APIRouter(tags=["connectors-dashboard"])


@router.get("/", response_class=HTMLResponse)
async def connectors_home(
    request: Request,
    tab: str = "catalog",  # Default to catalog tab
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Main connectors page with two tabs: Catalog and Installed.

    Query Parameters:
        tab: Which tab to show ("catalog" or "installed")

    Returns:
        HTML page with tabbed interface
    """
    try:
        logger.info("Connectors home accessed", tenant_id=tenant_id, user_id=current_user.id if current_user else None)

        service = ConnectorService(db, tenant_id)

        # Get counts for tabs
        catalog_count = len(await service.list_catalog())
        installed = await service.list_installed()
        installed_count = len(installed)
        active_count = sum(1 for c in installed if c.status == "active")

        return templates.TemplateResponse(
            "connectors/index.html",
            {
                "request": request,
                "user": current_user,
                "tenant_id": tenant_id,
                "active_tab": tab,
                "catalog_count": catalog_count,
                "installed_count": installed_count,
                "active_count": active_count,
            }
        )

    except Exception as e:
        handle_route_error("connectors_home", e)
        raise HTTPException(status_code=500, detail="Failed to load connectors page")


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_view(
    request: Request,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Render catalog card grid (HTMX partial or full page).

    Query Parameters:
        category: Optional category filter

    Returns:
        HTML with catalog cards
    """
    try:
        service = ConnectorService(db)
        catalog_items = await service.list_catalog(category=category)

        # Check if HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        template = "connectors/partials/catalog_grid.html" if is_htmx else "connectors/catalog.html"

        return templates.TemplateResponse(
            template,
            {
                "request": request,
                "catalog_items": catalog_items,
                "selected_category": category,
            }
        )

    except Exception as e:
        handle_route_error("catalog_view", e)
        raise HTTPException(status_code=500, detail="Failed to load catalog")


@router.get("/installed", response_class=HTMLResponse)
async def installed_view(
    request: Request,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Render installed connectors card grid (HTMX partial or full page).

    Query Parameters:
        search: Search term
        category: Category filter
        status: Status filter

    Returns:
        HTML with installed connector cards
    """
    try:
        service = ConnectorService(db, tenant_id)

        # Build filters
        from app.features.connectors.connectors.models import ConnectorSearchFilter, ConnectorStatus
        filters = ConnectorSearchFilter(
            search=search,
            category=category,
            status=ConnectorStatus(status) if status else None,
            limit=50,
            offset=0
        )

        connectors = await service.list_installed(filters)

        # Check if HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        template = "connectors/partials/installed_grid.html" if is_htmx else "connectors/installed.html"

        return templates.TemplateResponse(
            template,
            {
                "request": request,
                "connectors": connectors,
                "search": search,
                "selected_category": category,
                "selected_status": status,
            }
        )

    except Exception as e:
        handle_route_error("installed_view", e)
        raise HTTPException(status_code=500, detail="Failed to load installed connectors")
