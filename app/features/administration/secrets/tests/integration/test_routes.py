"""
Integration tests for Secrets slice routes and API endpoints.

Tests the API layer with proper tenant isolation,
HTTP status codes, and HTMX functionality for the Secrets slice.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.features.administration.secrets.models import SecretType, SecretCreate
from app.features.administration.secrets.services import SecretsService


@pytest.mark.api
@pytest.mark.asyncio
class TestSecretsRoutes:
    """Test suite for secrets API routes."""

    async def test_secrets_dashboard_loads(self, client: AsyncClient):
        """Test that the secrets dashboard loads successfully."""
        response = await client.get("/features/administration/secrets/")

        assert response.status_code == 200
        assert "Secrets Management" in response.text
        assert "Create Secret" in response.text

    async def test_create_secret_modal_form(self, client: AsyncClient):
        """Test loading the create secret modal form."""
        response = await client.get("/features/administration/secrets/partials/form")

        assert response.status_code == 200
        assert "Create Secret" in response.text
        assert "form" in response.text.lower()
        assert "name" in response.text.lower()
        assert "value" in response.text.lower()

    async def test_create_secret_via_form_submission(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test creating a secret via HTMX form submission."""
        form_data = {
            "name": "Test API Key",
            "description": "Test description",
            "secret_type": SecretType.API_KEY.value,
            "value": "test_secret_value"
        }

        response = await client.post("/features/administration/secrets/new", data=form_data)

        # Should return 204 for successful HTMX form submission
        assert response.status_code == 204

        # Verify secret was created in database
        service = SecretsService(test_db_session)
        secrets = await service.list_secrets("default_tenant")
        assert len(secrets) == 1
        assert secrets[0].name == "Test API Key"

    async def test_create_secret_minimal_data(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test creating secret with minimal required data."""
        form_data = {
            "name": "Minimal Secret",
            "value": "minimal_value"
        }

        response = await client.post("/features/administration/secrets/new", data=form_data)

        assert response.status_code == 204

        # Verify secret was created
        service = SecretsService(test_db_session)
        secrets = await service.list_secrets("default_tenant")
        assert len(secrets) == 1
        assert secrets[0].name == "Minimal Secret"
        assert secrets[0].secret_type == SecretType.OTHER  # Default

    async def test_create_secret_duplicate_name_error(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test that creating duplicate secret names returns error."""
        # Create first secret
        form_data = {
            "name": "Duplicate Secret",
            "value": "value1"
        }
        await client.post("/features/administration/secrets/new", data=form_data)

        # Try to create duplicate
        response = await client.post("/features/administration/secrets/new", data=form_data)

        assert response.status_code == 400
        assert "already exists" in response.text

    async def test_create_secret_validation_errors(self, client: AsyncClient):
        """Test form validation errors."""
        # Missing required fields
        form_data = {}
        response = await client.post("/features/administration/secrets/new", data=form_data)
        assert response.status_code == 422  # FastAPI validation error

        # Empty name
        form_data = {"name": "", "value": "test_value"}
        response = await client.post("/features/administration/secrets/new", data=form_data)
        assert response.status_code == 422

        # Empty value
        form_data = {"name": "Test Secret", "value": ""}
        response = await client.post("/features/administration/secrets/new", data=form_data)
        assert response.status_code == 422

    async def test_edit_secret_modal_form(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test loading the edit secret modal form."""
        # Create a secret first
        service = SecretsService(test_db_session)
        secret_data = SecretCreate(
            name="Edit Test Secret",
            description="Original description",
            value="original_value"
        )
        created_secret = await service.create_secret("default_tenant", secret_data)

        # Load edit form
        response = await client.get(f"/features/administration/secrets/{created_secret.id}/edit")

        assert response.status_code == 200
        assert "Edit Secret" in response.text
        assert "Edit Test Secret" in response.text
        assert "Original description" in response.text

    async def test_edit_secret_nonexistent(self, client: AsyncClient):
        """Test loading edit form for nonexistent secret."""
        response = await client.get("/features/administration/secrets/99999/edit")

        assert response.status_code == 404

    async def test_update_secret_via_form_submission(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test updating a secret via HTMX form submission."""
        # Create a secret first
        service = SecretsService(test_db_session)
        secret_data = SecretCreate(
            name="Update Test Secret",
            description="Original description",
            value="original_value"
        )
        created_secret = await service.create_secret("default_tenant", secret_data)

        # Update the secret
        form_data = {
            "name": "Updated Secret Name",
            "description": "Updated description",
            "secret_type": SecretType.ACCESS_TOKEN.value
        }

        response = await client.post(f"/features/administration/secrets/{created_secret.id}/edit", data=form_data)

        # Should return 204 for successful HTMX form submission
        assert response.status_code == 204

        # Verify secret was updated
        updated_secret = await service.get_secret_by_id("default_tenant", created_secret.id)
        assert updated_secret.name == "Updated Secret Name"
        assert updated_secret.description == "Updated description"
        assert updated_secret.secret_type == SecretType.ACCESS_TOKEN

    async def test_update_secret_nonexistent(self, client: AsyncClient):
        """Test updating nonexistent secret."""
        form_data = {"name": "Does Not Exist"}
        response = await client.post("/features/administration/secrets/99999/edit", data=form_data)

        assert response.status_code == 404

    async def test_delete_secret_success(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test deleting a secret successfully."""
        # Create a secret first
        service = SecretsService(test_db_session)
        secret_data = SecretCreate(name="Delete Test Secret", value="delete_value")
        created_secret = await service.create_secret("default_tenant", secret_data)

        # Delete the secret
        response = await client.delete(f"/features/administration/secrets/{created_secret.id}/delete")

        # Should return 204 for successful HTMX delete
        assert response.status_code == 204

        # Verify secret was soft deleted
        deleted_secret = await service.get_secret_by_id("default_tenant", created_secret.id)
        assert deleted_secret.is_active is False

    async def test_delete_secret_nonexistent(self, client: AsyncClient):
        """Test deleting nonexistent secret."""
        response = await client.delete("/features/administration/secrets/99999/delete")

        assert response.status_code == 404

    async def test_list_secrets_api_endpoint(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test the API endpoint for listing secrets."""
        # Create some secrets
        service = SecretsService(test_db_session)
        for i in range(3):
            secret_data = SecretCreate(
                name=f"API Secret {i}",
                value=f"api_value_{i}",
                secret_type=SecretType.API_KEY
            )
            await service.create_secret("default_tenant", secret_data)

        # Call API endpoint
        response = await client.get("/features/administration/secrets/list")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("encrypted_value" not in secret for secret in data)  # Ensure no secret values exposed

    async def test_get_secret_api_endpoint(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test the API endpoint for getting a specific secret."""
        # Create a secret
        service = SecretsService(test_db_session)
        secret_data = SecretCreate(
            name="API Get Secret",
            description="Test description",
            value="api_value"
        )
        created_secret = await service.create_secret("default_tenant", secret_data)

        # Call API endpoint
        response = await client.get(f"/features/administration/secrets/{created_secret.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Get Secret"
        assert data["description"] == "Test description"
        assert "encrypted_value" not in data  # Ensure no secret value exposed

    async def test_get_secret_api_nonexistent(self, client: AsyncClient):
        """Test API endpoint for nonexistent secret."""
        response = await client.get("/features/administration/secrets/99999")

        assert response.status_code == 404

    async def test_secrets_stats_api_endpoint(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test the secrets statistics API endpoint."""
        # Create various secrets
        service = SecretsService(test_db_session)
        secrets_data = [
            (SecretType.API_KEY, True),
            (SecretType.API_KEY, True),
            (SecretType.ACCESS_TOKEN, True),
            (SecretType.DATABASE_URL, False),  # Will be deactivated
        ]

        for i, (secret_type, is_active) in enumerate(secrets_data):
            secret_data = SecretCreate(
                name=f"Stats Secret {i}",
                value=f"stats_value_{i}",
                secret_type=secret_type
            )
            created_secret = await service.create_secret("default_tenant", secret_data)

            if not is_active:
                from app.features.administration.secrets.models import SecretUpdate
                update_data = SecretUpdate(is_active=False)
                await service.update_secret("default_tenant", created_secret.id, update_data)

        # Call stats API endpoint
        response = await client.get("/features/administration/secrets/stats/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["total_secrets"] == 4
        assert data["active_secrets"] == 3
        assert data["inactive_secrets"] == 1
        assert SecretType.API_KEY in data["by_type"]


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
class TestSecretsRoutesTenantIsolation:
    """Test tenant isolation in secrets routes."""

    @patch('app.administration.routes.secrets_routes.get_tenant_id')
    async def test_dashboard_tenant_isolation(self, mock_get_tenant_id, client: AsyncClient, test_db_session: AsyncSession):
        """Test that dashboard only shows secrets for the correct tenant."""
        # Setup secrets for different tenants
        service = SecretsService(test_db_session)

        # Create secrets for tenant-a
        mock_get_tenant_id.return_value = "tenant-a"
        for i in range(2):
            secret_data = SecretCreate(name=f"Tenant A Secret {i}", value=f"value_a_{i}")
            await service.create_secret("tenant-a", secret_data)

        # Create secrets for tenant-b
        for i in range(3):
            secret_data = SecretCreate(name=f"Tenant B Secret {i}", value=f"value_b_{i}")
            await service.create_secret("tenant-b", secret_data)

        # Load dashboard for tenant-a
        response = await client.get("/features/administration/secrets/")

        assert response.status_code == 200
        # Should show tenant-a secrets but not tenant-b
        assert "Tenant A Secret" in response.text
        assert "Tenant B Secret" not in response.text

    @patch('app.administration.routes.secrets_routes.get_tenant_id')
    async def test_api_endpoints_tenant_isolation(self, mock_get_tenant_id, client: AsyncClient, test_db_session: AsyncSession):
        """Test that API endpoints respect tenant isolation."""
        service = SecretsService(test_db_session)

        # Create secret for tenant-a
        secret_data = SecretCreate(name="Tenant A Secret", value="tenant_a_value")
        tenant_a_secret = await service.create_secret("tenant-a", secret_data)

        # Create secret for tenant-b
        secret_data = SecretCreate(name="Tenant B Secret", value="tenant_b_value")
        tenant_b_secret = await service.create_secret("tenant-b", secret_data)

        # Set tenant context to tenant-a
        mock_get_tenant_id.return_value = "tenant-a"

        # List should only return tenant-a secrets
        response = await client.get("/features/administration/secrets/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Tenant A Secret"

        # Should be able to access tenant-a secret
        response = await client.get(f"/features/administration/secrets/{tenant_a_secret.id}")
        assert response.status_code == 200

        # Should NOT be able to access tenant-b secret
        response = await client.get(f"/features/administration/secrets/{tenant_b_secret.id}")
        assert response.status_code == 404

    @patch('app.administration.routes.secrets_routes.get_tenant_id')
    async def test_form_operations_tenant_isolation(self, mock_get_tenant_id, client: AsyncClient, test_db_session: AsyncSession):
        """Test that form operations respect tenant isolation."""
        service = SecretsService(test_db_session)

        # Create secret for tenant-b
        secret_data = SecretCreate(name="Tenant B Secret", value="tenant_b_value")
        tenant_b_secret = await service.create_secret("tenant-b", secret_data)

        # Set tenant context to tenant-a
        mock_get_tenant_id.return_value = "tenant-a"

        # Should not be able to load edit form for tenant-b secret
        response = await client.get(f"/features/administration/secrets/{tenant_b_secret.id}/edit")
        assert response.status_code == 404

        # Should not be able to update tenant-b secret
        form_data = {"name": "Hacked Name"}
        response = await client.post(f"/features/administration/secrets/{tenant_b_secret.id}/edit", data=form_data)
        assert response.status_code == 404

        # Should not be able to delete tenant-b secret
        response = await client.delete(f"/features/administration/secrets/{tenant_b_secret.id}/delete")
        assert response.status_code == 404

        # Verify original secret is unchanged
        original_secret = await service.get_secret_by_id("tenant-b", tenant_b_secret.id)
        assert original_secret.name == "Tenant B Secret"
        assert original_secret.is_active is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestSecretsRoutesIntegration:
    """Integration tests for secrets routes."""

    async def test_complete_secret_lifecycle_via_web_interface(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test complete CRUD lifecycle through web interface."""
        # 1. Load dashboard (should be empty initially)
        response = await client.get("/features/administration/secrets/")
        assert response.status_code == 200
        assert "No secrets found" in response.text or "empty" in response.text.lower()

        # 2. Create a secret via form
        form_data = {
            "name": "Lifecycle Test Secret",
            "description": "Integration test secret",
            "secret_type": SecretType.API_KEY.value,
            "value": "lifecycle_test_value"
        }
        response = await client.post("/features/administration/secrets/new", data=form_data)
        assert response.status_code == 204

        # 3. Verify secret appears in dashboard
        response = await client.get("/features/administration/secrets/")
        assert response.status_code == 200
        assert "Lifecycle Test Secret" in response.text

        # 4. Get secret ID for further operations
        service = SecretsService(test_db_session)
        secrets = await service.list_secrets("default_tenant")
        assert len(secrets) == 1
        secret_id = secrets[0].id

        # 5. Load edit form
        response = await client.get(f"/features/administration/secrets/{secret_id}/edit")
        assert response.status_code == 200
        assert "Edit Secret" in response.text
        assert "Lifecycle Test Secret" in response.text

        # 6. Update the secret
        update_data = {
            "name": "Updated Lifecycle Secret",
            "description": "Updated description"
        }
        response = await client.post(f"/features/administration/secrets/{secret_id}/edit", data=update_data)
        assert response.status_code == 204

        # 7. Verify update in dashboard
        response = await client.get("/features/administration/secrets/")
        assert response.status_code == 200
        assert "Updated Lifecycle Secret" in response.text
        assert "Lifecycle Test Secret" not in response.text

        # 8. Delete the secret
        response = await client.delete(f"/features/administration/secrets/{secret_id}/delete")
        assert response.status_code == 204

        # 9. Verify secret is no longer visible in dashboard (soft deleted)
        response = await client.get("/features/administration/secrets/")
        assert response.status_code == 200
        assert "Updated Lifecycle Secret" not in response.text

    async def test_dashboard_statistics_integration(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test that dashboard statistics are correctly displayed."""
        service = SecretsService(test_db_session)

        # Create various secrets to test statistics
        secrets_data = [
            ("Active API Key 1", SecretType.API_KEY, True),
            ("Active API Key 2", SecretType.API_KEY, True),
            ("Active Token", SecretType.ACCESS_TOKEN, True),
            ("Inactive Secret", SecretType.OTHER, False),  # Will be deactivated
        ]

        for name, secret_type, is_active in secrets_data:
            secret_data = SecretCreate(name=name, value=f"value_{name.lower().replace(' ', '_')}", secret_type=secret_type)
            created_secret = await service.create_secret("default_tenant", secret_data)

            if not is_active:
                from app.features.administration.secrets.models import SecretUpdate
                update_data = SecretUpdate(is_active=False)
                await service.update_secret("default_tenant", created_secret.id, update_data)

        # Load dashboard and check statistics
        response = await client.get("/features/administration/secrets/")
        assert response.status_code == 200

        # Should show correct counts (exact HTML structure depends on template)
        assert "4" in response.text  # Total secrets
        assert "3" in response.text  # Active secrets

    async def test_error_handling_integration(self, client: AsyncClient):
        """Test error handling across the web interface."""
        # Test various error conditions
        error_scenarios = [
            # Missing form data
            ("/features/administration/secrets/new", "POST", {}, 422),
            # Nonexistent secret operations
            ("/features/administration/secrets/99999/edit", "GET", {}, 404),
            ("/features/administration/secrets/99999/edit", "POST", {"name": "test"}, 404),
            ("/features/administration/secrets/99999/delete", "DELETE", {}, 404),
            ("/features/administration/secrets/99999", "GET", {}, 404),
        ]

        for url, method, data, expected_status in error_scenarios:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, data=data)
            elif method == "DELETE":
                response = await client.delete(url)

            assert response.status_code == expected_status

    async def test_htmx_specific_functionality(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test HTMX-specific functionality and responses."""
        # Create a secret for testing
        form_data = {
            "name": "HTMX Test Secret",
            "value": "htmx_test_value"
        }
        response = await client.post("/features/administration/secrets/new", data=form_data)
        assert response.status_code == 204  # HTMX expects 204 for successful form submission

        # Verify HTMX headers are handled correctly
        headers = {"HX-Request": "true"}

        # Test modal form loading with HTMX header
        response = await client.get("/features/administration/secrets/partials/form", headers=headers)
        assert response.status_code == 200

        # Test form submission with HTMX header
        response = await client.post("/features/administration/secrets/new", data=form_data, headers=headers)
        # Should still work but return error due to duplicate name
        assert response.status_code == 400
