"""Form routes for community content hub (articles, podcasts, videos, news)."""

import markdown
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Dict, List, Optional

from pydantic import ValidationError

import markdown

from app.features.auth.dependencies import get_admin_user
from app.features.core.validation import FormHandler
from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    Response,
    templates,
    get_db,
    tenant_dependency,
    User,
    AsyncSession,
    commit_transaction,
    get_current_user,
)

from ...dependencies import (
    get_article_service,
    get_podcast_service,
    get_video_service,
    get_news_service,
)
from ...schemas import (
    ContentCreate,
    ContentUpdate,
    PodcastCreate,
    PodcastUpdate,
    VideoCreate,
    VideoUpdate,
    NewsCreate,
    NewsUpdate,
)
from ...services import (
    ArticleCrudService,
    PodcastCrudService,
    VideoCrudService,
    NewsCrudService,
)

router = APIRouter()


# Helper functions

def _parse_comma_field(raw: str) -> List[str]:
    """Parse comma-separated field into list."""
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_datetime_field(raw: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    """Parse datetime field with validation."""
    if not raw:
        return None, None
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed, None
    except ValueError:
        return None, "Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."


def _validation_errors_to_dict(error: ValidationError) -> Dict[str, List[str]]:
    """Convert Pydantic validation errors to dictionary format."""
    errors: Dict[str, List[str]] = {}
    for err in error.errors():
        field = err["loc"][0]
        errors.setdefault(field, []).append(err["msg"])
    return errors


def _article_to_namespace(article) -> SimpleNamespace:
    """Convert article to namespace for templates."""
    data = article.to_dict()
    data["tags_csv"] = ", ".join(data.get("tags", []))
    return SimpleNamespace(**data)


def _podcast_to_namespace(episode) -> SimpleNamespace:
    """Convert podcast to namespace for templates."""
    data = episode.to_dict()
    data["categories_csv"] = ", ".join(data.get("categories", []))
    return SimpleNamespace(**data)


def _video_to_namespace(video) -> SimpleNamespace:
    """Convert video to namespace for templates."""
    return SimpleNamespace(**video.to_dict())


def _news_to_namespace(item) -> SimpleNamespace:
    """Convert news to namespace for templates."""
    return SimpleNamespace(**item.to_dict())


# --- Table partial endpoints ---

@router.get("/partials/articles", response_class=HTMLResponse)
async def content_article_table_partial(
    request: Request,
    category: Optional[str] = None,
    content_service: ArticleCrudService = Depends(get_article_service),
):
    """Render articles table partial."""
    articles, total = await content_service.list_articles(category=category, limit=50, offset=0)
    context = {
        "request": request,
        "articles": articles,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/article_table.html", context)


@router.get("/partials/podcasts", response_class=HTMLResponse)
async def content_podcast_table_partial(
    request: Request,
    podcast_service: PodcastCrudService = Depends(get_podcast_service),
):
    """Render podcasts table partial."""
    podcasts, total = await podcast_service.list_podcasts(limit=50, offset=0)
    context = {
        "request": request,
        "podcasts": podcasts,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/podcast_table.html", context)


@router.get("/partials/videos", response_class=HTMLResponse)
async def content_video_table_partial(
    request: Request,
    video_service: VideoCrudService = Depends(get_video_service),
):
    """Render videos table partial."""
    videos, total = await video_service.list_videos(limit=50, offset=0)
    context = {
        "request": request,
        "videos": videos,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/video_table.html", context)


@router.get("/partials/news", response_class=HTMLResponse)
async def content_news_table_partial(
    request: Request,
    news_service: NewsCrudService = Depends(get_news_service),
):
    """Render news table partial."""
    news_items, total = await news_service.list_news(limit=50, offset=0)
    context = {
        "request": request,
        "news_items": news_items,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/news_table.html", context)


@router.get("/partials/news_feed", response_class=HTMLResponse)
async def content_news_feed_partial(
    request: Request,
    news_service: NewsCrudService = Depends(get_news_service),
):
    """Render news feed (card/list) partial."""
    news_items, _ = await news_service.list_news(limit=10, offset=0)
    context = {"request": request, "news_items": news_items}
    return templates.TemplateResponse("community/content/partials/news_feed.html", context)


@router.get("/partials/video_play", response_class=HTMLResponse)
async def content_video_play_partial(
    request: Request,
    video_id: str,
    video_service: VideoCrudService = Depends(get_video_service),
):
    """Render a lightweight video play modal."""
    video = await video_service.get_by_id(video_id)
    if not video:
        return HTMLResponse("<div class='p-3'>Video not found.</div>", status_code=404)
    return templates.TemplateResponse("community/content/partials/video_play.html", {"request": request, "video": video})


# --- Articles ---

@router.get("/partials/article_form", response_class=HTMLResponse)
async def content_article_form_partial(
    request: Request,
    content_id: Optional[str] = None,
    content_service: ArticleCrudService = Depends(get_article_service),
    current_user: User = Depends(get_admin_user),
):
    """Render article form modal."""
    article_ns = None
    form_mode = "create"

    if content_id:
        article = await content_service.get_by_id(content_id)
        if not article:
            return HTMLResponse("<div class='alert alert-danger mb-0'>Article not found.</div>", status_code=404)
        article_ns = _article_to_namespace(article)
        form_mode = "edit"

    context = {
        "request": request,
        "article": article_ns,
        "form_mode": form_mode,
        "errors": {},
    }
    return templates.TemplateResponse("community/content/partials/article_form.html", context)


@router.get("/partials/article_view", response_class=HTMLResponse)
async def content_article_view_partial(
    request: Request,
    content_id: str,
    content_service: ArticleCrudService = Depends(get_article_service),
    current_user: User = Depends(get_current_user),
):
    """Render read-only article view."""
    article = await content_service.get_by_id(content_id)
    if not article:
        return HTMLResponse("<div class='p-3'>Article not found.</div>", status_code=404)
    raw_body = article.body_md or ""
    body_html = raw_body
    if "<" not in raw_body:
        body_html = markdown.markdown(raw_body, extensions=["extra", "sane_lists"])
    article_ns = article.to_dict()
    article_ns["body_html"] = body_html
    return templates.TemplateResponse(
        "community/content/partials/article_view.html",
        {"request": request, "article": SimpleNamespace(**article_ns)},
    )


@router.post("/partials/article_preview", response_class=HTMLResponse)
async def content_article_preview(
    request: Request,
    current_user: User = Depends(get_admin_user),
):
    """Render article markdown preview."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()
    body = form_handler.form_data.get("body_md", "")
    rendered = markdown.markdown(body or "", extensions=["extra", "tables", "fenced_code"]) if body else ""

    context = {
        "request": request,
        "rendered": rendered,
        "has_content": bool(body.strip()),
    }
    return templates.TemplateResponse("community/content/partials/article_preview.html", context)


@router.post("/articles", response_class=HTMLResponse)
async def content_article_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    content_service: ArticleCrudService = Depends(get_article_service),
):
    """Handle article creation form submission."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "body_md"])

    tags = _parse_comma_field(form_handler.form_data.get("tags", ""))
    published_at_input = form_handler.form_data.get("published_at")
    published_at, dt_error = _parse_datetime_field(published_at_input)
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    if form_handler.has_errors():
        context = {
            "request": request,
            "article": None,
            "form_mode": "create",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "body_md": form_handler.form_data.get("body_md"),
        "category": form_handler.form_data.get("category") or None,
        "tags": tags,
        "hero_image_url": form_handler.form_data.get("hero_image_url") or None,
        "author_id": form_handler.form_data.get("author_id") or None,
        "published_at": published_at,
    }

    try:
        validated = ContentCreate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "article": None,
            "form_mode": "create",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    try:
        await content_service.create_article(
            {**validated.model_dump(), "tenant_id": tenant_id},
            current_user,
        )
        await commit_transaction(db, "create_article_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "article": None,
            "form_mode": "create",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/articles/{content_id}", response_class=HTMLResponse)
async def content_article_update(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    content_service: ArticleCrudService = Depends(get_article_service),
):
    """Handle article update form submission."""
    article = await content_service.get_by_id(content_id)
    if not article:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Article not found.</div>", status_code=404)

    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "body_md"])

    tags = _parse_comma_field(form_handler.form_data.get("tags", ""))
    published_at_input = form_handler.form_data.get("published_at")
    published_at, dt_error = _parse_datetime_field(published_at_input)
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    if form_handler.has_errors():
        context = {
            "request": request,
            "article": _article_to_namespace(article),
            "form_mode": "edit",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "body_md": form_handler.form_data.get("body_md"),
        "category": form_handler.form_data.get("category") or None,
        "tags": tags,
        "hero_image_url": form_handler.form_data.get("hero_image_url") or None,
        "author_id": form_handler.form_data.get("author_id") or None,
        "published_at": published_at,
    }

    try:
        validated = ContentUpdate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "article": _article_to_namespace(article),
            "form_mode": "edit",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    try:
        await content_service.update_article(
            content_id,
            validated.model_dump(exclude_unset=True),
            current_user,
        )
        await commit_transaction(db, "update_article_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "article": _article_to_namespace(article),
            "form_mode": "edit",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/article_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/articles/{content_id}/delete", response_class=HTMLResponse)
async def content_article_delete(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    content_service: ArticleCrudService = Depends(get_article_service),
    current_user: User = Depends(get_admin_user),
):
    """Handle article deletion."""
    deleted = await content_service.delete_article(content_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Article not found.</div>", status_code=404)
    await commit_transaction(db, "delete_article_form")
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- Podcasts ---

@router.get("/partials/podcast_form", response_class=HTMLResponse)
async def content_podcast_form_partial(
    request: Request,
    episode_id: Optional[str] = None,
    podcast_service: PodcastCrudService = Depends(get_podcast_service),
    current_user: User = Depends(get_admin_user),
):
    """Render podcast form modal."""
    episode_ns = None
    form_mode = "create"

    if episode_id:
        episode = await podcast_service.get_by_id(episode_id)
        if not episode:
            return HTMLResponse("<div class='alert alert-danger mb-0'>Podcast episode not found.</div>", status_code=404)
        episode_ns = _podcast_to_namespace(episode)
        form_mode = "edit"

    context = {
        "request": request,
        "episode": episode_ns,
        "form_mode": form_mode,
        "errors": {},
    }
    return templates.TemplateResponse("community/content/partials/podcast_form.html", context)


@router.post("/podcasts", response_class=HTMLResponse)
async def content_podcast_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    podcast_service: PodcastCrudService = Depends(get_podcast_service),
):
    """Handle podcast creation form submission."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "link"])

    categories = _parse_comma_field(form_handler.form_data.get("categories", ""))
    published_at, dt_error = _parse_datetime_field(form_handler.form_data.get("published_at"))
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    duration_raw = form_handler.form_data.get("duration_minutes")
    duration_value: Optional[float] = None
    if duration_raw:
        try:
            duration_value = float(duration_raw)
        except ValueError:
            form_handler.add_error("duration_minutes", "Duration must be a number")

    if form_handler.has_errors():
        context = {
            "request": request,
            "episode": None,
            "form_mode": "create",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "link": form_handler.form_data.get("link"),
        "description": form_handler.form_data.get("description") or None,
        "duration_minutes": duration_value,
        "host": form_handler.form_data.get("host") or None,
        "published_at": published_at,
        "categories": categories,
    }

    try:
        validated = PodcastCreate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "episode": None,
            "form_mode": "create",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    try:
        await podcast_service.create_podcast({**validated.model_dump(), "tenant_id": tenant_id}, current_user)
        await commit_transaction(db, "create_podcast_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "episode": None,
            "form_mode": "create",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/podcasts/{episode_id}", response_class=HTMLResponse)
async def content_podcast_update(
    request: Request,
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    podcast_service: PodcastCrudService = Depends(get_podcast_service),
):
    """Handle podcast update form submission."""
    episode = await podcast_service.get_by_id(episode_id)
    if not episode:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Podcast episode not found.</div>", status_code=404)

    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "link"])

    categories = _parse_comma_field(form_handler.form_data.get("categories", ""))
    published_at, dt_error = _parse_datetime_field(form_handler.form_data.get("published_at"))
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    duration_raw = form_handler.form_data.get("duration_minutes")
    duration_value: Optional[float] = None
    if duration_raw:
        try:
            duration_value = float(duration_raw)
        except ValueError:
            form_handler.add_error("duration_minutes", "Duration must be a number")

    if form_handler.has_errors():
        context = {
            "request": request,
            "episode": _podcast_to_namespace(episode),
            "form_mode": "edit",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "link": form_handler.form_data.get("link"),
        "description": form_handler.form_data.get("description") or None,
        "duration_minutes": duration_value,
        "host": form_handler.form_data.get("host") or None,
        "published_at": published_at,
        "categories": categories,
    }

    try:
        validated = PodcastUpdate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "episode": _podcast_to_namespace(episode),
            "form_mode": "edit",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    try:
        await podcast_service.update_podcast(
            episode_id,
            validated.model_dump(exclude_unset=True),
            current_user,
        )
        await commit_transaction(db, "update_podcast_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "episode": _podcast_to_namespace(episode),
            "form_mode": "edit",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/podcast_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/podcasts/{episode_id}/delete", response_class=HTMLResponse)
async def content_podcast_delete(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    podcast_service: PodcastCrudService = Depends(get_podcast_service),
    current_user: User = Depends(get_admin_user),
):
    """Handle podcast deletion."""
    deleted = await podcast_service.delete_podcast(episode_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Podcast episode not found.</div>", status_code=404)
    await commit_transaction(db, "delete_podcast_form")
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- Videos ---

@router.get("/partials/video_form", response_class=HTMLResponse)
async def content_video_form_partial(
    request: Request,
    video_id: Optional[str] = None,
    video_service: VideoCrudService = Depends(get_video_service),
    current_user: User = Depends(get_admin_user),
):
    """Render video form modal."""
    video_ns = None
    form_mode = "create"

    if video_id:
        video = await video_service.get_by_id(video_id)
        if not video:
            return HTMLResponse("<div class='alert alert-danger mb-0'>Video not found.</div>", status_code=404)
        video_ns = _video_to_namespace(video)
        form_mode = "edit"

    context = {
        "request": request,
        "video": video_ns,
        "form_mode": form_mode,
        "errors": {},
    }
    return templates.TemplateResponse("community/content/partials/video_form.html", context)


@router.post("/videos", response_class=HTMLResponse)
async def content_video_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    video_service: VideoCrudService = Depends(get_video_service),
):
    """Handle video creation form submission."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "embed_url"])

    published_at, dt_error = _parse_datetime_field(form_handler.form_data.get("published_at"))
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    duration_raw = form_handler.form_data.get("duration_minutes")
    duration_value: Optional[float] = None
    if duration_raw:
        try:
            duration_value = float(duration_raw)
        except ValueError:
            form_handler.add_error("duration_minutes", "Duration must be a number")

    if form_handler.has_errors():
        context = {
            "request": request,
            "video": None,
            "form_mode": "create",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "embed_url": form_handler.form_data.get("embed_url"),
        "description": form_handler.form_data.get("description") or None,
        "category": form_handler.form_data.get("category") or None,
        "duration_minutes": duration_value,
        "published_at": published_at,
    }

    try:
        validated = VideoCreate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "video": None,
            "form_mode": "create",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    try:
        await video_service.create_video({**validated.model_dump(), "tenant_id": tenant_id}, current_user)
        await commit_transaction(db, "create_video_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "video": None,
            "form_mode": "create",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/videos/{video_id}", response_class=HTMLResponse)
async def content_video_update(
    request: Request,
    video_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    video_service: VideoCrudService = Depends(get_video_service),
):
    """Handle video update form submission."""
    video = await video_service.get_by_id(video_id)
    if not video:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Video not found.</div>", status_code=404)

    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["title", "embed_url"])

    published_at, dt_error = _parse_datetime_field(form_handler.form_data.get("published_at"))
    if dt_error:
        form_handler.add_error("published_at", dt_error)

    duration_raw = form_handler.form_data.get("duration_minutes")
    duration_value: Optional[float] = None
    if duration_raw:
        try:
            duration_value = float(duration_raw)
        except ValueError:
            form_handler.add_error("duration_minutes", "Duration must be a number")

    if form_handler.has_errors():
        context = {
            "request": request,
            "video": _video_to_namespace(video),
            "form_mode": "edit",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    payload = {
        "title": form_handler.form_data.get("title"),
        "embed_url": form_handler.form_data.get("embed_url"),
        "description": form_handler.form_data.get("description") or None,
        "category": form_handler.form_data.get("category") or None,
        "duration_minutes": duration_value,
        "published_at": published_at,
    }

    try:
        validated = VideoUpdate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "video": _video_to_namespace(video),
            "form_mode": "edit",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    try:
        await video_service.update_video(
            video_id,
            validated.model_dump(exclude_unset=True),
            current_user,
        )
        await commit_transaction(db, "update_video_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "video": _video_to_namespace(video),
            "form_mode": "edit",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/video_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/videos/{video_id}/delete", response_class=HTMLResponse)
async def content_video_delete(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    video_service: VideoCrudService = Depends(get_video_service),
    current_user: User = Depends(get_admin_user),
):
    """Handle video deletion."""
    deleted = await video_service.delete_video(video_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Video not found.</div>", status_code=404)
    await commit_transaction(db, "delete_video_form")
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- News ---

@router.get("/partials/news_form", response_class=HTMLResponse)
async def content_news_form_partial(
    request: Request,
    news_id: Optional[str] = None,
    news_service: NewsCrudService = Depends(get_news_service),
    current_user: User = Depends(get_admin_user),
):
    """Render news form modal."""
    news_ns = None
    form_mode = "create"

    if news_id:
        news = await news_service.get_by_id(news_id)
        if not news:
            return HTMLResponse("<div class='alert alert-danger mb-0'>News item not found.</div>", status_code=404)
        news_ns = _news_to_namespace(news)
        form_mode = "edit"

    context = {
        "request": request,
        "news": news_ns,
        "form_mode": form_mode,
        "errors": {},
    }
    return templates.TemplateResponse("community/content/partials/news_form.html", context)


@router.post("/news", response_class=HTMLResponse)
async def content_news_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    news_service: NewsCrudService = Depends(get_news_service),
):
    """Handle news creation form submission."""
    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["headline", "url"])

    publish_date, dt_error = _parse_datetime_field(form_handler.form_data.get("publish_date"))
    if dt_error:
        form_handler.add_error("publish_date", dt_error)

    if form_handler.has_errors():
        context = {
            "request": request,
            "news": None,
            "form_mode": "create",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    payload = {
        "headline": form_handler.form_data.get("headline"),
        "url": form_handler.form_data.get("url"),
        "source": form_handler.form_data.get("source") or None,
        "summary": form_handler.form_data.get("summary") or None,
        "publish_date": publish_date,
        "category": form_handler.form_data.get("category") or None,
    }

    try:
        validated = NewsCreate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "news": None,
            "form_mode": "create",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    try:
        await news_service.create_news({**validated.model_dump(), "tenant_id": tenant_id}, current_user)
        await commit_transaction(db, "create_news_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "news": None,
            "form_mode": "create",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/news/{news_id}", response_class=HTMLResponse)
async def content_news_update(
    request: Request,
    news_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    news_service: NewsCrudService = Depends(get_news_service),
):
    """Handle news update form submission."""
    news_item = await news_service.get_by_id(news_id)
    if not news_item:
        return HTMLResponse("<div class='alert alert-danger mb-0'>News item not found.</div>", status_code=404)

    form_handler = FormHandler(request)
    await form_handler.parse_form()
    form_handler.validate_required_fields(["headline", "url"])

    publish_date, dt_error = _parse_datetime_field(form_handler.form_data.get("publish_date"))
    if dt_error:
        form_handler.add_error("publish_date", dt_error)

    if form_handler.has_errors():
        context = {
            "request": request,
            "news": _news_to_namespace(news_item),
            "form_mode": "edit",
            "errors": form_handler.errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    payload = {
        "headline": form_handler.form_data.get("headline"),
        "url": form_handler.form_data.get("url"),
        "source": form_handler.form_data.get("source") or None,
        "summary": form_handler.form_data.get("summary") or None,
        "publish_date": publish_date,
        "category": form_handler.form_data.get("category") or None,
    }

    try:
        validated = NewsUpdate(**payload)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "news": _news_to_namespace(news_item),
            "form_mode": "edit",
            "errors": errors,
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    try:
        await news_service.update_news(
            news_id,
            validated.model_dump(exclude_unset=True),
            current_user,
        )
        await commit_transaction(db, "update_news_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "news": _news_to_namespace(news_item),
            "form_mode": "edit",
            "errors": {"general": [str(exc)]},
            "form_data": SimpleNamespace(**form_handler.form_data),
        }
        return templates.TemplateResponse(
            "community/content/partials/news_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/news/{news_id}/delete", response_class=HTMLResponse)
async def content_news_delete(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    news_service: NewsCrudService = Depends(get_news_service),
    current_user: User = Depends(get_admin_user),
):
    """Handle news deletion."""
    deleted = await news_service.delete_news(news_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>News item not found.</div>", status_code=404)
    await commit_transaction(db, "delete_news_form")
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


__all__ = ["router"]
