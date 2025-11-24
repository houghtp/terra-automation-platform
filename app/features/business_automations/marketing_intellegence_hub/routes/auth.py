"""GA4 OAuth routes (HTMX-friendly)."""

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    RedirectResponse,
    Form,
    templates,
    get_db,
    tenant_dependency,
    get_current_user,
    get_logger,
    AsyncSession,
)

from app.features.business_automations.marketing_intellegence_hub.ga4_credentials import load_ga4_credentials
from app.features.business_automations.marketing_intellegence_hub.ga4_oauth import (
    build_auth_url,
    list_ga4_properties,
    perform_token_exchange,
)
from app.features.business_automations.marketing_intellegence_hub.schemas import Ga4ConnectionCreate
from app.features.business_automations.marketing_intellegence_hub.schemas_clients import Ga4ClientCreate
from app.features.business_automations.marketing_intellegence_hub.services import Ga4ConnectionCrudService, Ga4ClientCrudService
from app.features.business_automations.marketing_intellegence_hub.dependencies import get_client_service

router = APIRouter(prefix="/ga4/auth", tags=["ga4-auth"])


@router.get("/start", include_in_schema=False)
async def start_ga4_auth(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
):
    """Redirect the user to Google's consent screen."""
    creds = await load_ga4_credentials(db_session=db, accessed_by_user=None)
    state = tenant_id  # TODO: enhance with CSRF token if session support is added
    auth_url = build_auth_url(creds["client_id"], creds["redirect_uri"], state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback", include_in_schema=False)
async def ga4_auth_callback(
    request: Request,
    code: str,
    state: str | None = None,
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    client_service: Ga4ClientCrudService = Depends(get_client_service),
):
    """Handle Google OAuth callback, exchange code, and present property selection."""
    if state and state != tenant_id:
        raise HTTPException(status_code=400, detail="Invalid auth state")

    try:
        token_data = await perform_token_exchange(code, db_session=db, accessed_by_user=current_user)
        properties = await list_ga4_properties(token_data["access_token"])
        clients = await client_service.list_clients()

        return templates.TemplateResponse(
            "marketing_intelligence/ga4_connect.html",
            {
                "request": request,
                "properties": properties,
                "token_data": token_data,
                "clients": clients,
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GA4 authorization failed: {exc}")


@router.post("/connect", include_in_schema=False, response_class=Response)
async def ga4_connect(
    request: Request,
    property_id: str = Form(...),
    property_name: str = Form(...),
    client_name: str | None = Form(None),
    client_id: str | None = Form(None),
    refresh_token: str = Form(...),
    access_token: str | None = Form(None),
    access_token_expires_at: str | None = Form(None),
    tenant_id: str = Depends(tenant_dependency),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    client_service: Ga4ClientCrudService = Depends(get_client_service),
):
    """Create a GA4 connection for the selected property and persist tokens."""
    try:
        # Create a client if none selected and a name was provided.
        if not client_id and client_name:
            from app.features.business_automations.marketing_intellegence_hub.schemas_clients import Ga4ClientCreate
            new_client = await client_service.create_client(
                Ga4ClientCreate(name=client_name, notes=None, status="active")
            )
            client_id = new_client.id

        service = Ga4ConnectionCrudService(db, tenant_id)
        payload = Ga4ConnectionCreate(
            property_id=property_id,
            property_name=property_name,
            client_name=client_name,
            client_id=client_id,
        )

        if not refresh_token:
            return templates.TemplateResponse(
                "components/ui/error_message.html",
                {
                    "request": request,
                    "message": "Google did not return a refresh token. Please revoke access for this app and retry the GA4 connect flow with consent.",
                },
                status_code=200,
            )

        token_payload = {
            "refresh_token": refresh_token,
            "access_token": access_token,
            "access_token_expires_at": access_token_expires_at,
        }
        conn = await service.create_connection(payload, token_payload, current_user)

        await db.commit()

        # Redirect the user back to the GA4 landing page after successful connect.
        # HTMX supports redirect via HX-Redirect header.
        redirect_url = "/features/marketing-intelligence/ga4"
        if request.headers.get("HX-Request"):
            return Response(status_code=204, headers={"HX-Redirect": redirect_url})

        return RedirectResponse(url=redirect_url, status_code=303)
    except Exception as exc:
        logger = get_logger(__name__)
        logger.error("GA4 connect failed", error=str(exc))
        return templates.TemplateResponse(
            "components/ui/error_message.html",
            {
                "request": request,
                "message": f"Failed to connect GA4 property: {exc}",
            },
            status_code=200,
        )
