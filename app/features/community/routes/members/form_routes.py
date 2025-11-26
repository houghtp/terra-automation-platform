"""Form routes for community members (modal GET only)."""

from types import SimpleNamespace

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
    get_db,
    AsyncSession,
)
from sqlalchemy import select
from app.features.auth.models import User as AuthUser

from ...dependencies import get_member_service, get_member_form_service
from ...schemas import MemberResponse
from ...services import MemberCrudService, MemberFormService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def member_form_partial(
    request: Request,
    member_id: str | None = None,
    member_service: MemberCrudService = Depends(get_member_service),
    member_form_service: MemberFormService = Depends(get_member_form_service),
    db: AsyncSession = Depends(get_db),
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
    partner_options = await member_form_service.get_partner_options()
    result = await db.execute(select(AuthUser).order_by(AuthUser.name))
    user_options = result.scalars().all()

    context = {
        "request": request,
        "member": member,
        "form_data": None,
        "errors": {},
        "specialties_text": ", ".join(member.specialties or []) if member else "",
        "tags_text": ", ".join(member.tags or []) if member else "",
        "partner_options": partner_options,
        "user_options": user_options,
    }
    return templates.TemplateResponse("community/members/partials/form.html", context)


@router.get("/{member_id}/edit", response_class=HTMLResponse)
async def member_edit_form(
    request: Request,
    member_id: str,
    member_service: MemberCrudService = Depends(get_member_service),
    member_form_service: MemberFormService = Depends(get_member_form_service),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated edit endpoint to mirror users slice pattern."""
    member = await member_service.get_by_id(member_id)
    if not member:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Member not found.</div>",
            status_code=404,
        )

    member_ns = _member_to_namespace(member)
    partner_options = await member_form_service.get_partner_options()
    result = await db.execute(select(AuthUser).order_by(AuthUser.name))
    user_options = result.scalars().all()
    context = {
        "request": request,
        "member": member_ns,
        "form_data": None,
        "errors": {},
        "specialties_text": ", ".join(member_ns.specialties or []),
        "tags_text": ", ".join(member_ns.tags or []),
        "partner_options": partner_options,
        "user_options": user_options,
    }
    return templates.TemplateResponse("community/members/partials/form.html", context)


def _member_to_namespace(member):
    data = MemberResponse.model_validate(member, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


@router.get("/partials/users", response_class=HTMLResponse)
async def member_user_lookup(
    request: Request,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Search platform users to link a member to a login."""
    search = (q or "").strip().lower()
    stmt = select(AuthUser)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(func.lower(AuthUser.name).like(like), func.lower(AuthUser.email).like(like)))
    stmt = stmt.order_by(func.lower(AuthUser.name)).limit(10)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return templates.TemplateResponse(
        "community/members/partials/user_options.html",
        {"request": request, "users": users},
    )


@router.get("/partials/user_select", response_class=HTMLResponse)
async def member_user_select(
    request: Request,
    user_id: str,
    label: str,
):
    return templates.TemplateResponse(
        "community/members/partials/user_select.html",
        {"request": request, "user_id": user_id, "label": label},
    )


__all__ = ["router"]
