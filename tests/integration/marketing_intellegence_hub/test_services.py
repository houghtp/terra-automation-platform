import pytest
from datetime import date

from app.features.business_automations.marketing_intellegence_hub.schemas import (
    Ga4ConnectionCreate,
    Ga4DailyMetricPayload,
)
from app.features.business_automations.marketing_intellegence_hub.services import (
    Ga4ConnectionCrudService,
    Ga4MetricsIngestionService,
    Ga4MetricsQueryService,
)


class DummyUser:
    def __init__(self, email: str = "admin@example.com", name: str = "Admin"):
        self.email = email
        self.name = name


def _token_data():
    return {"refresh_token": "dummy-refresh", "access_token": "dummy-access"}


@pytest.mark.asyncio
async def test_connection_and_metrics_flow(test_db_session):
    tenant_id = "tenant_ga4_test"
    connection_service = Ga4ConnectionCrudService(test_db_session, tenant_id)
    ingestion_service = Ga4MetricsIngestionService(test_db_session, tenant_id)
    query_service = Ga4MetricsQueryService(test_db_session, tenant_id)

    conn = await connection_service.create_connection(
        Ga4ConnectionCreate(property_id="prop_123", property_name="Test Property"),
        token_data=_token_data(),
        user=DummyUser(),
    )
    assert conn.id is not None

    payloads = [
        Ga4DailyMetricPayload(
            date=date(2025, 1, 1),
            sessions=100,
            users=80,
            new_users=20,
            pageviews=150,
            bounce_rate=40,
            engaged_sessions=70,
            conversions=10,
            engagement_rate=60,
            avg_engagement_time=120,
            conversion_rate=0.1,
            conversions_per_1k=100,
        )
    ]
    await ingestion_service.upsert_daily_metrics(conn.id, payloads, DummyUser())

    kpis = await query_service.get_kpis(conn.id, date(2025, 1, 1), date(2025, 1, 1))
    assert kpis.sessions == 100
    assert kpis.new_users == 20
    assert kpis.conversion_rate == 0.1
    assert kpis.conversions_per_1k == 100
    assert kpis.available_start == date(2025, 1, 1)
    assert kpis.available_end == date(2025, 1, 1)
    timeseries = await query_service.get_time_series(conn.id, date(2025, 1, 1), date(2025, 1, 1))
    assert timeseries.points[0].sessions == 100
    assert timeseries.points[0].new_users == 20
