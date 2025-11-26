# Gold Standard Secrets Form Services
"""
Secrets form services - form data processing and validation.
"""
from typing import List, Dict, Any
from sqlalchemy import select
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from app.features.core.route_imports import get_logger

logger = get_logger(__name__)


class SecretsFormService(BaseService):
    """Service for secrets form operations."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(db, tenant_id)

    async def get_available_tenants_for_secrets_forms(self) -> List[Dict[str, Any]]:
        """
        Get active tenants for secrets form dropdowns (global admin only).
        Uses enhanced BaseService query patterns.

        Returns:
            List of tenant dictionaries with id and name
        """
        try:
            from app.features.administration.tenants.db_models import Tenant

            stmt = select(
                Tenant.id,
                Tenant.name
            ).where(
                Tenant.status == 'active'
            ).order_by(Tenant.name)

            result = await self.db.execute(stmt)
            tenants = result.fetchall()

            # Include "global" scope for platform-level secrets (client ids, shared creds).
            tenant_list = [{"id": "global", "name": "Global"}]
            tenant_list.extend(
                {"id": str(tenant.id), "name": tenant.name}
                for tenant in tenants
            )

            logger.info(f"Retrieved {len(tenant_list)} active tenants for secrets forms")
            return tenant_list

        except Exception as e:
            logger.exception("Failed to get available tenants for secrets forms")
            raise ValueError(f"Failed to get tenant list: {str(e)}")
