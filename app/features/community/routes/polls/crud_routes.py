"""CRUD routes for community polls (HTMX submits + APIs)."""

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

from ...dependencies import get_poll_service, get_poll_vote_service
from ...schemas import (
    PollCreate,
    PollResponse,
    PollUpdate,
    PollVoteCreate,
    PollVoteResponse,
)
from ...services import PollCrudService, PollVoteCrudService

router = APIRouter()


# --- HTMX form submissions ---

@router.post("/", response_class=HTMLResponse)
async def create_poll_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    poll_service: PollCrudService = Depends(get_poll_service),
):
    form = await request.form()
    raw_data = {
        "question": form.get("question") or None,
        "status": form.get("status") or "draft",
        "expires_at": form.get("expires_at") or None,
    }

    try:
        payload = PollCreate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {
            "request": request,
            "poll": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    try:
        await poll_service.create_poll(payload.model_dump(), current_user)
        await commit_transaction(db, "create_poll_form")
    except Exception as exc:
        await db.rollback()
        context = {
            "request": request,
            "poll": None,
            "form_data": SimpleNamespace(**raw_data),
            "errors": {"general": [str(exc)]},
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


@router.put("/{poll_id}", response_class=HTMLResponse)
async def update_poll_form(
    request: Request,
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    poll_service: PollCrudService = Depends(get_poll_service),
):
    poll = await poll_service.get_by_id(poll_id)
    if not poll:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Poll not found.</div>",
            status_code=404,
        )
    poll_ns = PollResponse.model_validate(poll, from_attributes=True)

    form = await request.form()
    raw_data = {
        "question": form.get("question") or None,
        "status": form.get("status") or None,
        "expires_at": form.get("expires_at") or None,
    }

    try:
        payload = PollUpdate(**raw_data)
    except ValidationError as exc:
        errors = {err["loc"][0]: [err["msg"]] for err in exc.errors()}
        context = {
            "request": request,
            "poll": poll_ns,
            "form_data": SimpleNamespace(**raw_data),
            "errors": errors,
        }
        return templates.TemplateResponse(
            "community/polls/partials/form.html",
            context,
            status_code=400,
        )

    updated = await poll_service.update_poll(poll_id, payload.model_dump(exclude_unset=True), current_user)
    if not updated:
        await db.rollback()
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Poll not found.</div>",
            status_code=404,
        )

    await commit_transaction(db, "update_poll_form")
    headers = {"HX-Trigger": "closeModal, refreshTable, showSuccess"}
    return Response(status_code=204, headers=headers)


# --- API endpoints ---

@router.get("/api")
async def list_polls_api(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    service: PollCrudService = Depends(get_poll_service),
):
    polls, total = await service.list_polls(status=status, limit=limit, offset=offset)
    data = []
    for poll in polls:
        payload = poll.to_dict()
        payload["options"] = [option.to_dict() for option in poll.options] if hasattr(poll, "options") else []
        data.append(payload)
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api", response_model=PollResponse, status_code=201)
async def create_poll_api(
    payload: PollCreate,
    current_user: User = Depends(get_current_user),
    service: PollCrudService = Depends(get_poll_service),
):
    poll = await service.create_poll(payload.model_dump(), current_user)
    if not poll:
        raise HTTPException(status_code=500, detail="Failed to create poll")
    poll_dict = poll.to_dict()
    poll_dict["options"] = [option.to_dict() for option in poll.options]
    return PollResponse.model_validate(poll_dict)


@router.put("/api/{poll_id}", response_model=PollResponse)
async def update_poll_api(
    poll_id: str,
    payload: PollUpdate,
    current_user: User = Depends(get_current_user),
    service: PollCrudService = Depends(get_poll_service),
):
    poll = await service.update_poll(poll_id, payload.model_dump(exclude_unset=True), current_user)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll_dict = poll.to_dict()
    poll_dict["options"] = [option.to_dict() for option in poll.options]
    return PollResponse.model_validate(poll_dict)


@router.delete("/api/{poll_id}", status_code=204)
async def delete_poll_api(
    poll_id: str,
    service: PollCrudService = Depends(get_poll_service),
):
    deleted = await service.delete_poll(poll_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Poll not found")
    return Response(status_code=204)


@router.post("/api/{poll_id}/vote", response_model=PollVoteResponse, status_code=201)
async def cast_vote_api(
    poll_id: str,
    payload: PollVoteCreate,
    current_user: User = Depends(get_current_user),
    vote_service: PollVoteCrudService = Depends(get_poll_vote_service),
):
    data = payload.model_dump()
    vote = await vote_service.cast_vote(
        poll_id=poll_id,
        option_id=data["option_id"],
        member_id=current_user.id if current_user else None,
    )
    return PollVoteResponse.model_validate(vote, from_attributes=True)


@router.get("/api/{poll_id}/summary")
async def poll_summary_api(
    poll_id: str,
    vote_service: PollVoteCrudService = Depends(get_poll_vote_service),
):
    return {"data": await vote_service.vote_summary(poll_id)}


__all__ = ["router"]
