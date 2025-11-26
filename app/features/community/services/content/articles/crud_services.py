"""CRUD services for Community Hub articles."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, func, or_, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import CommunityContent
from app.features.community.services.content.tenant_mixins import ContentTenantMixin


class ArticleCrudService(ContentTenantMixin, BaseService[CommunityContent]):
    """Manage long-form articles within the learning hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, content_id: str) -> Optional[CommunityContent]:
        return await super().get_by_id(CommunityContent, content_id)

    async def list_articles(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CommunityContent], int]:
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(CommunityContent.tenant_id == self.tenant_id)

            if category:
                filters.append(CommunityContent.category == category)

            if tags:
                filters.append(CommunityContent.tags.contains(list(tags)))

            if search:
                like = f"%{search.lower()}%"
                filters.append(
                    or_(
                        func.lower(CommunityContent.title).like(like),
                        func.lower(CommunityContent.body_md).like(like),
                    )
                )

            stmt = select(CommunityContent)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(
                CommunityContent.published_at.desc().nullslast(),
                CommunityContent.created_at.desc(),
            ).offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(CommunityContent.id))
            if filters:
                count_stmt = count_stmt.where(*filters)
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_articles", exc)

    async def create_article(self, payload: Dict[str, Any], user) -> CommunityContent:
        try:
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            audit = AuditContext.from_user(user) if user else None

            item = CommunityContent(tenant_id=tenant_id, **data)
            if audit:
                item.set_created_by(audit.user_email, audit.user_name)

            self.db.add(item)
            await self.db.flush()
            await self.db.refresh(item)
            return item
        except Exception as exc:
            await self.handle_error("create_article", exc)

    async def update_article(self, content_id: str, payload: Dict[str, Any], user) -> Optional[CommunityContent]:
        item = await self.get_by_id(CommunityContent, content_id)
        if not item:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(item, key, value)

            if user:
                audit = AuditContext.from_user(user)
                item.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
            await self.db.refresh(item)
            return item
        except Exception as exc:
            await self.handle_error("update_article", exc, content_id=content_id)

    async def delete_article(self, content_id: str) -> bool:
        item = await self.get_by_id(CommunityContent, content_id)
        if not item:
            return False
        await self.db.delete(item)
        await self.db.flush()
        return True
