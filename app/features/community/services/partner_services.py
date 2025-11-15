"""
Partner services implementing tenant-scoped CRUD operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    func,
    or_,
    select,
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Partner


class PartnerService(TenantScopedCRUDService[Partner]):
    """Service providing CRUD operations for community partners."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Partner)

    def _tenant_id_for_payload(self, payload: Dict[str, Any]) -> str:
        """Resolve tenant ID for create operations."""
        tenant_id = self.tenant_id or payload.get("tenant_id")
        if tenant_id in (None, "global"):
            raise ValueError("Tenant context is required for partner operations.")
        return tenant_id

    async def list_partners(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Partner], int]:
        """Return paginated partners with optional filtering."""
        try:
            filters = []
            if self.tenant_id is not None:
                filters.append(Partner.tenant_id == self.tenant_id)

            if search:
                like = f"%{search.lower()}%"
                filters.append(
                    or_(
                        func.lower(Partner.name).like(like),
                        func.lower(Partner.description).like(like),
                        func.lower(Partner.offer).like(like),
                    )
                )

            if category:
                filters.append(func.lower(Partner.category) == category.lower())

            stmt = select(Partner)
            if filters:
                stmt = stmt.where(*filters)

            stmt = stmt.order_by(func.lower(Partner.name)).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            partners = list(result.scalars().all())

            count_stmt = select(func.count(Partner.id))
            if filters:
                count_stmt = count_stmt.where(*filters)

            total = (await self.db.execute(count_stmt)).scalar_one()
            return partners, int(total or 0)
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("list_partners", exc)

    async def create_partner(self, payload: Dict[str, Any], user) -> Partner:
        """Create a partner directory entry."""
        try:
            audit_ctx = AuditContext.from_user(user)
            data = dict(payload)
            tenant_id = self._tenant_id_for_payload(data)
            data.pop("tenant_id", None)

            partner = Partner(tenant_id=tenant_id, **data)
            partner.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(partner)
            await self.db.flush()
            await self.db.refresh(partner)
            return partner
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Partner with this name already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("create_partner", exc)

    async def update_partner(self, partner_id: str, payload: Dict[str, Any], user) -> Optional[Partner]:
        """Update a partner entry."""
        partner = await self.get_by_id(partner_id)
        if not partner:
            return None

        try:
            for key, value in (payload or {}).items():
                setattr(partner, key, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                partner.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(partner)
            return partner
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Partner with this name already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("update_partner", exc, partner_id)

    async def update_partner_field(
        self,
        partner_id: str,
        field: str,
        value: Any,
        user=None,
    ) -> Optional[Partner]:
        """Update a single partner field (inline editing support)."""
        partner = await self.get_by_id(partner_id)
        if not partner:
            return None

        try:
            setattr(partner, field, value)

            if user:
                audit_ctx = AuditContext.from_user(user)
                partner.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(partner)
            return partner
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Partner with this name already exists for tenant.") from exc
        except Exception as exc:  # pragma: no cover - logged upstream
            await self.handle_service_error("update_partner_field", exc, partner_id)

    async def delete_partner(self, partner_id: str) -> bool:
        """Delete a partner record."""
        return await self.delete_by_id(partner_id)
