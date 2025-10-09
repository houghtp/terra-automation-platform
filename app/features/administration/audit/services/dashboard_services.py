"""
Audit dashboard services implementing FastAPI/SQLAlchemy best practices.
Statistics and analytics for audit logs.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.audit.models import AuditLog

logger = get_logger(__name__)


class AuditDashboardService(BaseService[AuditLog]):
    """
    Dashboard and analytics operations for audit logs.

    Provides statistics, timelines, and analytics data for audit logs.
    All operations are automatically tenant-scoped via BaseService.
    """

    async def get_audit_stats(self) -> Dict[str, Any]:
        """
        Get audit statistics for dashboard.

        Returns:
            Dictionary containing audit statistics
        """
        try:
            # Get current time for calculations
            now = datetime.now(timezone.utc)
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)

            # Total logs count using BaseService
            total_logs = await self.count_total(AuditLog)

            # Recent activity counts using BaseService patterns
            base_query = self.create_base_query(AuditLog)

            recent_24h = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(AuditLog.timestamp >= last_24h)
            )

            recent_7d = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(AuditLog.timestamp >= last_7d)
            )

            # Security events count using BaseService pattern
            security_events = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(AuditLog.severity.in_(["WARNING", "ERROR", "CRITICAL"]))
            )

            # Category breakdown using BaseService pattern
            category_result = await self.db.execute(
                base_query.with_only_columns(
                    AuditLog.category,
                    func.count(AuditLog.id).label('count')
                ).group_by(AuditLog.category)
            )
            by_category = {row.category: row.count for row in category_result}

            # Severity breakdown using BaseService pattern
            severity_result = await self.db.execute(
                base_query.with_only_columns(
                    AuditLog.severity,
                    func.count(AuditLog.id).label('count')
                ).group_by(AuditLog.severity)
            )
            by_severity = {row.severity: row.count for row in severity_result}

            # Top users (last 30 days) using BaseService pattern
            top_users_result = await self.db.execute(
                base_query.with_only_columns(
                    AuditLog.user_email,
                    func.count(AuditLog.id).label('count')
                ).where(
                    and_(
                        AuditLog.timestamp >= last_30d,
                        AuditLog.user_email.isnot(None)
                    )
                ).group_by(AuditLog.user_email)
                .order_by(desc('count'))
                .limit(5)
            )

            top_users = [
                {"email": row.user_email, "count": row.count}
                for row in top_users_result
            ]

            return {
                "total_logs": total_logs,
                "recent_24h": recent_24h or 0,
                "recent_7d": recent_7d or 0,
                "security_events": security_events or 0,
                "by_category": by_category,
                "by_severity": by_severity,
                "top_users": top_users,
                "categories_count": len(by_category),
                "last_updated": now.isoformat()
            }

        except Exception as e:
            logger.exception(f"Failed to get audit stats for tenant {self.tenant_id}")
            raise

    async def get_audit_timeline(
        self,
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
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                end_date = datetime.now(timezone.utc)

            # Build base query with tenant filtering
            base_query = self.create_base_query(AuditLog)
            conditions = [
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

            # Start with base query for tenant filtering, then add additional conditions
            query = base_query.with_only_columns(
                day_expr.label('day'),
                AuditLog.category,
                func.count(AuditLog.id).label('count')
            )

            # Add additional filtering conditions
            for condition in conditions:
                query = query.where(condition)

            query = query.group_by(
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
            logger.exception(f"Failed to get audit timeline for tenant {self.tenant_id}")
            raise

    async def get_security_summary(self) -> Dict[str, Any]:
        """
        Get security-focused audit summary.

        Returns:
            Dictionary containing security metrics
        """
        try:
            # Use BaseService for consistent tenant filtering
            base_query = self.create_base_query(AuditLog)

            # Get current time for calculations
            now = datetime.now(timezone.utc)
            last_24h = now - timedelta(hours=24)

            # Failed authentication attempts
            failed_auth_count = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(
                    and_(
                        AuditLog.category == "AUTH",
                        AuditLog.severity.in_(["WARNING", "ERROR"]),
                        AuditLog.timestamp >= last_24h
                    )
                )
            )

            # Admin actions
            admin_actions_count = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(
                    and_(
                        AuditLog.category == "ADMIN",
                        AuditLog.timestamp >= last_24h
                    )
                )
            )

            # Critical events
            critical_events_count = await self.db.scalar(
                base_query.with_only_columns(func.count(AuditLog.id))
                .where(
                    and_(
                        AuditLog.severity == "CRITICAL",
                        AuditLog.timestamp >= last_24h
                    )
                )
            )

            return {
                "failed_auth_24h": failed_auth_count or 0,
                "admin_actions_24h": admin_actions_count or 0,
                "critical_events_24h": critical_events_count or 0,
                "last_updated": now.isoformat()
            }

        except Exception as e:
            logger.exception(f"Failed to get security summary for tenant {self.tenant_id}")
            raise
