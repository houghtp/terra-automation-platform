"""
Combined SMTP Configuration Service that includes all service components.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .crud_services import SMTPCrudService
from .form_services import SMTPFormService
from .dashboard_services import SMTPDashboardService


class SMTPConfigurationService:
    """
    Comprehensive SMTP configuration management service for tenant administrators.

    Combines all service components:
    - CRUD operations (create, read, update, delete, list)
    - Form validation and testing helpers
    - Dashboard statistics and analytics
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id

        # Initialize component services
        self._crud_service = SMTPCrudService(db_session, tenant_id)
        self._form_service = SMTPFormService(db_session, tenant_id)
        self._dashboard_service = SMTPDashboardService(db_session, tenant_id)

    # --- CRUD Operations ---
    async def create_smtp_configuration(self, config_data, created_by_user=None, target_tenant_id=None):
        """Create a new SMTP configuration."""
        return await self._crud_service.create_smtp_configuration(config_data, created_by_user, target_tenant_id)

    async def get_configuration_by_id(self, config_id):
        """Get SMTP configuration by ID."""
        return await self._crud_service.get_configuration_by_id(config_id)

    async def get_configuration_by_name(self, name):
        """Get SMTP configuration by name."""
        return await self._crud_service.get_configuration_by_name(name)

    async def update_smtp_configuration(self, config_id, config_data, updated_by_user=None):
        """Update SMTP configuration."""
        return await self._crud_service.update_smtp_configuration(config_id, config_data, updated_by_user)

    async def update_smtp_field(self, config_id, field, value, updated_by_user=None):
        """Update a single SMTP configuration field."""
        return await self._crud_service.update_smtp_field(config_id, field, value, updated_by_user)

    async def delete_smtp_configuration(self, config_id):
        """Delete SMTP configuration."""
        return await self._crud_service.delete_smtp_configuration(config_id)

    async def list_smtp_configurations(self, filters=None):
        """List SMTP configurations."""
        return await self._crud_service.list_smtp_configurations(filters)

    async def activate_smtp_configuration(self, config_id):
        """Activate SMTP configuration."""
        return await self._crud_service.activate_smtp_configuration(config_id)

    async def deactivate_smtp_configuration(self, config_id):
        """Deactivate SMTP configuration."""
        return await self._crud_service.deactivate_smtp_configuration(config_id)

    # --- Global Admin Methods ---
    async def update_smtp_field_global(self, config_id, field, value, updated_by_user=None):
        """Update SMTP configuration field globally (global admin only)."""
        return await self._crud_service.update_smtp_field_global(config_id, field, value, updated_by_user)

    async def update_smtp_configuration_global(self, config_id, config_data, updated_by_user=None):
        """Update SMTP configuration globally (global admin only)."""
        return await self._crud_service.update_smtp_configuration_global(config_id, config_data, updated_by_user)

    async def list_smtp_configurations_global(self, filters=None):
        """List SMTP configurations globally (global admin only)."""
        return await self._crud_service.list_smtp_configurations_global(filters)

    # --- Form Services ---
    async def test_smtp_configuration(self, config_id, test_email=None):
        """Test SMTP configuration."""
        return await self._form_service.test_smtp_configuration(config_id, test_email)

    async def validate_smtp_configuration(self, config_data):
        """Validate SMTP configuration data."""
        return await self._form_service.validate_smtp_configuration(config_data)

    async def get_available_tenants_for_smtp_forms(self):
        """Get available tenants for SMTP forms."""
        return await self._form_service.get_available_tenants_for_smtp_forms()

    # --- Dashboard Services ---
    async def get_dashboard_stats(self):
        """Get dashboard statistics."""
        return await self._dashboard_service.get_dashboard_stats()