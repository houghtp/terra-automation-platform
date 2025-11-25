"""CRUD routes for community members (HTMX submits + APIs)."""

import json
from types import SimpleNamespace
from typing import Optional, List

from pydantic import ValidationError

from app.features.core.route_imports import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    JSONResponse,
    Query,
    Response,
    AsyncSession,
    HTMLResponse,
    Request,
    commit_transaction,
    create_error_response,
    create_success_response,
    get_current_user,
    get_db,
    handle_route_error,
    templates,
    tenant_dependency,
    User,
)
from ...dependencies import get_member_service, get_member_form_service
from ...schemas import MemberCreate, MemberResponse, MemberUpdate
from ...services import MemberCrudService, MemberFormService

router = APIRouter()

def _norm_user(val):
    return None if not val or val == "None" else val


# --- HTMX form submissions ---

@router.post("/", response_class=HTMLResponse)
async def member_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    member_service: MemberCrudService = Depends(get_member_service),
    member_form_service: MemberFormService = Depends(get_member_form_service),
):
    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "email": form.get("email"),
        "bio": form.get("bio") or None,
        "aum_range": form.get("aum_range") or None,
        "location": form.get("location") or None,
        "specialties": [item.strip() for item in form.get("specialties", "").split(",") if item.strip()],
        "tags": [item.strip() for item in form.get("tags", "").split(",") if item.strip()],
        "partner_id": form.get("partner_id") or None,
        "user_id": _norm_user(form.get("user_id")),
    }

    try:
        payload = MemberCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {
            "request": request,
            "member": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
            "partner_options": await member_form_service.get_partner_options(),
        }
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await member_service.create_member(payload.model_dump(), current_user)
        await commit_transaction(db, "create_member_form")
    except ValueError as exc:
        errors = {"email": [str(exc)]}
        context = {
            "request": request,
            "member": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
            "partner_options": await member_form_service.get_partner_options(),
        }
        await db.rollback()
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/{member_id}", response_class=HTMLResponse)
async def member_update_form(
    request: Request,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    member_service: MemberCrudService = Depends(get_member_service),
    member_form_service: MemberFormService = Depends(get_member_form_service),
):
    member = await member_service.get_by_id(member_id)
    if not member:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Member not found.</div>",
            status_code=404,
        )
    member_ns = MemberResponse.model_validate(member, from_attributes=True)

    form = await request.form()

    raw_data = {
        "name": form.get("name"),
        "email": form.get("email"),
        "bio": form.get("bio") or None,
        "aum_range": form.get("aum_range") or None,
        "location": form.get("location") or None,
        "specialties": [item.strip() for item in form.get("specialties", "").split(",") if item.strip()],
        "tags": [item.strip() for item in form.get("tags", "").split(",") if item.strip()],
        "partner_id": form.get("partner_id") or None,
        "user_id": _norm_user(form.get("user_id")),
    }

    try:
        payload = MemberUpdate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {
            "request": request,
            "member": member_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
            "specialties_text": form.get("specialties", ""),
            "tags_text": form.get("tags", ""),
            "partner_options": await member_form_service.get_partner_options(),
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
        await commit_transaction(db, "update_member_form")
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
            "partner_options": await member_form_service.get_partner_options(),
        }
        return templates.TemplateResponse(
            "community/members/partials/form.html",
            context,
            status_code=400,
        )
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_member_form", exc)
        errors = {"general": [f"Failed to update member: {str(exc)}"]}
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


# --- API endpoints for Tabulator ---

@router.get("/api/list", response_class=JSONResponse)
async def list_members_api(
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    specialties: Optional[List[str]] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    member_service: MemberCrudService = Depends(get_member_service),
):
    """Return members list for Tabulator (standardized pattern)."""
    try:
        items, total = await member_service.list_members(
            search=search,
            tags=tags,
            specialties=specialties,
            limit=limit,
            offset=offset,
        )
        return [member.to_dict() for member in items]
    except Exception as exc:
        handle_route_error("list_members_api", exc)
        raise HTTPException(status_code=500, detail="Failed to list members")


@router.get("/api/{member_id}", response_model=MemberResponse)
async def get_member_api(
    member_id: str,
    member_service: MemberCrudService = Depends(get_member_service),
):
    """Fetch a single member."""
    member = await member_service.get_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return MemberResponse.model_validate(member, from_attributes=True)


@router.post("/api", response_model=MemberResponse, status_code=201)
async def create_member_api(
    payload: MemberCreate,
    db: AsyncSession = Depends(get_db),
    member_service: MemberCrudService = Depends(get_member_service),
    current_user: User = Depends(get_current_user),
):
    """Create a member using standard CRUD helpers."""
    try:
        member = await member_service.create_member(payload.model_dump(), current_user)
        await commit_transaction(db, "create_member")
        return MemberResponse.model_validate(member, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        handle_route_error("create_member_api", exc)
        raise HTTPException(status_code=500, detail="Failed to create member")


@router.put("/api/{member_id}", response_model=MemberResponse)
async def update_member_api(
    member_id: str,
    payload: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    member_service: MemberCrudService = Depends(get_member_service),
    current_user: User = Depends(get_current_user),
):
    """Update an existing member."""
    try:
        member = await member_service.update_member(
            member_id,
            payload.model_dump(exclude_unset=True),
            current_user,
        )
        if not member:
            raise HTTPException(status_code=404, detail="Member not found.")
        await commit_transaction(db, "update_member")
        return MemberResponse.model_validate(member, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_member_api", exc, member_id=member_id)
        raise HTTPException(status_code=500, detail="Failed to update member")


@router.patch("/api/{member_id}/field")
async def update_member_field_api(
    member_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    member_service: MemberCrudService = Depends(get_member_service),
):
    """Update a single member field (for Tabulator inline edits)."""
    field = field_update.get("field")
    value = field_update.get("value")

    if not field:
        return create_error_response("Field name is required", status_code=400)

    # Normalize list fields when they arrive as comma-separated strings
    if field in {"specialties", "tags"} and isinstance(value, str):
        parsed = value.strip()
        if parsed.startswith("[") or parsed.startswith("{"):
            try:
                value = json.loads(parsed)
            except json.JSONDecodeError:
                value = [item.strip() for item in parsed.split(",") if item.strip()]
        else:
            value = [item.strip() for item in parsed.split(",") if item.strip()]

    try:
        updated = await member_service.update_member_field(member_id, field, value, current_user)
        if not updated:
            raise HTTPException(status_code=404, detail="Member not found.")
        await commit_transaction(db, "update_member_field")
        return {"success": True}
    except ValueError as exc:
        await db.rollback()
        return create_error_response(str(exc), status_code=400)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_member_field_api", exc, member_id=member_id, field=field)
        raise HTTPException(status_code=500, detail="Failed to update member field")


@router.delete("/api/{member_id}", status_code=204)
async def delete_member_api(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    member_service: MemberCrudService = Depends(get_member_service),
    current_user: User = Depends(get_current_user),
):
    """Delete a member via API."""
    success = await member_service.delete_member(member_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found.")

    await commit_transaction(db, "delete_member")
    return Response(status_code=204)


@router.delete("/{member_id}/delete")
@router.post("/{member_id}/delete")
async def delete_member_ui(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    member_service: MemberCrudService = Depends(get_member_service),
    current_user: User = Depends(get_current_user),
):
    """Delete member endpoint compatible with table helpers."""
    success = await member_service.delete_member(member_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found.")

    await commit_transaction(db, "delete_member")
    return create_success_response()


__all__ = ["router"]
