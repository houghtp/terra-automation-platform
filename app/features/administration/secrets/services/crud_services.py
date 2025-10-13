"""
Secrets CRUD services implementing FastAPI/SQLAlchemy best practices.
Secure storage and retrieval of API keys, tokens, and other sensitive data.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from sqlalchemy.exc import IntegrityError

from app.features.administration.secrets.models import (
    TenantSecret,
    SecretType,
    SecretCreate,
    SecretUpdate,
    SecretResponse,
    SecretValue
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.encryption import encrypt_secret, decrypt_secret, verify_secret_encryption
from datetime import datetime

logger = get_logger(__name__)


class SecretsCrudService(BaseService[TenantSecret]):
    """
    CRUD operations for tenant secrets with encryption.

    Provides secure storage and retrieval of API keys, tokens, and other sensitive data.
    All operations are automatically tenant-scoped via BaseService.
    """

    def _encrypt_secret(self, value: str, tenant_id: str) -> str:
        """Encrypt a secret value using AES-256-GCM encryption."""
        return encrypt_secret(value, tenant_id)

    def _decrypt_secret(self, encrypted_value: str, tenant_id: str) -> str:
        """Decrypt a secret value using AES-256-GCM encryption."""
        return decrypt_secret(encrypted_value, tenant_id)

    def _verify_secret_integrity(self, encrypted_value: str, tenant_id: str) -> bool:
        """Verify that encrypted secret data has integrity and can be decrypted."""
        return verify_secret_encryption(encrypted_value, tenant_id)

    async def create_secret(
        self,
        secret_data: SecretCreate,
        created_by_user=None,
        target_tenant_id: Optional[str] = None
    ) -> SecretResponse:
        """
        Create a new tenant secret with encryption.

        Args:
            secret_data: Secret creation data
            created_by_user: User object who created the secret
            target_tenant_id: Optional tenant ID for global admin cross-tenant creation

        Returns:
            SecretResponse: Created secret metadata (without value)

        Raises:
            ValueError: If secret name already exists for tenant
        """
        try:
            effective_tenant_id = target_tenant_id or self.tenant_id

            # Check if secret name already exists in effective tenant
            if await self._secret_name_exists_in_tenant(secret_data.name, effective_tenant_id):
                raise ValueError(f"Secret with name '{secret_data.name}' already exists in this tenant")

            # Create audit context
            audit_ctx = AuditContext.from_user(created_by_user)

            # Encrypt the secret value using AES-256-GCM
            encrypted_value = self._encrypt_secret(secret_data.value, effective_tenant_id)

            # Create the secret record
            secret = TenantSecret(
                tenant_id=effective_tenant_id,
                name=secret_data.name,
                description=secret_data.description,
                secret_type=secret_data.secret_type,
                encrypted_value=encrypted_value,
                expires_at=secret_data.expires_at,
                rotation_interval_days=secret_data.rotation_interval_days,
            )

            # Set audit information
            secret.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            secret.created_at = datetime.now()
            secret.updated_at = datetime.now()

            self.db.add(secret)
            await self.db.flush()
            await self.db.refresh(secret)

            logger.info(f"Created secret '{secret_data.name}' for tenant {effective_tenant_id}")
            return SecretResponse.model_validate(secret)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error(f"Failed to create secret - IntegrityError details",
                        error=error_str,
                        tenant_id=self.tenant_id,
                        secret_name=secret_data.name,
                        secret_type=secret_data.secret_type.value)

            # Provide more specific error messages based on constraint violation
            if "uq_tenant_secret_name" in error_str:
                raise ValueError(f"A secret with the name '{secret_data.name}' already exists")
            else:
                raise ValueError("Failed to create secret due to database constraint")

    async def get_secret_by_id(self, secret_id: int) -> Optional[SecretResponse]:
        """
        Get secret metadata by ID with tenant validation.

        Args:
            secret_id: Secret ID

        Returns:
            SecretResponse: Secret metadata or None if not found
        """
        try:
            # Use BaseService get_by_id method for automatic tenant filtering
            secret = await self.get_by_id(TenantSecret, secret_id)

            if secret:
                return SecretResponse.model_validate(secret)
            return None

        except Exception as e:
            logger.exception(f"Failed to get secret {secret_id} for tenant {self.tenant_id}")
            raise

    async def get_secret_by_name(self, secret_name: str) -> Optional[SecretResponse]:
        """
        Get secret metadata by name (tenant-scoped).
        Only returns active secrets.

        Args:
            secret_name: Secret name

        Returns:
            Optional[SecretResponse]: Secret metadata or None if not found
        """
        try:
            query = self.create_base_query(TenantSecret).where(
                and_(
                    TenantSecret.name == secret_name,
                    TenantSecret.is_active == True
                )
            )

            result = await self.db.execute(query)
            secret = result.scalar_one_or_none()

            if secret:
                return SecretResponse.model_validate(secret)
            return None

        except Exception as e:
            logger.exception(f"Failed to get secret by name {secret_name} for tenant {self.tenant_id}")
            raise

    async def list_secrets(
        self,
        secret_type: Optional[SecretType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecretResponse]:
        """
        List tenant secrets with filtering.

        Args:
            secret_type: Filter by secret type
            include_inactive: Include inactive secrets
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List[SecretResponse]: List of secret metadata
        """
        try:
            # Use BaseService query builder for automatic tenant filtering
            query = self.create_base_query(TenantSecret)

            # Apply filters
            if secret_type:
                query = query.where(TenantSecret.secret_type == secret_type)

            if not include_inactive:
                query = query.where(TenantSecret.is_active == True)

            # Apply sorting and pagination
            query = query.order_by(desc(TenantSecret.created_at)).offset(offset).limit(limit)

            result = await self.db.execute(query)
            secrets = result.scalars().all()

            return [SecretResponse.model_validate(secret) for secret in secrets]

        except Exception as e:
            logger.exception(f"Failed to list secrets for tenant {self.tenant_id}")
            raise

    async def update_secret(
        self,
        secret_id: int,
        update_data: SecretUpdate,
        updated_by_user=None
    ) -> Optional[SecretResponse]:
        """
        Update an existing secret.

        Args:
            secret_id: Secret ID
            update_data: Update data
            updated_by_user: User performing the update

        Returns:
            Optional[SecretResponse]: Updated secret metadata or None if not found
        """
        try:
            # Create audit context
            audit_ctx = AuditContext.from_user(updated_by_user)

            secret = await self.get_by_id(TenantSecret, secret_id)
            if not secret:
                return None

            # Update fields
            if update_data.name is not None:
                secret.name = update_data.name

            if update_data.description is not None:
                secret.description = update_data.description

            if update_data.secret_type is not None:
                secret.secret_type = update_data.secret_type

            if update_data.value is not None:
                secret.encrypted_value = self._encrypt_secret(update_data.value, self.tenant_id)

            if update_data.is_active is not None:
                secret.is_active = update_data.is_active

            if update_data.expires_at is not None:
                secret.expires_at = update_data.expires_at

            if update_data.rotation_interval_days is not None:
                secret.rotation_interval_days = update_data.rotation_interval_days

            # Set audit information
            secret.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(secret)

            logger.info(f"Updated secret {secret_id} for tenant {self.tenant_id} by {audit_ctx}")
            return SecretResponse.model_validate(secret)

        except IntegrityError as e:
            await self.db.rollback()
            error_str = str(e)
            logger.error(f"Failed to update secret: {e}")

            # Provide more specific error messages based on constraint violation
            if "uq_tenant_secret_name" in error_str and update_data.name:
                raise ValueError(f"A secret with the name '{update_data.name}' already exists")
            else:
                raise ValueError("Failed to update secret due to database constraint")

    async def update_secret_field(self, secret_id: int, field: str, value) -> Optional[SecretResponse]:
        """Update a single field of a secret within tenant scope."""
        try:
            secret = await self.get_by_id(TenantSecret, secret_id)
            if not secret:
                return None

            # Don't allow direct updates to encrypted_value or sensitive fields
            if field in ['encrypted_value', 'id', 'tenant_id', 'created_at']:
                return None

            if hasattr(secret, field):
                setattr(secret, field, value)
                await self.db.flush()
                await self.db.refresh(secret)

                return SecretResponse.model_validate(secret)

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update secret field: {e}")
            raise ValueError(f"Failed to update secret field: {str(e)}")

    async def delete_secret(self, secret_id: int, deleted_by_user=None) -> bool:
        """
        Delete a secret (soft delete by marking inactive).

        Args:
            secret_id: Secret ID
            deleted_by_user: User performing the deletion

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            # Create audit context
            audit_ctx = AuditContext.from_user(deleted_by_user)

            secret = await self.get_by_id(TenantSecret, secret_id)
            if not secret:
                return False

            # Soft delete
            secret.is_active = False
            secret.set_deleted_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            logger.info(f"Deleted secret {secret_id} for tenant {self.tenant_id} by {audit_ctx}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete secret: {e}")
            return False

    async def secret_name_exists(self, secret_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if a secret name exists for a tenant.
        Used for validation during creation/updates to respect database unique constraints.

        Args:
            secret_name: Secret name to check
            exclude_id: Optional secret ID to exclude from check (for updates)

        Returns:
            bool: True if name exists, False otherwise
        """
        try:
            query = self.create_base_query(TenantSecret).where(TenantSecret.name == secret_name)

            if exclude_id:
                query = query.where(TenantSecret.id != exclude_id)

            result = await self.db.execute(query)
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(f"Failed to check secret name existence for tenant {self.tenant_id}")
            raise

    async def _secret_name_exists_in_tenant(self, secret_name: str, tenant_id: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if a secret name exists in a specific tenant (for global admin operations).

        Args:
            secret_name: Secret name to check
            tenant_id: Tenant ID to check within
            exclude_id: Optional secret ID to exclude from check (for updates)

        Returns:
            bool: True if name exists, False otherwise
        """
        try:
            query = select(TenantSecret).where(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.name == secret_name,
                TenantSecret.deleted_at.is_(None)
            )

            if exclude_id:
                query = query.where(TenantSecret.id != exclude_id)

            result = await self.db.execute(query)
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(f"Failed to check secret name existence for tenant {tenant_id}")
            raise

    async def count_secrets(self, secret_type: Optional[SecretType] = None, include_inactive: bool = False) -> int:
        """
        Count secrets with optional filtering.

        Args:
            secret_type: Optional secret type filter
            include_inactive: Include inactive secrets

        Returns:
            Count of secrets matching the criteria
        """
        try:
            query = self.create_base_query(TenantSecret).with_only_columns(func.count(TenantSecret.id))

            if secret_type:
                query = query.where(TenantSecret.secret_type == secret_type)

            if not include_inactive:
                query = query.where(TenantSecret.is_active == True)

            result = await self.db.scalar(query)
            return result or 0

        except Exception as e:
            logger.exception(f"Failed to count secrets for tenant {self.tenant_id}")
            raise

    async def get_secret_value(
        self,
        secret_id: int,
        accessed_by_user=None
    ) -> Optional[SecretValue]:
        """
        Get the decrypted secret value (use carefully).
        Updates access tracking and returns the actual decrypted value.

        Args:
            secret_id: Secret ID
            accessed_by_user: User accessing the secret

        Returns:
            Optional[SecretValue]: Decrypted secret value or None if not found
        """
        try:
            # Create audit context for access logging
            audit_ctx = AuditContext.from_user(accessed_by_user)

            secret = await self.get_by_id(TenantSecret, secret_id)
            if not secret or not secret.is_active:
                return None

            # Check if secret has expired
            # Convert timezone-aware to naive for comparison with database TIMESTAMP WITHOUT TIME ZONE
            current_time_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            if secret.expires_at and secret.expires_at < current_time_naive:
                logger.warning(f"Attempted access to expired secret {secret_id} for tenant {self.tenant_id}")
                return None

            # Decrypt the secret value
            decrypted_value = self._decrypt_secret(secret.encrypted_value, self.tenant_id)

            # Update access tracking
            # Store as naive datetime to match database column type
            access_time = datetime.now(timezone.utc).replace(tzinfo=None)
            secret.last_accessed = access_time
            secret.access_count += 1

            await self.db.flush()
            logger.info(f"Secret '{secret.name}' (ID: {secret_id}) accessed by {audit_ctx} for tenant {self.tenant_id}")

            return SecretValue(
                value=decrypted_value,
                accessed_at=access_time
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to decrypt or access secret {secret_id}: {e}")
            return None
