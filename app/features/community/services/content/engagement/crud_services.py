"""Engagement services for content hub."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from app.features.core.sqlalchemy_imports import AsyncSession, func, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import ContentEngagement
from app.features.community.services.content.tenant_mixins import ContentTenantMixin


class ContentEngagementCrudService(ContentTenantMixin, BaseService[ContentEngagement]):
    """Track member engagement with content hub artefacts."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, engagement_id: str) -> Optional[ContentEngagement]:
        return await super().get_by_id(ContentEngagement, engagement_id)

    async def record_engagement(self, payload: Dict[str, Any], user=None) -> ContentEngagement:
        try:
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            engagement = ContentEngagement(tenant_id=tenant_id, **data)
            if user:
                audit = AuditContext.from_user(user)
                engagement.set_created_by(audit.user_email, audit.user_name)

            self.db.add(engagement)
            await self.db.flush()
            await self.db.refresh(engagement)
            return engagement
        except Exception as exc:
            await self.handle_error("record_engagement", exc)

    async def list_engagement_for_content(
        self, content_id: str, limit: int = 100, offset: int = 0
    ) -> Tuple[List[ContentEngagement], int]:
        try:
            filters = [ContentEngagement.content_id == content_id]
            if self.tenant_id is not None:
                filters.append(ContentEngagement.tenant_id == self.tenant_id)

            stmt = select(ContentEngagement).where(*filters).order_by(
                ContentEngagement.occurred_at.desc()
            ).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(ContentEngagement.id)).where(*filters)
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_engagement_for_content", exc, content_id=content_id)

    async def get_summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Return aggregated engagement stats for dashboard use."""
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(ContentEngagement.tenant_id == self.tenant_id)
            if since is not None:
                filters.append(ContentEngagement.occurred_at >= since)

            stmt = select(
                ContentEngagement.action,
                func.count(ContentEngagement.id),
            )
            if filters:
                stmt = stmt.where(*filters)
            stmt = stmt.group_by(ContentEngagement.action)

            result = await self.db.execute(stmt)
            rows = result.all()
            actions = {row[0]: int(row[1]) for row in rows}

            total_actions = sum(actions.values())

            unique_stmt = select(func.count(func.distinct(ContentEngagement.member_id))).where(
                ContentEngagement.member_id.isnot(None)
            )
            if filters:
                unique_stmt = unique_stmt.where(*filters)

            unique_members = (await self.db.execute(unique_stmt)).scalar_one() or 0

            return {
                "total_actions": int(total_actions),
                "unique_members": int(unique_members),
                "actions": actions,
            }
        except Exception as exc:
            await self.handle_error("get_summary", exc)
