"""Form routes for community groups (modal GET only)."""

from types import SimpleNamespace

from sqlalchemy import select

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    get_current_user,
    HTMLResponse,
    Request,
    templates,
    User,
)

from ...dependencies import get_group_service, get_group_post_service
from ...schemas import GroupResponse, GroupPostResponse
from ...services import GroupCrudService, GroupPostCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def group_form_partial(
    request: Request,
    group_id: str | None = None,
    current_user: User = Depends(get_current_user),
    group_service: GroupCrudService = Depends(get_group_service),
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

    owner_id = group.owner_id if group else getattr(current_user, "id", None)
    owner_name = None
    if owner_id:
        # Prefer current_user if matches, otherwise look up, finally fallback to ID
        if getattr(current_user, "id", None) == owner_id:
            owner_name = getattr(current_user, "name", None) or getattr(current_user, "email", None)
        if not owner_name:
            try:
                result = await group_service.db.execute(select(User).where(User.id == owner_id))
                owner = result.scalar_one_or_none()
                if owner:
                    owner_name = owner.name or owner.email
            except Exception:
                owner_name = None
        owner_name = owner_name or owner_id

    context = {
        "request": request,
        "group": group,
        "form_data": None,
        "errors": {},
        "owner_id": owner_id,
        "owner_name": owner_name,
    }
    return templates.TemplateResponse("community/groups/partials/form.html", context)


@router.get("/{group_id}/posts/partials/form", response_class=HTMLResponse)
async def group_post_form_partial(
    request: Request,
    group_id: str,
    post_id: str | None = None,
    post_service: GroupPostCrudService = Depends(get_group_post_service),
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


def _group_to_namespace(group) -> SimpleNamespace:
    data = GroupResponse.model_validate(group, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


__all__ = ["router"]
