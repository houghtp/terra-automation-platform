"""Audit service for read-only audit log operations."""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.sql import text
from datetime import datetime, timedelta
import structlog
from .models import AuditLog

logger = structlog.get_logger()


class AuditService:
    """
    Read-only service for audit log operations.

    This service provides methods to query and analyze audit logs
    without any modification capabilities to maintain audit integrity.
    """

    def __init__(self, db: AsyncSession):
        """Initialize audit service with database session."""
        self.db = db

    async def get_audit_logs(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        category_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc"
    ) -> List[AuditLog]:
        """
        Get paginated audit logs with optional filtering.

        Args:
            tenant_id: Tenant identifier for isolation
            limit: Maximum number of records to return
            offset: Number of records to skip
            category_filter: Filter by category (AUTH, DATA, ADMIN, etc.)
            severity_filter: Filter by severity (INFO, WARNING, ERROR, CRITICAL)
            user_filter: Filter by user email or ID
            action_filter: Filter by action type
            date_from: Start date for filtering
            date_to: End date for filtering
            sort_by: Field to sort by (timestamp, action, category, severity)
            sort_order: Sort direction (asc, desc)

        Returns:
            List of audit log entries
        """
        try:
            # Build base query
            query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

            # Apply filters
            if category_filter:
                query = query.where(AuditLog.category == category_filter.upper())

            if severity_filter:
                query = query.where(AuditLog.severity == severity_filter.upper())

            if user_filter:
                query = query.where(
                    func.lower(AuditLog.user_email).contains(user_filter.lower()) |
                    func.lower(AuditLog.user_id).contains(user_filter.lower())
                )

            if action_filter:
                query = query.where(
                    func.lower(AuditLog.action).contains(action_filter.lower())
                )

            if date_from:
                query = query.where(AuditLog.timestamp >= date_from)

            if date_to:
                query = query.where(AuditLog.timestamp <= date_to)

            # Apply sorting
            sort_column = getattr(AuditLog, sort_by, AuditLog.timestamp)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to get audit logs for tenant {tenant_id}")
            raise

    async def get_audit_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get audit statistics for dashboard.

        Args:
            tenant_id: Tenant identifier for isolation

        Returns:
            Dictionary containing audit statistics
        """
        try:
            # Get current time for calculations
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)

            # Total logs count
            total_query = select(func.count(AuditLog.id)).where(
                AuditLog.tenant_id == tenant_id
            )
            total_result = await self.db.execute(total_query)
            total_logs = total_result.scalar() or 0

            # Recent activity counts
            recent_24h_query = select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.timestamp >= last_24h
                )
            )
            recent_24h_result = await self.db.execute(recent_24h_query)
            recent_24h = recent_24h_result.scalar() or 0

            recent_7d_query = select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.timestamp >= last_7d
                )
            )
            recent_7d_result = await self.db.execute(recent_7d_query)
            recent_7d = recent_7d_result.scalar() or 0

            # Security events (WARNING, ERROR, CRITICAL)
            security_query = select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.severity.in_(["WARNING", "ERROR", "CRITICAL"])
                )
            )
            security_result = await self.db.execute(security_query)
            security_events = security_result.scalar() or 0

            # Category breakdown
            category_query = select(
                AuditLog.category,
                func.count(AuditLog.id).label('count')
            ).where(
                AuditLog.tenant_id == tenant_id
            ).group_by(AuditLog.category)

            category_result = await self.db.execute(category_query)
            by_category = {row.category: row.count for row in category_result}

            # Severity breakdown
            severity_query = select(
                AuditLog.severity,
                func.count(AuditLog.id).label('count')
            ).where(
                AuditLog.tenant_id == tenant_id
            ).group_by(AuditLog.severity)

            severity_result = await self.db.execute(severity_query)
            by_severity = {row.severity: row.count for row in severity_result}

            # Top users (last 30 days)
            top_users_query = select(
                AuditLog.user_email,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.timestamp >= last_30d,
                    AuditLog.user_email.isnot(None)
                )
            ).group_by(AuditLog.user_email).order_by(desc('count')).limit(5)

            top_users_result = await self.db.execute(top_users_query)
            top_users = [
                {"email": row.user_email, "count": row.count}
                for row in top_users_result
            ]

            return {
                "total_logs": total_logs,
                "recent_24h": recent_24h,
                "recent_7d": recent_7d,
                "security_events": security_events,
                "by_category": by_category,
                "by_severity": by_severity,
                "top_users": top_users,
                "categories_count": len(by_category),
                "last_updated": now.isoformat()
            }

        except Exception as e:
            logger.exception(f"Failed to get audit stats for tenant {tenant_id}")
            raise

    async def get_audit_log_by_id(self, tenant_id: str, log_id: int) -> Optional[AuditLog]:
        """
        Get a specific audit log by ID.

        Args:
            tenant_id: Tenant identifier for isolation
            log_id: Audit log ID

        Returns:
            Audit log if found, None otherwise
        """
        try:
            query = select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.id == log_id
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(f"Failed to get audit log {log_id} for tenant {tenant_id}")
            raise

    async def search_audit_logs(
        self,
        tenant_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Search audit logs by description or metadata.

        Args:
            tenant_id: Tenant identifier for isolation
            search_term: Search term to look for
            limit: Maximum number of results

        Returns:
            List of matching audit logs
        """
        try:
            # Search in description and metadata fields
            query = select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    func.lower(AuditLog.description).contains(search_term.lower()) |
                    func.lower(AuditLog.action).contains(search_term.lower()) |
                    func.lower(AuditLog.resource_type).contains(search_term.lower())
                )
            ).order_by(desc(AuditLog.timestamp)).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to search audit logs for tenant {tenant_id}")
            raise

    async def get_audit_timeline(
        self,
        tenant_id: str,
        days: int = 7,
        category_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit activity timeline for the last N days with optional filtering.

        Args:
            tenant_id: Tenant identifier for isolation
            days: Number of days to include in timeline
            category_filter: Filter by category
            severity_filter: Filter by severity level
            user_filter: Filter by user email
            action_filter: Filter by action type
            date_from: Start date for filtering
            date_to: End date for filtering

        Returns:
            List of daily activity counts by category
        """
        try:
            # Use custom date range if provided, otherwise use days parameter
            if date_from and date_to:
                start_date = date_from
                end_date = date_to
            else:
                start_date = datetime.utcnow() - timedelta(days=days)
                end_date = datetime.utcnow()

            # Build base query conditions
            conditions = [
                AuditLog.tenant_id == tenant_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            ]

            # Apply filters
            if category_filter:
                conditions.append(AuditLog.category == category_filter)

            if severity_filter:
                conditions.append(AuditLog.severity == severity_filter)

            if user_filter:
                conditions.append(AuditLog.user_email.ilike(f"%{user_filter}%"))

            if action_filter:
                conditions.append(AuditLog.action.ilike(f"%{action_filter}%"))

            # Use PostgreSQL-compatible date function with proper aliasing
            day_expr = func.date_trunc('day', AuditLog.timestamp)
            query = select(
                day_expr.label('day'),
                AuditLog.category,
                func.count(AuditLog.id).label('count')
            ).where(
                and_(*conditions)
            ).group_by(
                day_expr,
                AuditLog.category
            ).order_by(day_expr)

            result = await self.db.execute(query)
            timeline_data = []

            for row in result:
                # Convert the datetime to date string
                date_str = row.day.strftime('%Y-%m-%d') if hasattr(row.day, 'strftime') else str(row.day)
                timeline_data.append({
                    "date": date_str,
                    "category": row.category,
                    "count": row.count
                })

            return timeline_data

        except Exception as e:
            logger.exception(f"Failed to get audit timeline for tenant {tenant_id}")
            raise
