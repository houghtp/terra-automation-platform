"""
Member services implementing tenant-scoped CRUD operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    func,
    or_,
    select,
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Member


class MemberService(TenantScopedCRUDService[Member]):
    """Service providing CRUD operations for community members."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Member)

    def _tenant_id_for_payload(self, payload: Dict[str, Any]) -> str:
        """Resolve tenant ID for create operations."""
        tenant_id = self.tenant_id or payload.get("tenant_id")
        if tenant_id in (None, "global"):
            raise ValueError("Tenant context is required for member operations.")
        return tenant_id

    async def list_members(
        self,
        search: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        specialties: Optional[Sequence[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Member], int]:
        """Return paginated members with optional filtering."""
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(Member.tenant_id == self.tenant_id)

            if search:
                like = f"%{search.lower()}%"
                filters.append(
                    or_(
                        func.lower(Member.name).like(like),
                        func.lower(Member.email).like(like),
                        func.lower(Member.firm).like(like),
                    )
                )

            if tags:
                filters.append(Member.tags.contains(list(tags)))

            if specialties:
                filters.append(Member.specialties.contains(list(specialties)))

            stmt = select(Member)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(func.lower(Member.name)).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

            count_stmt = select(func.count(Member.id))
            if filters:
                count_stmt = count_stmt.where(*filters)

            total = (await self.db.execute(count_stmt)).scalar_one()
            return items, int(total or 0)
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("list_members", exc)

    async def create_member(self, payload: Dict[str, Any], user) -> Member:
        """Create a member record from validated payload."""
        try:
            audit_ctx = AuditContext.from_user(user)
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
            data.pop("tenant_id", None)

            member = Member(tenant_id=tenant_id, **data)
            member.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(member)
            await self.db.flush()
            await self.db.refresh(member)
            return member
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Member with this email already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("create_member", exc)

    async def update_member(self, member_id: str, payload: Dict[str, Any], user) -> Optional[Member]:
        """Update an existing member."""
        member = await self.get_by_id(member_id)
        if not member:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(member, key, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                member.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(member)
            return member
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Member with this email already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("update_member", exc, member_id)

    async def update_member_field(
        self,
        member_id: str,
        field: str,
        value: Any,
        user=None,
    ) -> Optional[Member]:
        """Update a single member field (used by Tabulator inline editing)."""
        member = await self.get_by_id(member_id)
        if not member:
            return None

        try:
            setattr(member, field, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                member.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(member)
            return member
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Member with this email already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("update_member_field", exc, member_id)

    async def delete_member(self, member_id: str) -> bool:
        """Delete a member record."""
        return await self.delete_by_id(member_id)
