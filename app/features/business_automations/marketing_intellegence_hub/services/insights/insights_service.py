"""Generate simple insights for GA4 metrics."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.features.business_automations.marketing_intellegence_hub.services.metrics.crud_services import Ga4MetricsQueryService


class Ga4InsightsService:
    def __init__(self, metrics_service: Ga4MetricsQueryService):
        self.metrics_service = metrics_service

    async def simple_insight(self, connection_id: str, end_date: date, days: int = 30) -> str:
        """Return a short, human-friendly insight comparing current vs prior period."""
        start_date = end_date - timedelta(days=days - 1)
        compare_end = start_date - timedelta(days=1)
        compare_start = compare_end - timedelta(days=days - 1)

        kpi = await self.metrics_service.get_kpis(
            connection_id,
            start_date,
            end_date,
            compare_start=compare_start,
            compare_end=compare_end,
        )
        deltas = kpi.deltas or {}

        def pct(key):
            val = deltas.get(key)
            return f"{val:+.1f}%" if val is not None else None

        parts = []
        if pct("conversions"):
            parts.append(f"conversions {pct('conversions')}")
        if pct("conversion_rate"):
            parts.append(f"conversion rate {pct('conversion_rate')}")
        if pct("sessions") and not parts:
            parts.append(f"sessions {pct('sessions')}")
        if pct("engagement_rate"):
            parts.append(f"engagement {pct('engagement_rate')}")

        if not parts:
            return "No significant change detected."
        return " | ".join(parts)
