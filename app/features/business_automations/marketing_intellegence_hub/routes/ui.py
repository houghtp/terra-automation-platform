"""UI routes for Marketing Intelligence (GA4 and future sources)."""

from datetime import date, timedelta

from app.features.core.route_imports import (
    APIRouter,
    Request,
    Depends,
    templates,
    get_db,
    tenant_dependency,
    get_current_user,
    AsyncSession,
)

from ..services import Ga4ConnectionCrudService, Ga4ClientCrudService

router = APIRouter()


@router.get("/", include_in_schema=False)
async def marketing_intel_overview(request: Request):
    """Overview page placeholder."""
    return templates.TemplateResponse(
        "marketing_intelligence/overview.html",
        {"request": request},
    )


@router.get("/ga4", include_in_schema=False)
async def marketing_intel_ga4(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GA4 landing page with client list."""
    client_service = Ga4ClientCrudService(db, tenant_id)
    clients = await client_service.list_clients()

    today = date.today()
    last_30_start = today - timedelta(days=29)
    last_365_start = today - timedelta(days=364)

    return templates.TemplateResponse(
        "marketing_intelligence/clients.html",
        {
            "request": request,
            "clients": clients,
            "today": today,
            "last_30_start": last_30_start,
            "last_365_start": last_365_start,
        },
    )


@router.get("/ga4/connections/{connection_id}", include_in_schema=False)
async def marketing_intel_ga4_dashboard(
    request: Request,
    connection_id: str,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GA4 dashboard for a specific connection."""
    connection_service = Ga4ConnectionCrudService(db, tenant_id)
    client_service = Ga4ClientCrudService(db, tenant_id)
    connection = await connection_service.get_connection(connection_id)
    if not connection:
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {"request": request, "message": "GA4 connection not found."},
            status_code=404,
        )
    peer_connections = []
    if connection.client_id:
        all_conns = await connection_service.list_connections()
        peer_connections = [c for c in all_conns if c.client_id == connection.client_id]
    client = await client_service.get_client(connection.client_id) if connection.client_id else None

    today = date.today()
    last_30_start = today - timedelta(days=29)
    last_90_start = today - timedelta(days=89)

    return templates.TemplateResponse(
        "marketing_intelligence/ga4_dashboard.html",
        {
            "request": request,
            "connection": connection,
            "client": client,
            "peer_connections": peer_connections,
            "today": today,
            "last_30_start": last_30_start,
            "last_90_start": last_90_start,
        },
    )


@router.get("/ga4/clients/{client_id}", include_in_schema=False)
async def marketing_intel_client_detail(
    request: Request,
    client_id: str,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Client detail page listing its GA4 connections."""
    client_service = Ga4ClientCrudService(db, tenant_id)
    connection_service = Ga4ConnectionCrudService(db, tenant_id)
    client = await client_service.get_client(client_id)
    if not client:
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {"request": request, "message": "Client not found."},
            status_code=404,
        )
    connections = await connection_service.list_connections()
    client_conns = [c for c in connections if c.client_id == client_id]

    today = date.today()
    last_30_start = today - timedelta(days=29)
    last_365_start = today - timedelta(days=364)

    return templates.TemplateResponse(
        "marketing_intelligence/client_detail.html",
        {
            "request": request,
            "client": client,
            "connections": client_conns,
            "today": today,
            "last_30_start": last_30_start,
            "last_365_start": last_365_start,
        },
    )


@router.get("/ga4/rollup", include_in_schema=False)
async def marketing_intel_rollup(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Roll-up dashboard across connections."""
    connection_service = Ga4ConnectionCrudService(db, tenant_id)
    connections = await connection_service.list_connections()
    return templates.TemplateResponse(
        "marketing_intelligence/rollup.html",
        {"request": request, "connections": connections},
    )
