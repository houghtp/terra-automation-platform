"""CRUD services for direct messages."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

from app.features.core.sqlalchemy_imports import AsyncSession, and_, func, or_, select
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Message, Member, Thread, ThreadParticipant
from app.features.auth.models import User

CROSS_TENANT_ID = "community"


class MessageCrudService(BaseService[Message]):
    """Service managing direct messages."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        return await super().get_by_id(Message, message_id)

    async def _threads_for_user(self, user_id: str) -> List[str]:
        stmt = select(ThreadParticipant.thread_id).where(ThreadParticipant.user_id == user_id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def create_thread(self, participant_ids: List[str], created_by: str) -> Thread:
        participant_set = set(participant_ids or [])
        participant_set.add(created_by)
        thread = Thread(id=str(uuid4()), tenant_id=CROSS_TENANT_ID, created_by=created_by)
        self.db.add(thread)
        await self.db.flush()
        participants = [
            ThreadParticipant(
                id=str(uuid4()),
                thread_id=thread.id,
                user_id=pid,
            )
            for pid in participant_set
        ]
        self.db.add_all(participants)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

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
        """Return latest message per thread for the member (rail view)."""
        try:
            thread_ids = await self._threads_for_user(member_id)
            if not thread_ids:
                return []
            msg_stmt = (
                select(Message)
                .where(Message.thread_id.in_(thread_ids))
                .order_by(Message.thread_id, Message.created_at.desc())
            )
            result = await self.db.execute(msg_stmt)
            messages = list(result.scalars().all())

            latest_by_thread: Dict[str, Message] = {}
            for msg in messages:
                if msg.thread_id not in latest_by_thread:
                    latest_by_thread[msg.thread_id] = msg
            thread_summaries = []
            for tid, msg in latest_by_thread.items():
                participant_ids = await self.participants_for_thread(tid)
                others = [p for p in participant_ids if p != member_id]
                names = await self._user_map(others + [msg.sender_id])
                thread_summaries.append(
                    {
                        "thread_id": tid,
                        "last_message": msg.content,
                        "last_sender_id": msg.sender_id,
                        "participants": [names.get(pid, {}).get("name") or pid for pid in participant_ids],
                        "created_at": msg.created_at,
                    }
                )
            thread_summaries.sort(key=lambda x: x["created_at"] or datetime.min, reverse=True)
            return thread_summaries[:limit]
        except Exception as exc:
            await self.handle_error("list_conversation_summaries", exc, member_id=member_id)

    async def _user_map(self, user_ids: List[str]) -> Dict[str, Dict[str, str]]:
        if not user_ids:
            return {}
        stmt = select(User).where(User.id.in_(user_ids))
        result = await self.db.execute(stmt)
        return {u.id: {"name": u.name, "email": u.email} for u in result.scalars().all()}

    async def participants_for_thread(self, thread_id: str) -> List[str]:
        stmt = select(ThreadParticipant.user_id).where(ThreadParticipant.thread_id == thread_id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def fetch_thread(
        self,
        thread_id: Optional[str],
        member_id: str,
        limit: int = 100,
    ) -> List[Message]:
        """Return chronological messages in a thread."""
        try:
            # Ensure membership
            participant_threads = await self._threads_for_user(member_id)
            if thread_id not in participant_threads:
                return []

            stmt = (
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_error("fetch_thread", exc, thread_id=thread_id)

    async def create_message(self, payload: Dict[str, str], sender_id: str) -> Message:
        """Persist a new message."""
        try:
            tenant_id = CROSS_TENANT_ID
            thread_id = payload.get("thread_id")
            if not thread_id:
                raise ValueError("thread_id is required for messaging")

            # Validate membership
            participant_threads = await self._threads_for_user(sender_id)
            if thread_id not in participant_threads:
                raise ValueError("Sender is not a participant of this thread")

            message = Message(
                id=str(uuid4()),
                tenant_id=tenant_id,
                thread_id=thread_id,
                sender_id=sender_id,
                recipient_id=None,
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
