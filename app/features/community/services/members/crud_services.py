"""CRUD services for community members (aligned with users slice patterns)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.features.core.sqlalchemy_imports import AsyncSession, func, or_, select
from sqlalchemy.orm import selectinload
from app.features.core.audit_mixin import AuditContext
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Member, Partner


class MemberCrudService(BaseService[Member]):
    """Service providing CRUD operations for community members."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_by_id(self, member_id: str) -> Optional[Member]:
        """Fetch a member by ID scoped to tenant."""
        return await super().get_by_id(Member, member_id)

    def _resolve_tenant_id(self, payload: Dict[str, Any]) -> str:
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

            stmt = select(Member).options(selectinload(Member.partner))
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
        except Exception as exc:
            await self.handle_error("list_members", exc)

    async def count_all(self) -> int:
        """Count members for the current tenant (or globally for admins)."""
        stmt = select(func.count(Member.id))
        if self.tenant_id is not None:
            stmt = stmt.where(Member.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def create_member(self, payload: Dict[str, Any], user) -> Member:
        """Create a member record from validated payload."""
        try:
            audit_ctx = AuditContext.from_user(user) if user else None
            data = dict(payload)
            tenant_id = self._resolve_tenant_id(data)
            data.pop("tenant_id", None)

            partner_id = data.get("partner_id")
            if partner_id:
                await self._validate_partner(partner_id, tenant_id)

            if await self._email_exists(data.get("email"), tenant_id):
                raise ValueError("Member with this email already exists for tenant.")

            member = Member(tenant_id=tenant_id, **data)
            if audit_ctx:
                member.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(member)
            await self.db.flush()
            await self.db.refresh(member)
            return member
        except Exception as exc:
            await self.handle_error("create_member", exc)

    async def update_member(self, member_id: str, payload: Dict[str, Any], user) -> Optional[Member]:
        """Update an existing member."""
        member = await self.get_by_id(member_id)
        if not member:
            return None

        try:
            partner_id = (payload or {}).get("partner_id")
            if "partner_id" in (payload or {}):
                if partner_id:
                    await self._validate_partner(partner_id, member.tenant_id)
                member.partner_id = partner_id

            new_email = (payload or {}).get("email")
            if new_email and new_email != member.email:
                if await self._email_exists(new_email, member.tenant_id, exclude_id=member_id):
                    raise ValueError("Member with this email already exists for tenant.")

            for key, value in (payload or {}).items():
                if value is None:
                    # partner handled explicitly above to allow clearing
                    continue
                if key == "partner_id":
                    continue
                setattr(member, key, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                member.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(member)
            return member
        except Exception as exc:
            await self.handle_error("update_member", exc, member_id=member_id)

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
            if field == "email" and value and value != member.email:
                if await self._email_exists(value, member.tenant_id, exclude_id=member_id):
                    raise ValueError("Member with this email already exists for tenant.")

            if field == "partner_id" and value:
                await self._validate_partner(value, member.tenant_id)

            setattr(member, field, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                member.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(member)
            return member
        except Exception as exc:
            await self.handle_error("update_member_field", exc, member_id=member_id, field=field)

    async def delete_member(self, member_id: str) -> bool:
        """Delete member by ID."""
        member = await self.get_by_id(member_id)
        if not member:
            return False
        await self.db.delete(member)
        await self.db.flush()
        return True

    async def _email_exists(self, email: Optional[str], tenant_id: str, exclude_id: Optional[str] = None) -> bool:
        if not email:
            return False
        stmt = select(Member).where(Member.email == email, Member.tenant_id == tenant_id)
        if exclude_id:
            stmt = stmt.where(Member.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _validate_partner(self, partner_id: str, tenant_id: str) -> None:
        """Ensure the partner exists for the tenant before linking."""
        stmt = select(Partner).where(Partner.id == partner_id, Partner.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        partner = result.scalar_one_or_none()
        if not partner:
            raise ValueError("Partner not found for this tenant.")
