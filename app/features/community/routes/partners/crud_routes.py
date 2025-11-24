"""CRUD routes for community partners (HTMX submits + APIs)."""

from types import SimpleNamespace
from typing import Optional

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

from ...dependencies import get_partner_service
from ...schemas import PartnerCreate, PartnerResponse, PartnerUpdate
from ...services import PartnerCrudService

router = APIRouter()


# --- HTMX form submissions ---

@router.post("/", response_class=HTMLResponse)
async def partner_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerCrudService = Depends(get_partner_service),
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
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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
        await commit_transaction(db, "create_partner_form")
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


@router.put("/{partner_id}", response_class=HTMLResponse)
async def partner_update_form(
    request: Request,
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerCrudService = Depends(get_partner_service),
):
    partner = await partner_service.get_by_id(partner_id)
    if not partner:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Partner not found.</div>",
            status_code=404,
        )
    partner_ns = PartnerResponse.model_validate(partner, from_attributes=True)

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
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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
        await commit_transaction(db, "update_partner_form")
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


# --- API endpoints for Tabulator ---

@router.get("/api", response_class=JSONResponse)
async def list_partners_api(
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    partner_service: PartnerCrudService = Depends(get_partner_service),
):
    """Return paginated partner directory entries."""
    try:
        items, total = await partner_service.list_partners(
            search=search,
            category=category,
            limit=limit,
            offset=offset,
        )
        return {
            "data": [partner.to_dict() for partner in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        handle_route_error("list_partners_api", exc)
        raise HTTPException(status_code=500, detail="Failed to list partners")


@router.get("/api/{partner_id}", response_model=PartnerResponse)
async def get_partner_api(
    partner_id: str,
    partner_service: PartnerCrudService = Depends(get_partner_service),
):
    """Fetch a single partner entry."""
    partner = await partner_service.get_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found.")
    return PartnerResponse.model_validate(partner, from_attributes=True)


@router.post("/api", response_model=PartnerResponse, status_code=201)
async def create_partner_api(
    payload: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerCrudService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new partner directory entry."""
    try:
        partner = await partner_service.create_partner(payload.model_dump(), current_user)
        await commit_transaction(db, "create_partner")
        return PartnerResponse.model_validate(partner, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        handle_route_error("create_partner_api", exc)
        raise HTTPException(status_code=500, detail="Failed to create partner")


@router.put("/api/{partner_id}", response_model=PartnerResponse)
async def update_partner_api(
    partner_id: str,
    payload: PartnerUpdate,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerCrudService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Update a partner entry."""
    try:
        partner = await partner_service.update_partner(
            partner_id,
            payload.model_dump(exclude_unset=True),
            current_user,
        )
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found.")
        await commit_transaction(db, "update_partner")
        return PartnerResponse.model_validate(partner, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_partner_api", exc, partner_id=partner_id)
        raise HTTPException(status_code=500, detail="Failed to update partner")


@router.patch("/api/{partner_id}/field")
async def update_partner_field_api(
    partner_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerCrudService = Depends(get_partner_service),
):
    """Update a single partner field (inline editing support)."""
    field = field_update.get("field")
    value = field_update.get("value")

    if not field:
        return create_error_response("Field name is required", status_code=400)

    try:
        updated = await partner_service.update_partner_field(partner_id, field, value, current_user)
        if not updated:
            raise HTTPException(status_code=404, detail="Partner not found.")
        await commit_transaction(db, "update_partner_field")
        return {"success": True}
    except ValueError as exc:
        await db.rollback()
        return create_error_response(str(exc), status_code=400)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_partner_field_api", exc, partner_id=partner_id, field=field)
        raise HTTPException(status_code=500, detail="Failed to update partner field")


@router.delete("/api/{partner_id}", status_code=204)
async def delete_partner_api(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerCrudService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Delete a partner entry."""
    success = await partner_service.delete_partner(partner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found.")

    await commit_transaction(db, "delete_partner")
    return Response(status_code=204)


@router.delete("/{partner_id}/delete")
@router.post("/{partner_id}/delete")
async def delete_partner_ui(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerCrudService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Delete partner endpoint compatible with table helpers."""
    success = await partner_service.delete_partner(partner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found.")

    await commit_transaction(db, "delete_partner")
    return create_success_response()


__all__ = ["router"]
