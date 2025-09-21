"""
Log management service for multi-tenant application logging.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import desc, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ApplicationLog
import structlog

logger = structlog.get_logger(__name__)


class LogService:
    """Service for managing application logs with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: Optional[str]):
        self.session = session
        self.tenant_id = tenant_id  # None means all tenants (for global admins)

    async def get_logs_list(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get paginated list of logs with filtering."""
        try:
            # Build base query with tenant isolation (skip for global admins)
            if self.tenant_id is not None:
                query = select(ApplicationLog).where(ApplicationLog.tenant_id == self.tenant_id)
            else:
                query = select(ApplicationLog)  # All tenants for global admins

            # Apply additional filters
            filters = []

            if level:
                filters.append(ApplicationLog.level == level.upper())

            if logger_name:
                filters.append(ApplicationLog.logger_name.ilike(f"%{logger_name}%"))

            if start_date:
                filters.append(ApplicationLog.timestamp >= start_date)

            if end_date:
                filters.append(ApplicationLog.timestamp <= end_date)

            if filters:
                query = query.filter(and_(*filters))

            # Get total count for pagination
            if self.tenant_id is not None:
                count_query = select(func.count(ApplicationLog.id)).where(ApplicationLog.tenant_id == self.tenant_id)
            else:
                count_query = select(func.count(ApplicationLog.id))

            if filters:
                count_query = count_query.filter(and_(*filters))
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(ApplicationLog.timestamp))
            query = query.offset(offset).limit(limit)

            result = await self.session.execute(query)
            logs = result.scalars().all()

            return {
                "data": [log.to_dict() for log in logs],
                "total": total,
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Failed to get logs list for tenant {tenant_id}")
            raise

    async def get_log_by_id(self, log_id: int) -> Optional[ApplicationLog]:
        """Get a specific log entry by ID."""
        try:
            query = select(ApplicationLog).filter(ApplicationLog.id == log_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(f"Failed to get log {log_id}")
            raise

    async def get_logs_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get log summary statistics."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Build base filter with tenant isolation (skip for global admins)
            if self.tenant_id is not None:
                base_filter = and_(
                    ApplicationLog.timestamp >= cutoff_time,
                    ApplicationLog.tenant_id == self.tenant_id
                )
            else:
                base_filter = ApplicationLog.timestamp >= cutoff_time

            # Get counts by level
            level_counts_query = select(
                ApplicationLog.level,
                func.count(ApplicationLog.id).label('count')
            ).filter(base_filter).group_by(ApplicationLog.level)
            level_counts_result = await self.session.execute(level_counts_query)
            level_counts = {row.level: row.count for row in level_counts_result}

            # Show appropriate tenants based on user permissions
            if self.tenant_id is not None:
                tenants = [self.tenant_id]  # Regular users see only their tenant
            else:
                # Global admins see all tenants with logs
                tenants_query = select(ApplicationLog.tenant_id).distinct().filter(base_filter)
                tenants_result = await self.session.execute(tenants_query)
                tenants = [row[0] for row in tenants_result]

            # Get recent errors (last 10)
            recent_errors_query = select(ApplicationLog).filter(
                and_(base_filter, ApplicationLog.level.in_(['ERROR', 'CRITICAL']))
            ).order_by(desc(ApplicationLog.timestamp)).limit(10)
            recent_errors_result = await self.session.execute(recent_errors_query)
            recent_errors = [log.to_dict() for log in recent_errors_result.scalars()]

            # Calculate derived metrics for stats cards
            error_count = (level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0))
            info_count = level_counts.get('INFO', 0)
            tenant_count = len(tenants)
            total_logs = sum(level_counts.values())

            return {
                "level_counts": level_counts,
                "total_logs": total_logs,
                "error_count": error_count,
                "info_count": info_count,
                "tenant_count": tenant_count,
                "tenants": tenants,
                "recent_errors": recent_errors,
                "time_range_hours": hours
            }

        except Exception as e:
            logger.exception("Failed to get logs summary")
            raise

    async def get_tenant_list(self) -> List[Dict[str, Any]]:
        """Get list of tenants with logs (tenant isolated for regular users)."""
        try:
            if self.tenant_id is not None:
                # Regular users see only their tenant
                query = select(
                    ApplicationLog.tenant_id,
                    func.count(ApplicationLog.id).label('log_count')
                ).where(
                    ApplicationLog.tenant_id == self.tenant_id
                ).group_by(ApplicationLog.tenant_id)
            else:
                # Global admins see all tenants
                query = select(
                    ApplicationLog.tenant_id,
                    func.count(ApplicationLog.id).label('log_count')
                ).group_by(ApplicationLog.tenant_id)

            result = await self.session.execute(query)

            return [
                {"tenant_id": row.tenant_id, "log_count": row.log_count}
                for row in result
            ]

        except Exception as e:
            logger.exception("Failed to get tenant list")
            raise

    async def cleanup_old_logs(self, days: int = 30) -> Dict[str, Any]:
        """Clean up old log entries to manage database size."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Count logs to be deleted
            count_query = select(func.count(ApplicationLog.id)).filter(
                ApplicationLog.timestamp < cutoff_date
            )
            count_result = await self.session.execute(count_query)
            count_to_delete = count_result.scalar()

            # Delete old logs using async delete
            from sqlalchemy import delete
            delete_query = delete(ApplicationLog).filter(
                ApplicationLog.timestamp < cutoff_date
            )
            await self.session.execute(delete_query)
            await self.session.commit()

            logger.info(f"Cleaned up {count_to_delete} log entries older than {days} days")

            return {
                "deleted_count": count_to_delete,
                "cutoff_date": cutoff_date.isoformat(),
                "days": days
            }

        except Exception as e:
            logger.exception("Failed to cleanup old logs")
            raise
