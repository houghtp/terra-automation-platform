"""
User management service for tenant administrators.
Provides comprehensive user CRUD operations within tenant scope.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from app.features.administration.users.models import (
    User, UserCreate, UserUpdate, UserResponse, UserStats,
    UserDashboardStats, UserSearchFilter, UserStatus, UserRole
)
from app.features.core.security import hash_password, validate_password_complexity

logger = logging.getLogger(__name__)


class UserManagementService:
    """
    Comprehensive user management service for tenant administrators.

    Provides:
    - Full user CRUD operations within tenant scope
    - Password management and validation
    - Search and filtering
    - Statistics and reporting
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user within the tenant.

        Args:
            user_data: User creation data

        Returns:
            UserResponse: Created user information
        """
        try:
            # Validate password complexity
            password_errors = validate_password_complexity(user_data.password)
            if password_errors:
                error_msg = "Password validation failed: " + "; ".join(password_errors)
                raise ValueError(error_msg)

            # Check password confirmation
            if user_data.password != user_data.confirm_password:
                raise ValueError("Passwords do not match")

            # Check if user with this email already exists in tenant
            existing = await self.get_user_by_email(user_data.email)
            if existing:
                raise ValueError(f"User with email '{user_data.email}' already exists in this tenant")

            # Create user record
            user = User(
                name=user_data.name,
                email=user_data.email,
                hashed_password=hash_password(user_data.password),
                description=user_data.description,
                status=user_data.status.value,
                role=user_data.role.value,
                enabled=user_data.enabled,
                tags=user_data.tags,
                tenant_id=self.tenant_id
            )

            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)

            logger.info(f"Created user: {user.name} (ID: {user.id}) in tenant {self.tenant_id}")

            return self._user_to_response(user)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID within tenant scope."""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        return self._user_to_response(user)

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email within tenant scope."""
        stmt = select(User).where(
            and_(
                User.email == email,
                User.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        return self._user_to_response(user)

    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """Update user information within tenant scope."""
        try:
            stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Update fields if provided
            update_fields = user_data.model_dump(exclude_unset=True)

            for field, value in update_fields.items():
                if hasattr(user, field):
                    if field in ['status', 'role'] and hasattr(value, 'value'):
                        setattr(user, field, value.value)
                    else:
                        setattr(user, field, value)

            await self.db.flush()
            await self.db.refresh(user)

            logger.info(f"Updated user: {user.name} (ID: {user_id}) in tenant {self.tenant_id}")

            return self._user_to_response(user)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user {user_id}: {e}")
            raise

    async def update_user_field(self, user_id: str, field: str, value) -> Optional[UserResponse]:
        """Update a single field of a user within tenant scope."""
        try:
            stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            if hasattr(user, field) and field != 'hashed_password':
                setattr(user, field, value)
                await self.db.flush()
                await self.db.refresh(user)
                return self._user_to_response(user)

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user field {field} for {user_id}: {e}")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user within tenant scope.

        Args:
            user_id: User ID to delete

        Returns:
            bool: True if deleted successfully
        """
        try:
            stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return False

            await self.db.delete(user)
            await self.db.flush()

            logger.info(f"Deleted user: {user.name} (ID: {user_id}) from tenant {self.tenant_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise

    async def list_users(self, filters: Optional[UserSearchFilter] = None) -> List[UserResponse]:
        """List users within tenant with optional filtering."""
        try:
            stmt = select(User).where(User.tenant_id == self.tenant_id)

            # Apply filters if provided
            if filters:
                conditions = []

                if filters.search:
                    search_term = f"%{filters.search}%"
                    conditions.append(
                        or_(
                            User.name.ilike(search_term),
                            User.email.ilike(search_term),
                            User.description.ilike(search_term)
                        )
                    )

                if filters.status:
                    conditions.append(User.status == filters.status.value)

                if filters.role:
                    conditions.append(User.role == filters.role.value)

                if filters.enabled is not None:
                    conditions.append(User.enabled == filters.enabled)

                if filters.created_after:
                    conditions.append(User.created_at >= filters.created_after)

                if filters.created_before:
                    conditions.append(User.created_at <= filters.created_before)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

            # Apply ordering and pagination
            stmt = stmt.order_by(User.created_at.desc())

            if filters:
                stmt = stmt.offset(filters.offset).limit(filters.limit)

            result = await self.db.execute(stmt)
            users = result.scalars().all()

            return [self._user_to_response(user) for user in users]

        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise

    async def get_dashboard_stats(self) -> UserDashboardStats:
        """Get comprehensive dashboard statistics for user management."""
        try:
            # Total user counts by status
            status_counts = await self.db.execute(
                select(
                    User.status,
                    func.count(User.id)
                ).where(User.tenant_id == self.tenant_id).group_by(User.status)
            )
            status_map = dict(status_counts.fetchall())

            # Role distribution
            role_counts = await self.db.execute(
                select(
                    User.role,
                    func.count(User.id)
                ).where(User.tenant_id == self.tenant_id).group_by(User.role)
            )
            role_map = dict(role_counts.fetchall())

            # Recent users (last 5)
            recent_users_stmt = select(User).where(
                User.tenant_id == self.tenant_id
            ).order_by(
                User.created_at.desc()
            ).limit(5)
            recent_result = await self.db.execute(recent_users_stmt)
            recent_users = recent_result.scalars().all()

            recent_user_responses = [self._user_to_response(user) for user in recent_users]

            return UserDashboardStats(
                total_users=sum(status_map.values()),
                active_users=status_map.get("active", 0),
                inactive_users=status_map.get("inactive", 0),
                suspended_users=status_map.get("suspended", 0),
                users_by_role=role_map,
                recent_users=recent_user_responses
            )

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            raise

    async def get_available_tenants_for_user_forms(self) -> List[dict]:
        """Get available tenants for user form dropdowns - user slice owns this query."""
        # Query tenant table directly within user slice for form needs
        result = await self.db.execute(
            text("SELECT id, name, status FROM tenants WHERE status = 'active' ORDER BY name")
        )

        tenants = []
        for row in result:
            tenants.append({
                'id': str(row.id),
                'name': row.name,
                'status': row.status
            })

        return tenants

    def _user_to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            description=user.description,
            status=user.status,
            role=user.role,
            enabled=user.enabled,
            tags=user.tags or [],
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )