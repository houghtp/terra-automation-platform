"""GA4 insights services."""

from __future__ import annotations

from typing import List, Optional

from app.features.core.sqlalchemy_imports import AsyncSession, select
from app.features.core.enhanced_base_service import BaseService
from app.features.core.audit_mixin import AuditContext

from ...models import Ga4Insight
from ...schemas import Ga4InsightCreate


class Ga4InsightCrudService(BaseService[Ga4Insight]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def list_insights(self, connection_id: str, limit: int = 20) -> List[Ga4Insight]:
        try:
            stmt = select(Ga4Insight).where(Ga4Insight.connection_id == connection_id)
            if self.tenant_id is not None:
                stmt = stmt.where(Ga4Insight.tenant_id == self.tenant_id)
            stmt = stmt.order_by(Ga4Insight.generated_at.desc()).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_error("list_insights", exc, connection_id=connection_id)

    async def create_insight(self, connection_id: str, payload: Ga4InsightCreate, user=None) -> Ga4Insight:
        try:
            audit = AuditContext.from_user(user) if user else None
            insight = Ga4Insight(
                tenant_id=self.tenant_id,
                connection_id=connection_id,
                period=payload.period,
                summary_type=payload.summary_type,
                content=payload.content,
                source=payload.source,
            )
            if audit:
                insight.set_created_by(audit.user_email, audit.user_name)
            self.db.add(insight)
            await self.db.flush()
            await self.db.refresh(insight)
            return insight
        except Exception as exc:
            await self.handle_error("create_insight", exc, connection_id=connection_id)
