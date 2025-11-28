"""CRUD routes for community content hub (API endpoints for articles, podcasts, videos, news)."""

from typing import Optional

from app.features.core.route_imports import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
    AsyncSession,
    get_db,
    tenant_dependency,
    get_current_user,
    User,
    handle_route_error,
)
from app.features.auth.dependencies import get_admin_user

from ...dependencies import (
    get_article_service,
    get_podcast_service,
    get_video_service,
    get_news_service,
    get_content_engagement_service,
)
from ...schemas import (
    ContentCreate,
    ContentUpdate,
    ContentResponse,
    PodcastCreate,
    PodcastUpdate,
    PodcastResponse,
    VideoCreate,
    VideoUpdate,
    VideoResponse,
    NewsCreate,
    NewsUpdate,
    NewsResponse,
    ContentEngagementCreate,
    ContentEngagementResponse,
)
from ...services import (
    ArticleCrudService,
    PodcastCrudService,
    VideoCrudService,
    NewsCrudService,
    ContentEngagementCrudService,
)
from ...services.content.news.ingest_service import NewsIngestService

router = APIRouter()


# --- Articles API ---

@router.get(
    "/api/articles",
    summary="List articles",
    description="Returns a paginated list of Community Hub articles for the current tenant.",
)
async def list_articles_api(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tags: Optional[str] = Query(default=None, description="Comma separated list of tags"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: ArticleCrudService = Depends(get_article_service),
):
    """List articles with filtering options."""
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    items, total = await service.list_articles(search=search, category=category, tags=tag_list, limit=limit, offset=offset)
    return {
        "data": [item.to_dict() for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/api/articles",
    response_model=ContentResponse,
    status_code=201,
    summary="Create article",
    description="Create a new article within the Community Hub for the current tenant.",
)
async def create_article_api(
    payload: ContentCreate,
    current_user: User = Depends(get_admin_user),
    service: ArticleCrudService = Depends(get_article_service),
):
    """Create a new article."""
    item = await service.create_article(payload.model_dump(), current_user)
    if not item:
        raise HTTPException(status_code=500, detail="Failed to create content item")
    return ContentResponse.model_validate(item, from_attributes=True)


@router.put(
    "/api/articles/{content_id}",
    response_model=ContentResponse,
    summary="Update article",
    description="Update an existing article by ID.",
)
async def update_article_api(
    content_id: str,
    payload: ContentUpdate,
    current_user: User = Depends(get_admin_user),
    service: ArticleCrudService = Depends(get_article_service),
):
    """Update an existing article."""
    item = await service.update_article(content_id, payload.model_dump(exclude_unset=True), current_user)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/api/articles/{content_id}",
    status_code=204,
    summary="Delete article",
    description="Delete an article by ID.",
)
async def delete_article_api(
    content_id: str,
    service: ArticleCrudService = Depends(get_article_service),
):
    """Delete an article."""
    deleted = await service.delete_article(content_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Content not found")
    return Response(status_code=204)


# --- Podcasts API ---

@router.get(
    "/api/podcasts",
    summary="List podcasts",
    description="Returns a paginated list of podcast episodes for the current tenant.",
)
async def list_podcasts_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: PodcastCrudService = Depends(get_podcast_service),
):
    """List podcast episodes."""
    items, total = await service.list_podcasts(limit=limit, offset=offset)
    return {
        "data": [episode.to_dict() for episode in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/api/podcasts",
    response_model=PodcastResponse,
    status_code=201,
    summary="Create podcast episode",
    description="Create a new podcast episode within the Community Hub.",
)
async def create_podcast_api(
    payload: PodcastCreate,
    current_user: User = Depends(get_admin_user),
    service: PodcastCrudService = Depends(get_podcast_service),
):
    """Create a new podcast episode."""
    episode = await service.create_podcast(payload.model_dump(), current_user)
    if not episode:
        raise HTTPException(status_code=500, detail="Failed to create podcast episode")
    return PodcastResponse.model_validate(episode, from_attributes=True)


@router.put(
    "/api/podcasts/{episode_id}",
    response_model=PodcastResponse,
    summary="Update podcast episode",
    description="Update an existing podcast episode by ID.",
)
async def update_podcast_api(
    episode_id: str,
    payload: PodcastUpdate,
    current_user: User = Depends(get_admin_user),
    service: PodcastCrudService = Depends(get_podcast_service),
):
    """Update an existing podcast episode."""
    episode = await service.update_podcast(episode_id, payload.model_dump(exclude_unset=True), current_user)
    if not episode:
        raise HTTPException(status_code=404, detail="Podcast episode not found")
    return PodcastResponse.model_validate(episode, from_attributes=True)


@router.delete(
    "/api/podcasts/{episode_id}",
    status_code=204,
    summary="Delete podcast episode",
    description="Delete a podcast episode by ID.",
)
async def delete_podcast_api(
    episode_id: str,
    service: PodcastCrudService = Depends(get_podcast_service),
):
    """Delete a podcast episode."""
    deleted = await service.delete_podcast(episode_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Podcast episode not found")
    return Response(status_code=204)


# --- Videos API ---

@router.get(
    "/api/videos",
    summary="List videos",
    description="Returns a paginated list of training videos for the current tenant.",
)
async def list_videos_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: VideoCrudService = Depends(get_video_service),
):
    """List training videos."""
    items, total = await service.list_videos(limit=limit, offset=offset)
    return {
        "data": [video.to_dict() for video in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/api/videos",
    response_model=VideoResponse,
    status_code=201,
    summary="Create video resource",
    description="Create a new video resource within the Community Hub.",
)
async def create_video_api(
    payload: VideoCreate,
    current_user: User = Depends(get_admin_user),
    service: VideoCrudService = Depends(get_video_service),
):
    """Create a new video resource."""
    video = await service.create_video(payload.model_dump(), current_user)
    if not video:
        raise HTTPException(status_code=500, detail="Failed to create video resource")
    return VideoResponse.model_validate(video, from_attributes=True)


@router.put(
    "/api/videos/{video_id}",
    response_model=VideoResponse,
    summary="Update video resource",
    description="Update an existing video resource by ID.",
)
async def update_video_api(
    video_id: str,
    payload: VideoUpdate,
    current_user: User = Depends(get_admin_user),
    service: VideoCrudService = Depends(get_video_service),
):
    """Update an existing video resource."""
    video = await service.update_video(video_id, payload.model_dump(exclude_unset=True), current_user)
    if not video:
        raise HTTPException(status_code=404, detail="Video resource not found")
    return VideoResponse.model_validate(video, from_attributes=True)


@router.delete(
    "/api/videos/{video_id}",
    status_code=204,
    summary="Delete video resource",
    description="Delete a video resource by ID.",
)
async def delete_video_api(
    video_id: str,
    service: VideoCrudService = Depends(get_video_service),
):
    """Delete a video resource."""
    deleted = await service.delete_video(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video resource not found")
    return Response(status_code=204)


# --- News API ---

@router.get(
    "/api/news",
    summary="List news items",
    description="Returns curated news articles for the current tenant.",
)
async def list_news_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: NewsCrudService = Depends(get_news_service),
):
    """List news items."""
    items, total = await service.list_news(limit=limit, offset=offset)
    return {
        "data": [news.to_dict() for news in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/api/news/ingest",
    summary="Ingest latest news via Firecrawl search",
    status_code=201,
)
async def ingest_news_api(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
):
    """Fetch latest news for US financial advisors/wealth management and store as news items."""
    service = NewsIngestService(db, tenant_id=None)
    try:
        items = await service.ingest_latest(current_user)
        await db.commit()
        headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
        return Response(status_code=201, content={"ingested": len(items)}, headers=headers)
    except Exception as exc:
        await db.rollback()
        handle_route_error("ingest_news_api", exc)
        raise HTTPException(status_code=500, detail="Failed to ingest news")


@router.post(
    "/api/news",
    response_model=NewsResponse,
    status_code=201,
    summary="Create news item",
    description="Create a curated news entry within the Community Hub.",
)
async def create_news_api(
    payload: NewsCreate,
    current_user: User = Depends(get_admin_user),
    service: NewsCrudService = Depends(get_news_service),
):
    """Create a new news item."""
    news = await service.create_news(payload.model_dump(), current_user)
    if not news:
        raise HTTPException(status_code=500, detail="Failed to create news item")
    return NewsResponse.model_validate(news, from_attributes=True)


@router.put(
    "/api/news/{news_id}",
    response_model=NewsResponse,
    summary="Update news item",
    description="Update an existing news entry by ID.",
)
async def update_news_api(
    news_id: str,
    payload: NewsUpdate,
    current_user: User = Depends(get_admin_user),
    service: NewsCrudService = Depends(get_news_service),
):
    """Update an existing news item."""
    news = await service.update_news(news_id, payload.model_dump(exclude_unset=True), current_user)
    if not news:
        raise HTTPException(status_code=404, detail="News item not found")
    return NewsResponse.model_validate(news, from_attributes=True)


@router.delete(
    "/api/news/{news_id}",
    status_code=204,
    summary="Delete news item",
    description="Delete a news entry by ID.",
)
async def delete_news_api(
    news_id: str,
    service: NewsCrudService = Depends(get_news_service),
):
    """Delete a news item."""
    deleted = await service.delete_news(news_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="News item not found")
    return Response(status_code=204)


# --- Engagement API ---

@router.post(
    "/api/articles/{content_id}/engagement",
    response_model=ContentEngagementResponse,
    status_code=201,
    summary="Record content engagement",
    description="Record a member engagement action (view, like, share) against an article.",
)
async def record_engagement_api(
    content_id: str,
    payload: ContentEngagementCreate,
    current_user: User = Depends(get_current_user),
    service: ContentEngagementCrudService = Depends(get_content_engagement_service),
):
    """Record engagement on an article."""
    data = payload.model_dump()
    data["content_id"] = content_id
    engagement = await service.record_engagement(data, current_user)
    if not engagement:
        raise HTTPException(status_code=500, detail="Failed to record engagement")
    return ContentEngagementResponse.model_validate(engagement, from_attributes=True)


__all__ = ["router"]
