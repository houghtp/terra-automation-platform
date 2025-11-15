"""
Services powering the Content & Learning hub (Phase 3).

Provides tenant-scoped CRUD helpers for articles, podcasts, videos,
news, and engagement tracking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import (
    CommunityContent,
    PodcastEpisode,
    VideoResource,
    NewsItem,
    ContentEngagement,
)


class _TenantResolverMixin:
    """Shared helper for determining tenant ID for new records."""

    def _tenant_id_for_payload(self, payload: Dict[str, Any]) -> str:
        tenant_id = self.tenant_id or payload.get("tenant_id")
        if tenant_id in (None, "global"):
            raise ValueError("Tenant context is required for this operation.")
        return tenant_id


class ContentService(TenantScopedCRUDService[CommunityContent], _TenantResolverMixin):
    """Manage long-form articles within the learning hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, CommunityContent)

    async def list_content(
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
            await self.handle_service_error("list_content", exc)

    async def create_content(self, payload: Dict[str, Any], user) -> CommunityContent:
        try:
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
            data.pop("tenant_id", None)

            audit = AuditContext.from_user(user) if user else None

            item = CommunityContent(tenant_id=tenant_id, **data)
            if audit:
                item.set_created_by(audit.user_email, audit.user_name)

            self.db.add(item)
            await self.db.flush()
            await self.db.refresh(item)
            return item
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Unable to create content item.") from exc
        except Exception as exc:
            await self.handle_service_error("create_content", exc)

    async def update_content(self, content_id: str, payload: Dict[str, Any], user) -> Optional[CommunityContent]:
        item = await self.get_by_id(content_id)
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
            await self.handle_service_error("update_content", exc, content_id)

    async def delete_content(self, content_id: str) -> bool:
        return await self.delete_by_id(content_id)


class PodcastService(TenantScopedCRUDService[PodcastEpisode], _TenantResolverMixin):
    """Manage podcast episodes in the content hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, PodcastEpisode)

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
            await self.handle_service_error("list_podcasts", exc)

    async def create_podcast(self, payload: Dict[str, Any], user) -> PodcastEpisode:
        try:
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
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
            await self.handle_service_error("create_podcast", exc)

    async def update_podcast(self, episode_id: str, payload: Dict[str, Any], user) -> Optional[PodcastEpisode]:
        episode = await self.get_by_id(episode_id)
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
            await self.handle_service_error("update_podcast", exc, episode_id)

    async def delete_podcast(self, episode_id: str) -> bool:
        return await self.delete_by_id(episode_id)


class VideoService(TenantScopedCRUDService[VideoResource], _TenantResolverMixin):
    """Manage video resources within the hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, VideoResource)

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
            await self.handle_service_error("list_videos", exc)

    async def create_video(self, payload: Dict[str, Any], user) -> VideoResource:
        try:
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
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
            await self.handle_service_error("create_video", exc)

    async def update_video(self, video_id: str, payload: Dict[str, Any], user) -> Optional[VideoResource]:
        resource = await self.get_by_id(video_id)
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
            await self.handle_service_error("update_video", exc, video_id)

    async def delete_video(self, video_id: str) -> bool:
        return await self.delete_by_id(video_id)


class NewsService(TenantScopedCRUDService[NewsItem], _TenantResolverMixin):
    """Manage news items in the hub."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, NewsItem)

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
            await self.handle_service_error("list_news", exc)

    async def create_news(self, payload: Dict[str, Any], user) -> NewsItem:
        try:
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
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
            await self.handle_service_error("create_news", exc)

    async def update_news(self, news_id: str, payload: Dict[str, Any], user) -> Optional[NewsItem]:
        news = await self.get_by_id(news_id)
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
            await self.handle_service_error("update_news", exc, news_id)

    async def delete_news(self, news_id: str) -> bool:
        return await self.delete_by_id(news_id)


class ContentEngagementService(TenantScopedCRUDService[ContentEngagement], _TenantResolverMixin):
    """Track member engagement with content hub artefacts."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, ContentEngagement)

    async def record_engagement(self, payload: Dict[str, Any], user=None) -> ContentEngagement:
        try:
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
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
            await self.handle_service_error("record_engagement", exc)

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
            await self.handle_service_error("list_engagement_for_content", exc, content_id)

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
            await self.handle_service_error("get_summary", exc)
