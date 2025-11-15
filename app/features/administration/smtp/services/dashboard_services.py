"""
SMTP dashboard services implementing FastAPI/SQLAlchemy best practices.
🏆 GOLD STANDARD dashboard statistics and analytics patterns.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.smtp.models import SMTPConfiguration
from app.features.administration.smtp.schemas import SMTPConfigurationResponse, SMTPDashboardStats

logger = get_logger(__name__)


class SMTPDashboardService(BaseService[SMTPConfiguration]):
    """
    🏆 GOLD STANDARD SMTP dashboard service implementation.

    Demonstrates:
    - Enhanced BaseService for dashboard analytics
    - Type-safe statistical queries
    - Proper error handling for statistics
    - Reusable dashboard patterns
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def get_dashboard_stats(self) -> SMTPDashboardStats:
        """
        Get comprehensive dashboard statistics for SMTP configurations.

        Returns:
            SMTPDashboardStats: Complete dashboard statistics
        """
        try:
            # Get basic counts using enhanced query patterns
            total_configurations = await self.count_total(SMTPConfiguration)
            active_configurations = await self._count_active_configurations()
            verified_configurations = await self._count_verified_configurations()
            failed_configurations = await self._count_failed_configurations()

            # Get breakdown statistics
            configurations_by_status = await self._get_status_breakdown()
            recent_configurations = await self._get_recent_configurations()

            stats = SMTPDashboardStats(
                total_configurations=total_configurations,
                active_configurations=active_configurations,
                verified_configurations=verified_configurations,
                failed_configurations=failed_configurations,
                configurations_by_status=configurations_by_status,
                recent_configurations=recent_configurations
            )

            logger.info(f"Generated SMTP dashboard stats for tenant {self.tenant_id}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get SMTP dashboard stats: {e}")
            raise

    async def _count_active_configurations(self) -> int:
        """Count active SMTP configurations."""
        return await self.count_filtered(
            SMTPConfiguration,
            SMTPConfiguration.is_active == True
        )

    async def _count_verified_configurations(self) -> int:
        """Count verified SMTP configurations."""
        return await self.count_filtered(
            SMTPConfiguration,
            SMTPConfiguration.is_verified == True
        )

    async def _count_failed_configurations(self) -> int:
        """Count failed SMTP configurations."""
        return await self.count_filtered(
            SMTPConfiguration,
            SMTPConfiguration.test_status == "failed"
        )

    async def _get_status_breakdown(self) -> Dict[str, int]:
        """Get configurations grouped by status."""
        try:
            stmt = self.create_base_query_select([
                SMTPConfiguration.status,
                func.count(SMTPConfiguration.id).label('count')
            ]).group_by(SMTPConfiguration.status)

            result = await self.db.execute(stmt)
            return dict(result.fetchall())

        except Exception as e:
            logger.error(f"Failed to get SMTP status breakdown: {e}")
            return {}

    async def _get_recent_configurations(self, limit: int = 5) -> List[SMTPConfigurationResponse]:
        """Get recent SMTP configurations."""
        try:
            stmt = self.create_base_query(SMTPConfiguration).order_by(
                SMTPConfiguration.created_at.desc()
            ).limit(limit)

            result = await self.db.execute(stmt)
            configurations = result.scalars().all()

            return [self._configuration_to_response(config) for config in configurations]

        except Exception as e:
            logger.error(f"Failed to get recent SMTP configurations: {e}")
            return []

    def _configuration_to_response(self, configuration: SMTPConfiguration) -> SMTPConfigurationResponse:
        """Convert SQLAlchemy model to response schema."""
        return SMTPConfigurationResponse(
            id=configuration.id,
            name=configuration.name,
            description=configuration.description,
            host=configuration.host,
            port=configuration.port,
            use_tls=configuration.use_tls,
            use_ssl=configuration.use_ssl,
            username=configuration.username,
            from_email=configuration.from_email,
            from_name=configuration.from_name,
            reply_to=configuration.reply_to,
            status=configuration.status,
            enabled=configuration.enabled,
            is_active=configuration.is_active,
            is_verified=configuration.is_verified,
            tags=configuration.tags or [],
            tenant_id=configuration.tenant_id,
            last_tested_at=configuration.last_tested_at.isoformat() if configuration.last_tested_at else None,
            test_status=configuration.test_status,
            error_message=configuration.error_message,
            created_at=configuration.created_at.isoformat() if configuration.created_at else None,
            updated_at=configuration.updated_at.isoformat() if configuration.updated_at else None,
        )
