"""
Connector service implementing business logic for the Connectors slice.

Follows BaseService pattern with JSON Schema validation and encryption.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.features.connectors.connectors.models import (
    ConnectorCatalog,
    Connector,
    ConnectorCatalogResponse,
    ConnectorResponse,
    ConnectorCreate,
    ConnectorUpdate,
    ConnectorSearchFilter,
    ConfigValidationRequest,
    ConfigValidationResponse,
    ConnectorStatus,
)
from app.features.core.audit_mixin import AuditContext
import json
import jsonschema
from jsonschema import validate, ValidationError as JSONSchemaValidationError


logger = get_logger(__name__)


class ConnectorService(BaseService[Connector]):
    """
    Service for managing connector catalog and installed connector instances.

    Provides:
    - Catalog browsing (global, read-only)
    - Connector installation and configuration
    - JSON Schema validation
    - Auth field encryption/decryption
    - Publish target listing for integrations
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        """
        Initialize connector service.

        Args:
            db_session: Database session
            tenant_id: Optional tenant ID for tenant-scoped operations
        """
        super().__init__(db_session, tenant_id)

    # === CATALOG OPERATIONS (GLOBAL) ===

    async def list_catalog(
        self,
        category: Optional[str] = None
    ) -> List[ConnectorCatalogResponse]:
        """
        List all available connectors from the global catalog.

        Args:
            category: Optional category filter (e.g., "Social", "Web")

        Returns:
            List of connector catalog items
        """
        try:
            stmt = select(ConnectorCatalog)

            if category:
                stmt = stmt.where(ConnectorCatalog.category == category)

            stmt = stmt.order_by(ConnectorCatalog.name)

            result = await self.db.execute(stmt)
            catalogs = result.scalars().all()

            self.log_operation("list_catalog", {
                "category": category,
                "count": len(catalogs)
            })

            return [
                ConnectorCatalogResponse.model_validate(catalog.to_dict())
                for catalog in catalogs
            ]

        except Exception as e:
            await self.handle_error("list_catalog", e, category=category)
            raise

    async def get_catalog_by_id(self, catalog_id: str) -> Optional[ConnectorCatalogResponse]:
        """
        Get a specific catalog entry by ID.

        Args:
            catalog_id: Catalog connector ID

        Returns:
            Catalog entry or None
        """
        try:
            catalog = await self.get_by_id(ConnectorCatalog, catalog_id)

            if not catalog:
                return None

            return ConnectorCatalogResponse.model_validate(catalog.to_dict())

        except Exception as e:
            await self.handle_error("get_catalog_by_id", e, catalog_id=catalog_id)
            raise

    async def get_catalog_by_key(self, key: str) -> Optional[ConnectorCatalogResponse]:
        """
        Get a catalog entry by its unique key (e.g., "twitter").

        Args:
            key: Catalog connector key

        Returns:
            Catalog entry or None
        """
        try:
            stmt = select(ConnectorCatalog).where(ConnectorCatalog.key == key)
            result = await self.db.execute(stmt)
            catalog = result.scalar_one_or_none()

            if not catalog:
                return None

            return ConnectorCatalogResponse.model_validate(catalog.to_dict())

        except Exception as e:
            await self.handle_error("get_catalog_by_key", e, key=key)
            raise

    # === INSTALLED CONNECTOR OPERATIONS (TENANT-SCOPED) ===

    async def list_installed(
        self,
        filters: Optional[ConnectorSearchFilter] = None
    ) -> List[ConnectorResponse]:
        """
        List installed connectors for the current tenant.

        For global admins (tenant_id=None), returns all connectors across all tenants.

        Args:
            filters: Optional search and filter parameters

        Returns:
            List of installed connectors with catalog info joined
        """
        try:
            # Base query with tenant scope
            stmt = self.create_base_query(Connector)

            # Apply filters
            if filters:
                if filters.search:
                    stmt = self.apply_search_filters(
                        stmt,
                        Connector,
                        filters.search,
                        ['name']
                    )

                if filters.status:
                    stmt = stmt.where(Connector.status == filters.status.value)

                if filters.category:
                    # Join with catalog to filter by category
                    stmt = stmt.join(
                        ConnectorCatalog,
                        Connector.catalog_id == ConnectorCatalog.id
                    ).where(ConnectorCatalog.category == filters.category)

                # Pagination
                stmt = stmt.limit(filters.limit).offset(filters.offset)

            stmt = stmt.order_by(desc(Connector.created_at))

            result = await self.db.execute(stmt)
            connectors = result.scalars().all()

            # Enrich with catalog info
            enriched = []
            for connector in connectors:
                response = await self._enrich_connector_response(connector)
                enriched.append(response)

            self.log_operation("list_installed", {
                "tenant_id": self.tenant_id,
                "count": len(enriched),
                "filters": filters.model_dump() if filters else None
            })

            return enriched

        except Exception as e:
            await self.handle_error("list_installed", e, tenant_id=self.tenant_id)
            raise

    async def install_connector(
        self,
        connector_data: ConnectorCreate,
        created_by_user=None
    ) -> ConnectorResponse:
        """
        Install a new connector instance for the tenant.

        Validates config against catalog schema and encrypts auth.

        Args:
            connector_data: Connector creation data
            created_by_user: User object creating the connector (for audit trail)

        Returns:
            Created connector with catalog info

        Raises:
            ValueError: If validation fails or connector already exists
        """
        try:
            # 1. Validate catalog exists
            catalog = await self.get_catalog_by_id(connector_data.catalog_id)
            if not catalog:
                raise ValueError(f"Catalog connector not found: {connector_data.catalog_id}")

            # 2. Check name uniqueness within tenant
            existing = await self.exists_by_field(Connector, 'name', connector_data.name)
            if existing:
                raise ValueError(f"Connector with name '{connector_data.name}' already exists")

            # 3. Validate config against catalog schema
            validation_result = await self.validate_config(
                catalog.key,
                connector_data.config
            )
            if not validation_result.valid:
                raise ValueError(f"Config validation failed: {', '.join(validation_result.errors)}")

            # 4. Encrypt auth data
            encrypted_auth = await self._encrypt_auth(connector_data.auth)

            # 5. Create audit context
            audit_ctx = AuditContext.from_user(created_by_user) if created_by_user else None

            # 6. Create connector instance
            connector = Connector(
                tenant_id=self.tenant_id,
                catalog_id=connector_data.catalog_id,
                name=connector_data.name,
                status=ConnectorStatus.INACTIVE.value,  # Default to inactive
                config=connector_data.config,
                auth=encrypted_auth,
                tags=connector_data.tags
            )

            # Set audit information with explicit timestamps
            if audit_ctx:
                connector.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            connector.created_at = datetime.now()
            connector.updated_at = datetime.now()

            self.db.add(connector)
            await self.db.flush()
            await self.db.refresh(connector)

            self.log_operation("install_connector", {
                "connector_id": connector.id,
                "name": connector.name,
                "catalog_key": catalog.key,
                "tenant_id": self.tenant_id
            })

            return await self._enrich_connector_response(connector)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to install connector - IntegrityError",
                        error=error_str,
                        name=connector_data.name,
                        catalog_id=connector_data.catalog_id)
            if "unique constraint" in error_str.lower():
                raise ValueError(f"Connector with name '{connector_data.name}' already exists")
            raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.handle_error("install_connector", e,
                                   name=connector_data.name,
                                   catalog_id=connector_data.catalog_id)
            raise

    async def update_connector(
        self,
        connector_id: str,
        connector_data: ConnectorUpdate,
        updated_by_user=None
    ) -> ConnectorResponse:
        """
        Update an installed connector.

        Re-validates config and re-encrypts auth if provided.

        Args:
            connector_id: Connector ID
            connector_data: Update data
            updated_by_user: User object updating the connector (for audit trail)

        Returns:
            Updated connector

        Raises:
            ValueError: If validation fails or connector not found
        """
        try:
            # Get existing connector (tenant-scoped)
            connector = await self.get_by_id(Connector, connector_id)
            if not connector:
                raise ValueError(f"Connector not found: {connector_id}")

            # Get catalog for validation
            catalog = await self.get_catalog_by_id(connector.catalog_id)

            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user) if updated_by_user else None

            # Update fields
            update_dict = connector_data.model_dump(exclude_unset=True)

            # Validate config if provided
            if 'config' in update_dict and update_dict['config'] is not None:
                validation_result = await self.validate_config(
                    catalog.key,
                    update_dict['config']
                )
                if not validation_result.valid:
                    raise ValueError(f"Config validation failed: {', '.join(validation_result.errors)}")
                connector.config = update_dict['config']

            # Encrypt auth if provided
            if 'auth' in update_dict and update_dict['auth'] is not None:
                connector.auth = await self._encrypt_auth(update_dict['auth'])

            # Update other fields
            if 'name' in update_dict and update_dict['name']:
                # Check name uniqueness
                existing = await self.db.execute(
                    select(Connector).where(
                        and_(
                            Connector.name == update_dict['name'],
                            Connector.tenant_id == self.tenant_id,
                            Connector.id != connector_id
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"Connector with name '{update_dict['name']}' already exists")
                connector.name = update_dict['name']

            if 'status' in update_dict and update_dict['status']:
                connector.status = update_dict['status'].value

            if 'tags' in update_dict and update_dict['tags'] is not None:
                connector.tags = update_dict['tags']

            # Set audit information with explicit timestamp
            if audit_ctx:
                connector.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            connector.updated_at = datetime.now()

            await self.db.flush()
            await self.db.refresh(connector)

            self.log_operation("update_connector", {
                "connector_id": connector_id,
                "updated_fields": list(update_dict.keys())
            })

            return await self._enrich_connector_response(connector)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to update connector - IntegrityError",
                        error=error_str,
                        connector_id=connector_id)
            raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.handle_error("update_connector", e, connector_id=connector_id)
            raise

    async def get_by_id_with_enrichment(self, connector_id: str) -> Optional[ConnectorResponse]:
        """
        Get connector by ID with catalog info enriched.

        Args:
            connector_id: Connector ID

        Returns:
            Enriched connector response or None
        """
        try:
            connector = await self.get_by_id(Connector, connector_id)
            if not connector:
                return None

            return await self._enrich_connector_response(connector)

        except Exception as e:
            await self.handle_error("get_by_id_with_enrichment", e, connector_id=connector_id)
            raise

    async def delete_connector(self, connector_id: str) -> bool:
        """
        Delete an installed connector (hard delete).

        Args:
            connector_id: Connector ID

        Returns:
            True if deleted, False if not found
        """
        try:
            connector = await self.get_by_id(Connector, connector_id)
            if not connector:
                return False

            connector_name = connector.name
            await self.db.delete(connector)
            await self.db.flush()

            self.log_operation("delete_connector", {
                "connector_id": connector_id,
                "name": connector_name,
                "tenant_id": self.tenant_id
            })

            return True

        except Exception as e:
            await self.handle_error("delete_connector", e, connector_id=connector_id)
            raise

    # === VALIDATION ===

    async def validate_config(
        self,
        catalog_key: str,
        config: Dict[str, Any]
    ) -> ConfigValidationResponse:
        """
        Validate configuration against catalog's JSON Schema.

        Args:
            catalog_key: Catalog connector key (e.g., "twitter")
            config: Configuration to validate

        Returns:
            Validation result with errors if any
        """
        try:
            # Get catalog
            catalog = await self.get_catalog_by_key(catalog_key)
            if not catalog:
                return ConfigValidationResponse(
                    valid=False,
                    errors=[f"Unknown connector type: {catalog_key}"]
                )

            # Get schema
            schema = catalog.default_config_schema
            if not schema:
                # No schema means any config is valid
                return ConfigValidationResponse(valid=True)

            # Validate using jsonschema
            try:
                validate(instance=config, schema=schema)
                return ConfigValidationResponse(valid=True)
            except JSONSchemaValidationError as e:
                return ConfigValidationResponse(
                    valid=False,
                    errors=[f"{e.path[0] if e.path else 'config'}: {e.message}"]
                )
            except Exception as e:
                return ConfigValidationResponse(
                    valid=False,
                    errors=[f"Validation error: {str(e)}"]
                )

        except Exception as e:
            await self.handle_error("validate_config", e, catalog_key=catalog_key)
            return ConfigValidationResponse(
                valid=False,
                errors=[f"Validation failed: {str(e)}"]
            )

    # === INTEGRATION HELPERS ===

    async def get_publish_targets(self) -> List[Dict[str, Any]]:
        """
        Get list of active connectors suitable for publishing/scheduling.

        Used by content broadcaster and other integrations.

        Returns:
            List of publish targets with id, name, catalog info, capabilities
        """
        try:
            # Get active connectors
            stmt = self.create_base_query(Connector).where(
                Connector.status == ConnectorStatus.ACTIVE.value
            )

            result = await self.db.execute(stmt)
            connectors = result.scalars().all()

            # Enrich with catalog info
            targets = []
            for connector in connectors:
                catalog = await self.get_catalog_by_id(connector.catalog_id)
                if catalog:
                    targets.append({
                        "id": connector.id,
                        "name": connector.name,
                        "catalog_key": catalog.key,
                        "catalog_name": catalog.name,
                        "category": catalog.category,
                        "icon": catalog.icon,
                        "capabilities": catalog.capabilities,
                    })

            self.log_operation("get_publish_targets", {
                "tenant_id": self.tenant_id,
                "count": len(targets)
            })

            return targets

        except Exception as e:
            await self.handle_error("get_publish_targets", e)
            raise

    # === PRIVATE HELPERS ===

    async def _enrich_connector_response(
        self,
        connector: Connector
    ) -> ConnectorResponse:
        """
        Enrich connector with catalog information.

        Args:
            connector: Connector instance

        Returns:
            ConnectorResponse with catalog fields populated
        """
        # Get catalog
        catalog = await self.get_catalog_by_id(connector.catalog_id)

        # Build response dict
        response_dict = connector.to_dict()

        # Add catalog fields
        if catalog:
            response_dict.update({
                "catalog_key": catalog.key,
                "catalog_name": catalog.name,
                "catalog_description": catalog.description,
                "catalog_category": catalog.category,
                "catalog_icon": catalog.icon,
                "catalog_auth_type": catalog.auth_type,
                "catalog_capabilities": catalog.capabilities,
            })

        return ConnectorResponse.model_validate(response_dict)

    async def _encrypt_auth(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt auth data for storage using Fernet symmetric encryption.

        Args:
            auth_data: Auth data to encrypt

        Returns:
            Encrypted auth data (values encrypted, keys preserved)
        """
        if not auth_data:
            return {}

        try:
            from cryptography.fernet import Fernet
            import json
            import os
            import base64

            # Get encryption key from environment (or generate one)
            encryption_key = os.getenv("CONNECTOR_ENCRYPTION_KEY")

            if not encryption_key:
                logger.warning(
                    "No CONNECTOR_ENCRYPTION_KEY found in environment. "
                    "Generating temporary key. Set CONNECTOR_ENCRYPTION_KEY for production!"
                )
                encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode()

            fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

            # Encrypt each value in the auth dict
            encrypted_auth = {}
            for key, value in auth_data.items():
                if value:
                    json_value = json.dumps(value)
                    encrypted_value = fernet.encrypt(json_value.encode())
                    encrypted_auth[key] = base64.b64encode(encrypted_value).decode()
                else:
                    encrypted_auth[key] = value

            return encrypted_auth

        except Exception as e:
            logger.error("Failed to encrypt auth data", error=str(e))
            logger.warning("Storing auth data unencrypted due to encryption error")
            return auth_data

    async def _decrypt_auth(self, encrypted_auth: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt auth data for use.

        Args:
            encrypted_auth: Encrypted auth data

        Returns:
            Decrypted auth data
        """
        if not encrypted_auth:
            return {}

        try:
            from cryptography.fernet import Fernet
            import json
            import os
            import base64

            encryption_key = os.getenv("CONNECTOR_ENCRYPTION_KEY")

            if not encryption_key:
                logger.warning("No CONNECTOR_ENCRYPTION_KEY found, cannot decrypt")
                return encrypted_auth

            fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

            decrypted_auth = {}
            for key, value in encrypted_auth.items():
                if value and isinstance(value, str):
                    try:
                        encrypted_bytes = base64.b64decode(value.encode())
                        decrypted_bytes = fernet.decrypt(encrypted_bytes)
                        json_value = decrypted_bytes.decode()
                        decrypted_auth[key] = json.loads(json_value)
                    except Exception as decrypt_error:
                        logger.warning("Failed to decrypt field", field_key=key, error=str(decrypt_error))
                        decrypted_auth[key] = value
                else:
                    decrypted_auth[key] = value

            return decrypted_auth

        except Exception as e:
            logger.error("Failed to decrypt auth data", error=str(e))
            return encrypted_auth
