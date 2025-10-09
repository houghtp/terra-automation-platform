"""
Log dashboard services implementing FastAPI/SQLAlchemy best practices.
Statistics and analytics for application logs.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.logs.models import ApplicationLog

logger = get_logger(__name__)


class LogDashboardService(BaseService[ApplicationLog]):
    """
    Dashboard and analytics operations for application logs.

    Provides statistics, trends, and analytics data for application logs.
    All operations are automatically tenant-scoped via BaseService.
    """

    async def get_logs_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive log statistics.

        Returns:
            Dictionary containing various log statistics
        """
        try:
            # Base query with tenant filtering
            base_query = self.create_base_query(ApplicationLog)

            # Total logs (consistent db usage)
            total_logs = await self.db.scalar(
                base_query.with_only_columns(func.count(ApplicationLog.id))
            )

            # Log level distribution (consistent db usage)
            level_stats = await self.db.execute(
                base_query.with_only_columns(
                    ApplicationLog.level,
                    func.count(ApplicationLog.id).label('count')
                ).group_by(ApplicationLog.level)
            )

            # Recent activity (last 24 hours) (consistent db usage)
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_logs = await self.db.scalar(
                base_query.with_only_columns(func.count(ApplicationLog.id))
                .where(ApplicationLog.timestamp >= twenty_four_hours_ago)
            )

            # Top modules/components (consistent db usage)
            top_modules = await self.db.execute(
                base_query.with_only_columns(
                    ApplicationLog.logger_name,
                    func.count(ApplicationLog.id).label('count')
                ).group_by(ApplicationLog.logger_name)
                .order_by(func.count(ApplicationLog.id).desc())
                .limit(10)
            )

            # Error rate (last 24 hours) (consistent db usage)
            error_logs = await self.db.scalar(
                base_query.with_only_columns(func.count(ApplicationLog.id))
                .where(
                    and_(
                        ApplicationLog.level.in_(['ERROR', 'CRITICAL']),
                        ApplicationLog.timestamp >= twenty_four_hours_ago
                    )
                )
            )

            error_rate = (error_logs / recent_logs * 100) if recent_logs > 0 else 0

            stats = {
                'total_logs': total_logs or 0,
                'recent_logs_24h': recent_logs or 0,
                'error_rate_24h': round(error_rate, 2),
                'level_distribution': {
                    row.level: row.count for row in level_stats.all()
                },
                'top_modules': [
                    {'module': row.logger_name, 'count': row.count}
                    for row in top_modules.all()
                ]
            }

            logger.info(f"Generated log statistics for tenant {self.tenant_id}")
            return stats

        except Exception as e:
            logger.exception(f"Failed to get log stats for tenant {self.tenant_id}")
            raise

    async def get_log_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get log trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing trend data
        """
        try:
            base_query = self.create_base_query(ApplicationLog)
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Daily log counts
            day_expr = func.date_trunc('day', ApplicationLog.timestamp)
            daily_counts = await self.db.execute(
                base_query.with_only_columns(
                    day_expr.label('day'),
                    func.count(ApplicationLog.id).label('count')
                ).where(ApplicationLog.timestamp >= start_date)
                .group_by(day_expr)
                .order_by(day_expr)
            )

            # Daily error counts
            daily_errors = await self.db.execute(
                base_query.with_only_columns(
                    day_expr.label('day'),
                    func.count(ApplicationLog.id).label('count')
                ).where(
                    and_(
                        ApplicationLog.timestamp >= start_date,
                        ApplicationLog.level.in_(['ERROR', 'CRITICAL'])
                    )
                ).group_by(day_expr)
                .order_by(day_expr)
            )

            trends = {
                'daily_counts': [
                    {
                        'date': row.day.strftime('%Y-%m-%d') if hasattr(row.day, 'strftime') else str(row.day),
                        'count': row.count
                    }
                    for row in daily_counts
                ],
                'daily_errors': [
                    {
                        'date': row.day.strftime('%Y-%m-%d') if hasattr(row.day, 'strftime') else str(row.day),
                        'count': row.count
                    }
                    for row in daily_errors
                ]
            }

            return trends

        except Exception as e:
            logger.exception(f"Failed to get log trends for tenant {self.tenant_id}")
            raise

    async def get_error_summary(self) -> Dict[str, Any]:
        """
        Get error-focused log summary.

        Returns:
            Dictionary containing error metrics
        """
        try:
            base_query = self.create_base_query(ApplicationLog)

            # Get current time for calculations
            now = datetime.now(timezone.utc)
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            # Error counts by severity
            error_counts = await self.db.execute(
                base_query.with_only_columns(
                    ApplicationLog.level,
                    func.count(ApplicationLog.id).label('count')
                ).where(
                    and_(
                        ApplicationLog.level.in_(['WARNING', 'ERROR', 'CRITICAL']),
                        ApplicationLog.timestamp >= last_24h
                    )
                ).group_by(ApplicationLog.level)
            )

            # Top error modules
            error_modules = await self.db.execute(
                base_query.with_only_columns(
                    ApplicationLog.logger_name,
                    func.count(ApplicationLog.id).label('count')
                ).where(
                    and_(
                        ApplicationLog.level.in_(['ERROR', 'CRITICAL']),
                        ApplicationLog.timestamp >= last_7d
                    )
                ).group_by(ApplicationLog.logger_name)
                .order_by(func.count(ApplicationLog.id).desc())
                .limit(5)
            )

            return {
                "error_counts_24h": {
                    row.level: row.count for row in error_counts
                },
                "top_error_modules_7d": [
                    {"module": row.logger_name, "count": row.count}
                    for row in error_modules
                ],
                "last_updated": now.isoformat()
            }

        except Exception as e:
            logger.exception(f"Failed to get error summary for tenant {self.tenant_id}")
            raise
