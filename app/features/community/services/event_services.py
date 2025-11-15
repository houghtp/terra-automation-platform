"""
Event services for community calendars.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    func,
    select,
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Event


class EventService(TenantScopedCRUDService[Event]):
    """Service handling community events."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Event)

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
            await self.handle_service_error("list_events", exc)

    async def create_event(self, payload: Dict[str, Optional[str]], user) -> Event:
        """Create a new event record."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for events.")

            audit_ctx = AuditContext.from_user(user)
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
            event.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            self.db.add(event)
            await self.db.flush()
            await self.db.refresh(event)
            return event
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Unable to create event") from exc
        except Exception as exc:
            await self.handle_service_error("create_event", exc)

    async def update_event(self, event_id: str, payload: Dict[str, Optional[str]], user) -> Optional[Event]:
        """Update an event."""
        event = await self.get_by_id(event_id)
        if not event:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(event, key):
                    setattr(event, key, value)

            audit_ctx = AuditContext.from_user(user)
            event.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            await self.db.flush()
            await self.db.refresh(event)
            return event
        except Exception as exc:
            await self.handle_service_error("update_event", exc, event_id)

    async def delete_event(self, event_id: str) -> bool:
        """Delete event."""
        return await self.delete_by_id(event_id)
