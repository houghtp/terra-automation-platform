"""
Messaging services for direct member communication.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    and_,
    func,
    or_,
    select,
)
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Message


class MessageService(TenantScopedCRUDService[Message]):
    """Service managing direct messages."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Message)

    async def list_conversations(
        self,
        member_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Message], int]:
        """Fetch messages involving the member."""
        try:
            stmt = select(Message).where(
                or_(
                    Message.sender_id == member_id,
                    Message.recipient_id == member_id,
                )
            )
            count_stmt = select(func.count(Message.id)).where(
                or_(
                    Message.sender_id == member_id,
                    Message.recipient_id == member_id,
                )
            )

            if self.tenant_id is not None:
                stmt = stmt.where(Message.tenant_id == self.tenant_id)
                count_stmt = count_stmt.where(Message.tenant_id == self.tenant_id)

            stmt = stmt.order_by(Message.created_at.desc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_service_error("list_conversations", exc, item_id=member_id)

    async def fetch_thread(
        self,
        thread_id: Optional[str],
        member_id: str,
        limit: int = 100,
    ) -> List[Message]:
        """Return chronological messages in a thread."""
        try:
            stmt = select(Message)
            if thread_id:
                stmt = stmt.where(Message.thread_id == thread_id)
            else:
                stmt = stmt.where(
                    and_(
                        Message.sender_id == member_id,
                        Message.thread_id.is_(None)
                    )
                )

            if self.tenant_id is not None:
                stmt = stmt.where(Message.tenant_id == self.tenant_id)

            stmt = stmt.order_by(Message.created_at.asc()).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_service_error("fetch_thread", exc, item_id=thread_id)

    async def send_message(self, payload: Dict[str, str], sender_id: str) -> Message:
        """Persist a new message."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for messaging.")

            message = Message(
                id=str(uuid4()),
                tenant_id=tenant_id,
                thread_id=payload.get("thread_id"),
                sender_id=sender_id,
                recipient_id=payload["recipient_id"],
                content=payload["content"],
                is_read=False,
                created_at=datetime.utcnow(),
            )

            self.db.add(message)
            await self.db.flush()
            await self.db.refresh(message)
            return message
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Unable to save message.") from exc
        except Exception as exc:
            await self.handle_service_error("send_message", exc)

    async def mark_read(self, message_ids: List[str]) -> None:
        """Mark selected messages as read."""
        if not message_ids:
            return
        try:
            stmt = (
                select(Message)
                .where(Message.id.in_(message_ids))
            )
            if self.tenant_id is not None:
                stmt = stmt.where(Message.tenant_id == self.tenant_id)
            result = await self.db.execute(stmt)
            for message in result.scalars().all():
                message.is_read = True
            await self.db.flush()
        except Exception as exc:
            await self.handle_service_error("mark_read", exc)
