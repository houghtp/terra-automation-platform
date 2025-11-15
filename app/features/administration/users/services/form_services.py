"""
User form services implementing FastAPI/SQLAlchemy best practices.
🏆 GOLD STANDARD form handling and validation patterns.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.tenants.db_models import Tenant
from app.features.administration.users.schemas import User, UserStatus, UserRole

logger = structlog.get_logger(__name__)


class UserFormService(BaseService[User]):
    """
    🏆 GOLD STANDARD form service implementation.

    Demonstrates:
    - Enhanced BaseService inheritance for forms
    - Type-safe query building
    - Proper error handling and logging
    - Reusable form helper methods
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def get_available_tenants_for_user_forms(self) -> List[Dict[str, Any]]:
        """
        Get active tenants for form dropdowns using enhanced query patterns.
        Global admin only - uses proper tenant querying.

        Returns:
            List of tenant dictionaries with id and name
        """
        try:
            stmt = select(
                Tenant.id,
                Tenant.name
            ).where(
                Tenant.status == 'active'
            ).order_by(Tenant.name)

            result = await self.db.execute(stmt)
            tenants = result.fetchall()

            tenant_list = [
                {"id": str(tenant.id), "name": tenant.name}
                for tenant in tenants
            ]

            self.log_operation("get_available_tenants", {
                "tenant_count": len(tenant_list)
            })

            return tenant_list

        except Exception as e:
            await self.handle_error("get_available_tenants", e)

    async def get_form_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all form options needed for user forms.
        Centralized form data retrieval for consistency.

        Returns:
            Dictionary with all form options (statuses, roles, tenants)
        """
        try:
            form_options = {
                "statuses": self._get_status_options(),
                "roles": self._get_role_options(),
                "tenants": []
            }

            # Add tenants for global admin
            if self.tenant_id is None:
                form_options["tenants"] = await self.get_available_tenants_for_user_forms()

            return form_options

        except Exception as e:
            await self.handle_error("get_form_options", e)

    async def validate_user_email_availability(self, email: str,
                                             exclude_user_id: Optional[str] = None) -> bool:
        """
        Validate email availability within tenant scope.

        Args:
            email: Email to check
            exclude_user_id: User ID to exclude (for updates)

        Returns:
            True if email is available, False if taken
        """
        try:
            stmt = self.create_base_query(User).where(User.email == email)

            # Exclude current user if updating
            if exclude_user_id:
                stmt = stmt.where(User.id != exclude_user_id)

            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            is_available = existing_user is None

            self.log_operation("validate_email_availability", {
                "email": email,
                "available": is_available,
                "exclude_user": exclude_user_id
            })

            return is_available

        except Exception as e:
            await self.handle_error("validate_email_availability", e,
                                  email=email, exclude_user_id=exclude_user_id)

    async def get_user_form_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete form data for user creation/editing.
        Combines user data (if editing) with form options.

        Args:
            user_id: User ID if editing, None if creating

        Returns:
            Complete form data dictionary
        """
        try:
            form_data = {
                "user": None,
                "options": await self.get_form_options(),
                "is_editing": user_id is not None
            }

            # Get user data if editing
            if user_id:
                user = await self.get_by_id(User, user_id)
                if user:
                    form_data["user"] = {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "description": user.description,
                        "status": user.status,
                        "role": user.role,
                        "enabled": user.enabled,
                        "tags": user.tags or [],
                        "tenant_id": user.tenant_id
                    }

            self.log_operation("get_user_form_data", {
                "user_id": user_id,
                "is_editing": form_data["is_editing"]
            })

            return form_data

        except Exception as e:
            await self.handle_error("get_user_form_data", e, user_id=user_id)

    # === HELPER METHODS ===

    def _get_status_options(self) -> List[Dict[str, Any]]:
        """Get available user status options."""
        return [
            {"value": status.value, "label": status.value.title()}
            for status in UserStatus
        ]

    def _get_role_options(self) -> List[Dict[str, Any]]:
        """Get available user role options."""
        return [
            {"value": role.value, "label": role.value.replace('_', ' ').title()}
            for role in UserRole
        ]
