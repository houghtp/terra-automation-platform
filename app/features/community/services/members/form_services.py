"""Form services for members (options, validations)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.features.core.sqlalchemy_imports import AsyncSession, select
from app.features.core.enhanced_base_service import BaseService
from app.features.community.models import Member, Partner


class MemberFormService(BaseService[Member]):
    """Provide form dropdowns and lightweight validations for members."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def get_partner_options(self) -> List[Dict[str, Any]]:
        """Return partner options for the current tenant."""
        try:
            stmt = select(Partner).order_by(Partner.name.asc())
            if self.tenant_id is not None:
                stmt = stmt.where(Partner.tenant_id == self.tenant_id)
            result = await self.db.execute(stmt)
            partners = result.scalars().all()
            return [{"id": p.id, "name": p.name} for p in partners]
        except Exception as exc:
            await self.handle_error("get_partner_options", exc)
