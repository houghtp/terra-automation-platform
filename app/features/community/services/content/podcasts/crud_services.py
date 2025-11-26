"""CRUD services for podcast episodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, func, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import PodcastEpisode
from app.features.community.services.content.tenant_mixins import ContentTenantMixin


class PodcastCrudService(ContentTenantMixin, BaseService[PodcastEpisode]):
    """Manage podcast episodes in the content hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, episode_id: str) -> Optional[PodcastEpisode]:
        return await super().get_by_id(PodcastEpisode, episode_id)

    async def list_podcasts(self, limit: int = 50, offset: int = 0) -> Tuple[List[PodcastEpisode], int]:
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(PodcastEpisode.tenant_id == self.tenant_id)

            stmt = select(PodcastEpisode)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(
                PodcastEpisode.published_at.desc().nullslast(),
                PodcastEpisode.created_at.desc(),
            ).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(PodcastEpisode.id))
            if filters:
                count_stmt = count_stmt.where(*filters)
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_podcasts", exc)

    async def create_podcast(self, payload: Dict[str, Any], user) -> PodcastEpisode:
        try:
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            audit = AuditContext.from_user(user) if user else None
            episode = PodcastEpisode(tenant_id=tenant_id, **data)
            if audit:
                episode.set_created_by(audit.user_email, audit.user_name)

            self.db.add(episode)
            await self.db.flush()
            await self.db.refresh(episode)
            return episode
        except Exception as exc:
            await self.handle_error("create_podcast", exc)

    async def update_podcast(self, episode_id: str, payload: Dict[str, Any], user) -> Optional[PodcastEpisode]:
        episode = await self.get_by_id(PodcastEpisode, episode_id)
        if not episode:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(episode, key, value)

            if user:
                audit = AuditContext.from_user(user)
                episode.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
            await self.db.refresh(episode)
            return episode
        except Exception as exc:
            await self.handle_error("update_podcast", exc, episode_id=episode_id)

    async def delete_podcast(self, episode_id: str) -> bool:
        episode = await self.get_by_id(PodcastEpisode, episode_id)
        if not episode:
            return False
        await self.db.delete(episode)
        await self.db.flush()
        return True
