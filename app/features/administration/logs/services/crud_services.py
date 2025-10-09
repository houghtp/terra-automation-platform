"""
Log CRUD services implementing FastAPI/SQLAlchemy best practices.
Read-only operations for application log integrity.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

from app.features.administration.logs.models import ApplicationLog

logger = get_logger(__name__)


class LogCrudService(BaseService[ApplicationLog]):
    """
    Read-only CRUD operations for application logs.

    Maintains log integrity by providing only read operations.
    All operations are automatically tenant-scoped via BaseService.
    """

    async def get_application_logs(
        self,
        level_filter: Optional[str] = None,
        logger_filter: Optional[str] = None,
        user_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> List[ApplicationLog]:
        """
        Get application logs with optional filtering.

        Args:
            level_filter: Filter by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_filter: Filter by logger name
            user_filter: Filter by user ID
            date_from: Filter logs from this date
            date_to: Filter logs to this date
            sort_by: Column to sort by
            sort_order: Sort order (asc or desc)
            limit: Optional maximum number of records to return
            offset: Optional number of records to skip

        Returns:
            List of ApplicationLog instances
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            query = self.create_base_query(ApplicationLog)

            # Apply filters
            if level_filter:
                query = query.where(ApplicationLog.level == level_filter.upper())

            if logger_filter:
                query = query.where(ApplicationLog.logger_name.ilike(f"%{logger_filter}%"))

            if user_filter:
                query = query.where(ApplicationLog.user_id.ilike(f"%{user_filter}%"))

            if date_from:
                query = query.where(ApplicationLog.timestamp >= date_from)

            if date_to:
                query = query.where(ApplicationLog.timestamp <= date_to)

            # Apply sorting
            sort_column = getattr(ApplicationLog, sort_by, ApplicationLog.timestamp)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to get application logs for tenant {self.tenant_id}")
            raise

    async def get_log_by_id(self, log_id: int) -> Optional[ApplicationLog]:
        """
        Get a single log by ID with tenant validation.

        Args:
            log_id: Log entry ID

        Returns:
            ApplicationLog instance or None if not found
        """
        try:
            # Use BaseService get_by_id method for automatic tenant filtering
            return await self.get_by_id(ApplicationLog, log_id)

        except Exception as e:
            logger.exception(f"Failed to get log {log_id} for tenant {self.tenant_id}")
            raise

    async def count_logs(self, search_query: Optional[str] = None, level_filter: Optional[str] = None) -> int:
        """
        Count logs with optional filtering.

        Args:
            search_query: Optional text search query
            level_filter: Optional log level filter

        Returns:
            Count of logs matching the criteria
        """
        try:
            # Use consistent db property (was mixing session/db)
            query = self.create_base_query(ApplicationLog).with_only_columns(func.count(ApplicationLog.id))

            if search_query:
                search_filter = or_(
                    ApplicationLog.message.ilike(f"%{search_query}%"),
                    ApplicationLog.logger_name.ilike(f"%{search_query}%"),
                    ApplicationLog.function_name.ilike(f"%{search_query}%")
                )
                query = query.where(search_filter)

            if level_filter:
                query = query.where(ApplicationLog.level == level_filter)

            result = await self.db.scalar(query)
            logger.debug(f"Counted {result} logs for tenant {self.tenant_id}")
            return result or 0

        except Exception as e:
            logger.exception(f"Failed to count logs for tenant {self.tenant_id}")
            raise

    async def search_logs(
        self,
        search_term: str,
        limit: int = 50,
        level_filter: Optional[str] = None
    ) -> List[ApplicationLog]:
        """
        Search application logs by message content.

        Args:
            search_term: Search term to look for
            limit: Maximum number of results
            level_filter: Optional level filter

        Returns:
            List of matching application logs
        """
        try:
            # Search in message and module fields using BaseService
            query = self.create_base_query(ApplicationLog).where(
                or_(
                    ApplicationLog.message.ilike(f"%{search_term}%"),
                    ApplicationLog.logger_name.ilike(f"%{search_term}%"),
                    ApplicationLog.function_name.ilike(f"%{search_term}%")
                )
            )

            if level_filter:
                query = query.where(ApplicationLog.level == level_filter.upper())

            query = query.order_by(desc(ApplicationLog.timestamp)).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.exception(f"Failed to search logs for tenant {self.tenant_id}")
            raise
