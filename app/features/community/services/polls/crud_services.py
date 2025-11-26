"""CRUD services for polls and votes."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.features.core.sqlalchemy_imports import AsyncSession, func, select, selectinload
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Poll, PollOption, PollVote


class PollCrudService(BaseService[Poll]):
    """Service for managing polls."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, poll_id: str) -> Optional[Poll]:
        return await super().get_by_id(Poll, poll_id)

    async def get_by_id_with_options(self, poll_id: str) -> Optional[Poll]:
        """Fetch poll with options eagerly loaded."""
        try:
            stmt = (
                select(Poll)
                .options(selectinload(Poll.options))
                .where(Poll.id == poll_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:
            await self.handle_error("get_by_id_with_options", exc, poll_id=poll_id)

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
            await self.handle_error("list_polls", exc)

    async def create_poll(self, payload: Dict[str, any], user) -> Poll:
        """Create poll with options."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for polls.")

            audit_ctx = AuditContext.from_user(user) if user else None
            poll = Poll(
                id=str(uuid4()),
                tenant_id=tenant_id,
                question=payload["question"],
                status="active",
                created_by_id=payload.get("created_by_id"),
                expires_at=payload.get("expires_at"),
            )
            if audit_ctx:
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
                if audit_ctx:
                    poll_option.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
                poll_options.append(poll_option)

            if poll_options:
                self.db.add_all(poll_options)
                await self.db.flush()

            await self.db.refresh(poll, attribute_names=["options"])
            return poll
        except Exception as exc:
            await self.handle_error("create_poll", exc)

    async def update_poll(self, poll_id: str, payload: Dict[str, any], user) -> Optional[Poll]:
        """Update poll metadata."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(poll, key):
                    setattr(poll, key, value)

            audit_ctx = AuditContext.from_user(user) if user else None
            if audit_ctx:
                poll.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            await self.db.flush()
            await self.db.refresh(poll)
            return poll
        except Exception as exc:
            await self.handle_error("update_poll", exc, poll_id=poll_id)

    async def update_poll_with_options(
        self,
        poll_id: str,
        payload: Dict[str, any],
        options: List[Dict[str, any]],
        user,
    ) -> Optional[Poll]:
        """Update poll and replace options."""
        poll = await self.get_by_id_with_options(poll_id)
        if not poll:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(poll, key):
                    setattr(poll, key, value)

            # Replace options
            await self.db.execute(PollOption.__table__.delete().where(PollOption.poll_id == poll.id))
            audit_ctx = AuditContext.from_user(user) if user else None
            option_rows = []
            for idx, opt in enumerate(options):
                option = PollOption(
                    id=str(uuid4()),
                    poll_id=poll.id,
                    text=opt["text"],
                    order=opt.get("order", idx),
                )
                if audit_ctx:
                    option.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
                option_rows.append(option)
            if option_rows:
                self.db.add_all(option_rows)

            audit_ctx = AuditContext.from_user(user) if user else None
            if audit_ctx:
                poll.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(poll)
            return poll
        except Exception as exc:
            await self.handle_error("update_poll_with_options", exc, poll_id=poll_id)

    async def delete_poll(self, poll_id: str) -> bool:
        """Delete poll."""
        poll = await self.get_by_id(poll_id)
        if not poll:
            return False
        await self.db.delete(poll)
        await self.db.flush()
        return True


class PollVoteCrudService(BaseService[PollVote]):
    """Service for managing votes."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, vote_id: str) -> Optional[PollVote]:
        return await super().get_by_id(PollVote, vote_id)

    async def cast_vote(self, poll_id: str, option_id: str, member_id: Optional[str]) -> PollVote:
        """Cast or replace a vote."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for votes.")

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
        except Exception as exc:
            await self.handle_error("cast_vote", exc, poll_id=poll_id)

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
            await self.handle_error("vote_summary", exc, poll_id=poll_id)
