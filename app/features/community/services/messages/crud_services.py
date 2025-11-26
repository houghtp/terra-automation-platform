"""CRUD services for direct messages."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

from app.features.core.sqlalchemy_imports import AsyncSession, and_, func, or_, select
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Message, Member
from app.features.auth.models import User

CROSS_TENANT_ID = "community"


class MessageCrudService(BaseService[Message]):
    """Service managing direct messages."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        return await super().get_by_id(Message, message_id)

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

            if self.tenant_id not in (None, "global"):
                stmt = stmt.where(Message.tenant_id == self.tenant_id)
                count_stmt = count_stmt.where(Message.tenant_id == self.tenant_id)

            stmt = stmt.order_by(Message.created_at.desc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())
            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_conversations", exc, member_id=member_id)

    def _compute_thread_id(self, sender_id: str, recipient_id: str, provided: Optional[str] = None) -> str:
        """Deterministically compute a thread id when not supplied."""
        if provided:
            return provided
        return ":".join(sorted([sender_id, recipient_id]))

    async def list_conversation_summaries(
        self,
        member_id: str,
        limit: int = 50,
    ) -> List[Dict[str, str]]:
        """
        Return latest message per thread for the member (rail view).
        Favors simplicity by picking the newest message for each thread in Python.
        """
        try:
            stmt = select(Message).where(
                or_(Message.sender_id == member_id, Message.recipient_id == member_id)
            )
            if self.tenant_id not in (None, "global"):
                stmt = stmt.where(Message.tenant_id == self.tenant_id)

            stmt = stmt.order_by(Message.created_at.desc()).limit(limit * 4)
            result = await self.db.execute(stmt)
            messages = list(result.scalars().all())

            summaries: Dict[str, Dict[str, str]] = {}
            for msg in messages:
                thread = msg.thread_id or self._compute_thread_id(msg.sender_id, msg.recipient_id)
                if thread in summaries:
                    continue
                other_party = msg.recipient_id if msg.sender_id == member_id else msg.sender_id
                summaries[thread] = {
                    "thread_id": thread,
                    "last_message": msg.content,
                    "last_sender_id": msg.sender_id,
                    "other_party_id": other_party,
                    "created_at": msg.created_at,
                    "is_unread": (msg.recipient_id == member_id) and (not msg.is_read),
                }
                if len(summaries) >= limit:
                    break

            # Fetch user display info for other parties
            other_party_ids = [s["other_party_id"] for s in summaries.values() if s.get("other_party_id")]
            user_map: Dict[str, Dict[str, str]] = {}
            if other_party_ids:
                user_stmt = select(User).where(User.id.in_(other_party_ids))
            if self.tenant_id not in (None, "global"):
                user_stmt = user_stmt.where(User.tenant_id == self.tenant_id)
                user_result = await self.db.execute(user_stmt)
                for user in user_result.scalars().all():
                    user_map[user.id] = {"name": user.name, "email": user.email}

            enriched = []
            for s in summaries.values():
                details = user_map.get(s.get("other_party_id"), {})
                s["other_party_name"] = details.get("name")
                s["other_party_email"] = details.get("email")
                enriched.append(s)

            return enriched
        except Exception as exc:
            await self.handle_error("list_conversation_summaries", exc, member_id=member_id)

    async def fetch_thread(
        self,
        thread_id: Optional[str],
        member_id: str,
        limit: int = 100,
    ) -> List[Message]:
        """Return chronological messages in a thread."""
        try:
            stmt = select(Message)
            computed_thread_id = thread_id
            if not computed_thread_id:
                # Fallback to messages sent by the member with no thread id (legacy)
                stmt = stmt.where(and_(Message.sender_id == member_id, Message.thread_id.is_(None)))
            else:
                if ":" in computed_thread_id:
                    try:
                        a, b = computed_thread_id.split(":", 1)
                        stmt = stmt.where(
                            or_(
                                Message.thread_id == computed_thread_id,
                                and_(
                                    Message.thread_id.is_(None),
                                    or_(
                                        and_(Message.sender_id == a, Message.recipient_id == b),
                                        and_(Message.sender_id == b, Message.recipient_id == a),
                                    ),
                                ),
                            )
                        )
                    except ValueError:
                        stmt = stmt.where(Message.thread_id == computed_thread_id)
                else:
                    stmt = stmt.where(Message.thread_id == computed_thread_id)

            # Only return messages where the requester is a participant
            stmt = stmt.where(or_(Message.sender_id == member_id, Message.recipient_id == member_id))

            if self.tenant_id not in (None, "global"):
                stmt = stmt.where(Message.tenant_id == self.tenant_id)

            stmt = stmt.order_by(Message.created_at.asc()).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_error("fetch_thread", exc, thread_id=thread_id)

    async def create_message(self, payload: Dict[str, str], sender_id: str) -> Message:
        """Persist a new message."""
        try:
            tenant_id = CROSS_TENANT_ID

            recipient_id = payload["recipient_id"]
            thread_id = self._compute_thread_id(sender_id, recipient_id, payload.get("thread_id"))

            message = Message(
                id=str(uuid4()),
                tenant_id=tenant_id,
                thread_id=thread_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=payload["content"],
                is_read=False,
                created_at=datetime.utcnow(),
            )

            self.db.add(message)
            await self.db.flush()
            await self.db.refresh(message)
            return message
        except Exception as exc:
            await self.handle_error("create_message", exc)

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
            await self.handle_error("mark_read", exc)

    async def delete_message(self, message_id: str) -> bool:
        message = await self.get_by_id(message_id)
        if not message:
            return False
        await self.db.delete(message)
        await self.db.flush()
        return True
