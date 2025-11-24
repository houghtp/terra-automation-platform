"""Form routes for community polls (modal GET only)."""

from types import SimpleNamespace

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
)

from ...dependencies import get_poll_service
from ...schemas import PollResponse
from ...services import PollCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def poll_form_partial(
    request: Request,
    poll_id: str | None = None,
    poll_service: PollCrudService = Depends(get_poll_service),
):
    poll = None
    if poll_id:
        poll = await poll_service.get_by_id(poll_id)
        if not poll:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Poll not found.</div>",
                status_code=404,
            )
        poll = _poll_to_namespace(poll)

    context = {
        "request": request,
        "poll": poll,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/polls/partials/form.html", context)


def _poll_to_namespace(poll) -> SimpleNamespace:
    data = PollResponse.model_validate(poll, from_attributes=True).model_dump()
    return SimpleNamespace(**data)


__all__ = ["router"]
