"""
Combined Secrets Management Service that includes all service components.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .crud_services import SecretsCrudService
from .dashboard_services import SecretsDashboardService
from .form_services import SecretsFormService


class SecretsManagementService:
    """
    Comprehensive secrets management service.

    Combines all service components:
    - CRUD operations for secure secrets management
    - Dashboard statistics and analytics
    - Encryption and access tracking
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id

        # Initialize component services
        self._crud_service = SecretsCrudService(db_session, tenant_id)
        self._dashboard_service = SecretsDashboardService(db_session, tenant_id)
        self._form_service = SecretsFormService(db_session, tenant_id)

    # --- CRUD Operations ---
    async def create_secret(self, *args, **kwargs):
        """Create a new secret with encryption."""
        return await self._crud_service.create_secret(*args, **kwargs)

    async def get_secret_by_id(self, secret_id):
        """Get secret by ID."""
        return await self._crud_service.get_secret_by_id(secret_id)

    async def get_secret_by_name(self, secret_name):
        """Get secret by name."""
        return await self._crud_service.get_secret_by_name(secret_name)

    async def list_secrets(self, *args, **kwargs):
        """List secrets with filtering."""
        return await self._crud_service.list_secrets(*args, **kwargs)

    async def update_secret(self, *args, **kwargs):
        """Update an existing secret."""
        return await self._crud_service.update_secret(*args, **kwargs)

    async def update_secret_field(self, *args, **kwargs):
        """Update a single field of a secret."""
        return await self._crud_service.update_secret_field(*args, **kwargs)

    async def delete_secret(self, *args, **kwargs):
        """Delete a secret (soft delete)."""
        return await self._crud_service.delete_secret(*args, **kwargs)

    async def secret_name_exists(self, *args, **kwargs):
        """Check if secret name exists."""
        return await self._crud_service.secret_name_exists(*args, **kwargs)

    async def count_secrets(self, *args, **kwargs):
        """Count secrets with filtering."""
        return await self._crud_service.count_secrets(*args, **kwargs)

    async def get_secret_value(self, *args, **kwargs):
        """Get decrypted secret value (use carefully)."""
        return await self._crud_service.get_secret_value(*args, **kwargs)

    # --- Dashboard Services ---
    async def get_secrets_stats(self):
        """Get dashboard statistics."""
        return await self._dashboard_service.get_secrets_stats()

    async def get_expiring_secrets(self, *args, **kwargs):
        """Get secrets expiring soon."""
        return await self._dashboard_service.get_expiring_secrets(*args, **kwargs)

    async def get_secrets_by_type_stats(self):
        """Get count of secrets by type."""
        return await self._dashboard_service.get_secrets_by_type_stats()

    async def get_access_summary(self):
        """Get access summary statistics."""
        return await self._dashboard_service.get_access_summary()

    # --- Form Services ---
    async def get_available_tenants_for_secrets_forms(self):
        """Get available tenants for forms."""
        return await self._form_service.get_available_tenants_for_secrets_forms()

    # --- Legacy Compatibility Methods ---
    async def _secret_name_exists(self, tenant_id: str, secret_name: str, exclude_id: Optional[int] = None):
        """Legacy method for compatibility."""
        return await self.secret_name_exists(secret_name, exclude_id)
