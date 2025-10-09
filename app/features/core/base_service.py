"""
Base service class for common service patterns across all slices.
"""

import logging
from typing import Optional, Dict, Any, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for models


class BaseService(Generic[T]):
    """
    Base service class that provides common functionality for all services.

    Provides:
    - Database session management
    - Tenant-scoped operations
    - Common error handling patterns
    - Logging setup
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        """
        Initialize base service with database session and tenant context.

        Args:
            db_session: AsyncSession for database operations
            tenant_id: Tenant ID for scoping operations (None or "global" for global admin access)
        """
        self.db = db_session
        # Treat "global" tenant_id the same as None for global admin access
        self.tenant_id = None if tenant_id == "global" else tenant_id
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_by_id(self, model_class: type[T], item_id: str) -> Optional[T]:
        """
        Get an item by ID within tenant scope.

        Args:
            model_class: SQLAlchemy model class
            item_id: ID of the item to retrieve

        Returns:
            Model instance or None if not found
        """
        try:
            if self.tenant_id is not None:
                stmt = select(model_class).where(
                    and_(
                        model_class.id == item_id,
                        model_class.tenant_id == self.tenant_id
                    )
                )
            else:
                # Global admin access - no tenant filtering
                stmt = select(model_class).where(model_class.id == item_id)

            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get {model_class.__name__} by ID {item_id}: {e}")
            raise

    async def delete_by_id(self, model_class: type[T], item_id: str) -> bool:
        """
        Delete an item by ID within tenant scope.

        Args:
            model_class: SQLAlchemy model class
            item_id: ID of the item to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            if self.tenant_id is not None:
                stmt = select(model_class).where(
                    and_(
                        model_class.id == item_id,
                        model_class.tenant_id == self.tenant_id
                    )
                )
            else:
                # Global admin access - no tenant filtering
                stmt = select(model_class).where(model_class.id == item_id)

            result = await self.db.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                return False

            await self.db.delete(item)
            await self.db.flush()

            tenant_info = f"from tenant {self.tenant_id}" if self.tenant_id else "(global admin)"
            self.logger.info(f"Deleted {model_class.__name__} (ID: {item_id}) {tenant_info}")
            return True

        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Failed to delete {model_class.__name__} {item_id}: {e}")
            raise

    async def count_by_tenant(self, model_class: type[T]) -> int:
        """
        Count items for the current tenant.

        Args:
            model_class: SQLAlchemy model class

        Returns:
            Count of items in tenant
        """
        try:
            from sqlalchemy import func
            if self.tenant_id is not None:
                stmt = select(func.count(model_class.id)).where(
                    model_class.tenant_id == self.tenant_id
                )
            else:
                # Global admin access - count all
                stmt = select(func.count(model_class.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            tenant_info = self.tenant_id if self.tenant_id else "all tenants"
            self.logger.error(f"Failed to count {model_class.__name__} for {tenant_info}: {e}")
            raise

    def log_operation(self, operation: str, details: str = ""):
        """
        Log service operations with consistent format.

        Args:
            operation: Operation name (create, update, delete, etc.)
            details: Additional details
        """
        service_name = self.__class__.__name__
        message = f"[{service_name}] {operation}"
        if details:
            message += f": {details}"
        tenant_info = f"tenant: {self.tenant_id}" if self.tenant_id else "global admin"
        message += f" ({tenant_info})"

        self.logger.info(message)

    async def handle_service_error(self, operation: str, error: Exception, item_id: str = None):
        """
        Handle service errors with consistent logging and rollback.

        Args:
            operation: Operation that failed
            error: Exception that occurred
            item_id: ID of item involved (optional)
        """
        await self.db.rollback()

        error_details = f"{operation}"
        if item_id:
            error_details += f" for item {item_id}"
        tenant_info = f"in tenant {self.tenant_id}" if self.tenant_id else "(global admin)"
        error_details += f" {tenant_info}: {error}"

        self.logger.error(error_details)
        raise error

    def create_tenant_filter(self, model_class: type[T]):
        """
        Create a tenant filter condition for queries.

        Args:
            model_class: SQLAlchemy model class

        Returns:
            SQLAlchemy filter condition or True for global admin
        """
        if self.tenant_id is not None:
            return model_class.tenant_id == self.tenant_id
        else:
            # Global admin - no tenant filtering
            return True


class TenantScopedCRUDService(BaseService[T]):
    """
    Extended base service with common CRUD operations for tenant-scoped models.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str], model_class: type[T]):
        """
        Initialize CRUD service with model class.

        Args:
            db_session: AsyncSession for database operations
            tenant_id: Tenant ID for scoping operations (None for global admin access)
            model_class: SQLAlchemy model class this service operates on
        """
        super().__init__(db_session, tenant_id)
        self.model_class = model_class

    async def get_by_id(self, item_id: str) -> Optional[T]:
        """Get item by ID using the service's model class."""
        return await super().get_by_id(self.model_class, item_id)

    async def delete_by_id(self, item_id: str) -> bool:
        """Delete item by ID using the service's model class."""
        return await super().delete_by_id(self.model_class, item_id)

    async def count_all(self) -> int:
        """Count all items for this service's model class."""
        return await super().count_by_tenant(self.model_class)

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[T]:
        """
        List all items for the current tenant with pagination.

        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of model instances
        """
        try:
            tenant_filter = self.create_tenant_filter(self.model_class)
            if tenant_filter is not True:  # Only apply filter if not global admin
                stmt = select(self.model_class).where(tenant_filter)
            else:
                stmt = select(self.model_class)

            stmt = stmt.order_by(
                self.model_class.created_at.desc()
            ).offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            self.logger.error(f"Failed to list {self.model_class.__name__}: {e}")
            raise