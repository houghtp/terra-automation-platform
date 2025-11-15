"""
Comprehensive tenant isolation integration tests.

This test suite ensures that users from different tenants cannot access each other's data
across all administration features, preventing cross-tenant data leakage.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.features.core.database import get_db
from app.features.auth.services import AuthService
from app.features.administration.tenants.services import TenantManagementService
from app.features.administration.tenants.schemas import TenantCreate, TenantTier, TenantStatus
from app.features.administration.users.services import UserManagementService
from app.features.administration.users.schemas import UserCreate, UserStatus, UserRole
from app.features.administration.secrets.services import SecretsManagementService
from app.features.administration.secrets.schemas import SecretCreate
from app.features.administration.smtp.services import SMTPManagementService
from app.features.administration.smtp.schemas import SMTPConfigurationCreate
from tests.conftest import TestDatabase
import json


class TestTenantIsolation:
    """
    Comprehensive tenant isolation security tests.

    Tests cross-tenant access prevention across all administration features:
    - Users
    - Secrets
    - SMTP configurations
    - Audit logs
    - Application logs
    """

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, test_db: TestDatabase):
        """Set up test data with multiple tenants and users."""
        self.db = test_db.session

        # Create test tenants
        tenant_service = TenantManagementService(self.db)

        self.tenant1_data = TenantCreate(
            name="TenantOne",
            description="First test tenant",
            status=TenantStatus.active,
            tier=TenantTier.professional,
            contact_email="contact@tenant1.com",
            contact_name="Tenant One Admin",
            max_users=10
        )

        self.tenant2_data = TenantCreate(
            name="TenantTwo",
            description="Second test tenant",
            status=TenantStatus.active,
            tier=TenantTier.professional,
            contact_email="contact@tenant2.com",
            contact_name="Tenant Two Admin",
            max_users=10
        )

        self.tenant1 = await tenant_service.create_tenant(self.tenant1_data)
        self.tenant2 = await tenant_service.create_tenant(self.tenant2_data)
        await self.db.commit()

        # Create test users in different tenants
        auth_service = AuthService()

        # Tenant 1 users
        self.tenant1_user = await auth_service.create_user(
            session=self.db,
            email="user1@tenant1.com",
            password="SecurePass123!",
            tenant_id=str(self.tenant1.id),
            role="user",
            name="Tenant1 User"
        )

        self.tenant1_admin = await auth_service.create_user(
            session=self.db,
            email="admin1@tenant1.com",
            password="SecurePass123!",
            tenant_id=str(self.tenant1.id),
            role="admin",
            name="Tenant1 Admin"
        )

        # Tenant 2 users
        self.tenant2_user = await auth_service.create_user(
            session=self.db,
            email="user2@tenant2.com",
            password="SecurePass123!",
            tenant_id=str(self.tenant2.id),
            role="user",
            name="Tenant2 User"
        )

        self.tenant2_admin = await auth_service.create_user(
            session=self.db,
            email="admin2@tenant2.com",
            password="SecurePass123!",
            tenant_id=str(self.tenant2.id),
            role="admin",
            name="Tenant2 Admin"
        )

        # Global admin
        self.global_admin = await auth_service.create_user(
            session=self.db,
            email="global@admin.com",
            password="SecurePass123!",
            tenant_id="global",
            role="global_admin",
            name="Global Admin"
        )

        await self.db.commit()

        # Create tenant-specific test data
        await self._create_tenant_specific_data()

    async def _create_tenant_specific_data(self):
        """Create tenant-specific data for testing isolation."""

        # Create secrets for each tenant
        secrets_service1 = SecretsManagementService(self.db, str(self.tenant1.id))
        secrets_service2 = SecretsManagementService(self.db, str(self.tenant2.id))

        await secrets_service1.create_secret(
            str(self.tenant1.id),
            SecretCreate(
                name="tenant1-api-key",
                description="Tenant 1 API Key",
                secret_value="secret-key-tenant1",
                tags=["api", "tenant1"]
            ),
            created_by=self.tenant1_admin.id
        )

        await secrets_service2.create_secret(
            str(self.tenant2.id),
            SecretCreate(
                name="tenant2-api-key",
                description="Tenant 2 API Key",
                secret_value="secret-key-tenant2",
                tags=["api", "tenant2"]
            ),
            created_by=self.tenant2_admin.id
        )

        # Create SMTP configurations for each tenant
        smtp_service1 = SMTPManagementService(self.db, str(self.tenant1.id))
        smtp_service2 = SMTPManagementService(self.db, str(self.tenant2.id))

        await smtp_service1.create_configuration(
            SMTPConfigurationCreate(
                name="tenant1-smtp",
                description="Tenant 1 SMTP",
                host="smtp.tenant1.com",
                port=587,
                username="smtp@tenant1.com",
                password="smtppass1",
                use_tls=True,
                use_ssl=False,
                tags=["smtp", "tenant1"]
            )
        )

        await smtp_service2.create_configuration(
            SMTPConfigurationCreate(
                name="tenant2-smtp",
                description="Tenant 2 SMTP",
                host="smtp.tenant2.com",
                port=587,
                username="smtp@tenant2.com",
                password="smtppass2",
                use_tls=True,
                use_ssl=False,
                tags=["smtp", "tenant2"]
            )
        )

        await self.db.commit()

    async def _get_auth_headers(self, user_email: str, password: str = "SecurePass123!") -> dict:
        """Get authentication headers for a user."""
        auth_service = AuthService()

        # Find user's tenant first
        from sqlalchemy import select
        from app.features.auth.models import User

        result = await self.db.execute(
            select(User.tenant_id).where(User.email == user_email, User.is_active == True)
        )
        tenant_id = result.scalar_one_or_none() or "global"

        user = await auth_service.authenticate_user(
            session=self.db,
            email=user_email,
            password=password,
            tenant_id=tenant_id
        )

        if not user:
            raise ValueError(f"Failed to authenticate user: {user_email}")

        access_token, _ = auth_service.create_tokens(user)
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.mark.asyncio
    async def test_user_isolation_via_api(self):
        """Test that users from different tenants cannot see each other via API."""

        # Get auth headers for tenant 1 user
        tenant1_headers = await self._get_auth_headers("user1@tenant1.com")
        tenant2_headers = await self._get_auth_headers("user2@tenant2.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Tenant 1 user tries to access users API
            response1 = await client.get(
                "/features/administration/users/api",
                headers=tenant1_headers
            )
            assert response1.status_code == 200
            users1 = response1.json()

            # Tenant 2 user tries to access users API
            response2 = await client.get(
                "/features/administration/users/api",
                headers=tenant2_headers
            )
            assert response2.status_code == 200
            users2 = response2.json()

            # Verify tenant isolation
            tenant1_emails = {user["email"] for user in users1}
            tenant2_emails = {user["email"] for user in users2}

            # Users should only see users from their own tenant
            assert "user1@tenant1.com" in tenant1_emails
            assert "admin1@tenant1.com" in tenant1_emails
            assert "user2@tenant2.com" not in tenant1_emails
            assert "admin2@tenant2.com" not in tenant1_emails

            assert "user2@tenant2.com" in tenant2_emails
            assert "admin2@tenant2.com" in tenant2_emails
            assert "user1@tenant1.com" not in tenant2_emails
            assert "admin1@tenant1.com" not in tenant2_emails

    @pytest.mark.asyncio
    async def test_secrets_isolation_via_api(self):
        """Test that secrets are isolated between tenants."""

        tenant1_headers = await self._get_auth_headers("admin1@tenant1.com")
        tenant2_headers = await self._get_auth_headers("admin2@tenant2.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Tenant 1 admin accesses secrets
            response1 = await client.get(
                "/features/administration/secrets/api",
                headers=tenant1_headers
            )
            assert response1.status_code == 200
            secrets1 = response1.json()

            # Tenant 2 admin accesses secrets
            response2 = await client.get(
                "/features/administration/secrets/api",
                headers=tenant2_headers
            )
            assert response2.status_code == 200
            secrets2 = response2.json()

            # Verify isolation
            secret1_names = {secret["name"] for secret in secrets1}
            secret2_names = {secret["name"] for secret in secrets2}

            assert "tenant1-api-key" in secret1_names
            assert "tenant2-api-key" not in secret1_names

            assert "tenant2-api-key" in secret2_names
            assert "tenant1-api-key" not in secret2_names

    @pytest.mark.asyncio
    async def test_smtp_isolation_via_api(self):
        """Test that SMTP configurations are isolated between tenants."""

        tenant1_headers = await self._get_auth_headers("admin1@tenant1.com")
        tenant2_headers = await self._get_auth_headers("admin2@tenant2.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Tenant 1 admin accesses SMTP configs
            response1 = await client.get(
                "/features/administration/smtp/api",
                headers=tenant1_headers
            )
            assert response1.status_code == 200
            configs1 = response1.json()

            # Tenant 2 admin accesses SMTP configs
            response2 = await client.get(
                "/features/administration/smtp/api",
                headers=tenant2_headers
            )
            assert response2.status_code == 200
            configs2 = response2.json()

            # Verify isolation
            config1_names = {config["name"] for config in configs1}
            config2_names = {config["name"] for config in configs2}

            assert "tenant1-smtp" in config1_names
            assert "tenant2-smtp" not in config1_names

            assert "tenant2-smtp" in config2_names
            assert "tenant1-smtp" not in config2_names

    @pytest.mark.asyncio
    async def test_audit_logs_isolation(self):
        """Test that audit logs are isolated between tenants."""

        tenant1_headers = await self._get_auth_headers("admin1@tenant1.com")
        tenant2_headers = await self._get_auth_headers("admin2@tenant2.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Tenant 1 admin accesses audit logs
            response1 = await client.get(
                "/features/administration/audit/api/logs",
                headers=tenant1_headers
            )
            assert response1.status_code == 200
            logs1 = response1.json()

            # Tenant 2 admin accesses audit logs
            response2 = await client.get(
                "/features/administration/audit/api/logs",
                headers=tenant2_headers
            )
            assert response2.status_code == 200
            logs2 = response2.json()

            # Verify that logs are tenant-specific
            # (This assumes audit logs contain tenant_id and are filtered properly)
            if logs1.get("logs"):
                for log in logs1["logs"]:
                    assert log.get("tenant_id") == str(self.tenant1.id)

            if logs2.get("logs"):
                for log in logs2["logs"]:
                    assert log.get("tenant_id") == str(self.tenant2.id)

    @pytest.mark.asyncio
    async def test_application_logs_isolation(self):
        """Test that application logs are isolated between tenants."""

        tenant1_headers = await self._get_auth_headers("admin1@tenant1.com")
        tenant2_headers = await self._get_auth_headers("admin2@tenant2.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Tenant 1 admin accesses logs
            response1 = await client.get(
                "/features/administration/logs/api",
                headers=tenant1_headers
            )
            assert response1.status_code == 200
            logs1 = response1.json()

            # Tenant 2 admin accesses logs
            response2 = await client.get(
                "/features/administration/logs/api",
                headers=tenant2_headers
            )
            assert response2.status_code == 200
            logs2 = response2.json()

            # Verify logs are tenant-specific
            if logs1.get("logs"):
                for log in logs1["logs"]:
                    assert log.get("tenant_id") == str(self.tenant1.id)

            if logs2.get("logs"):
                for log in logs2["logs"]:
                    assert log.get("tenant_id") == str(self.tenant2.id)

    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_access_other_tenants(self):
        """Test that tenant admins cannot access other tenant's data."""

        tenant1_admin_headers = await self._get_auth_headers("admin1@tenant1.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try to access tenant 2's users by manipulating headers
            response = await client.get(
                "/features/administration/users/api",
                headers={
                    **tenant1_admin_headers,
                    "x-tenant-id": str(self.tenant2.id)  # Try to override tenant
                }
            )

            # Should either get 403 forbidden or only see tenant 1 users
            if response.status_code == 200:
                users = response.json()
                user_emails = {user["email"] for user in users}
                # Should not see tenant 2 users even with header manipulation
                assert "user2@tenant2.com" not in user_emails
                assert "admin2@tenant2.com" not in user_emails

    @pytest.mark.asyncio
    async def test_global_admin_can_access_tenant_management(self):
        """Test that global admin can access tenant management but respects tenant isolation."""

        global_admin_headers = await self._get_auth_headers("global@admin.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Global admin should be able to access tenants
            response = await client.get(
                "/features/administration/tenants/api",
                headers=global_admin_headers
            )
            assert response.status_code == 200
            tenants = response.json()

            # Should see all tenants
            tenant_names = {tenant["name"] for tenant in tenants}
            assert "TenantOne" in tenant_names
            assert "TenantTwo" in tenant_names

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_tenants(self):
        """Test that regular users cannot access tenant management."""

        user_headers = await self._get_auth_headers("user1@tenant1.com")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Regular user should not be able to access tenants
            response = await client.get(
                "/features/administration/tenants/api",
                headers=user_headers
            )
            # Should get 403 Forbidden due to global admin requirement
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_jwt_token_contains_correct_tenant_id(self):
        """Test that JWT tokens contain the correct tenant ID for proper isolation."""

        from app.features.auth.jwt_utils import JWTUtils

        # Test tenant 1 user
        tenant1_headers = await self._get_auth_headers("user1@tenant1.com")
        token = tenant1_headers["Authorization"].replace("Bearer ", "")
        token_data = JWTUtils.verify_token(token)

        assert token_data is not None
        assert token_data.tenant_id == str(self.tenant1.id)
        assert token_data.email == "user1@tenant1.com"

        # Test tenant 2 user
        tenant2_headers = await self._get_auth_headers("user2@tenant2.com")
        token = tenant2_headers["Authorization"].replace("Bearer ", "")
        token_data = JWTUtils.verify_token(token)

        assert token_data is not None
        assert token_data.tenant_id == str(self.tenant2.id)
        assert token_data.email == "user2@tenant2.com"

        # Test global admin
        global_headers = await self._get_auth_headers("global@admin.com")
        token = global_headers["Authorization"].replace("Bearer ", "")
        token_data = JWTUtils.verify_token(token)

        assert token_data is not None
        assert token_data.tenant_id == "global"
        assert token_data.email == "global@admin.com"

    @pytest.mark.asyncio
    async def test_cross_tenant_record_access_blocked(self):
        """Test that direct record access across tenants is blocked."""

        tenant1_headers = await self._get_auth_headers("admin1@tenant1.com")

        # Get a secret from tenant 2 to try accessing it
        secrets_service2 = SecretsManagementService(self.db, str(self.tenant2.id))
        tenant2_secrets = await secrets_service2.list_secrets()

        if tenant2_secrets:
            tenant2_secret_id = tenant2_secrets[0].id

            async with AsyncClient(app=app, base_url="http://test") as client:
                # Tenant 1 admin tries to access tenant 2's secret
                response = await client.get(
                    f"/features/administration/secrets/{tenant2_secret_id}",
                    headers=tenant1_headers
                )
                # Should get 404 (not found) because it's filtered by tenant
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_service_level_tenant_isolation(self):
        """Test tenant isolation at the service level."""

        # Test UserManagementService isolation
        user_service1 = UserManagementService(self.db, str(self.tenant1.id))
        user_service2 = UserManagementService(self.db, str(self.tenant2.id))

        tenant1_users = await user_service1.list_users()
        tenant2_users = await user_service2.list_users()

        tenant1_emails = {user.email for user in tenant1_users}
        tenant2_emails = {user.email for user in tenant2_users}

        # Verify service-level isolation
        assert "user1@tenant1.com" in tenant1_emails
        assert "user2@tenant2.com" not in tenant1_emails

        assert "user2@tenant2.com" in tenant2_emails
        assert "user1@tenant1.com" not in tenant2_emails

        # Test SecretsManagementService isolation
        secrets_service1 = SecretsManagementService(self.db, str(self.tenant1.id))
        secrets_service2 = SecretsManagementService(self.db, str(self.tenant2.id))

        tenant1_secrets = await secrets_service1.list_secrets()
        tenant2_secrets = await secrets_service2.list_secrets()

        tenant1_secret_names = {secret.name for secret in tenant1_secrets}
        tenant2_secret_names = {secret.name for secret in tenant2_secrets}

        assert "tenant1-api-key" in tenant1_secret_names
        assert "tenant2-api-key" not in tenant1_secret_names

        assert "tenant2-api-key" in tenant2_secret_names
        assert "tenant1-api-key" not in tenant2_secret_names

    @pytest.mark.asyncio
    async def test_tenant_data_creation_isolation(self):
        """Test that data creation is properly scoped to the correct tenant."""

        # Create a new user via tenant 1 admin
        user_service1 = UserManagementService(self.db, str(self.tenant1.id))

        new_user_data = UserCreate(
            name="New User",
            email="newuser@tenant1.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            status=UserStatus.active,
            role=UserRole.user,
            enabled=True,
            tags=["test"]
        )

        new_user = await user_service1.create_user(new_user_data)
        await self.db.commit()

        # Verify the user was created in the correct tenant
        assert new_user.tenant_id == str(self.tenant1.id)

        # Verify tenant 2 service cannot see this user
        user_service2 = UserManagementService(self.db, str(self.tenant2.id))
        tenant2_user = await user_service2.get_user_by_email("newuser@tenant1.com")
        assert tenant2_user is None

        # But tenant 1 service can see it
        tenant1_user = await user_service1.get_user_by_email("newuser@tenant1.com")
        assert tenant1_user is not None
        assert tenant1_user.email == "newuser@tenant1.com"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
