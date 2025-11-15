"""Enhanced BaseService with common query patterns and utilities."""

from typing import Any, Dict, List, Optional, Type, Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.sqlalchemy_imports import *

T = TypeVar('T')
from app.features.core.database import get_async_session
from app.features.administration.tenants.db_models import Tenant


class TenantFilterError(Exception):
    """Raised when a query is missing required tenant filtering."""
    pass


class BaseService(Generic[T]):
    """
    Enhanced base service with common patterns for FastAPI/SQLAlchemy.

    Provides:
    - Standardized database operations
    - Tenant-scoped queries with automatic validation
    - Common query builders
    - Type-safe operations
    - Consistent error handling

    Global Admin Support:
    - When tenant_id="global" is passed, it's converted to None
    - When tenant_id is None, NO tenant filter is applied (global admin sees all data)
    - Validation is automatically skipped for global admins
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        """
        Initialize service with database session and tenant context.

        Args:
            db_session: SQLAlchemy async session
            tenant_id: Tenant ID for scoping queries, or "global" for global admin access

        Note:
            tenant_id="global" is automatically converted to None for global admin access
        """
        self._raw_db = db_session  # Store raw session
        self._db_warning_logged = False  # Track if deprecation warning shown
        self.tenant_id = None if tenant_id == "global" else tenant_id
        self.logger = get_logger(self.__class__.__name__)
        self.is_global_admin = self.tenant_id is None  # Track if this is global admin

    @property
    def db(self) -> AsyncSession:
        """
        Return database session with deprecation warning for direct execute() usage.

        DEPRECATED: Direct db.execute() usage is discouraged for tenant safety.
        Use self.execute() instead for automatic tenant filter validation.

        This property still works for backward compatibility but logs a warning.
        Global admins don't see warnings (they can query across tenants).
        """
        # Only warn for non-global-admin usage (once per service instance)
        if not self.is_global_admin and not self._db_warning_logged:
            self.logger.warning(
                "DEPRECATED: Direct self.db.execute() usage detected. "
                "Consider using self.execute() for tenant filter validation.",
                service=self.__class__.__name__,
                tenant_id=self.tenant_id
            )
            self._db_warning_logged = True

        return self._raw_db

    # === QUERY BUILDERS ===

    def create_base_query(self, model_class: type[T]) -> Select:
        """
        Create base SELECT query with tenant filtering.

        Global Admin Behavior:
        - If self.tenant_id is None (global admin), NO tenant filter is applied
        - Returns all records across all tenants

        Regular User Behavior:
        - If self.tenant_id is set, adds WHERE tenant_id = ? filter
        - Returns only records for that tenant

        Args:
            model_class: SQLAlchemy model class

        Returns:
            Select statement with appropriate tenant filtering
        """
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

    # === ADVANCED QUERY EXECUTION (Optional Safety Features) ===

    def _has_tenant_filter(self, stmt: Select, model_class: type[T]) -> bool:
        """
        Check if a SELECT statement includes tenant_id filtering.

        This is a best-effort check - converts statement to string and looks for tenant_id.
        Not 100% accurate but catches most cases.

        Args:
            stmt: SQLAlchemy SELECT statement
            model_class: Model class being queried

        Returns:
            True if tenant_id filter appears to be present, False otherwise
        """
        try:
            # Check if model has tenant_id field
            if not hasattr(model_class, 'tenant_id'):
                return True  # No tenant_id field, so no filter needed

            # Convert statement to SQL string
            stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))

            # Look for tenant_id in WHERE clause
            return "tenant_id" in stmt_str.lower()
        except Exception as e:
            self.logger.warning("Failed to check tenant filter", error=str(e))
            return True  # Assume filter is present on error (fail open)

    async def execute(
        self,
        stmt: Select,
        model_class: type[T],
        allow_cross_tenant: bool = False,
        reason: Optional[str] = None
    ):
        """
        Execute query with mandatory tenant filter validation (Option 3: Hybrid Enforcement).

        This is the RECOMMENDED way to execute custom queries. Provides automatic
        tenant filter validation while allowing explicit bypasses when needed.

        Global Admin Behavior:
        - Validation is automatically SKIPPED
        - Global admins can query across all tenants without restrictions
        - No reason parameter needed

        Regular User Behavior:
        - Tenant filter is MANDATORY (validates automatically)
        - Missing filter raises TenantFilterError
        - Prevents accidental data leaks

        Cross-Tenant Queries (Special Cases):
        - Set allow_cross_tenant=True to bypass validation
        - MUST provide reason parameter (for audit trail)
        - All cross-tenant queries are logged

        Args:
            stmt: SQLAlchemy SELECT statement to execute
            model_class: Model class being queried (for validation)
            allow_cross_tenant: Set True to bypass tenant validation (requires reason)
            reason: Required when allow_cross_tenant=True (for audit logging)

        Returns:
            Query result from database

        Raises:
            TenantFilterError: If tenant filter is missing (regular users only)
            ValueError: If allow_cross_tenant=True but reason is not provided

        Examples:
            # Standard query (auto-validated)
            stmt = select(User).where(User.email == email, User.tenant_id == self.tenant_id)
            result = await self.execute(stmt, User)

            # Using create_base_query (recommended - auto-validated)
            stmt = self.create_base_query(User).where(User.email == email)
            result = await self.execute(stmt, User)

            # Cross-tenant aggregation (explicit bypass with reason)
            stmt = select(func.count(User.id)).group_by(User.tenant_id)
            result = await self.execute(
                stmt, User,
                allow_cross_tenant=True,
                reason="Admin dashboard - tenant statistics report"
            )

            # System config table (no tenant_id field)
            stmt = select(SystemConfig).where(SystemConfig.key == "version")
            result = await self.execute(
                stmt, SystemConfig,
                allow_cross_tenant=True,
                reason="SystemConfig model has no tenant_id field"
            )
        """
        # Auto-skip validation for global admins
        if self.is_global_admin:
            return await self._raw_db.execute(stmt)

        # Handle explicit cross-tenant bypass
        if allow_cross_tenant:
            # Require reason for audit trail
            if not reason:
                raise ValueError(
                    "Cross-tenant query requires 'reason' parameter for audit logging. "
                    f"Model: {model_class.__name__}, Tenant: {self.tenant_id}"
                )

            # Log cross-tenant query for audit trail
            self.logger.warning(
                "Cross-tenant query executed (explicit bypass)",
                model=model_class.__name__,
                tenant_id=self.tenant_id,
                reason=reason,
                service=self.__class__.__name__,
                query_preview=str(stmt)[:200]  # First 200 chars
            )

            return await self._raw_db.execute(stmt)

        # Validate tenant filter is present for regular users
        if not self._has_tenant_filter(stmt, model_class):
            self.logger.error(
                "Query missing required tenant filter",
                model=model_class.__name__,
                tenant_id=self.tenant_id,
                service=self.__class__.__name__,
                query=str(stmt)
            )
            raise TenantFilterError(
                f"Query for {model_class.__name__} is missing tenant filter! "
                f"Current tenant: {self.tenant_id}. "
                f"Solutions: "
                f"1) Use create_base_query() for automatic filtering, "
                f"2) Add .where({model_class.__name__}.tenant_id == self.tenant_id), "
                f"3) Set allow_cross_tenant=True with reason if intentional"
            )

        return await self._raw_db.execute(stmt)

    async def execute_with_tenant_check(
        self,
        stmt: Select,
        model_class: type[T],
        allow_cross_tenant: bool = False
    ):
        """
        DEPRECATED: Use execute() method instead.

        This method is kept for backward compatibility.
        """
        self.logger.warning(
            "DEPRECATED: execute_with_tenant_check() is deprecated. Use execute() instead.",
            service=self.__class__.__name__
        )
        return await self.execute(stmt, model_class, allow_cross_tenant, reason="Legacy method usage")

    # === LOGGING & ERROR HANDLING ===

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
