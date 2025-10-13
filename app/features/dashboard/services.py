"""
Dashboard service for aggregating and providing chart data.

Uses BaseService for consistent patterns and proper tenant isolation.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from app.features.auth.models import User

logger = get_logger(__name__)


class DashboardService(BaseService[User]):
    """
    Service for dashboard data aggregation and analytics.

    Inherits from BaseService for consistent tenant isolation patterns.
    """

    async def get_user_status_breakdown(self) -> Dict[str, Any]:
        """
        Get breakdown of users by status for bar chart.

        Returns:
            Dict with categories, values, and total count
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            stmt = self.create_base_query(User).where(User.status.isnot(None))

            # Group by status and count
            stmt = select(
                User.status,
                func.count(User.id).label('count')
            ).select_from(stmt.subquery()).group_by(User.status).order_by(desc('count'))

            result = await self.db.execute(stmt)
            rows = result.all()

            categories = [row.status.title() for row in rows]
            values = [row.count for row in rows]

            self.log_operation("user_status_breakdown", {
                "categories_count": len(categories),
                "total": sum(values)
            })

            return {
                "categories": categories,
                "values": values,
                "total": sum(values)
            }
        except Exception as e:
            await self.handle_error("get_user_status_breakdown", e)
            return {"categories": [], "values": [], "total": 0}

    async def get_user_enabled_breakdown(self) -> Dict[str, Any]:
        """
        Get breakdown of enabled vs disabled users for donut chart.

        Returns:
            Dict with items (name, value, color) and total count
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            stmt = select(
                User.enabled,
                func.count(User.id).label('count')
            )

            # Apply tenant filtering
            if self.tenant_id is not None:
                stmt = stmt.where(User.tenant_id == self.tenant_id)

            stmt = stmt.group_by(User.enabled)

            result = await self.db.execute(stmt)
            rows = result.all()

            items = []
            colors = ['#3b82f6', '#ef4444']  # Blue for enabled, red for disabled

            for i, row in enumerate(rows):
                status_name = 'Enabled' if row.enabled else 'Disabled'
                items.append({
                    "name": status_name,
                    "value": row.count,
                    "itemStyle": {"color": colors[0 if row.enabled else 1]}
                })

            total = sum(item["value"] for item in items)

            self.log_operation("user_enabled_breakdown", {"total": total})

            return {
                "items": items,
                "total": total
            }
        except Exception as e:
            await self.handle_error("get_user_enabled_breakdown", e)
            return {"items": [], "total": 0}

    async def get_user_tag_distribution(self) -> Dict[str, Any]:
        """
        Get tag distribution for pie chart.

        Returns:
            Dict with items (name, value, color) and total count
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            stmt = self.create_base_query(User).where(
                User.tags.isnot(None),
                User.tags != cast('[]', JSON)
            )

            result = await self.db.execute(stmt)
            users = result.scalars().all()

            tag_counts = {}

            for user in users:
                if user.tags:
                    try:
                        # Parse JSON tags
                        tags = json.loads(user.tags) if isinstance(user.tags, str) else user.tags
                        if isinstance(tags, list):
                            for tag in tags:
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        continue

            # Sort by count and take top 10
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            colors = [
                '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
                '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6b7280'
            ]

            items = []
            for i, (tag, count) in enumerate(sorted_tags):
                items.append({
                    "name": tag.title(),
                    "value": count,
                    "itemStyle": {"color": colors[i % len(colors)]}
                })

            total = sum(item["value"] for item in items)

            self.log_operation("user_tag_distribution", {"total_tags": len(items)})

            return {
                "items": items,
                "total": total
            }
        except Exception as e:
            await self.handle_error("get_user_tag_distribution", e)
            return {"items": [], "total": 0}

    async def get_user_items_over_time(self) -> Dict[str, Any]:
        """
        Get users created over time for line chart (last 30 days).

        Returns:
            Dict with categories (dates), values (counts), and total
        """
        try:
            # Get items created over the last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # Use BaseService query builder for automatic tenant filtering
            stmt = select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            )

            # Apply tenant filtering
            if self.tenant_id is not None:
                stmt = stmt.where(User.tenant_id == self.tenant_id)

            stmt = stmt.where(
                User.created_at >= start_date
            ).group_by(func.date(User.created_at)).order_by('date')

            result = await self.db.execute(stmt)
            rows = result.all()

            # Fill in missing dates with zero counts
            date_counts = {row.date: row.count for row in rows}

            categories = []
            values = []
            current_date = start_date.date()

            while current_date <= end_date.date():
                categories.append(current_date.strftime('%m/%d'))
                values.append(date_counts.get(current_date, 0))
                current_date += timedelta(days=1)

            total = sum(values)

            self.log_operation("user_items_over_time", {"total": total, "days": 30})

            return {
                "categories": categories,
                "values": values,
                "total": total
            }
        except Exception as e:
            await self.handle_error("get_user_items_over_time", e)
            return {"categories": [], "values": [], "total": 0}

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get overall dashboard summary statistics.

        Returns:
            Dict with total_items, active_items, enabled_items, recent_items, completion_rate
        """
        try:
            # Base query with tenant filtering
            base_query = self.create_base_query(User)

            # Total items
            total_stmt = select(func.count(User.id)).select_from(base_query.subquery())
            total_result = await self.db.execute(total_stmt)
            total_items = total_result.scalar() or 0

            # Active items
            active_stmt = select(func.count(User.id)).select_from(
                base_query.where(User.status == 'active').subquery()
            )
            active_result = await self.db.execute(active_stmt)
            active_items = active_result.scalar() or 0

            # Enabled items
            enabled_stmt = select(func.count(User.id)).select_from(
                base_query.where(User.enabled == True).subquery()
            )
            enabled_result = await self.db.execute(enabled_stmt)
            enabled_items = enabled_result.scalar() or 0

            # Items created in last 7 days
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_stmt = select(func.count(User.id)).select_from(
                base_query.where(User.created_at >= seven_days_ago).subquery()
            )
            recent_result = await self.db.execute(recent_stmt)
            recent_items = recent_result.scalar() or 0

            completion_rate = round((active_items / total_items * 100) if total_items > 0 else 0, 1)

            self.log_operation("dashboard_summary", {
                "total_items": total_items,
                "active_items": active_items,
                "enabled_items": enabled_items,
                "recent_items": recent_items
            })

            return {
                "total_items": total_items,
                "active_items": active_items,
                "enabled_items": enabled_items,
                "recent_items": recent_items,
                "completion_rate": completion_rate
            }
        except Exception as e:
            await self.handle_error("get_dashboard_summary", e)
            return {
                "total_items": 0,
                "active_items": 0,
                "enabled_items": 0,
                "recent_items": 0,
                "completion_rate": 0.0
            }
