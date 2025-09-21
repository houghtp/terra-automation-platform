"""
Dashboard service for aggregating and providing chart data
"""
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from datetime import datetime, timedelta
from app.features.auth.models import User


class DashboardService:
    """Service for dashboard data aggregation and analytics"""

    @staticmethod
    async def get_user_status_breakdown(session: AsyncSession, tenant: str = None) -> Dict[str, Any]:
        """Get breakdown of users by status for bar chart"""
        try:
            # Query status counts with tenant filtering
            # Global admin (tenant="global") should see all data
            if tenant and tenant != "global":
                query = text("""
                    SELECT status, COUNT(*) as count
                    FROM users
                    WHERE status IS NOT NULL AND tenant_id = :tenant
                    GROUP BY status
                    ORDER BY count DESC
                """)
                result = await session.execute(query, {"tenant": tenant})
            else:
                query = text("""
                    SELECT status, COUNT(*) as count
                    FROM users
                    WHERE status IS NOT NULL
                    GROUP BY status
                    ORDER BY count DESC
                """)
                result = await session.execute(query)

            rows = result.fetchall()

            categories = [row.status.title() for row in rows]
            values = [row.count for row in rows]

            return {
                "categories": categories,
                "values": values,
                "total": sum(values)
            }
        except Exception as e:
            print(f"Error getting user status breakdown: {e}")
            return {"categories": [], "values": [], "total": 0}

    @staticmethod
    async def get_user_enabled_breakdown(session: AsyncSession, tenant: str = None) -> Dict[str, Any]:
        """Get breakdown of enabled vs disabled users for donut chart"""
        try:
            # Global admin (tenant="global") should see all data
            if tenant and tenant != "global":
                query = text("""
                    SELECT
                        CASE WHEN enabled = true THEN 'Enabled' ELSE 'Disabled' END as status,
                        COUNT(*) as count
                    FROM users
                    WHERE tenant_id = :tenant
                    GROUP BY enabled
                """)
                result = await session.execute(query, {"tenant": tenant})
            else:
                query = text("""
                    SELECT
                        CASE WHEN enabled = true THEN 'Enabled' ELSE 'Disabled' END as status,
                        COUNT(*) as count
                    FROM users
                    GROUP BY enabled
                """)
                result = await session.execute(query)

            rows = result.fetchall()

            items = []
            colors = ['#3b82f6', '#ef4444']  # Blue for enabled, red for disabled

            for i, row in enumerate(rows):
                items.append({
                    "name": row.status,
                    "value": row.count,
                    "itemStyle": {"color": colors[i % len(colors)]}
                })

            return {
                "items": items,
                "total": sum(item["value"] for item in items)
            }
        except Exception as e:
            print(f"Error getting enabled breakdown: {e}")
            return {"items": [], "total": 0}

    @staticmethod
    async def get_user_tag_distribution(session: AsyncSession) -> Dict[str, Any]:
        """Get tag distribution for pie chart"""
        try:
            # Process JSON array fields - PostgreSQL can handle JSON but we'll process in Python for simplicity
            query = text("SELECT tags FROM users WHERE tags IS NOT NULL AND tags != '[]'")
            result = await session.execute(query)
            rows = result.fetchall()

            tag_counts = {}

            for row in rows:
                if row.tags:
                    try:
                        # Parse JSON tags
                        import json
                        tags = json.loads(row.tags) if isinstance(row.tags, str) else row.tags
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

            return {
                "items": items,
                "total": sum(item["value"] for item in items)
            }
        except Exception as e:
            print(f"Error getting tag distribution: {e}")
            return {"items": [], "total": 0}

    @staticmethod
    async def get_user_items_over_time(session: AsyncSession) -> Dict[str, Any]:
        """Get users created over time for line chart"""
        try:
            # Get items created over the last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            query = text("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM users
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """)

            result = await session.execute(query, {"start_date": start_date})
            rows = result.fetchall()

            # Fill in missing dates with zero counts
            date_counts = {row.date: row.count for row in rows}

            categories = []
            values = []
            current_date = start_date.date()

            while current_date <= end_date.date():
                date_str = current_date.strftime('%Y-%m-%d')
                categories.append(current_date.strftime('%m/%d'))
                values.append(date_counts.get(date_str, 0))
                current_date += timedelta(days=1)

            return {
                "categories": categories,
                "values": values,
                "total": sum(values)
            }
        except Exception as e:
            print(f"Error getting items over time: {e}")
            return {"categories": [], "values": [], "total": 0}

    @staticmethod
    async def get_dashboard_summary(session: AsyncSession, tenant: str = None) -> Dict[str, Any]:
        """Get overall dashboard summary statistics"""
        try:
            # Global admin (tenant="global") should see all data
            # Total items
            if tenant and tenant != "global":
                total_query = text("SELECT COUNT(*) as total FROM users WHERE tenant_id = :tenant")
                total_result = await session.execute(total_query, {"tenant": tenant})
            else:
                total_query = text("SELECT COUNT(*) as total FROM users")
                total_result = await session.execute(total_query)
            total_items = total_result.scalar()

            # Active items
            if tenant and tenant != "global":
                active_query = text("SELECT COUNT(*) as active FROM users WHERE status = 'active' AND tenant_id = :tenant")
                active_result = await session.execute(active_query, {"tenant": tenant})
            else:
                active_query = text("SELECT COUNT(*) as active FROM users WHERE status = 'active'")
                active_result = await session.execute(active_query)
            active_items = active_result.scalar()

            # Enabled items
            if tenant and tenant != "global":
                enabled_query = text("SELECT COUNT(*) as enabled FROM users WHERE enabled = true AND tenant_id = :tenant")
                enabled_result = await session.execute(enabled_query, {"tenant": tenant})
            else:
                enabled_query = text("SELECT COUNT(*) as enabled FROM users WHERE enabled = true")
                enabled_result = await session.execute(enabled_query)
            enabled_items = enabled_result.scalar()

            # Items created in last 7 days (replace due dates)
            if tenant and tenant != "global":
                recent_query = text("SELECT COUNT(*) as recent FROM users WHERE created_at >= NOW() - INTERVAL '7 days' AND tenant_id = :tenant")
                recent_result = await session.execute(recent_query, {"tenant": tenant})
            else:
                recent_query = text("SELECT COUNT(*) as recent FROM users WHERE created_at >= NOW() - INTERVAL '7 days'")
                recent_result = await session.execute(recent_query)
            recent_items = recent_result.scalar()

            return {
                "total_items": total_items,
                "active_items": active_items,
                "enabled_items": enabled_items,
                "recent_items": recent_items,
                "completion_rate": round((active_items / total_items * 100) if total_items > 0 else 0, 1)
            }
        except Exception as e:
            print(f"Error getting dashboard summary: {e}")
            return {
                "total_items": 0,
                "active_items": 0,
                "enabled_items": 0,
                "recent_items": 0,
                "completion_rate": 0.0
            }
