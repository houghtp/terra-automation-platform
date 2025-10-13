"""
Global admin bootstrap system for multi-tenant applications.
Creates and manages the initial global administrator account.
"""

import logging
import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.auth.models import User
from app.features.auth.services import AuthService
from app.features.core.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)

# Global admin configuration
GLOBAL_TENANT_ID = "global"
GLOBAL_ADMIN_ROLE = "global_admin"
DEFAULT_GLOBAL_ADMIN_EMAIL = "admin@system.local"


class GlobalAdminBootstrap:
    """
    Bootstrap system for creating and managing global administrators.

    Global admins have special privileges:
    - Can create and manage tenants
    - Access to all system-wide administrative functions
    - Special tenant_id "global" for system-level operations
    """

    def __init__(self):
        # Don't instantiate AuthService here - it needs a db_session
        # We'll create it on-demand in methods that need it
        pass

    async def ensure_global_admin_exists(self, db: AsyncSession) -> bool:
        """
        Ensure at least one global admin exists in the system.
        Creates default admin if none exists.

        Returns:
            bool: True if global admin exists or was created successfully
        """
        try:
            # Check if any global admin exists
            global_admin = await self.get_any_global_admin(db)

            if global_admin:
                logger.info(f"Global admin exists: {global_admin.email}")
                return True

            # No global admin exists, create default one
            logger.warning("No global admin found. Creating default global admin.")
            return await self.create_default_global_admin(db)

        except Exception as e:
            logger.error(f"Failed to ensure global admin exists: {e}")
            return False

    async def get_any_global_admin(self, db: AsyncSession) -> Optional[User]:
        """Get any global admin user from the system."""
        stmt = select(User).where(
            User.tenant_id == GLOBAL_TENANT_ID,
            User.role == GLOBAL_ADMIN_ROLE,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_global_admin_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get specific global admin by email."""
        stmt = select(User).where(
            User.email == email,
            User.tenant_id == GLOBAL_TENANT_ID,
            User.role == GLOBAL_ADMIN_ROLE,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_default_global_admin(self, db: AsyncSession) -> bool:
        """
        Create the default global administrator account.
        Uses secure secrets manager for credential handling.
        """
        try:
            # Use secrets manager for secure credential handling
            secrets_manager = get_secrets_manager()

            admin_email = await secrets_manager.get_secret("GLOBAL_ADMIN_EMAIL")
            if not admin_email:
                admin_email = DEFAULT_GLOBAL_ADMIN_EMAIL

            admin_password = await secrets_manager.get_secret("GLOBAL_ADMIN_PASSWORD")
            admin_name = await secrets_manager.get_secret("GLOBAL_ADMIN_NAME")
            if not admin_name:
                admin_name = "System Administrator"

            if not admin_password:
                # Generate a secure random password if none provided
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                admin_password = ''.join(secrets.choice(alphabet) for _ in range(20))

                # Store generated password in secrets manager
                await secrets_manager.set_secret("GLOBAL_ADMIN_PASSWORD", admin_password)

                logger.warning("Auto-generated secure password for global admin account")
                logger.warning("Password has been stored securely - check your secrets backend")
                logger.warning("For production, set GLOBAL_ADMIN_PASSWORD via your secrets management system!")

            # Create global admin user using AuthService
            auth_service = AuthService(db)
            admin_user = await auth_service.create_user(
                session=db,
                email=admin_email,
                password=admin_password,
                tenant_id=GLOBAL_TENANT_ID,
                role=GLOBAL_ADMIN_ROLE,
                name=admin_name
            )

            # Update user with additional fields for consistency
            admin_user.name = admin_name
            admin_user.description = "Global system administrator with tenant management privileges"
            admin_user.status = "active"
            admin_user.enabled = True

            await db.commit()

            logger.info(f"✅ Global admin created successfully: {admin_email}")
            logger.info("🔑 Global admin password has been stored securely")
            logger.warning("⚠️  Please change the default password immediately!")

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create global admin: {e}")
            return False

    async def create_global_admin(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        name: str = "Global Administrator"
    ) -> Optional[User]:
        """
        Create a new global administrator account.

        Args:
            db: Database session
            email: Admin email address
            password: Admin password (will be hashed)
            name: Admin display name

        Returns:
            Optional[User]: Created admin user or None if failed
        """
        try:
            # Check if admin with this email already exists
            existing = await self.get_global_admin_by_email(db, email)
            if existing:
                logger.warning(f"Global admin already exists: {email}")
                return existing

            # Create the global admin user using AuthService
            auth_service = AuthService(db)
            admin_user = await auth_service.create_user(
                session=db,
                email=email,
                password=password,
                tenant_id=GLOBAL_TENANT_ID,
                role=GLOBAL_ADMIN_ROLE,
                name=name
            )

            # Set additional fields
            admin_user.name = name
            admin_user.description = "Global system administrator"
            admin_user.status = "active"
            admin_user.enabled = True

            await db.commit()

            logger.info(f"✅ Global admin created: {email}")
            return admin_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create global admin {email}: {e}")
            return None

    async def list_global_admins(self, db: AsyncSession) -> list[User]:
        """List all global administrators."""
        stmt = select(User).where(
            User.tenant_id == GLOBAL_TENANT_ID,
            User.role == GLOBAL_ADMIN_ROLE,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_global_admin(self, db: AsyncSession, admin_id: int) -> bool:
        """
        Deactivate a global admin (but prevent deactivating the last one).

        Args:
            db: Database session
            admin_id: Admin user ID to deactivate

        Returns:
            bool: True if deactivated successfully
        """
        try:
            # Ensure we don't deactivate the last global admin
            active_admins = await self.list_global_admins(db)
            if len(active_admins) <= 1:
                logger.error("Cannot deactivate the last global administrator")
                return False

            # Find and deactivate the specified admin
            admin = await db.get(User, admin_id)
            if not admin or admin.tenant_id != GLOBAL_TENANT_ID or admin.role != GLOBAL_ADMIN_ROLE:
                logger.error(f"Global admin not found: {admin_id}")
                return False

            admin.is_active = False
            await db.commit()

            logger.info(f"Global admin deactivated: {admin.email}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to deactivate global admin {admin_id}: {e}")
            return False

    def is_global_admin(self, user: User) -> bool:
        """Check if a user is a global administrator."""
        return (
            user.tenant_id == GLOBAL_TENANT_ID and
            user.role == GLOBAL_ADMIN_ROLE and
            user.is_active
        )

    async def validate_system_setup(self, db: AsyncSession) -> dict:
        """
        Validate the global admin system setup.

        Returns:
            dict: System validation status and recommendations
        """
        try:
            global_admins = await self.list_global_admins(db)

            validation = {
                "status": "healthy" if global_admins else "critical",
                "global_admin_count": len(global_admins),
                "global_admins": [
                    {
                        "id": admin.id,
                        "email": admin.email,
                        "name": admin.name,
                        "created_at": admin.created_at
                    }
                    for admin in global_admins
                ],
                "recommendations": []
            }

            # Add recommendations based on findings
            if not global_admins:
                validation["recommendations"].append("Create at least one global administrator")
            elif len(global_admins) == 1:
                validation["recommendations"].append("Consider creating backup global administrator")

            # Check for default credentials
            for admin in global_admins:
                if admin.email == DEFAULT_GLOBAL_ADMIN_EMAIL:
                    validation["recommendations"].append("Change default admin email address")

            return validation

        except Exception as e:
            logger.error(f"System validation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recommendations": ["Fix system validation errors"]
            }


# Global instance for easy access
global_admin_bootstrap = GlobalAdminBootstrap()
