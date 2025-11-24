"""Form routes for community messages (modal GET only)."""

from types import SimpleNamespace
from typing import Dict, List

from pydantic import ValidationError

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    Response,
    templates,
    get_db,
    tenant_dependency,
    get_current_user,
    User,
    AsyncSession,
    commit_transaction,
)

from ...dependencies import get_message_service
from ...schemas import MessageCreate
from ...services import MessageCrudService

router = APIRouter()


def _validation_errors_to_dict(error: ValidationError) -> Dict[str, List[str]]:
    """Convert Pydantic validation errors to dictionary format."""
    errors: Dict[str, List[str]] = {}
    for err in error.errors():
        field = err["loc"][0]
        errors.setdefault(field, []).append(err["msg"])
    return errors


@router.get("/partials/form", response_class=HTMLResponse)
async def message_form_partial(request: Request):
    """Render the message form modal (new message only)."""
    return templates.TemplateResponse(
        "community/messages/partials/form.html",
        {"request": request, "errors": {}, "form_data": None},
    )


@router.post("/", response_class=HTMLResponse)
async def send_message_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
):
    """Handle message form submission."""
    form = await request.form()
    raw_data = {
        "recipient_id": form.get("recipient_id"),
        "content": form.get("content"),
        "thread_id": form.get("thread_id") or None,
    }

    try:
        payload = MessageCreate(**raw_data)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        context = {
            "request": request,
            "errors": errors,
            "form_data": SimpleNamespace(**raw_data),
        }
        return templates.TemplateResponse(
            "community/messages/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await message_service.send_message(payload.model_dump(), sender_id=current_user.id)
        await commit_transaction(db, "create_message_form")
    except ValueError as exc:
        await db.rollback()
        context = {
            "request": request,
            "errors": {"recipient_id": [str(exc)]},
            "form_data": SimpleNamespace(**raw_data),
        }
        return templates.TemplateResponse(
            "community/messages/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


__all__ = ["router"]
