"""Form routes for community members (modal GET only)."""

from types import SimpleNamespace

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
)

from ...dependencies import get_member_service
from ...schemas import MemberResponse
from ...services import MemberCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def member_form_partial(
    request: Request,
    member_id: str | None = None,
    member_service: MemberCrudService = Depends(get_member_service),
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


@router.get("/{member_id}/edit", response_class=HTMLResponse)
async def member_edit_form(
    request: Request,
    member_id: str,
    member_service: MemberCrudService = Depends(get_member_service),
):
    """Dedicated edit endpoint to mirror users slice pattern."""
    member = await member_service.get_by_id(member_id)
    if not member:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Member not found.</div>",
            status_code=404,
        )

    member_ns = _member_to_namespace(member)
    context = {
        "request": request,
        "member": member_ns,
        "form_data": None,
        "errors": {},
        "specialties_text": ", ".join(member_ns.specialties or []),
        "tags_text": ", ".join(member_ns.tags or []),
    }
    return templates.TemplateResponse("community/members/partials/form.html", context)


def _member_to_namespace(member):
    data = MemberResponse.model_validate(member, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


__all__ = ["router"]
