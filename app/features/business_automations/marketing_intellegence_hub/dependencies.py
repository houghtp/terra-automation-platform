"""Dependency providers for Marketing Intelligence Hub (GA4 Phase 1)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.deps.tenant import tenant_dependency

from .services import (
    Ga4ConnectionCrudService,
    Ga4MetricsIngestionService,
    Ga4MetricsQueryService,
    Ga4InsightCrudService,
    Ga4ReportCrudService,
    Ga4ClientCrudService,
)


def get_connection_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4ConnectionCrudService:
    return Ga4ConnectionCrudService(session, tenant_id)


def get_metrics_ingestion_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4MetricsIngestionService:
    return Ga4MetricsIngestionService(session, tenant_id)


def get_metrics_query_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4MetricsQueryService:
    return Ga4MetricsQueryService(session, tenant_id)


def get_insight_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4InsightCrudService:
    return Ga4InsightCrudService(session, tenant_id)


def get_report_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4ReportCrudService:
    return Ga4ReportCrudService(session, tenant_id)


def get_client_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> Ga4ClientCrudService:
    return Ga4ClientCrudService(session, tenant_id)
