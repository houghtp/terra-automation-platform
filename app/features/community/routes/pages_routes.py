"""HTML page routes for the community feature."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.features.core.templates import templates

from ..dependencies import (
    get_member_service,
    get_partner_service,
    get_group_service,
    get_event_service,
    get_poll_service,
    get_message_service,
    get_content_service,
    get_podcast_service,
    get_video_service,
    get_news_service,
    get_content_engagement_service,
)
from ..services import (
    MemberService,
    PartnerService,
    GroupService,
    EventService,
    PollService,
    MessageService,
    ContentService,
    PodcastService,
    VideoService,
    NewsService,
    ContentEngagementService,
)

router = APIRouter(tags=["community-pages"])


async def _community_dashboard_context(
    member_service: MemberService,
    partner_service: PartnerService,
) -> dict:
    """Build context for the community landing page."""
    member_count = await member_service.count_all()
    partner_count = await partner_service.count_all()

    return {
        "member_count": member_count,
        "partner_count": partner_count,
    }


def _summarize_copy(value: str | None, limit: int = 140) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


async def _build_announcements(
    event_service: EventService,
    poll_service: PollService,
    content_service: ContentService,
    news_service: NewsService,
) -> list[dict]:
    announcements: list[dict] = []

    events, _ = await event_service.list_events(limit=1, offset=0)
    if events:
        event = events[0]
        meta_value = None
        if getattr(event, "start_date", None):
            meta_value = event.start_date.strftime("%b %d")
        announcements.append(
            {
                "label": "Upcoming Event",
                "icon": "ti ti-calendar-event",
                "title": event.title,
                "body": _summarize_copy(event.description),
                "meta": meta_value,
                "link": "/features/community/events",
                "link_text": "View calendar",
            }
        )

    polls, _ = await poll_service.list_polls(limit=1, offset=0)
    if polls:
        poll = polls[0]
        meta_value = None
        if getattr(poll, "expires_at", None):
            meta_value = poll.expires_at.strftime("%b %d")
        option_count = len(getattr(poll, "options", []) or [])
        body = f"{option_count} option{'s' if option_count != 1 else ''} • Cast your vote"
        announcements.append(
            {
                "label": "Open Poll",
                "icon": "ti ti-ballot",
                "title": poll.question,
                "body": body,
                "meta": meta_value,
                "link": "/features/community/polls",
                "link_text": "Vote now",
            }
        )

    articles, _ = await content_service.list_content(limit=1, offset=0)
    if articles:
        article = articles[0]
        announcements.append(
            {
                "label": "New Insight",
                "icon": "ti ti-article",
                "title": article.title,
                "body": _summarize_copy(article.body_md),
                "meta": article.category,
                "link": "/features/community/content",
                "link_text": "Read article",
            }
        )

    news_items, _ = await news_service.list_news(limit=1, offset=0)
    if news_items:
        news = news_items[0]
        meta_value = news.source or news.category
        announcements.append(
            {
                "label": "Industry News",
                "icon": "ti ti-speakerphone",
                "title": news.headline,
                "body": _summarize_copy(news.summary),
                "meta": meta_value,
                "link": news.url,
                "link_text": "Open article",
            }
        )

    return announcements[:4]


@router.get("/", response_class=HTMLResponse)
async def community_home(
    request: Request,
    current_user: User = Depends(get_current_user),
    member_service: MemberService = Depends(get_member_service),
    partner_service: PartnerService = Depends(get_partner_service),
    event_service: EventService = Depends(get_event_service),
    poll_service: PollService = Depends(get_poll_service),
    content_service: ContentService = Depends(get_content_service),
    news_service: NewsService = Depends(get_news_service),
):
    """Render the community landing page with high-level metrics."""
    context = await _community_dashboard_context(member_service, partner_service)
    announcements = await _build_announcements(
        event_service=event_service,
        poll_service=poll_service,
        content_service=content_service,
        news_service=news_service,
    )
    context.update(
        {
            "request": request,
            "user": current_user,
            "page_title": "Community Hub",
            "page_description": "Connect with peers, partners, and shared insights.",
            "page_icon": "users",
            "announcements": announcements,
        }
    )
    return templates.TemplateResponse("community/index.html", context)


@router.get("/members", response_class=HTMLResponse)
async def members_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    member_service: MemberService = Depends(get_member_service),
):
    """Render the members directory."""
    total = await member_service.count_all()
    return templates.TemplateResponse(
        "community/members/list.html",
        {
            "request": request,
            "user": current_user,
            "member_total": total,
            "page_title": "Members Directory",
            "page_description": "Search, filter, and manage community members.",
            "page_icon": "address-book",
        },
    )


@router.get("/partners", response_class=HTMLResponse)
async def partners_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    partner_service: PartnerService = Depends(get_partner_service),
):
    """Render the partner directory shell."""
    total = await partner_service.count_all()
    return templates.TemplateResponse(
        "community/partners/list.html",
        {
            "request": request,
            "user": current_user,
            "partner_total": total,
            "page_title": "Partner Directory",
            "page_description": "Discover partner offerings and strategic alliances.",
            "page_icon": "handshake",
        },
    )


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
):
    total = await group_service.count_all()
    return templates.TemplateResponse(
        "community/groups/list.html",
        {
            "request": request,
            "user": current_user,
            "groups_total": total,
            "page_title": "Community Groups",
            "page_description": "Create cohorts, manage membership, and foster discussion threads.",
            "page_icon": "users-group",
        },
    )


@router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    conversations, total = await message_service.list_conversations(member_id=current_user.id, limit=1, offset=0)
    return templates.TemplateResponse(
        "community/messages/inbox.html",
        {
            "request": request,
            "user": current_user,
            "conversation_count": total,
            "page_title": "Messages",
            "page_description": "Keep in touch with members across your tenant.",
            "page_icon": "messages",
            "member_id": current_user.id,
        },
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    total = await event_service.count_all()
    return templates.TemplateResponse(
        "community/events/list.html",
        {
            "request": request,
            "user": current_user,
            "events_total": total,
            "page_title": "Events Calendar",
            "page_description": "Plan webinars, workshops, and regional meetups for advisors.",
            "page_icon": "calendar-event",
        },
    )


@router.get("/polls", response_class=HTMLResponse)
async def polls_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    poll_service: PollService = Depends(get_poll_service),
):
    _, total = await poll_service.list_polls(limit=1, offset=0)
    return templates.TemplateResponse(
        "community/polls/list.html",
        {
            "request": request,
            "user": current_user,
            "polls_total": total,
            "page_title": "Community Polls",
            "page_description": "Launch surveys and measure engagement across tenants.",
            "page_icon": "chart-bar",
        },
    )


@router.get("/content", response_class=HTMLResponse)
async def content_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service),
    podcast_service: PodcastService = Depends(get_podcast_service),
    video_service: VideoService = Depends(get_video_service),
    news_service: NewsService = Depends(get_news_service),
    engagement_service: ContentEngagementService = Depends(get_content_engagement_service),
):
    articles, article_total = await content_service.list_content(limit=5, offset=0)
    podcasts, podcast_total = await podcast_service.list_podcasts(limit=5, offset=0)
    videos, video_total = await video_service.list_videos(limit=5, offset=0)
    news_items, news_total = await news_service.list_news(limit=5, offset=0)
    engagement_summary = await engagement_service.get_summary()

    return templates.TemplateResponse(
        "community/content/dashboard.html",
        {
            "request": request,
            "user": current_user,
            "articles": articles,
            "podcasts": podcasts,
            "videos": videos,
            "news_items": news_items,
            "article_total": article_total,
            "podcast_total": podcast_total,
            "video_total": video_total,
            "news_total": news_total,
            "engagement_summary": engagement_summary,
            "page_title": "Content & Learning Hub",
            "page_description": "Publish articles, podcasts, videos, and curated news for your advisors.",
            "page_icon": "book",
        },
    )
