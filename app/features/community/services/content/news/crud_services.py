"""CRUD services for news items."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, func, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import NewsItem
from app.features.community.services.content.tenant_mixins import ContentTenantMixin


class NewsCrudService(ContentTenantMixin, BaseService[NewsItem]):
    """Manage news items in the hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, news_id: str) -> Optional[NewsItem]:
        return await super().get_by_id(NewsItem, news_id)

    async def list_news(self, limit: int = 50, offset: int = 0) -> Tuple[List[NewsItem], int]:
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(NewsItem.tenant_id == self.tenant_id)

            stmt = select(NewsItem)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(
                NewsItem.publish_date.desc().nullslast(),
                NewsItem.created_at.desc(),
            ).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(NewsItem.id))
            if filters:
                count_stmt = count_stmt.where(*filters)
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_news", exc)

    async def create_news(self, payload: Dict[str, Any], user) -> NewsItem:
        try:
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            audit = AuditContext.from_user(user) if user else None
            news = NewsItem(tenant_id=tenant_id, **data)
            if audit:
                news.set_created_by(audit.user_email, audit.user_name)

            self.db.add(news)
            await self.db.flush()
            await self.db.refresh(news)
            return news
        except Exception as exc:
            await self.handle_error("create_news", exc)

    async def update_news(self, news_id: str, payload: Dict[str, Any], user) -> Optional[NewsItem]:
        news = await self.get_by_id(NewsItem, news_id)
        if not news:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(news, key, value)

            if user:
                audit = AuditContext.from_user(user)
                news.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
            await self.db.refresh(news)
            return news
        except Exception as exc:
            await self.handle_error("update_news", exc, news_id=news_id)

    async def delete_news(self, news_id: str) -> bool:
        news = await self.get_by_id(NewsItem, news_id)
        if not news:
            return False
        await self.db.delete(news)
        await self.db.flush()
        return True
