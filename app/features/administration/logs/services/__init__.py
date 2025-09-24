"""
Combined Log Management Service that includes all service components.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .crud_services import LogCrudService
from .dashboard_services import LogDashboardService


class LogManagementService:
    """
    Comprehensive log management service.

    Combines all service components:
    - CRUD operations (read-only for log integrity)
    - Dashboard statistics and analytics
    - Trend analysis and error summaries
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id

        # Initialize component services
        self._crud_service = LogCrudService(db_session, tenant_id)
        self._dashboard_service = LogDashboardService(db_session, tenant_id)

    # --- CRUD Operations ---
    async def get_application_logs(self, *args, **kwargs):
        """Get application logs with filtering."""
        return await self._crud_service.get_application_logs(*args, **kwargs)

    async def get_log_by_id(self, log_id):
        """Get log by ID."""
        return await self._crud_service.get_log_by_id(log_id)

    async def get_application_log_by_id(self, log_id):
        """Get application log by ID - standardized method name."""
        return await self._crud_service.get_log_by_id(log_id)

    async def count_logs(self, *args, **kwargs):
        """Count logs with filtering."""
        return await self._crud_service.count_logs(*args, **kwargs)

    async def search_logs(self, *args, **kwargs):
        """Search logs."""
        return await self._crud_service.search_logs(*args, **kwargs)

    # --- Dashboard Services ---
    async def get_logs_stats(self):
        """Get dashboard statistics."""
        return await self._dashboard_service.get_logs_stats()

    async def get_log_trends(self, days=7):
        """Get log trends over time."""
        return await self._dashboard_service.get_log_trends(days)

    async def get_error_summary(self):
        """Get error-focused log summary."""
        return await self._dashboard_service.get_error_summary()
