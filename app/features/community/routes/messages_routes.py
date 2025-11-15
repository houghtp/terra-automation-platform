"""API routes for direct messaging."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User

from ..dependencies import get_message_service
from ..services import MessageService
from ..schemas import MessageCreate, MessageResponse

router = APIRouter(prefix="/messages", tags=["community-messages"])


@router.get("/api")
async def list_messages_api(
    member_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: MessageService = Depends(get_message_service),
):
    """Return messages where member is sender or recipient."""
    messages, total = await service.list_conversations(member_id=member_id, limit=limit, offset=offset)
    return {
        "data": [message.to_dict() for message in messages],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/thread")
async def fetch_thread_api(
    member_id: str,
    thread_id: Optional[str] = Query(default=None),
    service: MessageService = Depends(get_message_service),
):
    """Return conversation thread messages."""
    messages = await service.fetch_thread(thread_id=thread_id, member_id=member_id)
    return {
        "data": [message.to_dict() for message in messages],
    }


@router.post("/api", response_model=MessageResponse, status_code=201)
async def send_message_api(
    payload: MessageCreate,
    service: MessageService = Depends(get_message_service),
    current_user: User = Depends(get_current_user),
):
    message = await service.send_message(payload.model_dump(), sender_id=current_user.id)
    if not message:
        raise HTTPException(status_code=500, detail="Failed to send message")
    return MessageResponse.model_validate(message, from_attributes=True)


@router.post("/api/mark-read")
async def mark_read_api(
    message_ids: list[str] = Body(default=[]),
    service: MessageService = Depends(get_message_service),
):
    await service.mark_read(message_ids)
    return {"status": "ok"}
