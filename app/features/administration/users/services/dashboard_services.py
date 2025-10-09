"""
User dashboard services implementing FastAPI/SQLAlchemy best practices.
🏆 GOLD STANDARD dashboard statistics and analytics patterns.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.users.models import User, UserDashboardStats

logger = structlog.get_logger(__name__)


class UserDashboardService(BaseService[User]):
    """
    🏆 GOLD STANDARD dashboard service implementation.

    Demonstrates:
    - Enhanced BaseService for dashboard analytics
    - Type-safe statistical queries
    - Proper error handling for statistics
    - Reusable dashboard patterns
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def get_dashboard_stats(self) -> UserDashboardStats:
        """
        Get comprehensive dashboard statistics using enhanced query patterns.

        Returns:
            UserDashboardStats: Complete dashboard statistics
        """
        try:
            # Get basic counts using helper methods
            total_users = await self.count_total(User)
            active_users = await self._count_active_users()

            # Get breakdown statistics
            status_breakdown = await self._get_status_breakdown()
            role_breakdown = await self._get_role_breakdown()
            recent_users = await self._count_recent_users()

            stats = UserDashboardStats(
                total_users=total_users,
                active_users=active_users,
                inactive_users=total_users - active_users,
                users_by_status=status_breakdown,
                users_by_role=role_breakdown,
                recent_users=recent_users
            )

            self.log_operation("get_dashboard_stats", {
                "total_users": total_users,
                "active_users": active_users
            })

            return stats

        except Exception as e:
            # Return safe fallback stats on error
            return await self.handle_error("get_dashboard_stats", e,
                                         fallback=self._get_empty_stats())

    async def _count_active_users(self) -> int:
        """Count active users in tenant scope."""
        query = self.create_base_query(User).where(
            User.enabled == True,
            User.status == 'active'
        )
        result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar() or 0

    async def _get_status_breakdown(self) -> Dict[str, int]:
        """Get user count by status."""
        query = self.create_base_query(User)
        stmt = select(User.status, func.count(User.id)).select_from(
            query.subquery()
        ).group_by(User.status)

        result = await self.db.execute(stmt)
        return {row.status: row.count for row in result.fetchall()}

    async def _get_role_breakdown(self) -> Dict[str, int]:
        """Get user count by role."""
        query = self.create_base_query(User)
        stmt = select(User.role, func.count(User.id)).select_from(
            query.subquery()
        ).group_by(User.role)

        result = await self.db.execute(stmt)
        return {row.role: row.count for row in result.fetchall()}

    async def _count_recent_users(self, days: int = 30) -> int:
        """Count users created in recent days."""
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = self.create_base_query(User).where(User.created_at >= cutoff_date)
        result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar() or 0

    def _get_empty_stats(self) -> UserDashboardStats:
        """Return empty/safe stats for error fallback."""
        return UserDashboardStats(
            total_users=0,
            active_users=0,
            inactive_users=0,
            users_by_status={},
            users_by_role={},
            recent_users=0
        )
