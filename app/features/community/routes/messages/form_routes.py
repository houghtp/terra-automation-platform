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
from ...schemas import MessageCreate, ThreadCreate
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
    db: AsyncSession = Depends(get_db),
):
    user_options = (await db.execute(select(User).order_by(User.name))).scalars().all()
    return templates.TemplateResponse(
        "community/messages/partials/new_thread.html",
        {"request": request, "current_member_id": current_user.id, "user_options": user_options},
    )


@router.post("/partials/new", response_class=HTMLResponse)
async def create_new_thread(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    message_service: MessageCrudService = Depends(get_message_service),
):
    form = await request.form()
    recipient_ids = form.getlist("recipient_ids")
    content = form.get("content")
    try:
        payload = ThreadCreate(recipient_ids=recipient_ids, content=content)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        user_options = (await db.execute(select(User).order_by(User.name))).scalars().all()
        return templates.TemplateResponse(
            "community/messages/partials/new_thread.html",
            {
                "request": request,
                "errors": errors,
                "current_member_id": current_user.id,
                "recipient_ids": recipient_ids,
                "content": content,
                "user_options": user_options,
            },
            status_code=400,
        )

    try:
        thread = await message_service.create_thread(payload.recipient_ids, created_by=current_user.id)
        msg = await message_service.create_message({"thread_id": thread.id, "content": payload.content}, sender_id=current_user.id)
        await commit_transaction(db, "create_message_form")
        messages = await message_service.fetch_thread(thread_id=thread.id, member_id=current_user.id)
        participant_ids = await message_service.participants_for_thread(thread.id)
        names = await message_service._user_map(participant_ids)
        participants_label = ", ".join([names.get(pid, {}).get("name") or pid for pid in participant_ids])
        return templates.TemplateResponse(
            "community/messages/partials/thread.html",
            {
                "request": request,
                "messages": messages,
                "thread_id": thread.id,
                "participants_label": participants_label,
                "participants_secondary": None,
                "current_member_id": current_user.id,
            },
        )
    except Exception as exc:
        await db.rollback()
        user_options = (await db.execute(select(User).order_by(User.name))).scalars().all()
        errors = {"general": [str(exc)]}
        return templates.TemplateResponse(
            "community/messages/partials/new_thread.html",
            {
                "request": request,
                "errors": errors,
                "current_member_id": current_user.id,
                "recipient_ids": recipient_ids,
                "content": content,
                "user_options": user_options,
            },
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
    participant_ids = await message_service.participants_for_thread(thread_id)
    names = await message_service._user_map(participant_ids)
    participants_label = ", ".join([names.get(pid, {}).get("name") or pid for pid in participant_ids])
    participants_secondary = ", ".join([names.get(pid, {}).get("email") or "" for pid in participant_ids if names.get(pid, {}).get("email")])
    context = {
        "request": request,
        "messages": messages,
        "thread_id": thread_id,
        "participants_label": participants_label,
        "participants_secondary": participants_secondary,
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
    content = form.get("content")

    try:
        payload = MessageCreate(content=content, thread_id=thread_id)
    except ValidationError as exc:
        errors = _validation_errors_to_dict(exc)
        messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
        context = {
            "request": request,
            "messages": messages,
            "thread_id": thread_id,
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
            "current_member_id": current_user.id,
            "errors": {"general": [str(exc)]},
        }
        return templates.TemplateResponse("community/messages/partials/thread.html", context, status_code=400)

    messages = await message_service.fetch_thread(thread_id=thread_id, member_id=current_user.id)
    participant_ids = await message_service.participants_for_thread(thread_id)
    names = await message_service._user_map(participant_ids)
    participants_label = ", ".join([names.get(pid, {}).get("name") or pid for pid in participant_ids])
    participants_secondary = ", ".join([names.get(pid, {}).get("email") or "" for pid in participant_ids if names.get(pid, {}).get("email")])
    context = {
        "request": request,
        "messages": messages,
        "thread_id": thread_id,
        "current_member_id": current_user.id,
        "participants_label": participants_label,
        "participants_secondary": participants_secondary,
    }
    return templates.TemplateResponse("community/messages/partials/thread.html", context)


__all__ = ["router"]
