"""GA4 connection routes."""

from datetime import date, timedelta
from typing import List

from app.features.core.route_imports import APIRouter, Depends, HTTPException, Response, Body, Request, templates, Form
from app.features.auth.dependencies import get_current_user

from ..schemas import Ga4ConnectionCreate, Ga4ConnectionResponse, Ga4ConnectionUpdate, Ga4DailyMetricPayload
from ..services import Ga4ConnectionCrudService, Ga4MetricsIngestionService
from ..dependencies import get_connection_service, get_metrics_ingestion_service
from ..clients.ga4_client import Ga4Client
from ..ga4_credentials import load_ga4_credentials
try:
    from google.auth.exceptions import RefreshError
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard for tests
    class RefreshError(Exception):
        """Fallback when google-auth is not installed."""

try:
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
except ModuleNotFoundError:  # pragma: no cover
    RunReportRequest = DateRange = Dimension = Metric = None  # type: ignore

router = APIRouter(prefix="/ga4/connections", tags=["ga4-connections"])

def _parse_date(val: str | None, fallback: date) -> date:
    if not val:
        return fallback
    val = val.strip()
    try:
        return date.fromisoformat(val)
    except ValueError:
        digits = "".join(ch for ch in val if ch.isdigit())
        if len(digits) == 8:
            return date.fromisoformat(f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}")
        raise


@router.get("/", response_model=List[Ga4ConnectionResponse])
async def list_connections(service: Ga4ConnectionCrudService = Depends(get_connection_service)):
    return [Ga4ConnectionResponse.model_validate(item, from_attributes=True) for item in await service.list_connections()]


@router.post("/", response_model=Ga4ConnectionResponse, status_code=201)
async def create_connection(
    payload: Ga4ConnectionCreate,
    token_data: dict = Body(..., description="GA4 tokens (refresh/access)"),
    service: Ga4ConnectionCrudService = Depends(get_connection_service),
    current_user = Depends(get_current_user),
):
    conn = await service.create_connection(payload, token_data, current_user)
    return Ga4ConnectionResponse.model_validate(conn, from_attributes=True)


@router.put("/{connection_id}", response_model=Ga4ConnectionResponse)
async def update_connection(
    connection_id: str,
    payload: Ga4ConnectionUpdate,
    service: Ga4ConnectionCrudService = Depends(get_connection_service),
    current_user = Depends(get_current_user),
):
    updated = await service.update_connection(connection_id, payload, current_user)
    if not updated:
        raise HTTPException(status_code=404, detail="Connection not found")
    return Ga4ConnectionResponse.model_validate(updated, from_attributes=True)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    service: Ga4ConnectionCrudService = Depends(get_connection_service),
):
    deleted = await service.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connection not found")
    return Response(status_code=204)


@router.post("/{connection_id}/sync", status_code=202)
async def sync_connection(
    connection_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    request: Request = None,
    connection_service: Ga4ConnectionCrudService = Depends(get_connection_service),
    metrics_service: Ga4MetricsIngestionService = Depends(get_metrics_ingestion_service),
    current_user=Depends(get_current_user),
):
    """
    Pull GA4 metrics for the given connection and date range (default: last 7 days).
    """
    hx = request.headers.get("HX-Request") if request else None

    try:
        connection = await connection_service.get_connection(connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        tokens = await connection_service.get_tokens(connection_id)
        if not tokens or not tokens.get("refresh_token"):
            raise HTTPException(status_code=400, detail="No tokens stored for this connection")

        creds = await load_ga4_credentials(connection_service.db, accessed_by_user=current_user)
        client = Ga4Client.from_tokens(
            access_token=tokens.get("access_token"),
            refresh_token=tokens["refresh_token"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            access_token_expires_at=tokens.get("access_token_expires_at"),
        )

        # Parse dates from query strings (supports YYYY-MM-DD and YYYYMMDD)
        end_date = _parse_date(end_date, date.today())
        start_date = _parse_date(start_date, end_date - timedelta(days=6))

        metrics = await client.fetch_daily_metrics(connection.property_id, start_date, end_date)
        # Persist refreshed access token/expiry if Google rotated it.
        token_data = client.current_token_data()
        if token_data.get("access_token"):
            await connection_service.upsert_tokens(
                connection_id,
                {
                    "refresh_token": tokens["refresh_token"],
                    "access_token": token_data["access_token"],
                    "access_token_expires_at": token_data["access_token_expires_at"],
                },
            )
        if not metrics:
            if hx:
                return templates.TemplateResponse(
                    "components/ui/error_message.html",
                    {
                        "request": request,
                        "message": f"No GA4 rows returned for {connection.property_name or connection.property_id} in the selected range.",
                    },
                    status_code=200,
                )
            return {"status": "ok", "count": 0}
        payloads = [
            Ga4DailyMetricPayload(
                date=item["date"],
                sessions=item.get("sessions"),
                users=item.get("users"),
                conversions=item.get("conversions"),
                engagement_rate=item.get("engagement_rate"),
                bounce_rate=item.get("bounce_rate"),
                new_users=item.get("new_users"),
                avg_engagement_time=item.get("avg_engagement_time"),
                conversion_rate=item.get("conversion_rate"),
                conversions_per_1k=item.get("conversions_per_1k"),
            )
            for item in metrics
        ]

        await metrics_service.upsert_daily_metrics(connection_id, payloads, current_user)
        # Commit at the route boundary to keep transaction control here.
        await connection_service.db.commit()

        if hx:
            return templates.TemplateResponse(
                "components/ui/success_message.html",
                {
                    "request": request,
                    "message": f"Synced {len(payloads)} days for {connection.property_name or connection.property_id}",
                },
                status_code=200,
            )

        return {"status": "ok", "count": len(payloads)}

    except HTTPException:
        raise
    except RefreshError as exc:
        # Refresh token rejected/expired
        msg = "GA4 credentials need reauthorization. Please reconnect this property."
        if hx:
            return templates.TemplateResponse(
                "components/ui/error_message.html",
                {"request": request, "message": msg},
                status_code=200,
            )
        raise HTTPException(status_code=401, detail=msg)
    except Exception as exc:
        detail = str(exc)
        if hx:
            return templates.TemplateResponse(
                "components/ui/error_message.html",
                {"request": request, "message": f"Failed to sync: {detail}"},
                status_code=200,
            )
        raise HTTPException(status_code=400, detail=f"Failed to sync GA4 data: {detail}")


@router.get("/{connection_id}/top_channels")
async def top_channels(
    connection_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 5,
    connection_service: Ga4ConnectionCrudService = Depends(get_connection_service),
    current_user=Depends(get_current_user),
):
    connection = await connection_service.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    tokens = await connection_service.get_tokens(connection_id)
    if not tokens or not tokens.get("refresh_token"):
        raise HTTPException(status_code=400, detail="No tokens stored for this connection")
    creds = await load_ga4_credentials(connection_service.db, accessed_by_user=current_user)
    client = Ga4Client.from_tokens(
        access_token=tokens.get("access_token"),
        refresh_token=tokens["refresh_token"],
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        access_token_expires_at=tokens.get("access_token_expires_at"),
    )
    if not RunReportRequest:
        raise HTTPException(status_code=500, detail="GA4 SDK not available")
    end = _parse_date(end_date, date.today())
    start = _parse_date(start_date, end - timedelta(days=29))
    req = RunReportRequest(
        property=connection.property_id,
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="conversions")],
        limit=limit,
        order_bys=[
            {"desc": True, "metric": {"metric_name": "conversions"}},
            {"desc": True, "metric": {"metric_name": "sessions"}},
        ],
    )
    try:
        resp = client.client.run_report(req)
        # persist refreshed token if rotated
        token_data = client.current_token_data()
        if token_data.get("access_token"):
            await connection_service.upsert_tokens(
                connection_id,
                {
                    "refresh_token": tokens["refresh_token"],
                    "access_token": token_data["access_token"],
                    "access_token_expires_at": token_data["access_token_expires_at"],
                },
            )
        items = []
        for row in resp.rows:
            name = row.dimension_values[0].value or "Unassigned"
            sessions = float(row.metric_values[0].value) if row.metric_values[0].value else 0.0
            conv = float(row.metric_values[1].value) if row.metric_values[1].value else 0.0
            items.append({"name": name, "sessions": sessions, "conversions": conv})
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "marketing_intelligence/partials/top_channels_rows.html",
                {"request": request, "items": items},
            )
        return {"items": items}
    except Exception as exc:
        msg = "Need GA4 reauth to fetch channels."
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "marketing_intelligence/partials/top_channels_rows.html",
                {"request": request, "items": [], "error": msg},
                status_code=200,
            )
        raise HTTPException(status_code=401, detail=msg)


@router.get("/{connection_id}/top_pages")
async def top_pages(
    connection_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 5,
    connection_service: Ga4ConnectionCrudService = Depends(get_connection_service),
    current_user=Depends(get_current_user),
):
    connection = await connection_service.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    tokens = await connection_service.get_tokens(connection_id)
    if not tokens or not tokens.get("refresh_token"):
        raise HTTPException(status_code=400, detail="No tokens stored for this connection")
    creds = await load_ga4_credentials(connection_service.db, accessed_by_user=current_user)
    client = Ga4Client.from_tokens(
        access_token=tokens.get("access_token"),
        refresh_token=tokens["refresh_token"],
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        access_token_expires_at=tokens.get("access_token_expires_at"),
    )
    if not RunReportRequest:
        raise HTTPException(status_code=500, detail="GA4 SDK not available")
    end = _parse_date(end_date, date.today())
    start = _parse_date(start_date, end - timedelta(days=29))
    req = RunReportRequest(
        property=connection.property_id,
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimensions=[Dimension(name="pageTitle")],
        metrics=[Metric(name="sessions"), Metric(name="conversions")],
        limit=limit,
        order_bys=[
            {"desc": True, "metric": {"metric_name": "conversions"}},
            {"desc": True, "metric": {"metric_name": "sessions"}},
        ],
    )
    try:
        resp = client.client.run_report(req)
        token_data = client.current_token_data()
        if token_data.get("access_token"):
            await connection_service.upsert_tokens(
                connection_id,
                {
                    "refresh_token": tokens["refresh_token"],
                    "access_token": token_data["access_token"],
                    "access_token_expires_at": token_data["access_token_expires_at"],
                },
            )
        items = []
        for row in resp.rows:
            title = row.dimension_values[0].value or "Untitled page"
            sessions = float(row.metric_values[0].value) if row.metric_values[0].value else 0.0
            conv = float(row.metric_values[1].value) if row.metric_values[1].value else 0.0
            items.append({"name": title, "sessions": sessions, "conversions": conv})
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "marketing_intelligence/partials/top_pages_rows.html",
                {"request": request, "items": items},
            )
        return {"items": items}
    except Exception:
        msg = "Need GA4 reauth to fetch pages."
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "marketing_intelligence/partials/top_pages_rows.html",
                {"request": request, "items": [], "error": msg},
                status_code=200,
            )
        raise HTTPException(status_code=401, detail=msg)


@router.post("/{connection_id}/client_label", include_in_schema=False)
async def update_client_label(
    request: Request,
    connection_id: str,
    client_name: str = Form(None),
    service: Ga4ConnectionCrudService = Depends(get_connection_service),
    current_user=Depends(get_current_user),
):
    """HTMX handler to update client/brand label for a connection."""
    await service.update_connection(connection_id, Ga4ConnectionUpdate(client_name=client_name or None), current_user)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "components/ui/success_message.html",
            {"request": request, "message": "Client updated"},
            status_code=200,
        )
    return {"status": "ok"}
