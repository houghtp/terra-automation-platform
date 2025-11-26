"""Dependency helpers for community services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.tenant import tenant_dependency
from app.features.core.database import get_db

from .services import (
    MemberCrudService,
    MemberFormService,
    PartnerCrudService,
    GroupCrudService,
    GroupPostCrudService,
    GroupCommentCrudService,
    MessageCrudService,
    EventCrudService,
    PollCrudService,
    PollVoteCrudService,
    ArticleCrudService,
    PodcastCrudService,
    VideoCrudService,
    NewsCrudService,
    ContentEngagementCrudService,
)


async def get_member_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> MemberCrudService:
    """Provide a MemberCrudService scoped to the current tenant."""
    return MemberCrudService(session, tenant_id)


async def get_member_form_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> MemberFormService:
    """Provide a MemberFormService scoped to the current tenant."""
    return MemberFormService(session, tenant_id)


async def get_partner_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PartnerCrudService:
    """Provide a PartnerCrudService scoped to the current tenant."""
    return PartnerCrudService(session, tenant_id)


async def get_group_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupCrudService:
    # Groups are global within the community hub, so bypass tenant scoping.
    return GroupCrudService(session, tenant_id=None)


async def get_group_post_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupPostCrudService:
    # Group posts are shared hub-wide (global).
    return GroupPostCrudService(session, tenant_id=None)


async def get_group_comment_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupCommentCrudService:
    # Comments inherit the global group scope.
    return GroupCommentCrudService(session, tenant_id=None)


async def get_message_service(
    session: AsyncSession = Depends(get_db),
) -> MessageCrudService:
    # Messaging should span community/global users, so we bypass tenant scoping here.
    return MessageCrudService(session, tenant_id=None)


async def get_event_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> EventCrudService:
    # Events are community-wide; bypass tenant scoping.
    return EventCrudService(session, tenant_id=None)


async def get_poll_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PollCrudService:
    return PollCrudService(session, tenant_id)


async def get_poll_vote_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PollVoteCrudService:
    return PollVoteCrudService(session, tenant_id)


async def get_article_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> ArticleCrudService:
    return ArticleCrudService(session, tenant_id)


async def get_podcast_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PodcastCrudService:
    return PodcastCrudService(session, tenant_id)


async def get_video_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> VideoCrudService:
    return VideoCrudService(session, tenant_id)


async def get_news_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> NewsCrudService:
    return NewsCrudService(session, tenant_id)


async def get_content_engagement_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> ContentEngagementCrudService:
    return ContentEngagementCrudService(session, tenant_id)
