"""GA4 report services."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from app.features.core.sqlalchemy_imports import AsyncSession, select
from app.features.core.enhanced_base_service import BaseService
from app.features.core.audit_mixin import AuditContext

from ...models import Ga4Report
from ...schemas import Ga4ReportCreate


class Ga4ReportCrudService(BaseService[Ga4Report]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def list_reports(self, connection_id: str, limit: int = 50) -> List[Ga4Report]:
        try:
            stmt = select(Ga4Report).where(Ga4Report.connection_id == connection_id)
            if self.tenant_id is not None:
                stmt = stmt.where(Ga4Report.tenant_id == self.tenant_id)
            stmt = stmt.order_by(Ga4Report.created_at.desc()).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_error("list_reports", exc, connection_id=connection_id)

    async def create_report(self, connection_id: str, payload: Ga4ReportCreate, user=None) -> Ga4Report:
        try:
            audit = AuditContext.from_user(user) if user else None
            report = Ga4Report(
                tenant_id=self.tenant_id,
                connection_id=connection_id,
                period=payload.period,
                report_type=payload.report_type,
                html_url=payload.html_url,
                pdf_url=payload.pdf_url,
                status=payload.status,
            )
            if audit:
                report.set_created_by(audit.user_email, audit.user_name)
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)
            return report
        except Exception as exc:
            await self.handle_error("create_report", exc, connection_id=connection_id)

    async def mark_sent(self, report_id: str, sent_at: Optional[datetime] = None) -> Optional[Ga4Report]:
        report = await self.get_by_id(Ga4Report, report_id)
        if not report:
            return None
        try:
            report.sent_at = sent_at or datetime.utcnow()
            report.status = "sent"
            await self.db.flush()
            await self.db.refresh(report)
            return report
        except Exception as exc:
            await self.handle_error("mark_sent", exc, report_id=report_id)
