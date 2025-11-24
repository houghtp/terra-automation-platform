"""GA4 metrics ingestion and query services."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, select, func, and_
from app.features.core.enhanced_base_service import BaseService
from app.features.core.audit_mixin import AuditContext

from ...models import Ga4DailyMetric
from ...schemas import Ga4DailyMetricPayload, MetricsKpiResponse, MetricsTimeSeriesPoint


class Ga4MetricsIngestionService(BaseService[Ga4DailyMetric]):
    """Store daily GA4 metrics with derived calculations."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def upsert_daily_metrics(self, connection_id: str, payloads: Sequence[Ga4DailyMetricPayload], user=None) -> None:
        try:
            for payload in payloads:
                # ensure tenant scope
                stmt = select(Ga4DailyMetric).where(
                    Ga4DailyMetric.connection_id == connection_id,
                    Ga4DailyMetric.tenant_id == self.tenant_id,
                    Ga4DailyMetric.date == payload.date,
                )
                existing = (await self.db.execute(stmt)).scalar_one_or_none()

                values = payload.model_dump()
                if existing:
                    for key, value in values.items():
                        setattr(existing, key, value)
                    metric = existing
                else:
                    metric = Ga4DailyMetric(
                        tenant_id=self.tenant_id,
                        connection_id=connection_id,
                        **values,
                    )
                    self.db.add(metric)

                if user:
                    audit = AuditContext.from_user(user)
                    metric.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
        except Exception as exc:
            await self.handle_error("upsert_daily_metrics", exc, connection_id=connection_id)


class Ga4MetricsQueryService(BaseService[Ga4DailyMetric]):
    """Query KPIs and time series for GA4 metrics."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_kpis(self, connection_id: str, start: date, end: date, compare_start: Optional[date] = None, compare_end: Optional[date] = None) -> MetricsKpiResponse:
        current = await self._aggregate_range(connection_id, start, end)
        deltas: Dict[str, float] = {}
        available_start, available_end = await self._get_available_range(connection_id)

        if compare_start and compare_end:
            baseline = await self._aggregate_range(connection_id, compare_start, compare_end)
            deltas = self._compute_deltas(current, baseline)

        return MetricsKpiResponse(
            sessions=current.get("sessions"),
            users=current.get("users"),
            conversions=current.get("conversions"),
            engagement_rate=current.get("engagement_rate"),
            bounce_rate=current.get("bounce_rate"),
            new_users=current.get("new_users"),
            avg_engagement_time=current.get("avg_engagement_time"),
            conversion_rate=current.get("conversion_rate"),
            conversions_per_1k=current.get("conversions_per_1k"),
            deltas=deltas,
            available_start=available_start,
            available_end=available_end,
        )

    async def get_time_series(self, connection_id: str, start: date, end: date) -> List[MetricsTimeSeriesPoint]:
        try:
            stmt = select(Ga4DailyMetric).where(
                Ga4DailyMetric.connection_id == connection_id,
                Ga4DailyMetric.date >= start,
                Ga4DailyMetric.date <= end,
            )
            if self.tenant_id is not None:
                stmt = stmt.where(Ga4DailyMetric.tenant_id == self.tenant_id)
            stmt = stmt.order_by(Ga4DailyMetric.date.asc())
            result = await self.db.execute(stmt)
            rows = result.scalars().all()
            return [
                MetricsTimeSeriesPoint(
                    date=row.date,
                    sessions=float(row.sessions) if row.sessions is not None else None,
                    users=float(row.users) if row.users is not None else None,
                    conversions=float(row.conversions) if row.conversions is not None else None,
                    engagement_rate=float(row.engagement_rate) if row.engagement_rate is not None else None,
                    bounce_rate=float(row.bounce_rate) if row.bounce_rate is not None else None,
                    new_users=float(row.new_users) if row.new_users is not None else None,
                    avg_engagement_time=float(row.avg_engagement_time) if row.avg_engagement_time is not None else None,
                    conversion_rate=float(row.conversion_rate) if row.conversion_rate is not None else None,
                    conversions_per_1k=float(row.conversions_per_1k) if row.conversions_per_1k is not None else None,
                )
                for row in rows
            ]
        except Exception as exc:
            await self.handle_error("get_time_series", exc, connection_id=connection_id)

    async def _aggregate_range(self, connection_id: str, start: date, end: date) -> Dict[str, Optional[float]]:
        stmt = select(
            func.sum(Ga4DailyMetric.sessions),
            func.sum(Ga4DailyMetric.users),
            func.sum(Ga4DailyMetric.conversions),
            func.avg(Ga4DailyMetric.engagement_rate),
            func.avg(Ga4DailyMetric.bounce_rate),
            func.sum(Ga4DailyMetric.new_users),
            func.avg(Ga4DailyMetric.avg_engagement_time),
            func.avg(Ga4DailyMetric.conversion_rate),
            func.avg(Ga4DailyMetric.conversions_per_1k),
        ).where(
            Ga4DailyMetric.connection_id == connection_id,
            Ga4DailyMetric.date >= start,
            Ga4DailyMetric.date <= end,
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Ga4DailyMetric.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        row = result.one()
        return {
            "sessions": float(row[0]) if row[0] is not None else None,
            "users": float(row[1]) if row[1] is not None else None,
            "conversions": float(row[2]) if row[2] is not None else None,
            "engagement_rate": float(row[3]) if row[3] is not None else None,
            "bounce_rate": float(row[4]) if row[4] is not None else None,
            "new_users": float(row[5]) if row[5] is not None else None,
            "avg_engagement_time": float(row[6]) if row[6] is not None else None,
            "conversion_rate": float(row[7]) if row[7] is not None else None,
            "conversions_per_1k": float(row[8]) if row[8] is not None else None,
        }

    def _compute_deltas(self, current: Dict[str, Optional[float]], baseline: Dict[str, Optional[float]]) -> Dict[str, float]:
        deltas: Dict[str, float] = {}
        for key in [
            "sessions",
            "users",
            "conversions",
            "engagement_rate",
            "bounce_rate",
            "new_users",
            "avg_engagement_time",
            "conversion_rate",
            "conversions_per_1k",
        ]:
            cur = current.get(key)
            base = baseline.get(key)
            if cur is None or base in (None, 0):
                continue
            deltas[key] = round(((cur - base) / base) * 100, 2)
        return deltas

    async def _get_available_range(self, connection_id: str) -> Tuple[Optional[date], Optional[date]]:
        stmt = select(func.min(Ga4DailyMetric.date), func.max(Ga4DailyMetric.date)).where(
            Ga4DailyMetric.connection_id == connection_id
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Ga4DailyMetric.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        row = result.one()
        min_date = row[0]
        max_date = row[1]
        return (min_date, max_date)

    async def aggregate_multi(self, connection_ids: List[str], start: date, end: date) -> Dict[str, Optional[float]]:
        if not connection_ids:
            return {}
        stmt = select(
            func.sum(Ga4DailyMetric.sessions),
            func.sum(Ga4DailyMetric.users),
            func.sum(Ga4DailyMetric.conversions),
            func.avg(Ga4DailyMetric.engagement_rate),
            func.avg(Ga4DailyMetric.bounce_rate),
            func.sum(Ga4DailyMetric.new_users),
            func.avg(Ga4DailyMetric.avg_engagement_time),
            func.avg(Ga4DailyMetric.conversion_rate),
            func.avg(Ga4DailyMetric.conversions_per_1k),
        ).where(
            Ga4DailyMetric.connection_id.in_(connection_ids),
            Ga4DailyMetric.date >= start,
            Ga4DailyMetric.date <= end,
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Ga4DailyMetric.tenant_id == self.tenant_id)
        row = (await self.db.execute(stmt)).one()
        return {
            "sessions": float(row[0]) if row[0] is not None else None,
            "users": float(row[1]) if row[1] is not None else None,
            "conversions": float(row[2]) if row[2] is not None else None,
            "engagement_rate": float(row[3]) if row[3] is not None else None,
            "bounce_rate": float(row[4]) if row[4] is not None else None,
            "new_users": float(row[5]) if row[5] is not None else None,
            "avg_engagement_time": float(row[6]) if row[6] is not None else None,
            "conversion_rate": float(row[7]) if row[7] is not None else None,
            "conversions_per_1k": float(row[8]) if row[8] is not None else None,
        }

    async def get_rollup_kpis(
        self,
        connection_ids: List[str],
        start: date,
        end: date,
        compare_start: Optional[date] = None,
        compare_end: Optional[date] = None,
    ) -> MetricsKpiResponse:
        current = await self.aggregate_multi(connection_ids, start, end)
        deltas: Dict[str, float] = {}

        if compare_start and compare_end:
            baseline = await self.aggregate_multi(connection_ids, compare_start, compare_end)
            deltas = self._compute_deltas(current, baseline)

        return MetricsKpiResponse(
            sessions=current.get("sessions"),
            users=current.get("users"),
            conversions=current.get("conversions"),
            engagement_rate=current.get("engagement_rate"),
            bounce_rate=current.get("bounce_rate"),
            new_users=current.get("new_users"),
            avg_engagement_time=current.get("avg_engagement_time"),
            conversion_rate=current.get("conversion_rate"),
            conversions_per_1k=current.get("conversions_per_1k"),
            deltas=deltas,
            available_start=None,
            available_end=None,
        )

    async def get_time_series_multi(self, connection_ids: List[str], start: date, end: date) -> List[MetricsTimeSeriesPoint]:
        if not connection_ids:
            return []
        stmt = (
            select(
                Ga4DailyMetric.date,
                func.sum(Ga4DailyMetric.sessions),
                func.sum(Ga4DailyMetric.users),
                func.sum(Ga4DailyMetric.conversions),
                func.avg(Ga4DailyMetric.engagement_rate),
                func.avg(Ga4DailyMetric.bounce_rate),
                func.sum(Ga4DailyMetric.new_users),
                func.avg(Ga4DailyMetric.avg_engagement_time),
                func.avg(Ga4DailyMetric.conversion_rate),
                func.avg(Ga4DailyMetric.conversions_per_1k),
            )
            .where(
                Ga4DailyMetric.connection_id.in_(connection_ids),
                Ga4DailyMetric.date >= start,
                Ga4DailyMetric.date <= end,
            )
            .group_by(Ga4DailyMetric.date)
            .order_by(Ga4DailyMetric.date.asc())
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Ga4DailyMetric.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            MetricsTimeSeriesPoint(
                date=row[0],
                sessions=float(row[1]) if row[1] is not None else None,
                users=float(row[2]) if row[2] is not None else None,
                conversions=float(row[3]) if row[3] is not None else None,
                engagement_rate=float(row[4]) if row[4] is not None else None,
                bounce_rate=float(row[5]) if row[5] is not None else None,
                new_users=float(row[6]) if row[6] is not None else None,
                avg_engagement_time=float(row[7]) if row[7] is not None else None,
                conversion_rate=float(row[8]) if row[8] is not None else None,
                conversions_per_1k=float(row[9]) if row[9] is not None else None,
            )
            for row in rows
        ]
