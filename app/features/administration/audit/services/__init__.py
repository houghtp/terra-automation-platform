"""
Combined Audit Management Service that includes all service components.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .crud_services import AuditCrudService
from .dashboard_services import AuditDashboardService


class AuditManagementService:
    """
    Comprehensive audit management service.

    Combines all service components:
    - CRUD operations (read-only for audit integrity)
    - Dashboard statistics and analytics
    - Timeline and security summaries
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id

        # Initialize component services
        self._crud_service = AuditCrudService(db_session, tenant_id)
        self._dashboard_service = AuditDashboardService(db_session, tenant_id)

    # --- CRUD Operations ---
    async def get_audit_logs(self, *args, **kwargs):
        """Get audit logs with filtering."""
        return await self._crud_service.get_audit_logs(*args, **kwargs)

    async def get_audit_log_by_id(self, log_id):
        """Get audit log by ID."""
        return await self._crud_service.get_audit_log_by_id(log_id)

    async def search_audit_logs(self, search_term, limit=50):
        """Search audit logs."""
        return await self._crud_service.search_audit_logs(search_term, limit)

    async def count_audit_logs(self, *args, **kwargs):
        """Count audit logs with filtering."""
        return await self._crud_service.count_audit_logs(*args, **kwargs)

    # --- Dashboard Services ---
    async def get_audit_stats(self):
        """Get dashboard statistics."""
        return await self._dashboard_service.get_audit_stats()

    async def get_audit_timeline(self, *args, **kwargs):
        """Get audit activity timeline."""
        return await self._dashboard_service.get_audit_timeline(*args, **kwargs)

    async def get_security_summary(self):
        """Get security-focused audit summary."""
        return await self._dashboard_service.get_security_summary()
