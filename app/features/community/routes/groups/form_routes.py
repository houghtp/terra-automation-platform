"""Form routes for community groups (modal GET only)."""

from types import SimpleNamespace

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
)

from ...dependencies import get_group_service, get_group_post_service
from ...schemas import GroupResponse, GroupPostResponse
from ...services import GroupCrudService, GroupPostCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def group_form_partial(
    request: Request,
    group_id: str | None = None,
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

    context = {
        "request": request,
        "group": group,
        "form_data": None,
        "errors": {},
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
