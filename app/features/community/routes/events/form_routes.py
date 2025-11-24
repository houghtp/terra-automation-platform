"""Form routes for community events (modal GET only)."""

from types import SimpleNamespace

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
)

from ...dependencies import get_event_service
from ...schemas import EventResponse
from ...services import EventCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def event_form_partial(
    request: Request,
    event_id: str | None = None,
    event_service: EventCrudService = Depends(get_event_service),
):
    event = None
    if event_id:
        event = await event_service.get_by_id(event_id)
        if not event:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Event not found.</div>",
                status_code=404,
            )
        event = _event_to_namespace(event)

    context = {
        "request": request,
        "event": event,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/events/partials/form.html", context)


def _event_to_namespace(event) -> SimpleNamespace:
    data = EventResponse.model_validate(event, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


__all__ = ["router"]
