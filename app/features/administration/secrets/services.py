"""
Tenant-aware secrets management service.
Integrates with shared security infrastructure for secure storage.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError

from app.features.administration.secrets.models import (
    TenantSecret,
    SecretType,
    SecretCreate,
    SecretUpdate,
    SecretResponse,
    SecretValue
)
from app.features.core.encryption import encrypt_secret, decrypt_secret, verify_secret_encryption

logger = logging.getLogger(__name__)


class SecretsService:
    """
    Tenant-aware secrets management service.
    Provides secure storage and retrieval of API keys, tokens, and other sensitive data.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def _encrypt_secret(self, value: str, tenant_id: str) -> str:
        """
        Encrypt a secret value using AES-256-GCM encryption.
        """
        return encrypt_secret(value, tenant_id)

    def _decrypt_secret(self, encrypted_value: str, tenant_id: str) -> str:
        """
        Decrypt a secret value using AES-256-GCM encryption.
        """
        return decrypt_secret(encrypted_value, tenant_id)

    def _verify_secret_integrity(self, encrypted_value: str, tenant_id: str) -> bool:
        """
        Verify that encrypted secret data has integrity and can be decrypted.
        """
        return verify_secret_encryption(encrypted_value, tenant_id)

    async def create_secret(
        self,
        tenant_id: str,
        secret_data: SecretCreate,
        created_by: Optional[str] = None
    ) -> SecretResponse:
        """
        Create a new tenant secret with encryption.

        Args:
            tenant_id: Tenant identifier
            secret_data: Secret creation data
            created_by: User who created the secret

        Returns:
            SecretResponse: Created secret metadata (without value)

        Raises:
            ValueError: If secret name already exists for tenant
        """
        # Check if secret name already exists for this tenant
        existing = await self.get_secret_by_name(tenant_id, secret_data.name)
        if existing:
            raise ValueError(f"Secret '{secret_data.name}' already exists for tenant {tenant_id}")

        # Encrypt the secret value using AES-256-GCM
        encrypted_value = self._encrypt_secret(secret_data.value, tenant_id)

        # Create the secret record
        secret = TenantSecret(
            tenant_id=tenant_id,
            name=secret_data.name,
            description=secret_data.description,
            secret_type=secret_data.secret_type,
            encrypted_value=encrypted_value,
            created_by=created_by,
            expires_at=secret_data.expires_at,
            rotation_interval_days=secret_data.rotation_interval_days,
        )

        try:
            self.db.add(secret)
            await self.db.commit()
            await self.db.refresh(secret)

            logger.info(f"Created secret '{secret_data.name}' for tenant {tenant_id}")
            return SecretResponse.model_validate(secret)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create secret: {e}")
            raise ValueError("Failed to create secret due to database constraint")

    async def get_secret_by_id(self, tenant_id: str, secret_id: int) -> Optional[SecretResponse]:
        """
        Get secret metadata by ID (tenant-scoped).

        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID

        Returns:
            Optional[SecretResponse]: Secret metadata or None if not found
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()

        if secret:
            return SecretResponse.model_validate(secret)
        return None

    async def get_secret_by_name(self, tenant_id: str, secret_name: str) -> Optional[SecretResponse]:
        """
        Get secret metadata by name (tenant-scoped).

        Args:
            tenant_id: Tenant identifier
            secret_name: Secret name

        Returns:
            Optional[SecretResponse]: Secret metadata or None if not found
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.name == secret_name,
                TenantSecret.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()

        if secret:
            return SecretResponse.model_validate(secret)
        return None

    async def get_secret_value(
        self,
        tenant_id: str,
        secret_id: int,
        accessed_by: Optional[str] = None
    ) -> Optional[SecretValue]:
        """
        Get the decrypted secret value (use carefully).
        Updates access tracking and returns the actual decrypted value.

        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID
            accessed_by: User accessing the secret

        Returns:
            Optional[SecretValue]: Decrypted secret value or None if not found
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id,
                TenantSecret.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()

        if not secret:
            return None

        # Check if secret has expired
        if secret.expires_at and secret.expires_at < datetime.utcnow():
            logger.warning(f"Attempted access to expired secret {secret_id} for tenant {tenant_id}")
            return None

        try:
            # Decrypt the secret value
            decrypted_value = self._decrypt_secret(secret.encrypted_value, tenant_id)
            
            # Update access tracking
            access_time = datetime.utcnow()
            secret.last_accessed = access_time
            secret.access_count += 1

            await self.db.commit()
            logger.info(f"Secret '{secret.name}' (ID: {secret_id}) accessed by {accessed_by} for tenant {tenant_id}")

            return SecretValue(
                value=decrypted_value,
                accessed_at=access_time
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to decrypt or access secret {secret_id}: {e}")
            return None

    async def list_secrets(
        self,
        tenant_id: str,
        secret_type: Optional[SecretType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecretResponse]:
        """
        List tenant secrets with filtering.

        Args:
            tenant_id: Tenant identifier
            secret_type: Filter by secret type
            include_inactive: Include inactive secrets
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List[SecretResponse]: List of secret metadata
        """
        conditions = [TenantSecret.tenant_id == tenant_id]

        if secret_type:
            conditions.append(TenantSecret.secret_type == secret_type)

        if not include_inactive:
            conditions.append(TenantSecret.is_active == True)

        stmt = (
            select(TenantSecret)
            .where(and_(*conditions))
            .order_by(TenantSecret.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        secrets = result.scalars().all()

        return [SecretResponse.model_validate(secret) for secret in secrets]

    async def update_secret(
        self,
        tenant_id: str,
        secret_id: int,
        update_data: SecretUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[SecretResponse]:
        """
        Update an existing secret.

        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID
            update_data: Update data
            updated_by: User performing the update

        Returns:
            Optional[SecretResponse]: Updated secret metadata or None if not found
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()

        if not secret:
            return None

        # Update fields
        if update_data.name is not None:
            # Check for name conflicts
            existing = await self.get_secret_by_name(tenant_id, update_data.name)
            if existing and existing.id != secret_id:
                raise ValueError(f"Secret name '{update_data.name}' already exists")
            secret.name = update_data.name

        if update_data.description is not None:
            secret.description = update_data.description

        if update_data.secret_type is not None:
            secret.secret_type = update_data.secret_type

        if update_data.value is not None:
            secret.encrypted_value = self._encrypt_secret(update_data.value, tenant_id)

        if update_data.is_active is not None:
            secret.is_active = update_data.is_active

        if update_data.expires_at is not None:
            secret.expires_at = update_data.expires_at

        if update_data.rotation_interval_days is not None:
            secret.rotation_interval_days = update_data.rotation_interval_days

        secret.updated_at = datetime.utcnow()

        try:
            await self.db.commit()
            await self.db.refresh(secret)

            logger.info(f"Updated secret {secret_id} for tenant {tenant_id} by {updated_by}")
            return SecretResponse.model_validate(secret)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to update secret: {e}")
            raise ValueError("Failed to update secret due to database constraint")

    async def update_secret_field(self, tenant_id: str, secret_id: int, field: str, value) -> Optional[SecretResponse]:
        """Update a single field of a secret within tenant scope."""
        try:
            stmt = select(TenantSecret).where(
                and_(
                    TenantSecret.id == secret_id,
                    TenantSecret.tenant_id == tenant_id
                )
            )
            result = await self.db.execute(stmt)
            secret = result.scalar_one_or_none()

            if not secret:
                return None

            # Don't allow direct updates to encrypted_value or sensitive fields
            if field in ['encrypted_value', 'id', 'tenant_id', 'created_at']:
                return None

            if hasattr(secret, field):
                setattr(secret, field, value)
                await self.db.flush()
                await self.db.refresh(secret)

                # Return the updated secret as response
                return SecretResponse(
                    id=secret.id,
                    name=secret.name,
                    description=secret.description,
                    category=secret.category,
                    environment=secret.environment,
                    tags=secret.tags or [],
                    created_at=secret.created_at,
                    updated_at=secret.updated_at,
                    expires_at=secret.expires_at,
                    last_accessed_at=secret.last_accessed_at,
                    access_count=secret.access_count,
                    is_active=secret.is_active
                )

            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update secret field: {e}")
            raise ValueError(f"Failed to update secret field: {str(e)}")

    async def delete_secret(
        self,
        tenant_id: str,
        secret_id: int,
        deleted_by: Optional[str] = None
    ) -> bool:
        """
        Delete a secret (soft delete by marking inactive).

        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID
            deleted_by: User performing the deletion

        Returns:
            bool: True if deleted, False if not found
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()

        if not secret:
            return False

        # Soft delete
        secret.is_active = False
        secret.updated_at = datetime.utcnow()

        try:
            await self.db.commit()
            logger.info(f"Deleted secret {secret_id} for tenant {tenant_id} by {deleted_by}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete secret: {e}")
            return False

    async def get_expiring_secrets(
        self,
        tenant_id: str,
        days_ahead: int = 30
    ) -> List[SecretResponse]:
        """
        Get secrets that will expire within the specified number of days.

        Args:
            tenant_id: Tenant identifier
            days_ahead: Number of days to look ahead for expiring secrets

        Returns:
            List[SecretResponse]: List of expiring secrets
        """
        expiration_threshold = datetime.utcnow() + timedelta(days=days_ahead)

        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.is_active == True,
                TenantSecret.expires_at.is_not(None),
                TenantSecret.expires_at <= expiration_threshold
            )
        ).order_by(TenantSecret.expires_at.asc())

        result = await self.db.execute(stmt)
        secrets = result.scalars().all()

        return [SecretResponse.model_validate(secret) for secret in secrets]

    async def verify_secret_integrity(
        self,
        tenant_id: str,
        secret_id: int
    ) -> bool:
        """
        Verify the integrity of a stored secret without decrypting it fully.
        
        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID
            
        Returns:
            bool: True if secret integrity is valid
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id,
                TenantSecret.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()
        
        if not secret:
            return False
        
        # Verify encryption integrity
        return self._verify_secret_integrity(secret.encrypted_value, tenant_id)

    async def rotate_secret_encryption(
        self,
        tenant_id: str,
        secret_id: int,
        rotated_by: Optional[str] = None
    ) -> bool:
        """
        Re-encrypt a secret with fresh encryption parameters (key rotation).
        
        Args:
            tenant_id: Tenant identifier
            secret_id: Secret ID
            rotated_by: User performing the rotation
            
        Returns:
            bool: True if rotation succeeded
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.id == secret_id,
                TenantSecret.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        secret = result.scalar_one_or_none()
        
        if not secret:
            return False
        
        try:
            # Decrypt with current encryption
            plaintext_value = self._decrypt_secret(secret.encrypted_value, tenant_id)
            
            # Re-encrypt with fresh parameters
            new_encrypted_value = self._encrypt_secret(plaintext_value, tenant_id)
            
            # Update the secret
            secret.encrypted_value = new_encrypted_value
            secret.updated_at = datetime.utcnow()
            
            await self.db.commit()
            logger.info(f"Rotated encryption for secret {secret_id} for tenant {tenant_id} by {rotated_by}")
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to rotate encryption for secret {secret_id}: {e}")
            return False

    async def validate_all_secrets_integrity(self, tenant_id: str) -> Dict[str, Any]:
        """
        Validate integrity of all active secrets for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with validation results
        """
        stmt = select(TenantSecret).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        secrets = result.scalars().all()
        
        validation_results = {
            "total_secrets": len(secrets),
            "valid_secrets": 0,
            "invalid_secrets": 0,
            "invalid_secret_ids": [],
            "validation_errors": []
        }
        
        for secret in secrets:
            try:
                is_valid = self._verify_secret_integrity(secret.encrypted_value, tenant_id)
                if is_valid:
                    validation_results["valid_secrets"] += 1
                else:
                    validation_results["invalid_secrets"] += 1
                    validation_results["invalid_secret_ids"].append(secret.id)
                    validation_results["validation_errors"].append(
                        f"Secret '{secret.name}' (ID: {secret.id}) failed integrity check"
                    )
            except Exception as e:
                validation_results["invalid_secrets"] += 1
                validation_results["invalid_secret_ids"].append(secret.id)
                validation_results["validation_errors"].append(
                    f"Secret '{secret.name}' (ID: {secret.id}) validation error: {str(e)}"
                )
        
        return validation_results

    async def get_secrets_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics about tenant secrets.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dict[str, Any]: Statistics about secrets
        """
        # Total secrets
        total_stmt = select(func.count(TenantSecret.id)).where(
            TenantSecret.tenant_id == tenant_id
        )
        total_result = await self.db.execute(total_stmt)
        total_secrets = total_result.scalar()

        # Active secrets
        active_stmt = select(func.count(TenantSecret.id)).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.is_active == True
            )
        )
        active_result = await self.db.execute(active_stmt)
        active_secrets = active_result.scalar()

        # Expiring soon (30 days)
        expiring_secrets = await self.get_expiring_secrets(tenant_id, 30)

        # By type
        type_stmt = select(
            TenantSecret.secret_type,
            func.count(TenantSecret.id)
        ).where(
            and_(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.is_active == True
            )
        ).group_by(TenantSecret.secret_type)

        type_result = await self.db.execute(type_stmt)
        types_breakdown = dict(type_result.fetchall())

        return {
            "total_secrets": total_secrets,
            "active_secrets": active_secrets,
            "inactive_secrets": total_secrets - active_secrets,
            "expiring_soon": len(expiring_secrets),
            "by_type": types_breakdown,
            "expiring_secrets": [secret.model_dump() for secret in expiring_secrets]
        }
