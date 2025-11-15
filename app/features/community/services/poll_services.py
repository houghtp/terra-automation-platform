"""
Poll services providing creation, voting, and analytics.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    func,
    select,
    selectinload,
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Poll, PollOption, PollVote


class PollService(TenantScopedCRUDService[Poll]):
    """Service for managing polls."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Poll)

    async def list_polls(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Poll], int]:
        """Return paginated polls."""
        try:
            stmt = select(Poll).options(selectinload(Poll.options))
            count_stmt = select(func.count(Poll.id))
            filters = []

            if self.tenant_id is not None:
                filters.append(Poll.tenant_id == self.tenant_id)

            if status:
                filters.append(func.lower(Poll.status) == status.lower())

            if filters:
                stmt = stmt.where(*filters)
                count_stmt = count_stmt.where(*filters)

            stmt = stmt.order_by(Poll.created_at.desc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            polls = list(result.scalars().all())
            total = (await self.db.execute(count_stmt)).scalar_one()
            return polls, int(total or 0)
        except Exception as exc:
            await self.handle_service_error("list_polls", exc)

    async def create_poll(self, payload: Dict[str, any], user) -> Poll:
        """Create poll with options."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for polls.")

            audit_ctx = AuditContext.from_user(user)
            poll = Poll(
                id=str(uuid4()),
                tenant_id=tenant_id,
                question=payload["question"],
                status="active",
                created_by_id=payload.get("created_by_id"),
                expires_at=payload.get("expires_at"),
            )
            poll.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            self.db.add(poll)
            await self.db.flush()

            poll_options = []
            for idx, option in enumerate(payload.get("options", [])):
                poll_option = PollOption(
                    id=str(uuid4()),
                    poll_id=poll.id,
                    text=option["text"],
                    order=option.get("order", idx),
                )
                poll_option.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
                poll_options.append(poll_option)

            if poll_options:
                self.db.add_all(poll_options)
                await self.db.flush()

            await self.db.refresh(poll, attribute_names=["options"])
            return poll
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Unable to create poll") from exc
        except Exception as exc:
            await self.handle_service_error("create_poll", exc)

    async def update_poll(self, poll_id: str, payload: Dict[str, any], user) -> Optional[Poll]:
        """Update poll metadata."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(poll, key):
                    setattr(poll, key, value)

            audit_ctx = AuditContext.from_user(user)
            poll.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            await self.db.flush()
            await self.db.refresh(poll)
            return poll
        except Exception as exc:
            await self.handle_service_error("update_poll", exc, poll_id)

    async def delete_poll(self, poll_id: str) -> bool:
        """Delete poll."""
        return await self.delete_by_id(poll_id)


class PollVoteService(TenantScopedCRUDService[PollVote]):
    """Service for managing votes."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, PollVote)

    async def cast_vote(self, poll_id: str, option_id: str, member_id: Optional[str]) -> PollVote:
        """Cast or replace a vote."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for votes.")

            # Delete previous vote for same member/poll
            if member_id:
                await self.db.execute(
                    PollVote.__table__.delete().where(
                        PollVote.poll_id == poll_id,
                        PollVote.member_id == member_id,
                        PollVote.tenant_id == tenant_id,
                    )
                )

            vote = PollVote(
                id=str(uuid4()),
                poll_id=poll_id,
                option_id=option_id,
                member_id=member_id,
                tenant_id=tenant_id,
            )
            self.db.add(vote)
            await self.db.flush()
            await self.db.refresh(vote)
            return vote
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Unable to cast vote") from exc
        except Exception as exc:
            await self.handle_service_error("cast_vote", exc, poll_id)

    async def vote_summary(self, poll_id: str) -> List[Dict[str, any]]:
        """Return aggregated vote counts for charting."""
        try:
            stmt = (
                select(
                    PollOption.id,
                    PollOption.text,
                    func.count(PollVote.id).label("votes"),
                )
                .join(PollVote, PollVote.option_id == PollOption.id, isouter=True)
                .where(PollOption.poll_id == poll_id)
                .group_by(PollOption.id, PollOption.text)
                .order_by(PollOption.order.asc())
            )
            result = await self.db.execute(stmt)
            rows = result.all()
            return [
                {"option_id": row.id, "label": row.text, "votes": int(row.votes or 0)}
                for row in rows
            ]
        except Exception as exc:
            await self.handle_service_error("vote_summary", exc, poll_id)
