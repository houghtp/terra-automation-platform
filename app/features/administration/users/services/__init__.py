"""
Combined User Management Service that includes all service components.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .crud_services import UserCrudService
from .form_services import UserFormService
from .dashboard_services import UserDashboardService


class UserManagementService:
    """
    Comprehensive user management service for tenant administrators.

    Combines all service components:
    - CRUD operations (create, read, update, delete, list)
    - Form validation and tenant helpers
    - Dashboard statistics and analytics
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id

        # Initialize component services
        self._crud_service = UserCrudService(db_session, tenant_id)
        self._form_service = UserFormService(db_session, tenant_id)
        self._dashboard_service = UserDashboardService(db_session, tenant_id)

    # --- CRUD Operations ---
    async def create_user(self, user_data, target_tenant_id=None, created_by_user=None):
        """Create a new user."""
        return await self._crud_service.create_user(
            user_data,
            created_by_user=created_by_user,
            target_tenant_id=target_tenant_id
        )

    async def get_user_by_id(self, user_id):
        """Get user by ID."""
        return await self._crud_service.get_user_by_id(user_id)

    async def get_user_by_email(self, email):
        """Get user by email."""
        return await self._crud_service.get_user_by_email(email)

    async def update_user(self, user_id, user_data):
        """Update user."""
        return await self._crud_service.update_user(user_id, user_data)

    async def update_user_field(self, user_id, field, value):
        """Update a single user field."""
        return await self._crud_service.update_user_field(user_id, field, value)

    async def delete_user(self, user_id):
        """Delete user."""
        return await self._crud_service.delete_user(user_id)

    async def list_users(self, filters=None):
        """List users."""
        return await self._crud_service.list_users(filters)

    # --- Global Admin Methods ---
    async def update_user_field_global(self, user_id, field, value):
        """Update user field globally (global admin only)."""
        return await self._crud_service.update_user_field_global(user_id, field, value)

    async def update_user_global(self, user_id, user_data):
        """Update user globally (global admin only)."""
        return await self._crud_service.update_user_global(user_id, user_data)

    async def list_users_global(self, filters=None):
        """List users globally (global admin only)."""
        return await self._crud_service.list_users_global(filters)

    # --- Form Services ---
    async def get_available_tenants_for_user_forms(self):
        """Get available tenants for forms."""
        return await self._form_service.get_available_tenants_for_user_forms()

    # --- Dashboard Services ---
    async def get_dashboard_stats(self):
        """Get dashboard statistics."""
        return await self._dashboard_service.get_dashboard_stats()
