"""
SMTP configuration management service for tenant administrators.
Provides comprehensive SMTP configuration CRUD operations within tenant scope.
"""

import logging
import smtplib
import ssl
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from app.features.administration.smtp.models import (
    SMTPConfiguration, SMTPConfigurationCreate, SMTPConfigurationUpdate,
    SMTPConfigurationResponse, SMTPConfigurationStats, SMTPDashboardStats,
    SMTPSearchFilter, SMTPStatus, SMTPTestResult
)
from app.features.core.security import security_manager

logger = logging.getLogger(__name__)


class SMTPConfigurationService:
    """
    Comprehensive SMTP configuration management service for tenant administrators.

    Provides:
    - Full SMTP configuration CRUD operations within tenant scope
    - SMTP connection testing and validation
    - Password encryption and security
    - Search and filtering
    - Statistics and reporting
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id

    async def create_smtp_configuration(self, config_data: SMTPConfigurationCreate) -> SMTPConfigurationResponse:
        """
        Create a new SMTP configuration within the tenant.

        Args:
            config_data: SMTP configuration creation data

        Returns:
            SMTPConfigurationResponse: Created configuration information
        """
        try:
            # Check password confirmation
            if config_data.password != config_data.confirm_password:
                raise ValueError("Passwords do not match")

            # Check if configuration with this name already exists in tenant
            existing = await self.get_configuration_by_name(config_data.name)
            if existing:
                raise ValueError(f"SMTP configuration with name '{config_data.name}' already exists in this tenant")

            # If this is set as active, deactivate others
            if config_data.status == SMTPStatus.ACTIVE:
                await self._deactivate_all_configurations()

            # Create configuration record
            configuration = SMTPConfiguration(
                name=config_data.name,
                description=config_data.description,
                host=config_data.host,
                port=config_data.port,
                use_tls=config_data.use_tls,
                use_ssl=config_data.use_ssl,
                username=config_data.username,
                hashed_password=security_manager.encrypt_password(config_data.password),  # Use encryption for SMTP passwords
                from_email=config_data.from_email,
                from_name=config_data.from_name,
                reply_to=config_data.reply_to,
                status=config_data.status.value,
                enabled=config_data.enabled,
                is_active=(config_data.status == SMTPStatus.ACTIVE),
                tags=config_data.tags,
                tenant_id=self.tenant_id
            )

            self.db.add(configuration)
            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Created SMTP configuration: {configuration.name} (ID: {configuration.id}) in tenant {self.tenant_id}")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create SMTP configuration: {e}")
            raise

    async def get_configuration_by_id(self, config_id: str) -> Optional[SMTPConfigurationResponse]:
        """Get SMTP configuration by ID within tenant scope."""
        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.id == config_id,
                SMTPConfiguration.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        configuration = result.scalar_one_or_none()

        if not configuration:
            return None

        return self._configuration_to_response(configuration)

    async def get_configuration_by_name(self, name: str) -> Optional[SMTPConfigurationResponse]:
        """Get SMTP configuration by name within tenant scope."""
        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.name == name,
                SMTPConfiguration.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(stmt)
        configuration = result.scalar_one_or_none()

        if not configuration:
            return None

        return self._configuration_to_response(configuration)

    async def update_smtp_configuration(self, config_id: str, config_data: SMTPConfigurationUpdate) -> Optional[SMTPConfigurationResponse]:
        """Update SMTP configuration information within tenant scope."""
        try:
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            # Update fields if provided
            update_fields = config_data.model_dump(exclude_unset=True)

            # Handle special cases
            if 'password' in update_fields:
                # Encrypt the new password
                update_fields['hashed_password'] = security_manager.encrypt_password(update_fields['password'])
                del update_fields['password']

            # If status is being set to active, deactivate others
            if 'status' in update_fields and update_fields['status'] == SMTPStatus.ACTIVE:
                await self._deactivate_all_configurations(exclude_id=config_id)
                update_fields['is_active'] = True
            elif 'status' in update_fields and update_fields['status'] != SMTPStatus.ACTIVE:
                update_fields['is_active'] = False

            for field, value in update_fields.items():
                if hasattr(configuration, field):
                    setattr(configuration, field, value)

            configuration.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Updated SMTP configuration: {configuration.name} (ID: {configuration.id})")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update SMTP configuration {config_id}: {e}")
            raise

    async def delete_smtp_configuration(self, config_id: str) -> bool:
        """Delete SMTP configuration within tenant scope."""
        try:
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

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

            # Then activate the specified one
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            configuration.is_active = True
            configuration.status = SMTPStatus.ACTIVE
            configuration.updated_at = datetime.utcnow()

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
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            configuration.is_active = False
            configuration.status = SMTPStatus.INACTIVE
            configuration.updated_at = datetime.utcnow()

            await self.db.flush()
            await self.db.refresh(configuration)

            logger.info(f"Deactivated SMTP configuration: {configuration.name} (ID: {config_id})")

            return self._configuration_to_response(configuration)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to deactivate SMTP configuration {config_id}: {e}")
            raise

    async def test_smtp_configuration(self, config_id: str, test_email: Optional[str] = None) -> SMTPTestResult:
        """Test SMTP configuration by attempting to connect and optionally send a test email."""
        try:
            configuration = await self.get_configuration_by_id(config_id)
            if not configuration:
                return SMTPTestResult(
                    success=False,
                    message="SMTP configuration not found",
                    tested_at=datetime.utcnow().isoformat()
                )

            # Get the actual configuration record for password
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            config_record = result.scalar_one_or_none()

            if not config_record:
                return SMTPTestResult(
                    success=False,
                    message="Configuration record not found",
                    tested_at=datetime.utcnow().isoformat()
                )

            # Test the SMTP connection
            test_result = await self._test_smtp_connection(
                host=configuration.host,
                port=configuration.port,
                username=configuration.username,
                password=config_record.hashed_password,  # This is encrypted, will be decrypted in _test_smtp_connection
                use_tls=configuration.use_tls,
                use_ssl=configuration.use_ssl,
                from_email=configuration.from_email,
                test_email=test_email
            )

            # Update the configuration with test results
            config_record.last_tested_at = datetime.utcnow()
            config_record.test_status = "success" if test_result.success else "failed"
            config_record.error_message = None if test_result.success else test_result.message
            config_record.is_verified = test_result.success

            await self.db.flush()

            return test_result

        except Exception as e:
            logger.error(f"Failed to test SMTP configuration {config_id}: {e}")
            return SMTPTestResult(
                success=False,
                message=f"Test failed: {str(e)}",
                tested_at=datetime.utcnow().isoformat()
            )

    async def _test_smtp_connection(self, host: str, port: int, username: str, password: str,
                                  use_tls: bool, use_ssl: bool, from_email: str,
                                  test_email: Optional[str] = None) -> SMTPTestResult:
        """Test SMTP connection and optionally send test email."""
        try:
            # Decrypt the password
            try:
                decrypted_password = security_manager.decrypt_password(password)
            except Exception as e:
                return SMTPTestResult(
                    success=False,
                    message=f"Password decryption failed: {str(e)}",
                    tested_at=datetime.utcnow().isoformat()
                )

            # Create SMTP connection
            if use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, context=context)
            else:
                server = smtplib.SMTP(host, port)
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            # Authenticate
            server.login(username, decrypted_password)

            details = {
                "host": host,
                "port": port,
                "tls": use_tls,
                "ssl": use_ssl,
                "auth": True
            }

            # If test email provided, send a test message
            if test_email:
                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = test_email
                msg['Subject'] = "SMTP Configuration Test"

                body = "This is a test email to verify SMTP configuration."
                msg.attach(MIMEText(body, 'plain'))

                server.sendmail(from_email, test_email, msg.as_string())
                details["test_email_sent"] = True

            server.quit()

            return SMTPTestResult(
                success=True,
                message="SMTP connection successful" + (" and test email sent" if test_email else ""),
                details=details,
                tested_at=datetime.utcnow().isoformat()
            )

        except Exception as e:
            return SMTPTestResult(
                success=False,
                message=f"SMTP connection failed: {str(e)}",
                tested_at=datetime.utcnow().isoformat()
            )

    async def list_smtp_configurations(self, filters: Optional[SMTPSearchFilter] = None) -> List[SMTPConfigurationResponse]:
        """List SMTP configurations with optional filtering."""
        stmt = select(SMTPConfiguration).where(SMTPConfiguration.tenant_id == self.tenant_id)

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

    async def get_dashboard_stats(self) -> SMTPDashboardStats:
        """Get dashboard statistics for SMTP configurations."""
        # Total configurations
        total_stmt = select(func.count(SMTPConfiguration.id)).where(
            SMTPConfiguration.tenant_id == self.tenant_id
        )
        total_result = await self.db.execute(total_stmt)
        total_configurations = total_result.scalar()

        # Active configurations
        active_stmt = select(func.count(SMTPConfiguration.id)).where(
            and_(
                SMTPConfiguration.tenant_id == self.tenant_id,
                SMTPConfiguration.is_active == True
            )
        )
        active_result = await self.db.execute(active_stmt)
        active_configurations = active_result.scalar()

        # Verified configurations
        verified_stmt = select(func.count(SMTPConfiguration.id)).where(
            and_(
                SMTPConfiguration.tenant_id == self.tenant_id,
                SMTPConfiguration.is_verified == True
            )
        )
        verified_result = await self.db.execute(verified_stmt)
        verified_configurations = verified_result.scalar()

        # Failed configurations
        failed_stmt = select(func.count(SMTPConfiguration.id)).where(
            and_(
                SMTPConfiguration.tenant_id == self.tenant_id,
                SMTPConfiguration.test_status == "failed"
            )
        )
        failed_result = await self.db.execute(failed_stmt)
        failed_configurations = failed_result.scalar()

        # Configurations by status
        status_stmt = select(
            SMTPConfiguration.status,
            func.count(SMTPConfiguration.id)
        ).where(
            SMTPConfiguration.tenant_id == self.tenant_id
        ).group_by(SMTPConfiguration.status)

        status_result = await self.db.execute(status_stmt)
        configurations_by_status = dict(status_result.fetchall())

        # Recent configurations
        recent_stmt = select(SMTPConfiguration).where(
            SMTPConfiguration.tenant_id == self.tenant_id
        ).order_by(SMTPConfiguration.created_at.desc()).limit(5)

        recent_result = await self.db.execute(recent_stmt)
        recent_configurations = [
            self._configuration_to_response(config)
            for config in recent_result.scalars().all()
        ]

        return SMTPDashboardStats(
            total_configurations=total_configurations,
            active_configurations=active_configurations,
            verified_configurations=verified_configurations,
            failed_configurations=failed_configurations,
            configurations_by_status=configurations_by_status,
            recent_configurations=recent_configurations
        )

    async def update_smtp_field(self, config_id: str, field: str, value: any) -> Optional[SMTPConfigurationResponse]:
        """Update a single field of an SMTP configuration."""
        try:
            stmt = select(SMTPConfiguration).where(
                and_(
                    SMTPConfiguration.id == config_id,
                    SMTPConfiguration.tenant_id == self.tenant_id
                )
            )
            result = await self.db.execute(stmt)
            configuration = result.scalar_one_or_none()

            if not configuration:
                return None

            # Handle special field updates
            if field == 'password':
                # Encrypt the password
                value = security_manager.encrypt_password(value)
                field = 'hashed_password'
            elif field == 'status':
                # Handle status changes and activation
                if value == SMTPStatus.ACTIVE:
                    await self._deactivate_all_configurations(exclude_id=config_id)
                    configuration.is_active = True
                elif value != SMTPStatus.ACTIVE:
                    configuration.is_active = False

            # Update the field if it exists
            if hasattr(configuration, field):
                setattr(configuration, field, value)
                configuration.updated_at = datetime.utcnow()
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
        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.tenant_id == self.tenant_id,
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
