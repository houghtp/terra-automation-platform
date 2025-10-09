"""Enhanced BaseService with common query patterns and utilities."""

from typing import Any, Dict, List, Optional, Type, Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.sqlalchemy_imports import *

T = TypeVar('T')
from app.features.core.database import get_async_session
from app.features.administration.tenants.db_models import Tenant


class BaseService(Generic[T]):
    """
    Enhanced base service with common patterns for FastAPI/SQLAlchemy.

    Provides:
    - Standardized database operations
    - Tenant-scoped queries
    - Common query builders
    - Type-safe operations
    - Consistent error handling
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        """Initialize service with database session and tenant context."""
        self.db = db_session
        self.tenant_id = None if tenant_id == "global" else tenant_id
        self.logger = get_logger(self.__class__.__name__)

    # === QUERY BUILDERS ===

    def create_base_query(self, model_class: type[T]) -> Select:
        """Create base SELECT query with tenant filtering."""
        stmt = select(model_class)
        if self.tenant_id is not None and hasattr(model_class, 'tenant_id'):
            stmt = stmt.where(model_class.tenant_id == self.tenant_id)
        return stmt

    def create_tenant_join_query(self, model_class: type[T]) -> Select:
        """
        Create query with tenant information join.
        Uses proper type casting for tenant_id (String) -> tenants.id (Integer) join.
        """
        if not hasattr(model_class, 'tenant_id'):
            raise ValueError(f"Model {model_class.__name__} does not have tenant_id field")

        return select(
            model_class,
            Tenant.name.label('tenant_name'),
            Tenant.status.label('tenant_status')
        ).outerjoin(
            Tenant, model_class.tenant_id == cast(Tenant.id, String)
        )

    def apply_search_filters(self, stmt: Select, model_class: type[T],
                           search_term: str, search_fields: List[str]) -> Select:
        """Apply search filters to multiple fields."""
        if not search_term or not search_fields:
            return stmt

        search_pattern = f"%{search_term}%"
        conditions = []

        for field_name in search_fields:
            if hasattr(model_class, field_name):
                field = getattr(model_class, field_name)
                conditions.append(field.ilike(search_pattern))

        if conditions:
            stmt = stmt.where(or_(*conditions))

        return stmt

    # === CRUD OPERATIONS ===

    async def get_by_id(self, model_class: type[T], item_id: str,
                       load_relationships: List[str] = None) -> Optional[T]:
        """Get item by ID with optional relationship loading."""
        try:
            stmt = self.create_base_query(model_class).where(model_class.id == item_id)

            # Add relationship loading
            if load_relationships:
                for rel in load_relationships:
                    if hasattr(model_class, rel):
                        stmt = stmt.options(selectinload(getattr(model_class, rel)))

            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error("Failed to get item by ID",
                            model=model_class.__name__, item_id=item_id, error=str(e))
            raise

    async def list_with_pagination(self, model_class: type[T],
                                 limit: int = 50, offset: int = 0,
                                 order_by: str = 'created_at',
                                 order_desc: bool = True) -> List[T]:
        """List items with pagination and ordering."""
        try:
            stmt = self.create_base_query(model_class)

            # Apply ordering
            if hasattr(model_class, order_by):
                order_field = getattr(model_class, order_by)
                if order_desc:
                    stmt = stmt.order_by(desc(order_field))
                else:
                    stmt = stmt.order_by(asc(order_field))

            stmt = stmt.offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            self.logger.error("Failed to list items",
                            model=model_class.__name__, error=str(e))
            raise

    async def count_total(self, model_class: type[T], filters=None) -> int:
        """Count total items with optional filtering."""
        try:
            stmt = select(func.count(model_class.id))

            if self.tenant_id is not None and hasattr(model_class, 'tenant_id'):
                stmt = stmt.where(model_class.tenant_id == self.tenant_id)

            # Apply additional filters if provided
            if filters:
                # Implement filter application based on your filter objects
                pass

            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            self.logger.error("Failed to count items",
                            model=model_class.__name__, error=str(e))
            raise

    # === UTILITY METHODS ===

    async def exists_by_field(self, model_class: type[T], field_name: str, value: Any) -> bool:
        """Check if item exists by specific field value."""
        try:
            if not hasattr(model_class, field_name):
                raise ValueError(f"Model {model_class.__name__} has no field {field_name}")

            field = getattr(model_class, field_name)
            stmt = select(func.count(model_class.id)).where(field == value)

            if self.tenant_id is not None and hasattr(model_class, 'tenant_id'):
                stmt = stmt.where(model_class.tenant_id == self.tenant_id)

            result = await self.db.execute(stmt)
            return (result.scalar() or 0) > 0

        except Exception as e:
            self.logger.error("Failed to check existence",
                            model=model_class.__name__, field=field_name, error=str(e))
            raise

    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """Standardized operation logging."""
        log_data = {
            "operation": operation,
            "service": self.__class__.__name__,
            "tenant_id": self.tenant_id or "global"
        }
        if details:
            log_data.update(details)

        self.logger.info("Service operation", **log_data)

    async def handle_error(self, operation: str, error: Exception, **context):
        """Standardized error handling with rollback."""
        await self.db.rollback()

        self.logger.error("Service operation failed",
                         operation=operation,
                         service=self.__class__.__name__,
                         tenant_id=self.tenant_id or "global",
                         error=str(error),
                         **context)
        raise error
