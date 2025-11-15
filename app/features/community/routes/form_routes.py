"""HTMX form routes for community feature."""

from datetime import datetime, timezone
import markdown
from types import SimpleNamespace
from typing import Dict, List, Optional

from pydantic import ValidationError

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
    get_current_user,
    User,
    AsyncSession,
)

from ..dependencies import (
    get_member_service,
    get_partner_service,
    get_group_service,
    get_group_post_service,
    get_event_service,
    get_poll_service,
    get_message_service,
    get_content_service,
    get_podcast_service,
    get_video_service,
    get_news_service,
)
from ..schemas import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    PartnerCreate,
    PartnerUpdate,
    PartnerResponse,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupPostCreate,
    GroupPostUpdate,
    GroupPostResponse,
    EventCreate,
    EventUpdate,
    EventResponse,
    PollCreate,
    PollUpdate,
    PollResponse,
    MessageCreate,
    MessageResponse,
    ContentCreate,
    ContentUpdate,
    PodcastCreate,
    PodcastUpdate,
    VideoCreate,
    VideoUpdate,
    NewsCreate,
    NewsUpdate,
)
from ..services import (
    MemberService,
    PartnerService,
    GroupService,
    GroupPostService,
    EventService,
    PollService,
    MessageService,
    ContentService,
    PodcastService,
    VideoService,
    NewsService,
)

router = APIRouter(tags=["community-forms"])


def _parse_comma_field(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_datetime_field(raw: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    if not raw:
        return None, None
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed, None
    except ValueError:
        return None, "Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."


def _article_to_namespace(article) -> SimpleNamespace:
    data = article.to_dict()
    data["tags_csv"] = ", ".join(data.get("tags", []))
    return SimpleNamespace(**data)


def _podcast_to_namespace(episode) -> SimpleNamespace:
    data = episode.to_dict()
    data["categories_csv"] = ", ".join(data.get("categories", []))
    return SimpleNamespace(**data)


def _video_to_namespace(video) -> SimpleNamespace:
    return SimpleNamespace(**video.to_dict())


def _news_to_namespace(item) -> SimpleNamespace:
    return SimpleNamespace(**item.to_dict())


def _validation_errors_to_dict(error: ValidationError) -> Dict[str, List[str]]:
    errors: Dict[str, List[str]] = {}
    for err in error.errors():
        field = err["loc"][0]
        errors.setdefault(field, []).append(err["msg"])
    return errors


def _member_to_namespace(member) -> SimpleNamespace:
    data = MemberResponse.model_validate(member, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


def _partner_to_namespace(partner) -> SimpleNamespace:
    data = PartnerResponse.model_validate(partner, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


def _group_to_namespace(group) -> SimpleNamespace:
    data = GroupResponse.model_validate(group, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


def _event_to_namespace(event) -> SimpleNamespace:
    data = EventResponse.model_validate(event, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


def _poll_to_namespace(poll) -> SimpleNamespace:
    data = PollResponse.model_validate(poll, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


def _format_datetime_for_input(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # Ensure timezone-aware values render properly for datetime-local inputs
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return value


# ---------------------
# Member form endpoints
# ---------------------

@router.get("/members/partials/form", response_class=HTMLResponse)
async def member_form_partial(
    request: Request,
    member_id: str | None = None,
    member_service: MemberService = Depends(get_member_service),
):
    member = None
    if member_id:
        member = await member_service.get_by_id(member_id)
        if not member:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Member not found.</div>",
                status_code=404,
            )
        member = _member_to_namespace(member)
    context = {
        "request": request,
        "member": member,
        "form_data": None,
        "errors": {},
        "specialties_text": ", ".join(member.specialties or []) if member else "",
        "tags_text": ", ".join(member.tags or []) if member else "",
    }
    return templates.TemplateResponse("community/members/partials/form.html", context)


@router.post("/members", response_class=HTMLResponse)
async def create_member_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    member_service: MemberService = Depends(get_member_service),
):
    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "email": form.get("email"),
        "firm": form.get("firm") or None,
        "bio": form.get("bio") or None,
        "aum_range": form.get("aum_range") or None,
        "location": form.get("location") or None,
        "specialties": _parse_comma_field(form.get("specialties", "")),
        "tags": _parse_comma_field(form.get("tags", "")),
        "user_id": form.get("user_id") or None,
    }

    try:
        payload = MemberCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "member": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
        }
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    try:
        member = await member_service.create_member(payload.model_dump(), current_user)
        await db.commit()
    except ValueError as exc:
        errors = {"email": [str(exc)]}
        context = {
            "request": request,
            "member": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
        }
        await db.rollback()
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# --------------------
# Group form endpoints
# --------------------


@router.get("/groups/partials/form", response_class=HTMLResponse)
async def group_form_partial(
    request: Request,
    group_id: str | None = None,
    group_service: GroupService = Depends(get_group_service),
):
    group = None
    if group_id:
        group = await group_service.get_by_id(group_id)
        if not group:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Group not found.</div>",
                status_code=404,
            )
        group = _group_to_namespace(group)

    context = {
        "request": request,
        "group": group,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/groups/partials/form.html", context)


@router.post("/groups", response_class=HTMLResponse)
async def create_group_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
):
    form = await request.form()
    raw_data = {
        "name": form.get("name"),
        "description": form.get("description") or None,
        "privacy": form.get("privacy") or "private",
        "owner_id": form.get("owner_id") or None,
    }

    try:
        payload = GroupCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "group": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/groups/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await group_service.create_group(payload.model_dump(), current_user)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        context = {
            "request": request,
            "group": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": {"name": [str(exc)]},
        }
        return templates.TemplateResponse(
            "community/groups/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/groups/{group_id}", response_class=HTMLResponse)
async def update_group_form(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
):
    group = await group_service.get_by_id(group_id)
    if not group:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Group not found.</div>",
            status_code=404,
        )
    group_ns = _group_to_namespace(group)

    form = await request.form()
    raw_data = {
        "name": form.get("name"),
        "description": form.get("description") or None,
        "privacy": form.get("privacy") or None,
        "owner_id": form.get("owner_id") or None,
    }

    try:
        payload = GroupUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "group": group_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/groups/partials/form.html",
            context,
            status_code=400,
        )

    updated = await group_service.update_group(group_id, payload.model_dump(exclude_unset=True), current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Group not found.</div>",
            status_code=404,
        )

    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.get("/groups/{group_id}/posts/partials/form", response_class=HTMLResponse)
async def group_post_form_partial(
    request: Request,
    group_id: str,
    post_id: str | None = None,
    post_service: GroupPostService = Depends(get_group_post_service),
):
    post = None
    if post_id:
        post = await post_service.get_by_id(post_id)
        if not post:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Post not found.</div>",
                status_code=404,
            )
        post = GroupPostResponse.model_validate(post, from_attributes=True).model_dump()
        post = SimpleNamespace(**post)

    context = {
        "request": request,
        "group_id": group_id,
        "post": post,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/groups/partials/post_form.html", context)


@router.post("/groups/{group_id}/posts", response_class=HTMLResponse)
async def create_group_post_form(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostService = Depends(get_group_post_service),
):
    form = await request.form()
    raw_data = {
        "group_id": group_id,
        "title": form.get("title") or None,
        "content": form.get("content"),
    }

    try:
        payload = GroupPostCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "group_id": group_id,
            "post": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/groups/partials/post_form.html",
            context,
            status_code=400,
        )

    await post_service.create_post(payload.model_dump(), current_user)
    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshPosts, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/groups/posts/{post_id}", response_class=HTMLResponse)
async def update_group_post_form(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostService = Depends(get_group_post_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Post not found.</div>",
            status_code=404,
        )
    post_ns = SimpleNamespace(**GroupPostResponse.model_validate(post, from_attributes=True).model_dump())

    form = await request.form()
    raw_data = {
        "title": form.get("title") or None,
        "content": form.get("content") or None,
    }

    try:
        payload = GroupPostUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "group_id": post_ns.group_id,
            "post": post_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/groups/partials/post_form.html",
            context,
            status_code=400,
        )

    updated = await post_service.update_post(post_id, payload.model_dump(exclude_unset=True), current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Post not found.</div>",
            status_code=404,
        )

    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshPosts, showSuccess"}
    return Response(status_code=204, headers=headers)


# ----------------------
# Messaging form endpoints
# ----------------------


@router.get("/messages/partials/form", response_class=HTMLResponse)
async def message_form_partial(request: Request):
    return templates.TemplateResponse(
        "community/messages/partials/form.html",
        {"request": request, "errors": {}, "form_data": None},
    )


@router.post("/messages", response_class=HTMLResponse)
async def send_message_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    form = await request.form()
    raw_data = {
        "recipient_id": form.get("recipient_id"),
        "content": form.get("content"),
        "thread_id": form.get("thread_id") or None,
    }

    try:
        payload = MessageCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "errors": errors,
            "form_data": SimpleNamespace(**raw_data),
        }
        return templates.TemplateResponse(
            "community/messages/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await message_service.send_message(payload.model_dump(), sender_id=current_user.id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        context = {
            "request": request,
            "errors": {"recipient_id": [str(exc)]},
            "form_data": SimpleNamespace(**raw_data),
        }
        return templates.TemplateResponse(
            "community/messages/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# -------------------
# Event form endpoints
# -------------------


@router.get("/events/partials/form", response_class=HTMLResponse)
async def event_form_partial(
    request: Request,
    event_id: str | None = None,
    event_service: EventService = Depends(get_event_service),
):
    event = None
    if event_id:
        event = await event_service.get_by_id(event_id)
        if not event:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Event not found.</div>",
                status_code=404,
            )
        event = _event_to_namespace(event)
        event.start_date = _format_datetime_for_input(event.start_date)
        event.end_date = _format_datetime_for_input(event.end_date)

    context = {
        "request": request,
        "event": event,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/events/partials/form.html", context)


@router.post("/events", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    form = await request.form()
    raw_data = {
        "title": form.get("title"),
        "description": form.get("description") or None,
        "start_date": form.get("start_date"),
        "end_date": form.get("end_date") or None,
        "location": form.get("location") or None,
        "url": form.get("url") or None,
        "category": form.get("category") or None,
    }

    try:
        payload = EventCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "event": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/events/partials/form.html",
            context,
            status_code=400,
        )

    await event_service.create_event(payload.model_dump(), current_user)
    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/events/{event_id}", response_class=HTMLResponse)
async def update_event_form(
    request: Request,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    event = await event_service.get_by_id(event_id)
    if not event:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Event not found.</div>",
            status_code=404,
        )
    event_ns = _event_to_namespace(event)
    event_ns.start_date = _format_datetime_for_input(event_ns.start_date)
    event_ns.end_date = _format_datetime_for_input(event_ns.end_date)

    form = await request.form()
    raw_data = {
        "title": form.get("title"),
        "description": form.get("description") or None,
        "start_date": form.get("start_date") or None,
        "end_date": form.get("end_date") or None,
        "location": form.get("location") or None,
        "url": form.get("url") or None,
        "category": form.get("category") or None,
    }

    try:
        payload = EventUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "event": event_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/events/partials/form.html",
            context,
            status_code=400,
        )

    updated = await event_service.update_event(event_id, payload.model_dump(exclude_unset=True), current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Event not found.</div>",
            status_code=404,
        )

    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.delete("/events/{event_id}", response_class=HTMLResponse)
async def delete_event_form(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    event_service: EventService = Depends(get_event_service),
):
    event = await event_service.get_by_id(event_id)
    if not event:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Event not found.</div>",
            status_code=404,
        )

    deleted = await event_service.delete_event(event_id)
    if not deleted:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Unable to delete event.</div>",
            status_code=400,
        )

    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# ------------------
# Poll form endpoints
# ------------------


@router.get("/polls/partials/form", response_class=HTMLResponse)
async def poll_form_partial(
    request: Request,
    poll_id: str | None = None,
    poll_service: PollService = Depends(get_poll_service),
):
    poll = None
    if poll_id:
        poll = await poll_service.get_by_id(poll_id)
        if not poll:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Poll not found.</div>",
                status_code=404,
            )
        poll = _poll_to_namespace(poll)

    context = {
        "request": request,
        "poll": poll,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/polls/partials/form.html", context)


@router.post("/polls", response_class=HTMLResponse)
async def create_poll_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    poll_service: PollService = Depends(get_poll_service),
):
    form = await request.form()
    raw_data = {
        "question": form.get("question"),
        "options_text": form.get("options", ""),
        "expires_at": form.get("expires_at") or None,
    }

    option_lines = [line.strip() for line in raw_data["options_text"].splitlines() if line.strip()]
    if len(option_lines) < 2:
        context = {
            "request": request,
            "poll": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": {"options": ["Provide at least two poll options."]},
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    try:
        options_payload = [
            {"text": label, "order": index}
            for index, label in enumerate(option_lines)
        ]
        payload = PollCreate(
            question=raw_data["question"],
            options=options_payload,
            expires_at=raw_data["expires_at"],
        )
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "poll": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    await poll_service.create_poll(payload.model_dump(), current_user)
    await db.commit()

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/polls/{poll_id}", response_class=HTMLResponse)
async def update_poll_form(
    request: Request,
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    poll_service: PollService = Depends(get_poll_service),
):
    poll = await poll_service.get_by_id(poll_id)
    if not poll:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Poll not found.</div>",
            status_code=404,
        )
    poll_ns = _poll_to_namespace(poll)

    form = await request.form()
    raw_data = {
        "question": form.get("question") or None,
        "status": form.get("status") or None,
        "expires_at": form.get("expires_at") or None,
    }

    try:
        payload = PollUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "poll": poll_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    updated = await poll_service.update_poll(poll_id, payload.model_dump(exclude_unset=True), current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Poll not found.</div>",
            status_code=404,
        )

    await db.commit()
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/members/{member_id}", response_class=HTMLResponse)
async def update_member_form(
    request: Request,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    member_service: MemberService = Depends(get_member_service),
):
    member = await member_service.get_by_id(member_id)
    if not member:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Member not found.</div>",
            status_code=404,
        )
    member_ns = _member_to_namespace(member)

    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "email": form.get("email"),
        "firm": form.get("firm") or None,
        "bio": form.get("bio") or None,
        "aum_range": form.get("aum_range") or None,
        "location": form.get("location") or None,
        "specialties": _parse_comma_field(form.get("specialties", "")),
        "tags": _parse_comma_field(form.get("tags", "")),
        "user_id": form.get("user_id") or None,
    }

    try:
        payload = MemberUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "member": member_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
        }
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    try:
        updated_member = await member_service.update_member(
            member_id, payload.model_dump(exclude_unset=True), current_user
        )
        if not updated_member:
            raise ValueError("Member not found.")
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        errors = {"email": [str(exc)]}
        context = {
            "request": request,
            "member": member_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
        }
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# ----------------------
# Partner form endpoints
# ----------------------

@router.get("/partners/partials/form", response_class=HTMLResponse)
async def partner_form_partial(
    request: Request,
    partner_id: str | None = None,
    partner_service: PartnerService = Depends(get_partner_service),
):
    partner = None
    if partner_id:
        partner = await partner_service.get_by_id(partner_id)
        if not partner:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Partner not found.</div>",
                status_code=404,
            )
        partner = _partner_to_namespace(partner)

    context = {
        "request": request,
        "partner": partner,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/partners/partials/form.html", context)


@router.post("/partners", response_class=HTMLResponse)
async def create_partner_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerService = Depends(get_partner_service),
):
    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "logo_url": form.get("logo_url") or None,
        "description": form.get("description") or None,
        "offer": form.get("offer") or None,
        "website": form.get("website") or None,
        "category": form.get("category") or None,
    }

    try:
        payload = PartnerCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "partner": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/partners/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await partner_service.create_partner(payload.model_dump(), current_user)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        errors = {"name": [str(exc)]}
        context = {
            "request": request,
            "partner": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/partners/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/partners/{partner_id}", response_class=HTMLResponse)
async def update_partner_form(
    request: Request,
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerService = Depends(get_partner_service),
):
    partner = await partner_service.get_by_id(partner_id)
    if not partner:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Partner not found.</div>",
            status_code=404,
        )
    partner_ns = _partner_to_namespace(partner)

    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "logo_url": form.get("logo_url") or None,
        "description": form.get("description") or None,
        "offer": form.get("offer") or None,
        "website": form.get("website") or None,
        "category": form.get("category") or None,
    }

    try:
        payload = PartnerUpdate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "partner": partner_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/partners/partials/form.html",
            context,
            status_code=400,
        )

    try:
        updated_partner = await partner_service.update_partner(
            partner_id, payload.model_dump(exclude_unset=True), current_user
        )
        if not updated_partner:
            raise ValueError("Partner not found.")
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        errors = {"name": [str(exc)]}
        context = {
            "request": request,
            "partner": partner_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/partners/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# ------------------------
# Content hub form routes
# ------------------------


@router.get("/content/partials/articles", response_class=HTMLResponse)
async def content_article_table_partial(
    request: Request,
    category: Optional[str] = None,
    content_service: ContentService = Depends(get_content_service),
):
    articles, total = await content_service.list_content(category=category, limit=50, offset=0)
    context = {
        "request": request,
        "articles": articles,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/article_table.html", context)


@router.get("/content/partials/podcasts", response_class=HTMLResponse)
async def content_podcast_table_partial(
    request: Request,
    podcast_service: PodcastService = Depends(get_podcast_service),
):
    podcasts, total = await podcast_service.list_podcasts(limit=50, offset=0)
    context = {
        "request": request,
        "podcasts": podcasts,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/podcast_table.html", context)


@router.get("/content/partials/videos", response_class=HTMLResponse)
async def content_video_table_partial(
    request: Request,
    video_service: VideoService = Depends(get_video_service),
):
    videos, total = await video_service.list_videos(limit=50, offset=0)
    context = {
        "request": request,
        "videos": videos,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/video_table.html", context)


@router.get("/content/partials/news", response_class=HTMLResponse)
async def content_news_table_partial(
    request: Request,
    news_service: NewsService = Depends(get_news_service),
):
    news_items, total = await news_service.list_news(limit=50, offset=0)
    context = {
        "request": request,
        "news_items": news_items,
        "total": total,
    }
    return templates.TemplateResponse("community/content/partials/news_table.html", context)


@router.get("/content/partials/article_form", response_class=HTMLResponse)
async def content_article_form_partial(
    request: Request,
    content_id: Optional[str] = None,
    content_service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_admin_user),
):
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


@router.post("/content/partials/article_preview", response_class=HTMLResponse)
async def content_article_preview(
    request: Request,
    current_user: User = Depends(get_admin_user),
):
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


@router.post("/content/articles", response_class=HTMLResponse)
async def content_article_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    content_service: ContentService = Depends(get_content_service),
):
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
        await content_service.create_content(
            {**validated.model_dump(), "tenant_id": tenant_id},
            current_user,
        )
        await db.commit()
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


@router.post("/content/articles/{content_id}", response_class=HTMLResponse)
async def content_article_update(
    request: Request,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    content_service: ContentService = Depends(get_content_service),
):
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
        await content_service.update_content(
            content_id,
            validated.model_dump(exclude_unset=True),
            current_user,
        )
        await db.commit()
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


@router.post("/content/articles/{content_id}/delete", response_class=HTMLResponse)
async def content_article_delete(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    content_service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_admin_user),
):
    deleted = await content_service.delete_content(content_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Article not found.</div>", status_code=404)
    await db.commit()
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.get("/content/partials/podcast_form", response_class=HTMLResponse)
async def content_podcast_form_partial(
    request: Request,
    episode_id: Optional[str] = None,
    podcast_service: PodcastService = Depends(get_podcast_service),
    current_user: User = Depends(get_admin_user),
):
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


@router.post("/content/podcasts", response_class=HTMLResponse)
async def content_podcast_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    podcast_service: PodcastService = Depends(get_podcast_service),
):
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
        await db.commit()
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


@router.post("/content/podcasts/{episode_id}", response_class=HTMLResponse)
async def content_podcast_update(
    request: Request,
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    podcast_service: PodcastService = Depends(get_podcast_service),
):
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
        await db.commit()
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


@router.post("/content/podcasts/{episode_id}/delete", response_class=HTMLResponse)
async def content_podcast_delete(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    podcast_service: PodcastService = Depends(get_podcast_service),
    current_user: User = Depends(get_admin_user),
):
    deleted = await podcast_service.delete_podcast(episode_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Podcast episode not found.</div>", status_code=404)
    await db.commit()
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.get("/content/partials/video_form", response_class=HTMLResponse)
async def content_video_form_partial(
    request: Request,
    video_id: Optional[str] = None,
    video_service: VideoService = Depends(get_video_service),
    current_user: User = Depends(get_admin_user),
):
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


@router.post("/content/videos", response_class=HTMLResponse)
async def content_video_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    video_service: VideoService = Depends(get_video_service),
):
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
        await db.commit()
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


@router.post("/content/videos/{video_id}", response_class=HTMLResponse)
async def content_video_update(
    request: Request,
    video_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    video_service: VideoService = Depends(get_video_service),
):
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
        await db.commit()
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


@router.post("/content/videos/{video_id}/delete", response_class=HTMLResponse)
async def content_video_delete(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    video_service: VideoService = Depends(get_video_service),
    current_user: User = Depends(get_admin_user),
):
    deleted = await video_service.delete_video(video_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Video not found.</div>", status_code=404)
    await db.commit()
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.get("/content/partials/news_form", response_class=HTMLResponse)
async def content_news_form_partial(
    request: Request,
    news_id: Optional[str] = None,
    news_service: NewsService = Depends(get_news_service),
    current_user: User = Depends(get_admin_user),
):
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


@router.post("/content/news", response_class=HTMLResponse)
async def content_news_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    news_service: NewsService = Depends(get_news_service),
):
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
        await db.commit()
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


@router.post("/content/news/{news_id}", response_class=HTMLResponse)
async def content_news_update(
    request: Request,
    news_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_admin_user),
    news_service: NewsService = Depends(get_news_service),
):
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
        await db.commit()
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


@router.post("/content/news/{news_id}/delete", response_class=HTMLResponse)
async def content_news_delete(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    news_service: NewsService = Depends(get_news_service),
    current_user: User = Depends(get_admin_user),
):
    deleted = await news_service.delete_news(news_id)
    if not deleted:
        return HTMLResponse("<div class='alert alert-danger mb-0'>News item not found.</div>", status_code=404)
    await db.commit()
    headers = {"HX-Trigger": "refreshContentTables, showSuccess"}
    return Response(status_code=204, headers=headers)

__all__ = ["router"]
