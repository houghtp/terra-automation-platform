"""Recipient selection endpoints for messaging multiselect."""

from typing import Optional, List
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import get_db
from app.features.auth.models import User
from app.features.community.models import Member
from app.features.core.templates import templates
from sqlalchemy.orm import selectinload

router = APIRouter()


def _parse_selected(query_params) -> List[str]:
    raw = query_params.get("recipient_ids") or ""
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return list(dict.fromkeys(items))


@router.get("/partials/recipient_picker")
async def recipient_picker(
    request: Request,
    db: AsyncSession = Depends(get_db),
    recipient_ids: Optional[str] = None,
):
    selected_ids = _parse_selected(request.query_params)
    users_stmt = select(User).where(User.id.in_(selected_ids)) if selected_ids else select(User).where(False)
    user_result = await db.execute(users_stmt)
    selected_users = list(user_result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_picker.html",
        {"request": request, "selected_ids": selected_ids, "selected_users": selected_users},
    )


@router.get("/partials/recipient_add")
async def recipient_add(
    request: Request,
    select_id: str,
    select_label: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    selected_ids = _parse_selected(request.query_params)
    if select_id not in selected_ids:
        selected_ids.append(select_id)
    users_stmt = select(User).where(User.id.in_(selected_ids)) if selected_ids else select(User).where(False)
    user_result = await db.execute(users_stmt)
    selected_users = list(user_result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_update.html",
        {"request": request, "selected_ids": selected_ids, "selected_users": selected_users},
    )


@router.get("/partials/recipient_remove")
async def recipient_remove(
    request: Request,
    remove_id: str,
    db: AsyncSession = Depends(get_db),
):
    selected_ids = _parse_selected(request.query_params)
    selected_ids = [sid for sid in selected_ids if sid != remove_id]
    users_stmt = select(User).where(User.id.in_(selected_ids)) if selected_ids else select(User).where(False)
    user_result = await db.execute(users_stmt)
    selected_users = list(user_result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_update.html",
        {"request": request, "selected_ids": selected_ids, "selected_users": selected_users},
    )
