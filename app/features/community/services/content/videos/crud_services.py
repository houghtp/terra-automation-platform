"""CRUD services for video resources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, func, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import VideoResource
from app.features.community.services.content.tenant_mixins import ContentTenantMixin


class VideoCrudService(ContentTenantMixin, BaseService[VideoResource]):
    """Manage video resources within the hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, video_id: str) -> Optional[VideoResource]:
        return await super().get_by_id(VideoResource, video_id)

    async def list_videos(self, limit: int = 50, offset: int = 0) -> Tuple[List[VideoResource], int]:
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(VideoResource.tenant_id == self.tenant_id)

            stmt = select(VideoResource)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(
                VideoResource.published_at.desc().nullslast(),
                VideoResource.created_at.desc(),
            ).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(VideoResource.id))
            if filters:
                count_stmt = count_stmt.where(*filters)
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_videos", exc)

    async def create_video(self, payload: Dict[str, Any], user) -> VideoResource:
        try:
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            audit = AuditContext.from_user(user) if user else None
            resource = VideoResource(tenant_id=tenant_id, **data)
            if audit:
                resource.set_created_by(audit.user_email, audit.user_name)

            self.db.add(resource)
            await self.db.flush()
            await self.db.refresh(resource)
            return resource
        except Exception as exc:
            await self.handle_error("create_video", exc)

    async def update_video(self, video_id: str, payload: Dict[str, Any], user) -> Optional[VideoResource]:
        resource = await self.get_by_id(VideoResource, video_id)
        if not resource:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(resource, key, value)

            if user:
                audit = AuditContext.from_user(user)
                resource.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
            await self.db.refresh(resource)
            return resource
        except Exception as exc:
            await self.handle_error("update_video", exc, video_id=video_id)

    async def delete_video(self, video_id: str) -> bool:
        resource = await self.get_by_id(VideoResource, video_id)
        if not resource:
            return False
        await self.db.delete(resource)
        await self.db.flush()
        return True
