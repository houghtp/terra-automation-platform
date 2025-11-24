"""CRUD routes for community groups and posts (HTMX submits + APIs)."""

from types import SimpleNamespace
from typing import Optional

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
)
from ...services import (
    GroupCrudService,
    GroupPostCrudService,
)

router = APIRouter()


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
        "privacy": form.get("privacy") or "private",
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
        "privacy": form.get("privacy") or None,
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


# --- API endpoints ---

@router.get("/api")
async def list_groups_api(
    search: Optional[str] = Query(default=None),
    privacy: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    service: GroupCrudService = Depends(get_group_service),
):
    """Return paginated group data."""
    try:
        groups, total = await service.list_groups(search=search, privacy=privacy, limit=limit, offset=offset)
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
