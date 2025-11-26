"""CRUD services for community events."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from app.features.core.sqlalchemy_imports import AsyncSession, func, select
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Event


class EventCrudService(BaseService[Event]):
    """Service handling community events."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        return await super().get_by_id(Event, event_id)

    async def list_events(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Event], int]:
        """Return paginated events with optional category filter."""
        try:
            stmt = select(Event)
            count_stmt = select(func.count(Event.id))
            filters = []

            if self.tenant_id is not None:
                filters.append(Event.tenant_id == self.tenant_id)

            if category:
                filters.append(func.lower(Event.category) == category.lower())

            if filters:
                stmt = stmt.where(*filters)
                count_stmt = count_stmt.where(*filters)

            stmt = stmt.order_by(Event.start_date.asc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            events = list(result.scalars().all())

            total = (await self.db.execute(count_stmt)).scalar_one()
            return events, int(total or 0)
        except Exception as exc:
            await self.handle_error("list_events", exc)

    async def count_all(self) -> int:
        """Count events for the current tenant (or globally for admins)."""
        stmt = select(func.count(Event.id))
        if self.tenant_id is not None:
            stmt = stmt.where(Event.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def create_event(self, payload: Dict[str, Optional[str]], user) -> Event:
        """Create a new event record."""
        try:
            tenant_id = self.tenant_id or "global"

            audit_ctx = AuditContext.from_user(user) if user else None
            event = Event(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title=payload["title"],
                description=payload.get("description"),
                start_date=payload["start_date"],
                end_date=payload.get("end_date"),
                location=payload.get("location"),
                url=payload.get("url"),
                category=payload.get("category"),
            )
            if audit_ctx:
                event.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            self.db.add(event)
            await self.db.flush()
            await self.db.refresh(event)
            return event
        except Exception as exc:
            await self.handle_error("create_event", exc)

    async def update_event(self, event_id: str, payload: Dict[str, Optional[str]], user) -> Optional[Event]:
        """Update an event."""
        event = await self.get_by_id(event_id)
        if not event:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(event, key):
                    setattr(event, key, value)

            audit_ctx = AuditContext.from_user(user) if user else None
            if audit_ctx:
                event.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            await self.db.flush()
            await self.db.refresh(event)
            return event
        except Exception as exc:
            await self.handle_error("update_event", exc, event_id=event_id)

    async def delete_event(self, event_id: str) -> bool:
        """Delete event."""
        event = await self.get_by_id(event_id)
        if not event:
            return False
        await self.db.delete(event)
        await self.db.flush()
        return True
