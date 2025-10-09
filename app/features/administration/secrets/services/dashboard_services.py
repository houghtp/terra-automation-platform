"""
Secrets dashboard services for analytics and statistics.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.secrets.models import TenantSecret, SecretType

logger = get_logger(__name__)


class SecretsDashboardService(BaseService[TenantSecret]):
    """
    Dashboard and analytics services for secrets management.

    Provides statistics, trends, and summary data for secrets.
    All operations are automatically tenant-scoped via BaseService.
    """

    async def get_secrets_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tenant secrets.

        Returns:
            Dict[str, Any]: Statistics about secrets
        """
        try:
            # Total secrets
            total_query = self.create_base_query(TenantSecret).with_only_columns(func.count(TenantSecret.id))
            total_result = await self.db.execute(total_query)
            total_secrets = total_result.scalar() or 0

            # Active secrets
            active_query = self.create_base_query(TenantSecret).with_only_columns(func.count(TenantSecret.id)).where(
                TenantSecret.is_active == True
            )
            active_result = await self.db.execute(active_query)
            active_secrets = active_result.scalar() or 0

            # Expiring soon (30 days)
            expiring_secrets = await self.get_expiring_secrets(30)

            # By type
            type_query = self.create_base_query(TenantSecret).with_only_columns(
                TenantSecret.secret_type,
                func.count(TenantSecret.id)
            ).where(
                TenantSecret.is_active == True
            ).group_by(TenantSecret.secret_type)

            type_result = await self.db.execute(type_query)
            types_breakdown = dict(type_result.fetchall())

            return {
                "total_secrets": total_secrets,
                "active_secrets": active_secrets,
                "inactive_secrets": total_secrets - active_secrets,
                "expiring_soon": len(expiring_secrets),
                "by_type": types_breakdown,
                "expiring_secrets": [secret.model_dump() for secret in expiring_secrets]
            }

        except Exception as e:
            logger.exception(f"Failed to get secrets stats for tenant {self.tenant_id}")
            raise

    async def get_expiring_secrets(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get secrets that will expire within the specified number of days.

        Args:
            days_ahead: Number of days to look ahead for expiring secrets

        Returns:
            List of expiring secrets
        """
        try:
            # Use timezone-aware datetime then convert to naive for database compatibility
            # Database uses TIMESTAMP WITHOUT TIME ZONE, so we remove timezone info
            expiration_threshold = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).replace(tzinfo=None)

            query = self.create_base_query(TenantSecret).where(
                and_(
                    TenantSecret.is_active == True,
                    TenantSecret.expires_at.is_not(None),
                    TenantSecret.expires_at <= expiration_threshold
                )
            ).order_by(asc(TenantSecret.expires_at))

            result = await self.db.execute(query)
            secrets = result.scalars().all()

            return [secret.to_dict() for secret in secrets]

        except Exception as e:
            logger.exception(f"Failed to get expiring secrets for tenant {self.tenant_id}")
            raise

    async def get_secrets_by_type_stats(self) -> Dict[str, int]:
        """
        Get count of secrets by type for analytics.

        Returns:
            Dict mapping secret type to count
        """
        try:
            query = self.create_base_query(TenantSecret).with_only_columns(
                TenantSecret.secret_type,
                func.count(TenantSecret.id)
            ).where(
                TenantSecret.is_active == True
            ).group_by(TenantSecret.secret_type)

            result = await self.db.execute(query)
            return dict(result.fetchall())

        except Exception as e:
            logger.exception(f"Failed to get secrets by type stats for tenant {self.tenant_id}")
            raise

    async def get_access_summary(self) -> Dict[str, Any]:
        """
        Get access summary statistics for secrets.

        Returns:
            Dict with access statistics
        """
        try:
            # Most accessed secrets
            most_accessed_query = self.create_base_query(TenantSecret).where(
                TenantSecret.is_active == True
            ).order_by(desc(TenantSecret.access_count)).limit(10)

            most_accessed_result = await self.db.execute(most_accessed_query)
            most_accessed = most_accessed_result.scalars().all()

            # Recently accessed secrets
            recently_accessed_query = self.create_base_query(TenantSecret).where(
                and_(
                    TenantSecret.is_active == True,
                    TenantSecret.last_accessed.is_not(None)
                )
            ).order_by(desc(TenantSecret.last_accessed)).limit(10)

            recently_accessed_result = await self.db.execute(recently_accessed_query)
            recently_accessed = recently_accessed_result.scalars().all()

            # Never accessed secrets
            never_accessed_query = self.create_base_query(TenantSecret).with_only_columns(func.count(TenantSecret.id)).where(
                and_(
                    TenantSecret.is_active == True,
                    TenantSecret.last_accessed.is_(None)
                )
            )

            never_accessed_result = await self.db.execute(never_accessed_query)
            never_accessed_count = never_accessed_result.scalar() or 0

            return {
                "most_accessed": [secret.to_dict() for secret in most_accessed],
                "recently_accessed": [secret.to_dict() for secret in recently_accessed],
                "never_accessed_count": never_accessed_count
            }

        except Exception as e:
            logger.exception(f"Failed to get access summary for tenant {self.tenant_id}")
            raise
