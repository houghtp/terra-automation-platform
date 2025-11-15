"""API routes for community events."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User

from ..dependencies import get_event_service
from ..schemas import EventCreate, EventResponse, EventUpdate
from ..services import EventService

router = APIRouter(prefix="/events", tags=["community-events"])


@router.get("/api")
async def list_events_api(
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: EventService = Depends(get_event_service),
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
    service: EventService = Depends(get_event_service),
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
    service: EventService = Depends(get_event_service),
):
    event = await service.update_event(event_id, payload.model_dump(exclude_unset=True), current_user)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event, from_attributes=True)


@router.delete("/api/{event_id}", status_code=204)
async def delete_event_api(
    event_id: str,
    service: EventService = Depends(get_event_service),
):
    deleted = await service.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return Response(status_code=204)
