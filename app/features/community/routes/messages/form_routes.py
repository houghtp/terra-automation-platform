"""HTML + HTMX routes for community messages."""

import json
from types import SimpleNamespace
from typing import Dict, List, Optional
from sqlalchemy import select

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
from sqlalchemy import func, or_
from app.features.community.models import Member

from ...dependencies import get_message_service
from ...schemas import MessageCreate
from ...services import MessageCrudService
from app.features.auth.models import User

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
    """Deprecated modal form (kept for compatibility)."""
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
        message = await message_service.create_message(payload.model_dump(), sender_id=current_user.id)
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

    thread_id = message.thread_id
    trigger = {
        "closeModal": True,
        "showSuccess": True,
        "refreshConversations": True,
        "openThread": {
            "thread_url": f"/features/community/messages/threads/{thread_id}",
            "subtitle": f"Thread with {payload.recipient_id}",
        },
    }
    headers = {"HX-Trigger": json.dumps(trigger)}
    return Response(status_code=204, headers=headers)


@router.get("/partials/new", response_class=HTMLResponse)
async def new_thread_form(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "community/messages/partials/new_thread.html",
        {"request": request, "current_member_id": current_user.id},
    )


@router.post("/partials/new", response_class=HTMLResponse)
async def create_new_thread(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
):
    form = await request.form()
    recipient_id = form.get("recipient_id")
    content = form.get("content")
    try:
        payload = MessageCreate(recipient_id=recipient_id, content=content, thread_id=None)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        return templates.TemplateResponse(
            "community/messages/partials/new_thread.html",
            {"request": request, "errors": errors, "current_member_id": current_user.id, "recipient_id": recipient_id, "content": content},
            status_code=400,
        )

    try:
        message = await message_service.create_message(payload.model_dump(), sender_id=current_user.id)
        await commit_transaction(db, "create_message_form")
        thread_id = message.thread_id
        messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
        return templates.TemplateResponse(
            "community/messages/partials/thread.html",
            {
                "request": request,
                "messages": messages,
                "thread_id": thread_id,
                "other_party": recipient_id,
                "other_party_name": None,
                "other_party_email": None,
                "current_member_id": current_user.id,
            },
        )
    except Exception as exc:
        await db.rollback()
        errors = {"general": [str(exc)]}
        return templates.TemplateResponse(
            "community/messages/partials/new_thread.html",
            {"request": request, "errors": errors, "current_member_id": current_user.id, "recipient_id": recipient_id, "content": content},
            status_code=400,
        )


@router.get("/partials/recipients", response_class=HTMLResponse)
async def recipient_options(
    request: Request,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
):
    search = (q or "").strip().lower()
    stmt = (
        select(User)
        .join(Member, Member.user_id == User.id)
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(like),
                func.lower(User.email).like(like),
            )
        )
    stmt = stmt.order_by(func.lower(User.name)).limit(10)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_options.html",
        {"request": request, "users": users},
    )


@router.get("/partials/select_recipient", response_class=HTMLResponse)
async def select_recipient(
    request: Request,
    recipient_id: str,
    label: str,
):
    return templates.TemplateResponse(
        "community/messages/partials/select_recipient.html",
        {"request": request, "recipient_id": recipient_id, "label": label},
    )


@router.get("/partials/conversations", response_class=HTMLResponse)
async def conversation_rail(
    request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
):
    """Render the left-rail conversation list."""
    conversations = await message_service.list_conversation_summaries(member_id=current_user.id, limit=50)
    return templates.TemplateResponse(
        "community/messages/partials/conversation_list.html",
        {"request": request, "conversations": conversations, "current_member_id": current_user.id},
    )


@router.get("/threads/{thread_id}", response_class=HTMLResponse)
async def thread_view(
    thread_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
    db: AsyncSession = Depends(get_db),
):
    """Render a thread with composer."""
    messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
    other_party: Optional[str] = None
    other_party_name: Optional[str] = None
    other_party_email: Optional[str] = None
    if messages:
        first = messages[0]
        other_party = first.recipient_id if first.sender_id == current_user.id else first.sender_id
        user_stmt = select(User).where(User.id == other_party)
        res = await db.execute(user_stmt)
        user = res.scalar_one_or_none()
        if user:
            other_party_name = user.name
            other_party_email = user.email
    context = {
        "request": request,
        "messages": messages,
        "thread_id": thread_id,
        "other_party": other_party,
        "other_party_name": other_party_name,
        "other_party_email": other_party_email,
        "current_member_id": current_user.id,
    }
    return templates.TemplateResponse("community/messages/partials/thread.html", context)


@router.post("/threads/{thread_id}/reply", response_class=HTMLResponse)
async def thread_reply(
    thread_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
):
    """Post a reply and re-render the thread."""
    form = await request.form()
    recipient_id = form.get("recipient_id")
    content = form.get("content")

    try:
        payload = MessageCreate(recipient_id=recipient_id, content=content, thread_id=thread_id)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
        context = {
            "request": request,
            "messages": messages,
            "thread_id": thread_id,
            "other_party": recipient_id,
            "current_member_id": current_user.id,
            "errors": errors,
        }
        return templates.TemplateResponse("community/messages/partials/thread.html", context, status_code=400)

    try:
        await message_service.create_message(payload.model_dump(), sender_id=current_user.id)
        await commit_transaction(db, "reply_message_form")
    except Exception as exc:
        await db.rollback()
        messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
        context = {
            "request": request,
            "messages": messages,
            "thread_id": thread_id,
            "other_party": recipient_id,
            "current_member_id": current_user.id,
            "errors": {"general": [str(exc)]},
        }
        return templates.TemplateResponse("community/messages/partials/thread.html", context, status_code=400)

    messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
    context = {
        "request": request,
        "messages": messages,
        "thread_id": thread_id,
        "other_party": recipient_id,
        "current_member_id": current_user.id,
    }
    return templates.TemplateResponse("community/messages/partials/thread.html", context)


__all__ = ["router"]
