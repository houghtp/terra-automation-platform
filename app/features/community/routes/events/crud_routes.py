"""CRUD routes for community events (HTMX submits + APIs)."""

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

from ...dependencies import get_event_service
from ...schemas import EventCreate, EventResponse, EventUpdate
from ...services import EventCrudService

router = APIRouter()


# --- HTMX form submissions ---

@router.post("/", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    event_service: EventCrudService = Depends(get_event_service),
):
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
        payload = EventCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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
    await commit_transaction(db, "create_event_form")
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/{event_id}", response_class=HTMLResponse)
async def update_event_form(
    request: Request,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    event_service: EventCrudService = Depends(get_event_service),
):
    event = await event_service.get_by_id(event_id)
    if not event:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Event not found.</div>",
            status_code=404,
        )
    event_ns = EventResponse.model_validate(event, from_attributes=True)

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
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
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

    await commit_transaction(db, "update_event_form")
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- API endpoints ---

@router.get("/api")
async def list_events_api(
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    service: EventCrudService = Depends(get_event_service),
):
    events, total = await service.list_events(category=category, limit=limit, offset=offset)
    return {
        "data": [event.to_dict() for event in events],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api", response_model=EventResponse, status_code=201)
async def create_event_api(
    payload: EventCreate,
    current_user: User = Depends(get_current_user),
    service: EventCrudService = Depends(get_event_service),
):
    event = await service.create_event(payload.model_dump(), current_user)
    if not event:
        raise HTTPException(status_code=500, detail="Failed to create event")
    return EventResponse.model_validate(event, from_attributes=True)


@router.put("/api/{event_id}", response_model=EventResponse)
async def update_event_api(
    event_id: str,
    payload: EventUpdate,
    current_user: User = Depends(get_current_user),
    service: EventCrudService = Depends(get_event_service),
):
    event = await service.update_event(event_id, payload.model_dump(exclude_unset=True), current_user)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event, from_attributes=True)


@router.delete("/api/{event_id}", status_code=204)
async def delete_event_api(
    event_id: str,
    service: EventCrudService = Depends(get_event_service),
):
    deleted = await service.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return Response(status_code=204)


# --- HTMX delete ---


@router.delete("/{event_id}", response_class=HTMLResponse)
async def delete_event_form(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    event_service: EventCrudService = Depends(get_event_service),
):
    deleted = await event_service.delete_event(event_id)
    if not deleted:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Event not found.</div>",
            status_code=404,
        )
    await commit_transaction(db, "delete_event_form")
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


__all__ = ["router"]
