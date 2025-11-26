"""CRUD routes for community groups and posts (HTMX submits + APIs)."""

from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select

from pydantic import ValidationError

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    AsyncSession,
    HTMLResponse,
    Request,
    commit_transaction,
    get_current_user,
    get_db,
    handle_route_error,
    templates,
    tenant_dependency,
    User,
    is_global_admin,
)

from ...dependencies import (
    get_group_service,
    get_group_post_service,
    get_group_comment_service,
)
from ...schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    GroupPostCreate,
    GroupPostResponse,
    GroupPostUpdate,
    GroupCommentCreate,
)
from ...services import (
    GroupCrudService,
    GroupPostCrudService,
    GroupCommentCrudService,
)

router = APIRouter()


def _is_moderator(user: User) -> bool:
    """Check if the user can moderate group content."""
    return getattr(user, "role", "") in {"admin", "global_admin"} or is_global_admin(user)


def _can_edit(author_id: Optional[str], user: User) -> bool:
    """Author or moderator can edit/delete."""
    return bool(author_id and getattr(user, "id", None) == author_id) or _is_moderator(user)


async def _fetch_author_map(db: AsyncSession, author_ids: set[str]) -> dict[str, str]:
    """Return a map of author_id -> display name/email."""
    if not author_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(author_ids)))
    return {user.id: (user.name or user.email or user.id) for user in result.scalars().all()}


def _comment_view_model(comment, author_map: dict[str, str], current_user: User):
    return SimpleNamespace(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        author_id=comment.author_id,
        author_name=author_map.get(comment.author_id) or (comment.author_id or "Unknown"),
        created_at=comment.created_at,
        can_edit=_can_edit(comment.author_id, current_user),
        can_delete=_can_edit(comment.author_id, current_user),
    )


def _post_view_model(post, comments, author_map: dict[str, str], current_user: User):
    return SimpleNamespace(
        id=post.id,
        group_id=post.group_id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_name=author_map.get(post.author_id) or (post.author_id or "Unknown"),
        created_at=post.created_at,
        comments=comments,
        can_edit=_can_edit(post.author_id, current_user),
        can_delete=_can_edit(post.author_id, current_user),
    )


async def _build_feed(
    group_id: str,
    post_service: GroupPostCrudService,
    comment_service: GroupCommentCrudService,
    db: AsyncSession,
    current_user: User,
    limit: int = 20,
    offset: int = 0,
):
    """Load posts + comments for a group with author metadata."""
    posts, total = await post_service.list_posts(group_id=group_id, limit=limit, offset=offset)
    author_ids: set[str] = set()
    comments_map: dict[str, list] = {}

    for post in posts:
        comments, _ = await comment_service.list_comments(post_id=post.id, limit=100, offset=0)
        comments_map[post.id] = comments
        if post.author_id:
            author_ids.add(post.author_id)
        for comment in comments:
            if comment.author_id:
                author_ids.add(comment.author_id)

    author_map = await _fetch_author_map(db, author_ids)

    post_views = []
    for post in posts:
        comment_views = [
            _comment_view_model(comment, author_map, current_user) for comment in comments_map.get(post.id, [])
        ]
        post_views.append(_post_view_model(post, comment_views, author_map, current_user))

    return post_views, total


async def _load_post_view(
    post,
    comment_service: GroupCommentCrudService,
    db: AsyncSession,
    current_user: User,
):
    comments, _ = await comment_service.list_comments(post_id=post.id, limit=100, offset=0)
    author_ids = {post.author_id} if post.author_id else set()
    for comment in comments:
        if comment.author_id:
            author_ids.add(comment.author_id)
    author_map = await _fetch_author_map(db, author_ids)
    comment_views = [_comment_view_model(comment, author_map, current_user) for comment in comments]
    return _post_view_model(post, comment_views, author_map, current_user)


# --- HTMX form submissions ---

@router.post("/", response_class=HTMLResponse)
async def create_group_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    group_service: GroupCrudService = Depends(get_group_service),
):
    form = await request.form()
    raw_data = {
        "name": form.get("name"),
        "description": form.get("description") or None,
        "owner_id": form.get("owner_id") or None,
    }

    try:
        payload = GroupCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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
        await commit_transaction(db, "create_group_form")
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


@router.put("/{group_id}", response_class=HTMLResponse)
async def update_group_form(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    group_service: GroupCrudService = Depends(get_group_service),
):
    group = await group_service.get_by_id(group_id)
    if not group:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Group not found.</div>",
            status_code=404,
        )
    group_ns = GroupResponse.model_validate(group, from_attributes=True)

    form = await request.form()
    raw_data = {
        "name": form.get("name"),
        "description": form.get("description") or None,
        "owner_id": form.get("owner_id") or None,
    }

    try:
        payload = GroupUpdate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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

    await commit_transaction(db, "update_group_form")
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.post("/{group_id}/posts", response_class=HTMLResponse)
async def create_group_post_form(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
):
    form = await request.form()
    raw_data = {
        "group_id": group_id,
        "title": form.get("title") or None,
        "content": form.get("content"),
        "author_id": form.get("author_id") or None,
    }

    try:
        payload = GroupPostCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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

    try:
        await post_service.create_post(payload.model_dump(), current_user)
        await commit_transaction(db, "create_group_post_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "group_id": group_id,
            "post": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": {"general": [str(exc)]},
        }
        return templates.TemplateResponse(
            "community/groups/partials/post_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshPosts, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/posts/{post_id}", response_class=HTMLResponse)
async def update_group_post_form(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Post not found.</div>",
            status_code=404,
        )
    post_ns = GroupPostResponse.model_validate(post, from_attributes=True).model_dump()
    post_ns = SimpleNamespace(**post_ns)

    form = await request.form()
    raw_data = {
        "title": form.get("title") or None,
        "content": form.get("content"),
        "author_id": form.get("author_id") or None,
    }

    try:
        payload = GroupPostUpdate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {
            "request": request,
            "group_id": post.group_id,
            "post": post_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/groups/partials/post_form.html",
            context,
            status_code=400,
        )

    try:
        updated_post = await post_service.update_post(
            post_id,
            payload.model_dump(exclude_unset=True),
            current_user,
        )
        if not updated_post:
            raise ValueError("Post not found.")
        await commit_transaction(db, "update_group_post_form")
    except ValueError as exc:
        await db.rollback()
        context = {
            "request": request,
            "group_id": post.group_id,
            "post": post_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": {"general": [str(exc)]},
        }
        return templates.TemplateResponse(
            "community/groups/partials/post_form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshPosts, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- Group discussion feed (HTMX) ---


@router.get("/{group_id}/partials/feed", response_class=HTMLResponse)
async def group_feed_partial(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    group_service: GroupCrudService = Depends(get_group_service),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    group = await group_service.get_by_id(group_id)
    if not group:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Group not found.</div>", status_code=404)

    posts, total = await _build_feed(group_id, post_service, comment_service, db, current_user)
    context = {
        "request": request,
        "group": group,
        "posts": posts,
        "post_errors": None,
        "post_form_data": None,
        "can_moderate": _is_moderator(current_user),
        "post_total": total,
    }
    return templates.TemplateResponse("community/groups/partials/feed.html", context)


@router.post("/{group_id}/posts/partials", response_class=HTMLResponse)
async def create_group_post_inline(
    request: Request,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    group_service: GroupCrudService = Depends(get_group_service),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    group = await group_service.get_by_id(group_id)
    if not group:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Group not found.</div>", status_code=404)

    form = await request.form()
    raw_data = {
        "group_id": group_id,
        "title": (form.get("title") or "").strip() or None,
        "content": (form.get("content") or "").strip(),
        "author_id": getattr(current_user, "id", None),
    }

    try:
        payload = GroupPostCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        posts, total = await _build_feed(group_id, post_service, comment_service, db, current_user)
        context = {
            "request": request,
            "group": group,
            "posts": posts,
            "post_errors": errors,
            "post_form_data": SimpleNamespace(**raw_data),
            "can_moderate": _is_moderator(current_user),
            "post_total": total,
        }
        return templates.TemplateResponse("community/groups/partials/feed.html", context, status_code=400)

    await post_service.create_post(payload.model_dump(), current_user)
    await commit_transaction(db, "create_group_post_inline")

    posts, total = await _build_feed(group_id, post_service, comment_service, db, current_user)
    context = {
        "request": request,
        "group": group,
        "posts": posts,
        "post_errors": None,
        "post_form_data": None,
        "can_moderate": _is_moderator(current_user),
        "post_total": total,
    }
    return templates.TemplateResponse("community/groups/partials/feed.html", context)


@router.get("/posts/{post_id}/partials", response_class=HTMLResponse)
async def get_post_card_partial(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)
    post_view = await _load_post_view(post, comment_service, db, current_user)
    context = {"request": request, "post": post_view, "can_moderate": _is_moderator(current_user)}
    return templates.TemplateResponse("community/groups/partials/post_card.html", context)


@router.get("/posts/{post_id}/partials/edit", response_class=HTMLResponse)
async def edit_post_partial(
    request: Request,
    post_id: str,
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)

    if not _can_edit(post.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot edit this post.</div>", status_code=403)

    post_ns = SimpleNamespace(
        id=post.id,
        title=post.title,
        content=post.content,
        group_id=post.group_id,
    )
    context = {"request": request, "post": post_ns}
    return templates.TemplateResponse("community/groups/partials/post_edit_form.html", context)


@router.put("/posts/{post_id}/partials", response_class=HTMLResponse)
async def update_post_partial(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)

    if not _can_edit(post.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot edit this post.</div>", status_code=403)

    form = await request.form()
    raw_data = {
        "title": (form.get("title") or "").strip() or None,
        "content": (form.get("content") or "").strip(),
        "author_id": getattr(current_user, "id", None),
    }

    try:
        payload = GroupPostUpdate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {"request": request, "post": SimpleNamespace(**{**raw_data, "id": post.id}), "errors": errors}
        return templates.TemplateResponse("community/groups/partials/post_edit_form.html", context, status_code=400)

    updated_post = await post_service.update_post(
        post_id,
        payload.model_dump(exclude_unset=True),
        current_user,
    )
    if not updated_post:
        await db.rollback()
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)

    await commit_transaction(db, "update_post_partial")
    post_view = await _load_post_view(updated_post, comment_service, db, current_user)
    context = {"request": request, "post": post_view, "can_moderate": _is_moderator(current_user)}
    return templates.TemplateResponse("community/groups/partials/post_card.html", context)


@router.delete("/posts/{post_id}/partials", response_class=HTMLResponse)
async def delete_post_partial(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)

    if not _can_edit(post.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot delete this post.</div>", status_code=403)

    await post_service.delete_post(post_id)
    await commit_transaction(db, "delete_post_partial")

    posts, total = await _build_feed(post.group_id, post_service, comment_service, db, current_user)
    context = {
        "request": request,
        "group": SimpleNamespace(id=post.group_id),
        "posts": posts,
        "post_errors": None,
        "post_form_data": None,
        "can_moderate": _is_moderator(current_user),
        "post_total": total,
    }
    return templates.TemplateResponse("community/groups/partials/feed.html", context)


@router.post("/posts/{post_id}/comments", response_class=HTMLResponse)
async def create_comment_partial(
    request: Request,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)

    form = await request.form()
    raw_data = {
        "post_id": post_id,
        "content": (form.get("content") or "").strip(),
        "author_id": getattr(current_user, "id", None),
    }

    try:
        payload = GroupCommentCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        post_view = await _load_post_view(post, comment_service, db, current_user)
        context = {
            "request": request,
            "post": post_view,
            "comment_errors": errors,
            "comment_form_data": SimpleNamespace(**raw_data),
            "can_moderate": _is_moderator(current_user),
        }
        return templates.TemplateResponse("community/groups/partials/comment_list.html", context, status_code=400)

    await comment_service.create_comment(payload.model_dump(), current_user)
    await commit_transaction(db, "create_comment_partial")

    post_view = await _load_post_view(post, comment_service, db, current_user)
    context = {"request": request, "post": post_view, "can_moderate": _is_moderator(current_user)}
    return templates.TemplateResponse("community/groups/partials/comment_list.html", context)


@router.get("/posts/{post_id}/comments/{comment_id}/partials/edit", response_class=HTMLResponse)
async def edit_comment_partial(
    request: Request,
    post_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)
    comment = await comment_service.get_by_id(comment_id)
    if not comment:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Comment not found.</div>", status_code=404)
    if not _can_edit(comment.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot edit this comment.</div>", status_code=403)

    context = {"request": request, "post_id": post_id, "comment": comment}
    return templates.TemplateResponse("community/groups/partials/comment_edit_form.html", context)


@router.put("/posts/{post_id}/comments/{comment_id}", response_class=HTMLResponse)
async def update_comment_partial(
    request: Request,
    post_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)
    comment = await comment_service.get_by_id(comment_id)
    if not comment:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Comment not found.</div>", status_code=404)
    if not _can_edit(comment.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot edit this comment.</div>", status_code=403)

    form = await request.form()
    raw_data = {
        "content": (form.get("content") or "").strip(),
    }
    try:
        payload = GroupCommentCreate(**{"post_id": post_id, "content": raw_data["content"]})
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {"request": request, "post_id": post_id, "comment": comment, "errors": errors}
        return templates.TemplateResponse("community/groups/partials/comment_edit_form.html", context, status_code=400)

    updated = await comment_service.update_comment(comment_id, {"content": payload.content}, current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse("<div class='alert alert-danger mb-0'>Comment not found.</div>", status_code=404)

    await commit_transaction(db, "update_comment_partial")
    post_view = await _load_post_view(post, comment_service, db, current_user)
    context = {"request": request, "post": post_view, "can_moderate": _is_moderator(current_user)}
    return templates.TemplateResponse("community/groups/partials/comment_list.html", context)


@router.delete("/posts/{post_id}/comments/{comment_id}", response_class=HTMLResponse)
async def delete_comment_partial(
    request: Request,
    post_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    post_service: GroupPostCrudService = Depends(get_group_post_service),
    comment_service: GroupCommentCrudService = Depends(get_group_comment_service),
):
    post = await post_service.get_by_id(post_id)
    if not post:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Post not found.</div>", status_code=404)
    comment = await comment_service.get_by_id(comment_id)
    if not comment:
        return HTMLResponse("<div class='alert alert-danger mb-0'>Comment not found.</div>", status_code=404)
    if not _can_edit(comment.author_id, current_user):
        return HTMLResponse("<div class='alert alert-warning mb-0'>You cannot delete this comment.</div>", status_code=403)

    await comment_service.delete_comment(comment_id)
    await commit_transaction(db, "delete_comment_partial")

    post_view = await _load_post_view(post, comment_service, db, current_user)
    context = {"request": request, "post": post_view, "can_moderate": _is_moderator(current_user)}
    return templates.TemplateResponse("community/groups/partials/comment_list.html", context)


# --- API endpoints ---

@router.get("/api")
async def list_groups_api(
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    service: GroupCrudService = Depends(get_group_service),
):
    """Return paginated group data."""
    try:
        groups, total = await service.list_groups(search=search, limit=limit, offset=offset)
        return {
            "data": [group.to_dict() for group in groups],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        handle_route_error("list_groups_api", exc)
        raise HTTPException(status_code=500, detail="Failed to list groups")


@router.post("/api", response_model=GroupResponse, status_code=201)
async def create_group_api(
    payload: GroupCreate,
    service: GroupCrudService = Depends(get_group_service),
    current_user: User = Depends(get_current_user),
):
    group = await service.create_group(payload.model_dump(), current_user)
    if not group:
        raise HTTPException(status_code=500, detail="Failed to create group")
    return GroupResponse.model_validate(group, from_attributes=True)


@router.put("/api/{group_id}", response_model=GroupResponse)
async def update_group_api(
    group_id: str,
    payload: GroupUpdate,
    service: GroupCrudService = Depends(get_group_service),
    current_user: User = Depends(get_current_user),
):
    group = await service.update_group(group_id, payload.model_dump(exclude_unset=True), current_user)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group, from_attributes=True)


@router.delete("/api/{group_id}", status_code=204)
async def delete_group_api(
    group_id: str,
    service: GroupCrudService = Depends(get_group_service),
):
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    return Response(status_code=204)


@router.get("/api/{group_id}/posts")
async def list_posts_api(
    group_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    service: GroupPostCrudService = Depends(get_group_post_service),
):
    posts, total = await service.list_posts(group_id=group_id, limit=limit, offset=offset)
    return {
        "data": [post.to_dict() for post in posts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/{group_id}/posts", response_model=GroupPostResponse, status_code=201)
async def create_post_api(
    group_id: str,
    payload: GroupPostCreate,
    service: GroupPostCrudService = Depends(get_group_post_service),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["group_id"] = group_id
    post = await service.create_post(data, current_user)
    if not post:
        raise HTTPException(status_code=500, detail="Failed to create post")
    return GroupPostResponse.model_validate(post, from_attributes=True)


@router.put("/api/posts/{post_id}", response_model=GroupPostResponse)
async def update_post_api(
    post_id: str,
    payload: GroupPostUpdate,
    service: GroupPostCrudService = Depends(get_group_post_service),
    current_user: User = Depends(get_current_user),
):
    post = await service.update_post(post_id, payload.model_dump(exclude_unset=True), current_user)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return GroupPostResponse.model_validate(post, from_attributes=True)


@router.delete("/api/posts/{post_id}", status_code=204)
async def delete_post_api(
    post_id: str,
    service: GroupPostCrudService = Depends(get_group_post_service),
):
    deleted = await service.delete_by_id(post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return Response(status_code=204)


__all__ = ["router"]
