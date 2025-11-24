"""GA4 metrics routes (read + ingestion stub)."""

from datetime import date
from typing import List

from app.features.core.route_imports import APIRouter, Depends, HTTPException
from app.features.auth.dependencies import get_current_user

from ..schemas import (
    Ga4DailyMetricPayload,
    MetricsKpiResponse,
    MetricsTimeSeriesResponse,
)
from ..services import Ga4MetricsIngestionService, Ga4MetricsQueryService, Ga4ConnectionCrudService
from ..dependencies import get_metrics_ingestion_service, get_metrics_query_service, get_connection_service

router = APIRouter(prefix="/ga4/metrics", tags=["ga4-metrics"])


@router.post("/{connection_id}/ingest", status_code=204)
async def ingest_metrics(
    connection_id: str,
    payloads: List[Ga4DailyMetricPayload],
    service: Ga4MetricsIngestionService = Depends(get_metrics_ingestion_service),
    current_user = Depends(get_current_user),
):
    await service.upsert_daily_metrics(connection_id, payloads, current_user)
    return None


@router.get("/{connection_id}/kpis", response_model=MetricsKpiResponse)
async def get_kpis(
    connection_id: str,
    start_date: date,
    end_date: date,
    compare_start: date | None = None,
    compare_end: date | None = None,
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
    connection_service: Ga4ConnectionCrudService = Depends(get_connection_service),
):
    kpis = await service.get_kpis(connection_id, start_date, end_date, compare_start, compare_end)
    connection = await connection_service.get_connection(connection_id)
    if connection:
        kpis.last_synced_at = connection.last_synced_at
    return kpis


@router.get("/{connection_id}/timeseries", response_model=MetricsTimeSeriesResponse)
async def get_time_series(
    connection_id: str,
    start_date: date,
    end_date: date,
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
):
    points = await service.get_time_series(connection_id, start_date, end_date)
    return MetricsTimeSeriesResponse(points=points)


@router.get("/{connection_id}/timeseries_chart")
async def get_time_series_chart(
    connection_id: str,
    start_date: date,
    end_date: date,
    metrics: str = "sessions,users",
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
):
    """
    Return time series in chart-widget friendly format.
    metrics: comma-separated keys (sessions,users,conversions,engagement_rate,bounce_rate,new_users,avg_engagement_time,conversion_rate,conversions_per_1k)
    """
    requested = [m.strip() for m in metrics.split(",") if m.strip()]
    points = await service.get_time_series(connection_id, start_date, end_date)
    if not points:
        return {"categories": [], "series": []}
    categories = [p.date.isoformat() for p in points]

    def pick(metric_key):
        return [getattr(p, metric_key) for p in points]

    series = []
    for key in requested:
        if not hasattr(points[0], key):
            continue
        series.append({"name": key.replace("_", " ").title(), "data": pick(key)})

    return {"categories": categories, "series": series}


@router.get("/rollup/top")
async def get_rollup_top(
    connection_ids: str,
    start_date: date,
    end_date: date,
    limit: int = 5,
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
    connection_service: Ga4ConnectionCrudService = Depends(get_connection_service),
):
    ids = _parse_ids(connection_ids)
    top = await service.get_top_connections(ids, start_date, end_date, limit=limit)
    # hydrate with connection names
    result = []
    for item in top:
        conn = await connection_service.get_connection(item["connection_id"])
        result.append(
            {
                "connection_id": item["connection_id"],
                "name": conn.client_name or conn.property_name or conn.property_id if conn else item["connection_id"],
                "conversions": item["conversions"],
                "sessions": item["sessions"],
            }
        )
    return {"items": result}


# Rollup (multi-connection) endpoints

def _parse_ids(csv: str | None) -> List[str]:
    if not csv:
        return []
    return [part.strip() for part in csv.split(",") if part.strip()]


@router.get("/rollup/kpis", response_model=MetricsKpiResponse)
async def get_rollup_kpis(
    connection_ids: str,
    start_date: date,
    end_date: date,
    compare_start: date | None = None,
    compare_end: date | None = None,
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
):
    ids = _parse_ids(connection_ids)
    return await service.get_rollup_kpis(ids, start_date, end_date, compare_start, compare_end)


@router.get("/rollup/timeseries_chart")
async def get_rollup_time_series_chart(
    connection_ids: str,
    start_date: date,
    end_date: date,
    metrics: str = "sessions,users",
    service: Ga4MetricsQueryService = Depends(get_metrics_query_service),
):
    ids = _parse_ids(connection_ids)
    points = await service.get_time_series_multi(ids, start_date, end_date)
    if not points:
        return {"categories": [], "series": []}
    requested = [m.strip() for m in metrics.split(",") if m.strip()]
    categories = [p.date.isoformat() for p in points]

    def pick(metric_key):
        return [getattr(p, metric_key) for p in points]

    series = []
    for key in requested:
        if not hasattr(points[0], key):
            continue
        series.append({"name": key.replace("_", " ").title(), "data": pick(key)})

    return {"categories": categories, "series": series}
