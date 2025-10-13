"""
User CRUD services implementing FastAPI/SQLAlchemy best practices.
This is the GOLD STANDARD implementation for all other slices.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.features.administration.users.models import (
    User, UserCreate, UserUpdate, UserResponse, UserSearchFilter, UserStatus, UserRole
)
from app.features.administration.tenants.db_models import Tenant
from app.features.core.security import hash_password, validate_password_complexity
from app.features.core.audit_mixin import AuditContext

logger = get_logger(__name__)


class UserCrudService(BaseService[User]):
    """
    🏆 GOLD STANDARD User CRUD operations.

    Demonstrates FastAPI/SQLAlchemy best practices:
    - Enhanced BaseService inheritance
    - Centralized imports and utilities
    - Proper error handling and logging
    - Type-safe query building
    - Consistent validation patterns
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def create_user(self, user_data: UserCreate, created_by_user=None, target_tenant_id: Optional[str] = None) -> UserResponse:
        """
        Create new user with validation and proper error handling.

        Args:
            user_data: User creation data with validation
            created_by_user: User object who created the user (for audit trail)
            target_tenant_id: Optional tenant ID for global admin cross-tenant creation

        Returns:
            UserResponse: Created user information

        Raises:
            ValueError: If validation fails or user already exists
        """
        try:
            effective_tenant_id = target_tenant_id or self.tenant_id

            # Use separated validation method
            await self._validate_user_creation(user_data, effective_tenant_id)

            # Create audit context
            audit_ctx = AuditContext.from_user(created_by_user) if created_by_user else None

            # Create user using consistent patterns
            user = User(
                name=user_data.name,
                email=user_data.email,
                hashed_password=hash_password(user_data.password),
                description=user_data.description,
                status=user_data.status.value,
                role=user_data.role.value,
                enabled=user_data.enabled,
                tags=user_data.tags,
                tenant_id=effective_tenant_id
            )

            # Set audit information with explicit timestamps
            if audit_ctx:
                user.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            user.created_at = datetime.now()
            user.updated_at = datetime.now()

            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)

            # Use enhanced logging pattern
            self.log_operation("user_creation", {
                "user_id": user.id,
                "user_email": user.email,
                "target_tenant": effective_tenant_id
            })

            return self._to_response(user)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to create user - IntegrityError",
                        error=error_str,
                        email=user_data.email,
                        target_tenant=target_tenant_id)

            if "unique constraint" in error_str.lower():
                raise ValueError(f"User with email '{user_data.email}' already exists in this tenant")
            else:
                raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.handle_error("create_user", e,
                                  email=user_data.email,
                                  target_tenant=target_tenant_id)

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID using enhanced BaseService method."""
        user = await self.get_by_id(User, user_id)
        return self._to_response(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Get user by email within tenant scope using query builders.

        Args:
            email: User's email address

        Returns:
            UserResponse or None if not found
        """
        try:
            stmt = self.create_base_query(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            return self._to_response(user) if user else None
        except Exception as e:
            self.logger.error("Failed to get user by email",
                            email=email, error=str(e))
            return None

    async def update_user(self, user_id: str, user_data: UserUpdate, updated_by_user=None) -> Optional[UserResponse]:
        """
        Update user with enhanced error handling and logging.

        Args:
            user_id: User ID to update
            user_data: Updated user data
            updated_by_user: User object who updated the user (for audit trail)

        Returns:
            Updated UserResponse or None if not found
        """
        try:
            user = await self.get_by_id(User, user_id)
            if not user:
                return None

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            # Apply updates using helper method
            self._apply_user_updates(user, user_data)

            # Set audit information with explicit timestamp
            if audit_ctx:
                user.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            user.updated_at = datetime.now()

            await self.db.flush()
            await self.db.refresh(user)

            self.log_operation("user_update", {
                "user_id": user_id,
                "updated_fields": self._get_updated_fields(user_data)
            })

            return self._to_response(user)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to update user - IntegrityError",
                        error=error_str,
                        user_id=user_id)
            raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.handle_error("update_user", e, user_id=user_id)

    async def update_user_field(self, user_id: str, field: str, value, updated_by_user=None) -> Optional[UserResponse]:
        """
        Update a single field for user within tenant scope.

        Args:
            user_id: User ID to update
            field: Field name to update
            value: New value for the field
            updated_by_user: User object who updated the user (for audit trail)

        Returns:
            Updated UserResponse or None if not found
        """
        try:
            user = await self.get_by_id(User, user_id)
            if not user:
                return None

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            # Validate and update the field
            if hasattr(user, field):
                setattr(user, field, value)

                # Set audit information with explicit timestamp
                if audit_ctx:
                    user.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
                user.updated_at = datetime.now()

                await self.db.flush()
                await self.db.refresh(user)

                self.log_operation("user_field_update", {
                    "user_id": user_id,
                    "field": field,
                    "value": str(value)
                })
                return self._to_response(user)
            else:
                raise ValueError(f"Invalid field: {field}")

        except Exception as e:
            await self.handle_error("update_user_field", e,
                                  user_id=user_id, field=field)

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user within tenant scope.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            user = await self.get_by_id(User, user_id)
            if not user:
                return False

            await self.db.delete(user)
            self.log_operation("user_deletion", {"user_id": user_id})
            return True

        except Exception as e:
            await self.handle_error("delete_user", e, user_id=user_id)
            return False

    async def list_users(self, filters: Optional[UserSearchFilter] = None) -> List[UserResponse]:
        """
        List users using enhanced BaseService query patterns.

        Args:
            filters: Optional search and filter criteria

        Returns:
            List of UserResponse objects
        """
        try:
            # Use BaseService query builder
            stmt = self.create_base_query(User)

            # Apply search filters using BaseService method
            if filters and filters.search:
                stmt = self.apply_search_filters(
                    stmt, User, filters.search, ['name', 'email', 'description']
                )

            # Apply specific filters
            if filters:
                if filters.status:
                    stmt = stmt.where(User.status == filters.status.value)
                if filters.role:
                    stmt = stmt.where(User.role == filters.role.value)
                if filters.enabled is not None:
                    stmt = stmt.where(User.enabled == filters.enabled)

            stmt = stmt.order_by(desc(User.created_at))
            result = await self.db.execute(stmt)
            users = result.scalars().all()

            return [self._to_response(user) for user in users]

        except Exception as e:
            await self.handle_error("list_users", e, filters=filters)

    # --- Global Admin Methods ---

    async def update_user_field_global(self, user_id: str, field: str, value, updated_by_user=None) -> Optional[UserResponse]:
        """Update a single field for user across all tenants (global admin only)."""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            if hasattr(user, field):
                setattr(user, field, value)

                # Set audit information with explicit timestamp
                if audit_ctx:
                    user.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
                user.updated_at = datetime.now()

                await self.db.flush()
                await self.db.refresh(user)

                self.log_operation("user_field_update_global", {
                    "user_id": user_id,
                    "field": field
                })
                return self._to_response(user)
            else:
                raise ValueError(f"Invalid field: {field}")

        except Exception as e:
            logger.error("Failed to update user field globally", error=str(e), user_id=user_id, field=field)
            raise

    async def update_user_global(self, user_id: str, user_data: UserUpdate, updated_by_user=None) -> Optional[UserResponse]:
        """Update user across all tenants (global admin only)."""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            # Update fields if provided (same logic as regular update)
            if user_data.name is not None:
                user.name = user_data.name
            if user_data.email is not None:
                user.email = user_data.email
            if user_data.description is not None:
                user.description = user_data.description
            if user_data.status is not None:
                user.status = user_data.status.value
            if user_data.role is not None:
                user.role = user_data.role.value
            if user_data.enabled is not None:
                user.enabled = user_data.enabled
            if user_data.tags is not None:
                user.tags = user_data.tags

            # Set audit information with explicit timestamp
            if audit_ctx:
                user.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            user.updated_at = datetime.now()

            await self.db.flush()
            await self.db.refresh(user)

            self.log_operation("user_update_global", {"user_id": user_id})
            return self._to_response(user)

        except Exception as e:
            logger.error("Failed to update user globally", error=str(e), user_id=user_id)
            raise

    async def list_users_global(self, filters: Optional[UserSearchFilter] = None) -> List[Dict[str, Any]]:
        """
        List users across tenants using enhanced BaseService patterns.
        Global admin only - uses tenant join query builder.
        """
        try:
            # Use BaseService tenant join query builder
            stmt = self.create_tenant_join_query(User)

            # Apply filters using BaseService methods
            if filters:
                if filters.search:
                    stmt = self.apply_search_filters(
                        stmt, User, filters.search, ['name', 'email']
                    )
                if filters.status:
                    stmt = stmt.where(User.status == filters.status.value)
                if filters.role:
                    stmt = stmt.where(User.role == filters.role.value)
                if filters.enabled is not None:
                    stmt = stmt.where(User.enabled == filters.enabled)

            stmt = stmt.order_by(desc(User.created_at))
            result = await self.db.execute(stmt)

            # Convert results using helper method
            return self._process_global_user_results(result)

        except Exception as e:
            await self.handle_error("list_users_global", e, filters=filters)

    # === 🏆 GOLD STANDARD HELPER METHODS ===

    async def _validate_user_creation(self, user_data: UserCreate, tenant_id: str) -> None:
        """
        Comprehensive user creation validation.
        Separated for reusability and testability.
        """
        # Password validation
        password_errors = validate_password_complexity(user_data.password)
        if password_errors:
            raise ValueError(f"Password validation failed: {'; '.join(password_errors)}")

        if user_data.password != user_data.confirm_password:
            raise ValueError("Passwords do not match")

        # Email uniqueness check using BaseService method
        if await self.exists_by_field(User, 'email', user_data.email):
            raise ValueError(f"User with email '{user_data.email}' already exists in this tenant")

    def _apply_user_updates(self, user: User, user_data: UserUpdate) -> None:
        """
        Apply user updates with consistent patterns.
        Centralized update logic for maintainability.
        """
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.description is not None:
            user.description = user_data.description
        if user_data.status is not None:
            user.status = user_data.status.value
        if user_data.role is not None:
            user.role = user_data.role.value
        if user_data.enabled is not None:
            user.enabled = user_data.enabled
        if user_data.tags is not None:
            user.tags = user_data.tags

    def _get_updated_fields(self, user_data: UserUpdate) -> List[str]:
        """Get list of fields being updated for logging."""
        updated_fields = []
        if user_data.name is not None:
            updated_fields.append('name')
        if user_data.email is not None:
            updated_fields.append('email')
        if user_data.description is not None:
            updated_fields.append('description')
        if user_data.status is not None:
            updated_fields.append('status')
        if user_data.role is not None:
            updated_fields.append('role')
        if user_data.enabled is not None:
            updated_fields.append('enabled')
        if user_data.tags is not None:
            updated_fields.append('tags')
        return updated_fields

    def _process_global_user_results(self, result) -> List[Dict[str, Any]]:
        """
        Process global user query results into consistent format.
        Centralized result processing for maintainability.
        """
        users_list = []
        for row in result:
            user = row[0]  # User object
            tenant_name = getattr(row, 'tenant_name', 'Unknown')

            user_dict = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "description": user.description,
                "status": user.status,
                "role": user.role,
                "enabled": user.enabled,
                "tags": user.tags or [],
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "tenant_id": user.tenant_id,
                "tenant_name": tenant_name or "Unknown"
            }
            users_list.append(user_dict)
        return users_list

    def _to_response(self, user: User) -> UserResponse:
        """
        Convert User model to UserResponse with consistent patterns.
        🏆 GOLD STANDARD response mapping.
        """
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            description=user.description,
            status=user.status,  # Keep as string, not enum
            role=user.role,      # Keep as string, not enum
            enabled=user.enabled,
            tags=user.tags or [],
            is_active=user.is_active,  # Add missing field
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
            tenant_id=user.tenant_id
        )
