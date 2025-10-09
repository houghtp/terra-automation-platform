"""
Connector management service for the automation platform.
Provides comprehensive connector management for both available connectors and tenant-specific instances.
"""

import structlog
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, join
from sqlalchemy.orm import selectinload

from app.features.core.base_service import BaseService
from app.features.connectors.connectors.models import (
    AvailableConnector, TenantConnector,
    AvailableConnectorResponse, TenantConnectorCreate, TenantConnectorUpdate,
    TenantConnectorResponse, ConnectorSearchFilter, ConnectorDashboardStats,
    ConnectorCategory, ConnectorStatus
)

logger = structlog.get_logger(__name__)


class ConnectorService(BaseService):
    """
    Comprehensive connector management service.

    Provides:
    - Available connector management (global)
    - Tenant connector instance CRUD operations
    - Connector picker and search functionality
    - Integration with secrets management
    - Statistics and reporting
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str = None):
        super().__init__(db_session, tenant_id)

    # Available Connectors (Global)
    async def list_available_connectors(self, category: Optional[ConnectorCategory] = None) -> List[AvailableConnectorResponse]:
        """List all available connector types for the picker."""
        stmt = select(AvailableConnector).where(AvailableConnector.is_active == True)

        if category:
            stmt = stmt.where(AvailableConnector.category == category.value)

        stmt = stmt.order_by(AvailableConnector.sort_order, AvailableConnector.display_name)

        result = await self.db.execute(stmt)
        connectors = result.scalars().all()

        return [AvailableConnectorResponse.model_validate(connector.to_dict()) for connector in connectors]

    async def get_available_connector_by_id(self, connector_id: str) -> Optional[AvailableConnectorResponse]:
        """Get a specific available connector by ID."""
        stmt = select(AvailableConnector).where(
            and_(
                AvailableConnector.id == connector_id,
                AvailableConnector.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        connector = result.scalar_one_or_none()

        if not connector:
            return None

        return AvailableConnectorResponse.model_validate(connector.to_dict())

    # Tenant Connector Instances
    async def create_tenant_connector(self, connector_data: TenantConnectorCreate, created_by: str = None) -> TenantConnectorResponse:
        """Create a new tenant connector instance."""
        try:
            # Verify the available connector exists
            available_connector = await self.get_available_connector_by_id(connector_data.available_connector_id)
            if not available_connector:
                raise ValueError(f"Available connector not found: {connector_data.available_connector_id}")

            # Check if connector with this name already exists in tenant
            existing = await self.get_tenant_connector_by_name(connector_data.instance_name)
            if existing:
                raise ValueError(f"Connector with name '{connector_data.instance_name}' already exists in this tenant")

            # Create connector instance
            connector = TenantConnector(
                tenant_id=self.tenant_id,
                available_connector_id=connector_data.available_connector_id,
                instance_name=connector_data.instance_name,
                description=connector_data.description,
                configuration=connector_data.configuration,
                secrets_references=connector_data.secrets_references,
                health_check_url=connector_data.health_check_url,
                tags=connector_data.tags,
                created_by=created_by
            )

            self.db.add(connector)
            await self.db.flush()
            await self.db.refresh(connector)

            logger.info(f"Created tenant connector: {connector.instance_name} (ID: {connector.id}) in tenant {self.tenant_id}")

            return await self._connector_to_response(connector)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create tenant connector: {e}")
            raise

    async def get_tenant_connector_by_id(self, connector_id: str) -> Optional[TenantConnectorResponse]:
        """Get tenant connector by ID within tenant scope."""
        stmt = select(TenantConnector).where(
            and_(
                TenantConnector.id == connector_id,
                TenantConnector.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        connector = result.scalar_one_or_none()

        if not connector:
            return None

        return await self._connector_to_response(connector)

    async def get_tenant_connector_by_name(self, name: str) -> Optional[TenantConnectorResponse]:
        """Get tenant connector by name within tenant scope."""
        stmt = select(TenantConnector).where(
            and_(
                TenantConnector.instance_name == name,
                TenantConnector.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        connector = result.scalar_one_or_none()

        if not connector:
            return None

        return await self._connector_to_response(connector)

    async def update_tenant_connector(self, connector_id: str, connector_data: TenantConnectorUpdate) -> Optional[TenantConnectorResponse]:
        """Update tenant connector information within tenant scope."""
        try:
            stmt = select(TenantConnector).where(
                and_(
                    TenantConnector.id == connector_id,
                    TenantConnector.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            connector = result.scalar_one_or_none()

            if not connector:
                return None

            # Update fields if provided
            update_fields = connector_data.model_dump(exclude_unset=True)

            for field, value in update_fields.items():
                if hasattr(connector, field):
                    setattr(connector, field, value)

            connector.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(connector)

            logger.info(f"Updated tenant connector: {connector.instance_name} (ID: {connector.id})")

            return await self._connector_to_response(connector)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update tenant connector {connector_id}: {e}")
            raise

    async def delete_tenant_connector(self, connector_id: str) -> bool:
        """Delete tenant connector within tenant scope."""
        try:
            stmt = select(TenantConnector).where(
                and_(
                    TenantConnector.id == connector_id,
                    TenantConnector.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            connector = result.scalar_one_or_none()

            if not connector:
                return False

            connector_name = connector.instance_name
            await self.db.delete(connector)
            await self.db.flush()

            logger.info(f"Deleted tenant connector: {connector_name} (ID: {connector_id})")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete tenant connector {connector_id}: {e}")
            raise

    async def list_tenant_connectors(self, filters: Optional[ConnectorSearchFilter] = None) -> List[TenantConnectorResponse]:
        """List tenant connectors with optional filtering."""
        stmt = select(TenantConnector).where(TenantConnector.tenant_id == self.tenant_id)

        if filters:
            if filters.search:
                search_term = f"%{filters.search}%"
                stmt = stmt.where(
                    or_(
                        TenantConnector.instance_name.ilike(search_term),
                        TenantConnector.description.ilike(search_term)
                    )
                )

            if filters.status:
                stmt = stmt.where(TenantConnector.status == filters.status.value)

            if filters.is_enabled is not None:
                stmt = stmt.where(TenantConnector.is_enabled == filters.is_enabled)

            if filters.created_after:
                stmt = stmt.where(TenantConnector.created_at >= filters.created_after)

            if filters.created_before:
                stmt = stmt.where(TenantConnector.created_at <= filters.created_before)

            stmt = stmt.limit(filters.limit).offset(filters.offset)

        stmt = stmt.order_by(TenantConnector.created_at.desc())

        result = await self.db.execute(stmt)
        connectors = result.scalars().all()

        return [await self._connector_to_response(connector) for connector in connectors]

    async def enable_connector(self, connector_id: str) -> Optional[TenantConnectorResponse]:
        """Enable a tenant connector."""
        return await self._update_connector_field(connector_id, 'is_enabled', True)

    async def disable_connector(self, connector_id: str) -> Optional[TenantConnectorResponse]:
        """Disable a tenant connector."""
        return await self._update_connector_field(connector_id, 'is_enabled', False)

    async def update_connector_status(self, connector_id: str, status: ConnectorStatus, error_message: str = None) -> Optional[TenantConnectorResponse]:
        """Update connector status and optionally error message."""
        connector = await self.get_tenant_connector_by_id(connector_id)
        if not connector:
            return None

        update_data = TenantConnectorUpdate(status=status)
        if error_message:
            update_data.last_error = error_message

        return await self.update_tenant_connector(connector_id, update_data)

    async def get_dashboard_stats(self) -> ConnectorDashboardStats:
        """Get dashboard statistics for tenant connectors."""
        # Total connectors
        total_stmt = select(func.count(TenantConnector.id)).where(
            TenantConnector.tenant_id == self.tenant_id
        )
        total_result = await self.db.execute(total_stmt)
        total_connectors = total_result.scalar()

        # Active connectors
        active_stmt = select(func.count(TenantConnector.id)).where(
            and_(
                TenantConnector.tenant_id == self.tenant_id,
                TenantConnector.status == ConnectorStatus.ACTIVE,
                TenantConnector.is_enabled == True
            )
        )
        active_result = await self.db.execute(active_stmt)
        active_connectors = active_result.scalar()

        # Error connectors
        error_stmt = select(func.count(TenantConnector.id)).where(
            and_(
                TenantConnector.tenant_id == self.tenant_id,
                TenantConnector.status == ConnectorStatus.ERROR
            )
        )
        error_result = await self.db.execute(error_stmt)
        error_connectors = error_result.scalar()

        # Pending setup connectors
        pending_stmt = select(func.count(TenantConnector.id)).where(
            and_(
                TenantConnector.tenant_id == self.tenant_id,
                TenantConnector.status == ConnectorStatus.PENDING_SETUP
            )
        )
        pending_result = await self.db.execute(pending_stmt)
        pending_setup_connectors = pending_result.scalar()

        # Connectors by category (join with available_connectors)
        category_stmt = select(
            AvailableConnector.category,
            func.count(TenantConnector.id)
        ).select_from(
            join(TenantConnector, AvailableConnector,
                 TenantConnector.available_connector_id == AvailableConnector.id)
        ).where(
            TenantConnector.tenant_id == self.tenant_id
        ).group_by(AvailableConnector.category)

        category_result = await self.db.execute(category_stmt)
        connectors_by_category = dict(category_result.fetchall())

        # Connectors by status
        status_stmt = select(
            TenantConnector.status,
            func.count(TenantConnector.id)
        ).where(
            TenantConnector.tenant_id == self.tenant_id
        ).group_by(TenantConnector.status)

        status_result = await self.db.execute(status_stmt)
        connectors_by_status = dict(status_result.fetchall())

        # Recent connectors
        recent_stmt = select(TenantConnector).where(
            TenantConnector.tenant_id == self.tenant_id
        ).order_by(TenantConnector.created_at.desc()).limit(5)

        recent_result = await self.db.execute(recent_stmt)
        recent_connectors = [
            await self._connector_to_response(connector)
            for connector in recent_result.scalars().all()
        ]

        return ConnectorDashboardStats(
            total_connectors=total_connectors,
            active_connectors=active_connectors,
            error_connectors=error_connectors,
            pending_setup_connectors=pending_setup_connectors,
            connectors_by_category=connectors_by_category,
            connectors_by_status=connectors_by_status,
            recent_connectors=recent_connectors
        )

    async def _update_connector_field(self, connector_id: str, field: str, value: any) -> Optional[TenantConnectorResponse]:
        """Update a single field of a tenant connector."""
        try:
            stmt = select(TenantConnector).where(
                and_(
                    TenantConnector.id == connector_id,
                    TenantConnector.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            connector = result.scalar_one_or_none()

            if not connector:
                return None

            # Update the field if it exists
            if hasattr(connector, field):
                setattr(connector, field, value)
                connector.updated_at = datetime.now(timezone.utc)
                await self.db.flush()
                await self.db.refresh(connector)

                logger.info(f"Updated connector field {field} for {connector.instance_name} (ID: {connector_id})")
                return await self._connector_to_response(connector)

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update connector field {field} for {connector_id}: {e}")
            raise

    async def _connector_to_response(self, connector: TenantConnector) -> TenantConnectorResponse:
        """Convert SQLAlchemy model to response schema with joined available connector data."""
        # Get the available connector info
        available_connector = await self.get_available_connector_by_id(connector.available_connector_id)

        connector_dict = connector.to_dict()

        # Add available connector fields
        if available_connector:
            connector_dict.update({
                "connector_name": available_connector.name,
                "connector_display_name": available_connector.display_name,
                "connector_icon_url": available_connector.icon_url,
                "connector_icon_class": available_connector.icon_class,
                "connector_brand_color": available_connector.brand_color,
                "connector_category": available_connector.category,
            })

        return TenantConnectorResponse.model_validate(connector_dict)

    async def get_connector_credentials(self, connector_id: int) -> Optional[Dict[str, Any]]:
        """
        Get resolved credentials for a tenant connector.

        This method resolves credentials from:
        1. Direct configuration (for simple API keys)
        2. Secrets manager references (for sensitive data)

        Args:
            connector_id: Tenant connector ID

        Returns:
            Dict[str, Any]: Resolved credentials ready for SDK use
        """
        if not self.tenant_id:
            raise ValueError("Tenant ID required for credential resolution")

        # Get the connector
        connector = await self.get_tenant_connector_by_id(connector_id)
        if not connector:
            return None

        credentials = {}

        # Start with direct configuration
        if connector.configuration:
            credentials.update(connector.configuration)

        # Resolve secrets references if they exist
        if connector.secrets_references:
            try:
                from app.features.administration.secrets.services import SecretsService
                secrets_service = SecretsService(self.db)

                for config_key, secret_ref in connector.secrets_references.items():
                    if isinstance(secret_ref, dict) and 'secret_name' in secret_ref:
                        # Resolve by secret name - first get the secret metadata
                        secret_metadata = await secrets_service.get_secret_by_name(
                            tenant_id=self.tenant_id,
                            secret_name=secret_ref['secret_name']
                        )
                        if secret_metadata:
                            secret_value = await secrets_service.get_secret_value(
                                tenant_id=self.tenant_id,
                                secret_id=secret_metadata.id,
                                accessed_by=f"connector_{connector_id}"
                            )
                            if secret_value:
                                credentials[config_key] = secret_value.value
                    elif isinstance(secret_ref, dict) and 'secret_id' in secret_ref:
                        # Resolve by secret ID
                        secret_value = await secrets_service.get_secret_value(
                            tenant_id=self.tenant_id,
                            secret_id=secret_ref['secret_id'],
                            accessed_by=f"connector_{connector_id}"
                        )
                        if secret_value:
                            credentials[config_key] = secret_value.value

            except Exception as e:
                logger.error(f"Failed to resolve secrets for connector {connector_id}: {e}")
                # Continue without secrets - some connectors might work with partial config

        return credentials

    async def create_sdk_connector_instance(self, connector_id: int):
        """
        Create an SDK connector instance with resolved credentials.

        Args:
            connector_id: Tenant connector ID

        Returns:
            BaseConnector: Configured SDK connector instance
        """
        if not self.tenant_id:
            raise ValueError("Tenant ID required for SDK connector creation")

        # Get connector and available connector info
        connector = await self.get_tenant_connector_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")

        available_connector = await self.get_available_connector_by_id(connector.available_connector_id)
        if not available_connector:
            raise ValueError(f"Available connector {connector.available_connector_id} not found")

        # Resolve credentials
        credentials = await self.get_connector_credentials(connector_id)
        if not credentials:
            raise ValueError(f"No credentials found for connector {connector_id}")

        # Create SDK connector instance
        try:
            from app.features.core.connectors import get_connector

            # Map connector names to SDK connector names
            sdk_name = available_connector.name

            # Create configuration overrides
            config_overrides = {}
            if connector.configuration and 'rate_limit_per_minute' in connector.configuration:
                config_overrides['rate_limit_per_minute'] = connector.configuration['rate_limit_per_minute']

            # Get SDK connector instance
            sdk_connector = get_connector(
                name=sdk_name,
                credentials=credentials,
                config_overrides=config_overrides
            )

            logger.info(f"Created SDK connector instance for {available_connector.name} (tenant connector {connector_id})")
            return sdk_connector

        except Exception as e:
            logger.error(f"Failed to create SDK connector instance for {connector_id}: {e}")
            raise ValueError(f"Failed to create SDK connector: {str(e)}")

    async def create_sdk_connector_instance_by_type(
        self,
        connector_type: str,
        tenant_id: Optional[str] = None
    ):
        """
        Create an SDK connector instance by connector type name for a specific tenant.

        This method bridges the gap between connector type names (e.g., "firecrawl")
        and tenant-specific connector instances with proper credential resolution.

        Args:
            connector_type: Name of the connector type (e.g., "firecrawl", "serpapi")
            tenant_id: Tenant identifier (uses service tenant_id if not provided)

        Returns:
            BaseConnector: Configured SDK connector instance

        Raises:
            ValueError: If connector type not found or no instances configured for tenant
        """
        # Use provided tenant_id or service default
        target_tenant_id = tenant_id or self.tenant_id
        if not target_tenant_id:
            raise ValueError("Tenant ID required for connector lookup")

        try:
            # First, get the available connector by name
            available_connector = None
            available_connectors = await self.list_available_connectors()

            for conn in available_connectors:
                if conn.name == connector_type:
                    available_connector = conn
                    break

            if not available_connector:
                raise ValueError(f"Connector type '{connector_type}' not found in available connectors")

            # Find tenant's instance of this connector type
            tenant_connectors = await self.list_tenant_connectors(
                available_connector_id=available_connector.id
            )

            if not tenant_connectors:
                raise ValueError(f"No {connector_type} connector instances configured for tenant {target_tenant_id}")

            # Use the first active instance (could be enhanced to support multiple instances)
            active_instances = [conn for conn in tenant_connectors if conn.is_active]
            if not active_instances:
                raise ValueError(f"No active {connector_type} connector instances found for tenant {target_tenant_id}")

            tenant_connector = active_instances[0]

            # Create SDK connector instance using the tenant connector ID
            return await self.create_sdk_connector_instance(tenant_connector.id)

        except Exception as e:
            logger.error(f"Failed to create SDK connector instance for type {connector_type}: {e}")
            raise ValueError(f"Failed to create {connector_type} connector: {str(e)}")

    async def test_connector_connection(self, connector_id: int) -> Dict[str, Any]:
        """
        Test connection for a tenant connector using SDK.

        Args:
            connector_id: Tenant connector ID

        Returns:
            Dict with test results
        """
        try:
            # Create SDK connector instance
            sdk_connector = await self.create_sdk_connector_instance(connector_id)

            # Initialize and test
            init_result = await sdk_connector.initialize()
            if not init_result.success:
                return {
                    "success": False,
                    "error": f"Initialization failed: {init_result.error}",
                    "error_code": init_result.error_code
                }

            # Test connection
            test_result = await sdk_connector.test_connection()

            # Cleanup
            await sdk_connector.cleanup()

            return {
                "success": test_result.success,
                "error": test_result.error,
                "error_code": test_result.error_code,
                "metadata": test_result.metadata
            }

        except Exception as e:
            logger.error(f"Connection test failed for connector {connector_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "CONNECTION_TEST_ERROR"
            }
