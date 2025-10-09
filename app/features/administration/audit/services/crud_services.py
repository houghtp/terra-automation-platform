"""
Audit CRUD services implementing FastAPI/SQLAlchemy best practices.
Read-only operations for audit log integrity.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.audit.models import AuditLog

logger = get_logger(__name__)


class AuditCrudService(BaseService[AuditLog]):
    """
    Read-only CRUD operations for audit logs.

    Maintains audit integrity by providing only read operations.
    All operations are automatically tenant-scoped via BaseService.
    """

    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        category_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc"
    ) -> List[AuditLog]:
        """
        Get paginated audit logs with optional filtering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            category_filter: Filter by category (AUTH, DATA, ADMIN, etc.)
            severity_filter: Filter by severity (INFO, WARNING, ERROR, CRITICAL)
            user_filter: Filter by user email or ID
            action_filter: Filter by action type
            date_from: Start date for filtering
            date_to: End date for filtering
            sort_by: Field to sort by (timestamp, action, category, severity)
            sort_order: Sort direction (asc, desc)

        Returns:
            List of audit log entries
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            query = self.create_base_query(AuditLog)

            # Apply filters
            if category_filter:
                query = query.where(AuditLog.category == category_filter.upper())

            if severity_filter:
                query = query.where(AuditLog.severity == severity_filter.upper())

            if user_filter:
                query = query.where(
                    func.lower(AuditLog.user_email).contains(user_filter.lower()) |
                    func.lower(AuditLog.user_id).contains(user_filter.lower())
                )

            if action_filter:
                query = query.where(
                    func.lower(AuditLog.action).contains(action_filter.lower())
                )

            if date_from:
                query = query.where(AuditLog.timestamp >= date_from)

            if date_to:
                query = query.where(AuditLog.timestamp <= date_to)

            # Apply sorting
            sort_column = getattr(AuditLog, sort_by, AuditLog.timestamp)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to get audit logs for tenant {self.tenant_id}")
            raise

    async def get_audit_log_by_id(self, log_id: int) -> Optional[AuditLog]:
        """
        Get a specific audit log by ID.

        Args:
            log_id: Audit log ID

        Returns:
            Audit log if found, None otherwise
        """
        try:
            # Use BaseService get_by_id method for automatic tenant filtering
            return await self.get_by_id(AuditLog, log_id)

        except Exception as e:
            logger.exception(f"Failed to get audit log {log_id} for tenant {self.tenant_id}")
            raise

    async def search_audit_logs(
        self,
        search_term: str,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Search audit logs by description or metadata.

        Args:
            search_term: Search term to look for
            limit: Maximum number of results

        Returns:
            List of matching audit logs
        """
        try:
            # Search in description and metadata fields using BaseService
            query = self.create_base_query(AuditLog).where(
                func.lower(AuditLog.description).contains(search_term.lower()) |
                func.lower(AuditLog.action).contains(search_term.lower()) |
                func.lower(AuditLog.resource_type).contains(search_term.lower())
            ).order_by(desc(AuditLog.timestamp)).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to search audit logs for tenant {self.tenant_id}")
            raise

    async def count_audit_logs(
        self,
        category_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> int:
        """
        Count audit logs with optional filtering.

        Args:
            category_filter: Filter by category
            severity_filter: Filter by severity
            user_filter: Filter by user email or ID
            action_filter: Filter by action type
            date_from: Start date for filtering
            date_to: End date for filtering

        Returns:
            Count of audit logs matching criteria
        """
        try:
            query = self.create_base_query(AuditLog).with_only_columns(func.count(AuditLog.id))

            # Apply same filters as get_audit_logs
            if category_filter:
                query = query.where(AuditLog.category == category_filter.upper())

            if severity_filter:
                query = query.where(AuditLog.severity == severity_filter.upper())

            if user_filter:
                query = query.where(
                    func.lower(AuditLog.user_email).contains(user_filter.lower()) |
                    func.lower(AuditLog.user_id).contains(user_filter.lower())
                )

            if action_filter:
                query = query.where(
                    func.lower(AuditLog.action).contains(action_filter.lower())
                )

            if date_from:
                query = query.where(AuditLog.timestamp >= date_from)

            if date_to:
                query = query.where(AuditLog.timestamp <= date_to)

            result = await self.db.scalar(query)
            logger.debug(f"Counted {result} audit logs for tenant {self.tenant_id}")
            return result or 0

        except Exception as e:
            logger.exception(f"Failed to count audit logs for tenant {self.tenant_id}")
            raise
