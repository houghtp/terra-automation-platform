"""
Unit tests for Secrets slice services.

Tests the business logic layer with proper tenant isolation,
error handling, and data validation for the Secrets slice.
"""

import pytest
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.features.administration.secrets.services import SecretsService
from app.features.administration.secrets.models import (
    TenantSecret,
    SecretType,
    SecretCreate,
    SecretUpdate,
    SecretResponse
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSecretsService:
    """Test suite for SecretsService."""

    async def test_create_secret_success(self, test_db_session: AsyncSession):
        """Test creating a secret successfully."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        secret_data = SecretCreate(
            name="Test API Key",
            description="Test description",
            secret_type=SecretType.API_KEY,
            value="test_secret_value"
        )

        result = await service.create_secret(tenant_id, secret_data, "test_user")

        assert isinstance(result, SecretResponse)
        assert result.tenant_id == tenant_id
        assert result.name == secret_data.name
        assert result.description == secret_data.description
        assert result.secret_type == secret_data.secret_type
        assert result.created_by == "test_user"
        assert result.is_active is True
        assert result.has_value is True

    async def test_create_secret_minimal_data(self, test_db_session: AsyncSession):
        """Test creating secret with minimal required data."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        secret_data = SecretCreate(
            name="Minimal Secret",
            value="secret_value"
        )

        result = await service.create_secret(tenant_id, secret_data)

        assert result.name == secret_data.name
        assert result.secret_type == SecretType.OTHER  # Default value
        assert result.description is None
        assert result.created_by is None

    async def test_create_secret_with_expiration(self, test_db_session: AsyncSession):
        """Test creating secret with expiration settings."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"
        expires_at = datetime.utcnow() + timedelta(days=30)

        secret_data = SecretCreate(
            name="Expiring Secret",
            value="secret_value",
            expires_at=expires_at,
            rotation_interval_days=90
        )

        result = await service.create_secret(tenant_id, secret_data)

        assert result.expires_at == expires_at
        assert result.rotation_interval_days == 90

    async def test_create_secret_duplicate_name_same_tenant(self, test_db_session: AsyncSession):
        """Test that duplicate secret names within same tenant are rejected."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        secret_data = SecretCreate(
            name="Duplicate Secret",
            value="value1"
        )

        # Create first secret
        await service.create_secret(tenant_id, secret_data)

        # Attempt to create duplicate - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            await service.create_secret(tenant_id, secret_data)

    async def test_create_secret_same_name_different_tenants(self, test_db_session: AsyncSession):
        """Test that same secret name can exist in different tenants."""
        service = SecretsService(test_db_session)

        secret_data = SecretCreate(
            name="Shared Secret Name",
            value="value"
        )

        result_a = await service.create_secret("tenant-a", secret_data)
        result_b = await service.create_secret("tenant-b", secret_data)

        assert result_a.name == result_b.name
        assert result_a.tenant_id != result_b.tenant_id
        assert result_a.id != result_b.id

    async def test_get_secret_by_id_success(self, test_db_session: AsyncSession):
        """Test retrieving a secret by ID successfully."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create a secret first
        secret_data = SecretCreate(name="Test Secret", value="test_value")
        created_secret = await service.create_secret(tenant_id, secret_data)

        # Retrieve it
        retrieved_secret = await service.get_secret_by_id(tenant_id, created_secret.id)

        assert retrieved_secret is not None
        assert retrieved_secret.id == created_secret.id
        assert retrieved_secret.tenant_id == tenant_id
        assert retrieved_secret.name == secret_data.name

    async def test_get_secret_by_id_wrong_tenant(self, test_db_session: AsyncSession):
        """Test that secrets cannot be accessed by wrong tenant."""
        service = SecretsService(test_db_session)

        # Create secret for tenant-a
        secret_data = SecretCreate(name="Tenant A Secret", value="value")
        created_secret = await service.create_secret("tenant-a", secret_data)

        # Try to access with tenant-b
        retrieved_secret = await service.get_secret_by_id("tenant-b", created_secret.id)

        assert retrieved_secret is None

    async def test_get_secret_by_id_nonexistent(self, test_db_session: AsyncSession):
        """Test retrieving nonexistent secret."""
        service = SecretsService(test_db_session)

        result = await service.get_secret_by_id("test-tenant", 99999)
        assert result is None

    async def test_get_secret_by_name_success(self, test_db_session: AsyncSession):
        """Test retrieving a secret by name successfully."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create a secret first
        secret_data = SecretCreate(name="Named Secret", value="test_value")
        created_secret = await service.create_secret(tenant_id, secret_data)

        # Retrieve it by name
        retrieved_secret = await service.get_secret_by_name(tenant_id, "Named Secret")

        assert retrieved_secret is not None
        assert retrieved_secret.id == created_secret.id
        assert retrieved_secret.name == "Named Secret"

    async def test_get_secret_by_name_inactive_not_returned(self, test_db_session: AsyncSession):
        """Test that inactive secrets are not returned by name search."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create and then deactivate a secret
        secret_data = SecretCreate(name="Inactive Secret", value="value")
        created_secret = await service.create_secret(tenant_id, secret_data)

        update_data = SecretUpdate(is_active=False)
        await service.update_secret(tenant_id, created_secret.id, update_data)

        # Try to retrieve by name - should not find it
        retrieved_secret = await service.get_secret_by_name(tenant_id, "Inactive Secret")
        assert retrieved_secret is None

    async def test_list_secrets_tenant_isolation(self, test_db_session: AsyncSession):
        """Test that list_secrets respects tenant isolation."""
        service = SecretsService(test_db_session)

        # Create secrets for different tenants
        tenant_a_secrets = []
        tenant_b_secrets = []

        for i in range(3):
            secret_data = SecretCreate(name=f"Tenant A Secret {i}", value=f"value_a_{i}")
            secret = await service.create_secret("tenant-a", secret_data)
            tenant_a_secrets.append(secret)

        for i in range(2):
            secret_data = SecretCreate(name=f"Tenant B Secret {i}", value=f"value_b_{i}")
            secret = await service.create_secret("tenant-b", secret_data)
            tenant_b_secrets.append(secret)

        # Retrieve secrets for each tenant
        retrieved_a = await service.list_secrets("tenant-a")
        retrieved_b = await service.list_secrets("tenant-b")

        assert len(retrieved_a) == 3
        assert len(retrieved_b) == 2

        # Verify tenant isolation
        assert all(secret.tenant_id == "tenant-a" for secret in retrieved_a)
        assert all(secret.tenant_id == "tenant-b" for secret in retrieved_b)

    async def test_list_secrets_filter_by_type(self, test_db_session: AsyncSession):
        """Test filtering secrets by type."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create secrets of different types
        secret_types = [SecretType.API_KEY, SecretType.ACCESS_TOKEN, SecretType.DATABASE_URL]
        for i, secret_type in enumerate(secret_types):
            secret_data = SecretCreate(
                name=f"Secret {i}",
                value=f"value_{i}",
                secret_type=secret_type
            )
            await service.create_secret(tenant_id, secret_data)

        # Filter by API_KEY type
        api_key_secrets = await service.list_secrets(tenant_id, secret_type=SecretType.API_KEY)

        assert len(api_key_secrets) == 1
        assert api_key_secrets[0].secret_type == SecretType.API_KEY

    async def test_list_secrets_include_inactive(self, test_db_session: AsyncSession):
        """Test including inactive secrets in list."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create active and inactive secrets
        active_data = SecretCreate(name="Active Secret", value="active_value")
        active_secret = await service.create_secret(tenant_id, active_data)

        inactive_data = SecretCreate(name="Inactive Secret", value="inactive_value")
        inactive_secret = await service.create_secret(tenant_id, inactive_data)

        # Deactivate one secret
        update_data = SecretUpdate(is_active=False)
        await service.update_secret(tenant_id, inactive_secret.id, update_data)

        # List only active secrets (default)
        active_only = await service.list_secrets(tenant_id)
        assert len(active_only) == 1
        assert active_only[0].id == active_secret.id

        # List all secrets including inactive
        all_secrets = await service.list_secrets(tenant_id, include_inactive=True)
        assert len(all_secrets) == 2

    async def test_list_secrets_pagination(self, test_db_session: AsyncSession):
        """Test pagination in list_secrets."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create multiple secrets
        for i in range(10):
            secret_data = SecretCreate(name=f"Secret {i:02d}", value=f"value_{i}")
            await service.create_secret(tenant_id, secret_data)

        # Test pagination
        page_1 = await service.list_secrets(tenant_id, limit=3, offset=0)
        page_2 = await service.list_secrets(tenant_id, limit=3, offset=3)

        assert len(page_1) == 3
        assert len(page_2) == 3

        # Verify different secrets
        page_1_ids = {secret.id for secret in page_1}
        page_2_ids = {secret.id for secret in page_2}
        assert page_1_ids.isdisjoint(page_2_ids)

    async def test_update_secret_success(self, test_db_session: AsyncSession):
        """Test updating a secret successfully."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create a secret first
        secret_data = SecretCreate(
            name="Original Secret",
            description="Original description",
            value="original_value"
        )
        created_secret = await service.create_secret(tenant_id, secret_data)

        # Update the secret
        update_data = SecretUpdate(
            name="Updated Secret",
            description="Updated description",
            secret_type=SecretType.API_KEY
        )
        updated_secret = await service.update_secret(tenant_id, created_secret.id, update_data, "admin_user")

        assert updated_secret is not None
        assert updated_secret.name == "Updated Secret"
        assert updated_secret.description == "Updated description"
        assert updated_secret.secret_type == SecretType.API_KEY

    async def test_update_secret_value(self, test_db_session: AsyncSession):
        """Test updating secret value."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create a secret first
        secret_data = SecretCreate(name="Value Test", value="original_value")
        created_secret = await service.create_secret(tenant_id, secret_data)

        # Update the secret value
        update_data = SecretUpdate(value="new_secret_value")
        updated_secret = await service.update_secret(tenant_id, created_secret.id, update_data)

        assert updated_secret is not None
        assert updated_secret.has_value is True

        # Verify the encrypted value was updated in the database
        retrieved = await service.get_secret_by_id(tenant_id, created_secret.id)
        assert retrieved.updated_at > created_secret.updated_at

    async def test_update_secret_name_conflict(self, test_db_session: AsyncSession):
        """Test that updating to an existing name raises error."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create two secrets
        secret1_data = SecretCreate(name="Secret 1", value="value1")
        secret1 = await service.create_secret(tenant_id, secret1_data)

        secret2_data = SecretCreate(name="Secret 2", value="value2")
        secret2 = await service.create_secret(tenant_id, secret2_data)

        # Try to update secret2 to have the same name as secret1
        update_data = SecretUpdate(name="Secret 1")

        with pytest.raises(ValueError, match="already exists"):
            await service.update_secret(tenant_id, secret2.id, update_data)

    async def test_update_secret_wrong_tenant(self, test_db_session: AsyncSession):
        """Test that secrets cannot be updated by wrong tenant."""
        service = SecretsService(test_db_session)

        # Create secret for tenant-a
        secret_data = SecretCreate(name="Tenant A Secret", value="value")
        created_secret = await service.create_secret("tenant-a", secret_data)

        # Try to update with tenant-b
        update_data = SecretUpdate(name="Hacked Name")
        result = await service.update_secret("tenant-b", created_secret.id, update_data)

        assert result is None

    async def test_update_secret_nonexistent(self, test_db_session: AsyncSession):
        """Test updating nonexistent secret."""
        service = SecretsService(test_db_session)

        update_data = SecretUpdate(name="Does Not Exist")
        result = await service.update_secret("test-tenant", 99999, update_data)

        assert result is None

    async def test_delete_secret_success(self, test_db_session: AsyncSession):
        """Test deleting a secret successfully (soft delete)."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create a secret first
        secret_data = SecretCreate(name="Delete Me", value="delete_value")
        created_secret = await service.create_secret(tenant_id, secret_data)

        # Delete the secret
        success = await service.delete_secret(tenant_id, created_secret.id, "admin_user")

        assert success is True

        # Verify secret is soft deleted (inactive)
        retrieved_secret = await service.get_secret_by_id(tenant_id, created_secret.id)
        assert retrieved_secret is not None
        assert retrieved_secret.is_active is False

    async def test_delete_secret_wrong_tenant(self, test_db_session: AsyncSession):
        """Test that secrets cannot be deleted by wrong tenant."""
        service = SecretsService(test_db_session)

        # Create secret for tenant-a
        secret_data = SecretCreate(name="Tenant A Secret", value="value")
        created_secret = await service.create_secret("tenant-a", secret_data)

        # Try to delete with tenant-b
        success = await service.delete_secret("tenant-b", created_secret.id)

        assert success is False

        # Verify secret still exists and is active
        retrieved_secret = await service.get_secret_by_id("tenant-a", created_secret.id)
        assert retrieved_secret is not None
        assert retrieved_secret.is_active is True

    async def test_delete_secret_nonexistent(self, test_db_session: AsyncSession):
        """Test deleting nonexistent secret."""
        service = SecretsService(test_db_session)

        success = await service.delete_secret("test-tenant", 99999)
        assert success is False

    async def test_get_expiring_secrets(self, test_db_session: AsyncSession):
        """Test retrieving secrets that are expiring soon."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        now = datetime.utcnow()

        # Create secrets with various expiration dates
        secrets_data = [
            ("Expired Secret", now - timedelta(days=1)),      # Already expired
            ("Expiring Soon", now + timedelta(days=5)),       # Expires in 5 days
            ("Expiring Later", now + timedelta(days=60)),     # Expires in 60 days
            ("No Expiration", None),                          # Never expires
        ]

        for name, expires_at in secrets_data:
            secret_data = SecretCreate(
                name=name,
                value=f"value_{name.lower().replace(' ', '_')}",
                expires_at=expires_at
            )
            await service.create_secret(tenant_id, secret_data)

        # Get secrets expiring within 30 days
        expiring_secrets = await service.get_expiring_secrets(tenant_id, days_ahead=30)

        assert len(expiring_secrets) == 2  # Expired and Expiring Soon
        secret_names = [secret.name for secret in expiring_secrets]
        assert "Expired Secret" in secret_names
        assert "Expiring Soon" in secret_names
        assert "Expiring Later" not in secret_names
        assert "No Expiration" not in secret_names

    async def test_get_secrets_stats(self, test_db_session: AsyncSession):
        """Test getting secrets statistics."""
        service = SecretsService(test_db_session)
        tenant_id = "test-tenant"

        # Create various secrets
        secrets_data = [
            (SecretType.API_KEY, True),
            (SecretType.API_KEY, True),
            (SecretType.API_KEY, False),     # Inactive
            (SecretType.ACCESS_TOKEN, True),
            (SecretType.DATABASE_URL, True),
        ]

        for i, (secret_type, is_active) in enumerate(secrets_data):
            secret_data = SecretCreate(
                name=f"Secret {i}",
                value=f"value_{i}",
                secret_type=secret_type
            )
            created_secret = await service.create_secret(tenant_id, secret_data)

            if not is_active:
                update_data = SecretUpdate(is_active=False)
                await service.update_secret(tenant_id, created_secret.id, update_data)

        # Create an expiring secret
        expiring_data = SecretCreate(
            name="Expiring Secret",
            value="expiring_value",
            expires_at=datetime.utcnow() + timedelta(days=15)
        )
        await service.create_secret(tenant_id, expiring_data)

        stats = await service.get_secrets_stats(tenant_id)

        assert stats["total_secrets"] == 6
        assert stats["active_secrets"] == 5
        assert stats["inactive_secrets"] == 1
        assert stats["expiring_soon"] == 1  # One expiring within 30 days

        # Check type breakdown
        by_type = stats["by_type"]
        assert by_type[SecretType.API_KEY] == 2    # Only active ones
        assert by_type[SecretType.ACCESS_TOKEN] == 1
        assert by_type[SecretType.DATABASE_URL] == 1
        assert by_type[SecretType.OTHER] == 1      # The expiring secret


@pytest.mark.unit
@pytest.mark.asyncio
class TestSecretsServiceEncryption:
    """Test encryption/decryption functionality."""

    def test_encrypt_secret_static_method(self):
        """Test the static encryption method."""
        value = "test_secret_value"
        encrypted = SecretsService._encrypt_secret(value)

        assert encrypted != value
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_verify_secret_static_method(self):
        """Test the static verification method."""
        value = "test_secret_value"
        encrypted = SecretsService._encrypt_secret(value)

        # Correct value should verify
        assert SecretsService._verify_secret(value, encrypted) is True

        # Wrong value should not verify
        assert SecretsService._verify_secret("wrong_value", encrypted) is False

    def test_encryption_is_consistent(self):
        """Test that encryption produces consistent results for verification."""
        value = "consistent_test_value"

        # Encrypt the same value multiple times
        encrypted1 = SecretsService._encrypt_secret(value)
        encrypted2 = SecretsService._encrypt_secret(value)

        # Encrypted values should be different (due to salt)
        assert encrypted1 != encrypted2

        # But both should verify against the original value
        assert SecretsService._verify_secret(value, encrypted1) is True
        assert SecretsService._verify_secret(value, encrypted2) is True


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
class TestSecretsServiceTenantIsolation:
    """Focused tests for tenant isolation in secrets service."""

    async def test_comprehensive_tenant_isolation(self, test_db_session: AsyncSession):
        """Comprehensive test of tenant isolation across all operations."""
        service = SecretsService(test_db_session)

        # Setup data for multiple tenants
        tenants = ["tenant-alpha", "tenant-beta", "tenant-gamma"]
        created_secrets = {}

        for tenant_id in tenants:
            tenant_secrets = []
            for i in range(2):
                secret_data = SecretCreate(
                    name=f"Secret {i}",
                    value=f"value_{tenant_id}_{i}",
                    secret_type=SecretType.API_KEY
                )
                secret = await service.create_secret(tenant_id, secret_data)
                tenant_secrets.append(secret)
            created_secrets[tenant_id] = tenant_secrets

        # Test that each tenant can only access their own data
        for tenant_id in tenants:
            tenant_secrets = await service.list_secrets(tenant_id)

            # Should only see own secrets
            assert len(tenant_secrets) == 2
            assert all(secret.tenant_id == tenant_id for secret in tenant_secrets)

            # Test cross-tenant access attempts
            for other_tenant in tenants:
                if other_tenant != tenant_id:
                    other_secrets = created_secrets[other_tenant]
                    for other_secret in other_secrets:
                        # Should not be able to access other tenant's secrets
                        result = await service.get_secret_by_id(tenant_id, other_secret.id)
                        assert result is None

                        # Should not be able to update other tenant's secrets
                        update_data = SecretUpdate(name="Hacked")
                        update_result = await service.update_secret(
                            tenant_id, other_secret.id, update_data
                        )
                        assert update_result is None

                        # Should not be able to delete other tenant's secrets
                        delete_result = await service.delete_secret(tenant_id, other_secret.id)
                        assert delete_result is False

    async def test_tenant_data_consistency(self, test_db_session: AsyncSession):
        """Test that tenant data remains consistent across operations."""
        service = SecretsService(test_db_session)
        tenant_id = "consistency-test"

        # Initial state - no secrets
        initial_stats = await service.get_secrets_stats(tenant_id)
        assert initial_stats["total_secrets"] == 0

        # Create secrets
        created_secrets = []
        for i in range(5):
            secret_data = SecretCreate(name=f"Secret {i}", value=f"value_{i}")
            secret = await service.create_secret(tenant_id, secret_data)
            created_secrets.append(secret)

        stats_after_create = await service.get_secrets_stats(tenant_id)
        assert stats_after_create["total_secrets"] == 5
        assert stats_after_create["active_secrets"] == 5

        # Update some secrets
        for secret in created_secrets[:3]:
            update_data = SecretUpdate(description="Updated description")
            await service.update_secret(tenant_id, secret.id, update_data)

        stats_after_update = await service.get_secrets_stats(tenant_id)
        assert stats_after_update["total_secrets"] == 5  # Count unchanged

        # Delete some secrets (soft delete)
        for secret in created_secrets[:2]:
            await service.delete_secret(tenant_id, secret.id)

        stats_after_delete = await service.get_secrets_stats(tenant_id)
        assert stats_after_delete["total_secrets"] == 5     # Total unchanged
        assert stats_after_delete["active_secrets"] == 3    # Active reduced
        assert stats_after_delete["inactive_secrets"] == 2  # Inactive increased

        # Verify remaining active secrets
        remaining_secrets = await service.list_secrets(tenant_id)
        assert len(remaining_secrets) == 3
        assert all(secret.tenant_id == tenant_id for secret in remaining_secrets)
        assert all(secret.is_active for secret in remaining_secrets)

    async def test_secret_name_isolation_across_tenants(self, test_db_session: AsyncSession):
        """Test that secret names are properly isolated across tenants."""
        service = SecretsService(test_db_session)

        secret_name = "Shared Secret Name"

        # Create secrets with same name in different tenants
        tenants = ["tenant-a", "tenant-b", "tenant-c"]
        for tenant_id in tenants:
            secret_data = SecretCreate(
                name=secret_name,
                value=f"value_for_{tenant_id}"
            )
            await service.create_secret(tenant_id, secret_data)

        # Verify each tenant can access their own secret by name
        for tenant_id in tenants:
            secret = await service.get_secret_by_name(tenant_id, secret_name)
            assert secret is not None
            assert secret.tenant_id == tenant_id
            assert secret.name == secret_name

        # Verify each tenant only sees their own secret in lists
        for tenant_id in tenants:
            secrets = await service.list_secrets(tenant_id)
            assert len(secrets) == 1
            assert secrets[0].tenant_id == tenant_id
            assert secrets[0].name == secret_name
