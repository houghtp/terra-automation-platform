"""Recipient selection endpoints for messaging multiselect."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import get_db
from app.features.auth.models import User
from app.features.community.models import Member
from app.features.core.templates import templates

router = APIRouter()


def _parse_selected(form_or_query) -> List[str]:
    raw = form_or_query.get("recipient_ids") or ""
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return list(dict.fromkeys(items))


@router.get("/partials/recipient_picker")
async def recipient_picker(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    selected_ids = _parse_selected(request.query_params)
    users_stmt = select(User).where(User.id.in_(selected_ids)) if selected_ids else select(User).where(False)
    user_result = await db.execute(users_stmt)
    selected_users = list(user_result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_picker.html",
        {"request": request, "selected_ids": selected_ids, "selected_users": selected_users},
    )


@router.post("/partials/recipients")
async def recipient_options(
    request: Request,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    selected_ids = _parse_selected(form)
    search = (q or form.get("recipient_query") or "").strip().lower()
    stmt = select(User).join(Member, Member.user_id == User.id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    if selected_ids:
        stmt = stmt.where(~User.id.in_(selected_ids))
    stmt = stmt.order_by(func.lower(User.name)).limit(10)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return templates.TemplateResponse(
        "community/messages/partials/recipient_options.html",
        {"request": request, "users": users, "search_query": search, "selected_ids": selected_ids},
    )


@router.post("/partials/recipient_update")
async def recipient_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    action = form.get("action") or request.query_params.get("action")
    key = form.get("key") or request.query_params.get("key")
    if not action or not key:
        raise HTTPException(status_code=400, detail="Missing action or key")

    selected_ids = _parse_selected(form)
    if action == "select":
        if key not in selected_ids:
            selected_ids.append(key)
    elif action == "remove":
        selected_ids = [sid for sid in selected_ids if sid != key]

    users_stmt = select(User).where(User.id.in_(selected_ids)) if selected_ids else select(User).where(False)
    user_result = await db.execute(users_stmt)
    selected_users = list(user_result.scalars().all())

    return templates.TemplateResponse(
        "community/messages/partials/recipient_picker.html",
        {"request": request, "selected_ids": selected_ids, "selected_users": selected_users},
    )
