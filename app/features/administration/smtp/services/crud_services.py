"""
SMTP CRUD services implementing FastAPI/SQLAlchemy best practices.
🏆 GOLD STANDARD SMTP configuration management operations.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from sqlalchemy.exc import IntegrityError
from datetime import datetime

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.features.administration.smtp.models import (
    SMTPConfiguration, SMTPConfigurationCreate, SMTPConfigurationUpdate,
    SMTPConfigurationResponse, SMTPSearchFilter, SMTPStatus, SMTPTestResult
)
from app.features.core.security import security_manager
from app.features.core.audit_mixin import AuditContext

logger = get_logger(__name__)


class SMTPCrudService(BaseService[SMTPConfiguration]):
    """
    🏆 GOLD STANDARD SMTP CRUD operations.

    Demonstrates FastAPI/SQLAlchemy best practices:
    - Enhanced BaseService inheritance
    - Centralized imports and utilities
    - Proper error handling and logging
    - Type-safe query building
    - Consistent validation patterns
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def create_smtp_configuration(self, config_data: SMTPConfigurationCreate, created_by_user=None, target_tenant_id: Optional[str] = None) -> SMTPConfigurationResponse:
        """
        Create a new SMTP configuration within the tenant.

        Args:
            config_data: SMTP configuration creation data
            created_by_user: User creating the configuration
            target_tenant_id: Optional tenant ID for global admin cross-tenant creation

        Returns:
            SMTPConfigurationResponse: Created configuration information
        """
        try:
            effective_tenant_id = target_tenant_id or self.tenant_id

            # Check password confirmation
            if config_data.password != config_data.confirm_password:
                raise ValueError("Passwords do not match")

            # Check if configuration with this name already exists in effective tenant
            existing = await self._get_configuration_by_name_in_tenant(config_data.name, effective_tenant_id)
            if existing:
                raise ValueError(f"SMTP configuration with name '{config_data.name}' already exists in this tenant")

            # If this is set as active, deactivate others in the target tenant
            if config_data.status == SMTPStatus.ACTIVE:
                await self._deactivate_all_configurations_in_tenant(effective_tenant_id)

            # Create audit context
            audit_ctx = AuditContext.from_user(created_by_user) if created_by_user else None

            # Create configuration record
            configuration = SMTPConfiguration(
                name=config_data.name,
                description=config_data.description,
                host=config_data.host,
                port=config_data.port,
                use_tls=config_data.use_tls,
                use_ssl=config_data.use_ssl,
                username=config_data.username,
                hashed_password=security_manager.encrypt_password(config_data.password),
                from_email=config_data.from_email,
                from_name=config_data.from_name,
                reply_to=config_data.reply_to,
                status=config_data.status.value,
                enabled=config_data.enabled,
                is_active=(config_data.status == SMTPStatus.ACTIVE),
                tags=config_data.tags,
                tenant_id=effective_tenant_id
            )

            # Apply audit context with explicit timestamps
            if audit_ctx:
                configuration.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            configuration.created_at = datetime.now()
            configuration.updated_at = datetime.now()

            self.db.add(configuration)
            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Created SMTP configuration: {configuration.name} (ID: {configuration.id}) in tenant {effective_tenant_id}")

            return self._configuration_to_response(configuration)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to create SMTP configuration - IntegrityError",
                        error=error_str,
                        name=config_data.name,
                        tenant_id=effective_tenant_id)
            if "unique constraint" in error_str.lower():
                raise ValueError(f"SMTP configuration with name '{config_data.name}' already exists")
            raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create SMTP configuration: {e}")
            raise

    async def get_configuration_by_id(self, config_id: str) -> Optional[SMTPConfigurationResponse]:
        """Get SMTP configuration by ID within tenant scope."""
        # Use enhanced BaseService method for automatic tenant filtering
        configuration = await self.get_by_id(SMTPConfiguration, config_id)

        if not configuration:
            return None

        return self._configuration_to_response(configuration)

    async def get_configuration_by_name(self, name: str) -> Optional[SMTPConfigurationResponse]:
        """Get SMTP configuration by name within tenant scope."""
        # Use enhanced BaseService query builder for automatic tenant filtering
        stmt = self.create_base_query(SMTPConfiguration).where(SMTPConfiguration.name == name)
        result = await self.db.execute(stmt)
        configuration = result.scalar_one_or_none()

        if not configuration:
            return None

        return self._configuration_to_response(configuration)

    async def update_smtp_configuration(self, config_id: str, config_data: SMTPConfigurationUpdate, updated_by_user=None) -> Optional[SMTPConfigurationResponse]:
        """Update SMTP configuration information within tenant scope."""
        try:
            # Use enhanced BaseService method for automatic tenant filtering
            configuration = await self.get_by_id(SMTPConfiguration, config_id)

            if not configuration:
                return None

            # Update fields if provided
            update_fields = config_data.model_dump(exclude_unset=True)

            # Handle special cases
            if 'password' in update_fields:
                update_fields['hashed_password'] = security_manager.encrypt_password(update_fields['password'])
                del update_fields['password']

            # If status is being set to active, deactivate others
            if 'status' in update_fields and update_fields['status'] == SMTPStatus.ACTIVE:
                await self._deactivate_all_configurations(exclude_id=config_id)
                update_fields['is_active'] = True
            elif 'status' in update_fields and update_fields['status'] != SMTPStatus.ACTIVE:
                update_fields['is_active'] = False

            # Apply audit context for updates with explicit timestamp
            if updated_by_user:
                audit_ctx = AuditContext.from_user(updated_by_user)
                configuration.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            configuration.updated_at = datetime.now()

            for field, value in update_fields.items():
                if hasattr(configuration, field):
                    setattr(configuration, field, value)

            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Updated SMTP configuration: {configuration.name} (ID: {configuration.id})")

            return self._configuration_to_response(configuration)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error("Failed to update SMTP configuration - IntegrityError",
                        error=error_str,
                        config_id=config_id)
            raise ValueError(f"Database constraint violation: {error_str}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update SMTP configuration {config_id}: {e}")
            raise

    async def delete_smtp_configuration(self, config_id: str) -> bool:
        """Delete SMTP configuration within tenant scope."""
        try:
            # Use enhanced BaseService method for automatic tenant filtering
            configuration = await self.get_by_id(SMTPConfiguration, config_id)

            if not configuration:
                return False

            configuration_name = configuration.name
            await self.db.delete(configuration)
            await self.db.flush()

            logger.info(f"Deleted SMTP configuration: {configuration_name} (ID: {config_id})")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete SMTP configuration {config_id}: {e}")
            raise

    async def activate_smtp_configuration(self, config_id: str) -> Optional[SMTPConfigurationResponse]:
        """Activate an SMTP configuration (deactivating others)."""
        try:
            # First, deactivate all other configurations
            await self._deactivate_all_configurations(exclude_id=config_id)

            # Then activate the specified one using BaseService method
            configuration = await self.get_by_id(SMTPConfiguration, config_id)

            if not configuration:
                return None

            configuration.is_active = True
            configuration.status = SMTPStatus.ACTIVE
            configuration.updated_at = datetime.now()

            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Activated SMTP configuration: {configuration.name} (ID: {config_id})")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to activate SMTP configuration {config_id}: {e}")
            raise

    async def deactivate_smtp_configuration(self, config_id: str) -> Optional[SMTPConfigurationResponse]:
        """Deactivate an SMTP configuration."""
        try:
            # Use BaseService method for tenant-scoped retrieval
            configuration = await self.get_by_id(SMTPConfiguration, config_id)

            if not configuration:
                return None

            configuration.is_active = False
            configuration.status = SMTPStatus.INACTIVE
            configuration.updated_at = datetime.now()

            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Deactivated SMTP configuration: {configuration.name} (ID: {config_id})")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to deactivate SMTP configuration {config_id}: {e}")
            raise

    async def list_smtp_configurations(self, filters: Optional[SMTPSearchFilter] = None) -> List[SMTPConfigurationResponse]:
        """List SMTP configurations with optional filtering."""
        # Use enhanced BaseService query builder for automatic tenant filtering
        stmt = self.create_base_query(SMTPConfiguration)

        if filters:
            if filters.search:
                search_term = f"%{filters.search}%"
                stmt = stmt.where(
                    or_(
                        SMTPConfiguration.name.ilike(search_term),
                        SMTPConfiguration.description.ilike(search_term),
                        SMTPConfiguration.host.ilike(search_term),
                        SMTPConfiguration.from_email.ilike(search_term)
                    )
                )

            if filters.status:
                stmt = stmt.where(SMTPConfiguration.status == filters.status.value)

            if filters.enabled is not None:
                stmt = stmt.where(SMTPConfiguration.enabled == filters.enabled)

            if filters.is_active is not None:
                stmt = stmt.where(SMTPConfiguration.is_active == filters.is_active)

            if filters.is_verified is not None:
                stmt = stmt.where(SMTPConfiguration.is_verified == filters.is_verified)

            if filters.created_after:
                stmt = stmt.where(SMTPConfiguration.created_at >= filters.created_after)

            if filters.created_before:
                stmt = stmt.where(SMTPConfiguration.created_at <= filters.created_before)

            stmt = stmt.limit(filters.limit).offset(filters.offset)

        stmt = stmt.order_by(SMTPConfiguration.created_at.desc())

        result = await self.db.execute(stmt)
        configurations = result.scalars().all()

        return [self._configuration_to_response(config) for config in configurations]

    async def update_smtp_field(self, config_id: str, field: str, value: any, updated_by_user=None) -> Optional[SMTPConfigurationResponse]:
        """Update a single field of an SMTP configuration."""
        try:
            # Use enhanced BaseService method for automatic tenant filtering
            configuration = await self.get_by_id(SMTPConfiguration, config_id)

            if not configuration:
                return None

            # Handle special field updates
            if field == 'password':
                value = security_manager.encrypt_password(value)
                field = 'hashed_password'
            elif field == 'status':
                if value == SMTPStatus.ACTIVE:
                    await self._deactivate_all_configurations(exclude_id=config_id)
                    configuration.is_active = True
                elif value != SMTPStatus.ACTIVE:
                    configuration.is_active = False

            # Update the field if it exists
            if hasattr(configuration, field):
                # Apply audit context for updates
                if updated_by_user:
                    audit_ctx = AuditContext.from_user(updated_by_user)
                    configuration.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

                setattr(configuration, field, value)
                await self.db.flush()
                await self.db.refresh(configuration)

                logger.info(f"Updated SMTP configuration field {field} for {configuration.name} (ID: {config_id})")
                return self._configuration_to_response(configuration)

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update SMTP configuration field {field} for {config_id}: {e}")
            raise

    async def _deactivate_all_configurations(self, exclude_id: Optional[str] = None) -> None:
        """Deactivate all SMTP configurations in the tenant (optionally excluding one)."""
        await self._deactivate_all_configurations_in_tenant(self.tenant_id, exclude_id)

    async def _deactivate_all_configurations_in_tenant(self, tenant_id: str, exclude_id: Optional[str] = None) -> None:
        """Deactivate all SMTP configurations in a specific tenant (optionally excluding one)."""
        # Use BaseService create_base_query with manual tenant override for cross-tenant operations
        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.tenant_id == tenant_id,
                SMTPConfiguration.is_active == True
            )
        )

        if exclude_id:
            stmt = stmt.where(SMTPConfiguration.id != exclude_id)

        result = await self.db.execute(stmt)
        configurations = result.scalars().all()

        for config in configurations:
            config.is_active = False
            config.status = SMTPStatus.INACTIVE

    async def _get_configuration_by_name_in_tenant(self, name: str, tenant_id: str) -> Optional[SMTPConfiguration]:
        """Get SMTP configuration by name within specific tenant."""
        # For cross-tenant operations by global admin, use manual query
        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.name == name,
                SMTPConfiguration.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # --- Global Admin Methods ---

    async def update_smtp_field_global(self, config_id: str, field: str, value: any, updated_by_user=None) -> Optional[SMTPConfigurationResponse]:
        """Update a single field of an SMTP configuration across all tenants (global admin only)."""
        try:
            stmt = select(SMTPConfiguration).where(SMTPConfiguration.id == config_id)
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            # Handle special field updates
            if field == 'password':
                value = security_manager.encrypt_password(value)
                field = 'hashed_password'
            elif field == 'status':
                if value == SMTPStatus.ACTIVE:
                    await self._deactivate_all_configurations_in_tenant(configuration.tenant_id, exclude_id=config_id)
                    configuration.is_active = True
                elif value != SMTPStatus.ACTIVE:
                    configuration.is_active = False

            # Update the field if it exists
            if hasattr(configuration, field):
                # Apply audit context for updates
                if updated_by_user:
                    audit_ctx = AuditContext.from_user(updated_by_user)
                    configuration.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

                setattr(configuration, field, value)
                await self.db.flush()
                await self.db.refresh(configuration)

                logger.info(f"Updated SMTP configuration field {field} globally for {configuration.name} (ID: {config_id})")
                return self._configuration_to_response(configuration)

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update SMTP configuration field {field} globally for {config_id}: {e}")
            raise

    async def update_smtp_configuration_global(self, config_id: str, config_data: SMTPConfigurationUpdate, updated_by_user=None) -> Optional[SMTPConfigurationResponse]:
        """Update SMTP configuration across all tenants (global admin only)."""
        try:
            stmt = select(SMTPConfiguration).where(SMTPConfiguration.id == config_id)
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            # Update fields if provided
            update_fields = config_data.model_dump(exclude_unset=True)

            # Handle special cases
            if 'password' in update_fields:
                update_fields['hashed_password'] = security_manager.encrypt_password(update_fields['password'])
                del update_fields['password']

            # If status is being set to active, deactivate others in same tenant
            if 'status' in update_fields and update_fields['status'] == SMTPStatus.ACTIVE:
                await self._deactivate_all_configurations_in_tenant(configuration.tenant_id, exclude_id=config_id)
                update_fields['is_active'] = True
            elif 'status' in update_fields and update_fields['status'] != SMTPStatus.ACTIVE:
                update_fields['is_active'] = False

            # Apply audit context for updates
            if updated_by_user:
                audit_ctx = AuditContext.from_user(updated_by_user)
                configuration.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            for field, value in update_fields.items():
                if hasattr(configuration, field):
                    setattr(configuration, field, value)

            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Updated SMTP configuration globally: {configuration.name} (ID: {configuration.id})")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update SMTP configuration globally {config_id}: {e}")
            raise

    async def list_smtp_configurations_global(self, filters: Optional[SMTPSearchFilter] = None) -> List[Dict[str, Any]]:
        """
        List SMTP configurations across all tenants (global admin only).
        Uses enhanced BaseService patterns with tenant join.
        """
        try:
            # Use BaseService tenant join query builder
            stmt = self.create_tenant_join_query(SMTPConfiguration)

            # Apply filters using BaseService methods
            if filters:
                if filters.search:
                    search_term = f"%{filters.search}%"
                    stmt = stmt.where(
                        or_(
                            SMTPConfiguration.name.ilike(search_term),
                            SMTPConfiguration.description.ilike(search_term),
                            SMTPConfiguration.host.ilike(search_term),
                            SMTPConfiguration.from_email.ilike(search_term)
                        )
                    )

                if filters.status:
                    stmt = stmt.where(SMTPConfiguration.status == filters.status.value)

                if filters.enabled is not None:
                    stmt = stmt.where(SMTPConfiguration.enabled == filters.enabled)

                if filters.is_active is not None:
                    stmt = stmt.where(SMTPConfiguration.is_active == filters.is_active)

                if filters.is_verified is not None:
                    stmt = stmt.where(SMTPConfiguration.is_verified == filters.is_verified)

                if filters.created_after:
                    stmt = stmt.where(SMTPConfiguration.created_at >= filters.created_after)

                if filters.created_before:
                    stmt = stmt.where(SMTPConfiguration.created_at <= filters.created_before)

                stmt = stmt.limit(filters.limit).offset(filters.offset)

            stmt = stmt.order_by(SMTPConfiguration.created_at.desc())

            result = await self.db.execute(stmt)
            return self._process_global_smtp_results(result)

        except Exception as e:
            logger.error(f"Failed to list SMTP configurations globally: {e}")
            raise

    def _process_global_smtp_results(self, result) -> List[Dict[str, Any]]:
        """Process global SMTP query results with tenant information."""
        smtp_list = []
        for row in result:
            config = row[0]  # SMTPConfiguration
            tenant = row[1]  # Tenant

            config_dict = {
                "id": config.id,
                "name": config.name,
                "description": config.description,
                "host": config.host,
                "port": config.port,
                "use_tls": config.use_tls,
                "use_ssl": config.use_ssl,
                "username": config.username,
                "from_email": config.from_email,
                "from_name": config.from_name,
                "reply_to": config.reply_to,
                "status": config.status,
                "enabled": config.enabled,
                "is_active": config.is_active,
                "is_verified": config.is_verified,
                "tags": config.tags or [],
                "tenant_id": config.tenant_id,
                "tenant_name": tenant.name if tenant else "Unknown",
                "last_tested_at": config.last_tested_at.isoformat() if config.last_tested_at else None,
                "test_status": config.test_status,
                "error_message": config.error_message,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            }
            smtp_list.append(config_dict)

        return smtp_list

    def _configuration_to_response(self, configuration: SMTPConfiguration) -> SMTPConfigurationResponse:
        """Convert SQLAlchemy model to response schema."""
        return SMTPConfigurationResponse(
            id=configuration.id,
            name=configuration.name,
            description=configuration.description,
            host=configuration.host,
            port=configuration.port,
            use_tls=configuration.use_tls,
            use_ssl=configuration.use_ssl,
            username=configuration.username,
            from_email=configuration.from_email,
            from_name=configuration.from_name,
            reply_to=configuration.reply_to,
            status=configuration.status,
            enabled=configuration.enabled,
            is_active=configuration.is_active,
            is_verified=configuration.is_verified,
            tags=configuration.tags or [],
            tenant_id=configuration.tenant_id,
            last_tested_at=configuration.last_tested_at.isoformat() if configuration.last_tested_at else None,
            test_status=configuration.test_status,
            error_message=configuration.error_message,
            created_at=configuration.created_at.isoformat() if configuration.created_at else None,
            updated_at=configuration.updated_at.isoformat() if configuration.updated_at else None,
        )
