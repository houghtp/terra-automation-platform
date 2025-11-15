"""Dependency helpers for community services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.tenant import tenant_dependency
from app.features.core.database import get_db

from .services import (
    MemberService,
    PartnerService,
    GroupService,
    GroupPostService,
    GroupCommentService,
    MessageService,
    EventService,
    PollService,
    PollVoteService,
    ContentService,
    PodcastService,
    VideoService,
    NewsService,
    ContentEngagementService,
)


async def get_member_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> MemberService:
    """Provide a MemberService scoped to the current tenant."""
    return MemberService(session, tenant_id)


async def get_partner_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PartnerService:
    """Provide a PartnerService scoped to the current tenant."""
    return PartnerService(session, tenant_id)


async def get_group_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupService:
    return GroupService(session, tenant_id)


async def get_group_post_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupPostService:
    return GroupPostService(session, tenant_id)


async def get_group_comment_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> GroupCommentService:
    return GroupCommentService(session, tenant_id)


async def get_message_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> MessageService:
    return MessageService(session, tenant_id)


async def get_event_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> EventService:
    return EventService(session, tenant_id)


async def get_poll_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PollService:
    return PollService(session, tenant_id)


async def get_poll_vote_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PollVoteService:
    return PollVoteService(session, tenant_id)


async def get_content_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> ContentService:
    return ContentService(session, tenant_id)


async def get_podcast_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> PodcastService:
    return PodcastService(session, tenant_id)


async def get_video_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> VideoService:
    return VideoService(session, tenant_id)


async def get_news_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> NewsService:
    return NewsService(session, tenant_id)


async def get_content_engagement_service(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
) -> ContentEngagementService:
    return ContentEngagementService(session, tenant_id)
