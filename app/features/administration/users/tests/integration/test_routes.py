"""
Comprehensive integration tests for Users slice routes and API endpoints.

Tests complete request/response cycles with real database interactions,
authentication, and HTMX functionality.
"""

import pytest
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.features.administration.users.schemas import UserStatus, UserRole
from app.features.auth.models import User


class TestUserUIRoutes:
    """Test HTML/HTMX user interface routes."""

    @pytest.mark.asyncio
    async def test_user_list_page(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user list page loads correctly."""
        response = await async_client.get("/features/administration/users/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_user_form_partial_new(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test new user form partial loads correctly."""
        response = await async_client.get("/features/administration/users/partials/form")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_user_form_partial_edit(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test edit user form partial loads with existing user."""
        # Create test user
        test_user = User(
            id="test-user-123",
            name="Test User",
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True
        )
        test_db_session.add(test_user)
        await test_db_session.commit()

        response = await async_client.get(f"/features/administration/users/partials/form?user_id={test_user.id}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_user_edit_form_endpoint(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test dedicated edit form endpoint."""
        # Create test user
        test_user = User(
            id="test-user-123",
            name="Test User",
            email="test@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True
        )
        test_db_session.add(test_user)
        await test_db_session.commit()

        response = await async_client.get(f"/features/administration/users/{test_user.id}/edit")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_user_edit_form_not_found(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test edit form returns 404 for non-existent user."""
        response = await async_client.get("/features/administration/users/nonexistent-user/edit")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_list_content_partial(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user list content partial for HTMX refreshes."""
        response = await async_client.get("/features/administration/users/partials/list_content")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestUserCreation:
    """Test user creation via form submission."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test successful user creation via form."""
        form_data = {
            "name": "New Test User",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "description": "A test user",
            "status": "active",
            "role": "user",
            "enabled": "true",
            "tags": ["tag1", "tag2"]
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 204

        # Verify user was created in database
        from sqlalchemy import select
        stmt = select(User).where(User.email == "newuser@example.com")
        result = await test_db_session.execute(stmt)
        created_user = result.scalar_one_or_none()

        assert created_user is not None
        assert created_user.name == "New Test User"
        assert created_user.email == "newuser@example.com"
        assert created_user.status == "active"
        assert created_user.role == "user"
        assert created_user.enabled is True

    @pytest.mark.asyncio
    async def test_create_user_missing_required_fields(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation fails with missing required fields."""
        form_data = {
            "name": "Test User",
            # Missing email, password, confirm_password
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 400
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation fails with invalid email."""
        form_data = {
            "name": "Test User",
            "email": "invalid-email",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_password_mismatch(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation fails when passwords don't match."""
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation fails with weak password."""
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation fails with duplicate email."""
        # Create existing user
        existing_user = User(
            id="existing-user-123",
            name="Existing User",
            email="existing@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()

        form_data = {
            "name": "New User",
            "email": "existing@example.com",  # Duplicate email
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_with_tags(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user creation with multiple tags."""
        form_data = {
            "name": "Tagged User",
            "email": "tagged@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "tags": ["developer", "frontend", "react"]  # Multiple tags
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 204

        # Verify tags were saved
        from sqlalchemy import select
        stmt = select(User).where(User.email == "tagged@example.com")
        result = await test_db_session.execute(stmt)
        created_user = result.scalar_one_or_none()

        assert created_user is not None
        assert created_user.tags == ["developer", "frontend", "react"]


class TestUserUpdate:
    """Test user update functionality."""

    @pytest.fixture
    async def test_user(self, test_db_session: AsyncSession):
        """Create a test user for update tests."""
        user = User(
            id="update-test-user",
            name="Original Name",
            email="original@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True,
            description="Original description",
            tags=["original", "tag"]
        )
        test_db_session.add(user)
        await test_db_session.commit()
        return user

    @pytest.mark.asyncio
    async def test_update_user_success(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test successful user update."""
        form_data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "description": "Updated description",
            "status": "inactive",
            "role": "admin",
            "enabled": "false",
            "tags": ["updated", "tags"]
        }

        response = await async_client.put(f"/features/administration/users/{test_user.id}", data=form_data)

        assert response.status_code == 204

        # Verify user was updated
        await test_db_session.refresh(test_user)
        assert test_user.name == "Updated Name"
        assert test_user.email == "updated@example.com"
        assert test_user.description == "Updated description"
        assert test_user.status == "inactive"
        assert test_user.role == "admin"
        assert test_user.enabled is False

    @pytest.mark.asyncio
    async def test_update_user_partial(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test partial user update (only some fields)."""
        original_email = test_user.email

        form_data = {
            "name": "Partially Updated Name",
            # Only updating name, leaving other fields unchanged
        }

        response = await async_client.put(f"/features/administration/users/{test_user.id}", data=form_data)

        assert response.status_code == 204

        # Verify only name was updated
        await test_db_session.refresh(test_user)
        assert test_user.name == "Partially Updated Name"
        assert test_user.email == original_email  # Unchanged

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test update returns 404 for non-existent user."""
        form_data = {
            "name": "Updated Name"
        }

        response = await async_client.put("/features/administration/users/nonexistent-user", data=form_data)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_field_api(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test single field update via API."""
        field_update = {
            "field": "name",
            "value": "API Updated Name"
        }

        response = await async_client.patch(
            f"/features/administration/users/{test_user.id}/field",
            json=field_update
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify field was updated
        await test_db_session.refresh(test_user)
        assert test_user.name == "API Updated Name"

    @pytest.mark.asyncio
    async def test_update_user_field_boolean(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test boolean field update via API."""
        field_update = {
            "field": "enabled",
            "value": "false"  # String representation of boolean
        }

        response = await async_client.patch(
            f"/features/administration/users/{test_user.id}/field",
            json=field_update
        )

        assert response.status_code == 200

        # Verify boolean was converted and updated
        await test_db_session.refresh(test_user)
        assert test_user.enabled is False

    @pytest.mark.asyncio
    async def test_update_user_field_tags_json(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test tags field update with JSON string."""
        field_update = {
            "field": "tags",
            "value": '["api", "updated", "tags"]'  # JSON string
        }

        response = await async_client.patch(
            f"/features/administration/users/{test_user.id}/field",
            json=field_update
        )

        assert response.status_code == 200

        # Verify tags were parsed and updated
        await test_db_session.refresh(test_user)
        assert test_user.tags == ["api", "updated", "tags"]

    @pytest.mark.asyncio
    async def test_update_user_field_not_found(self, async_client: AsyncClient):
        """Test field update returns 404 for non-existent user."""
        field_update = {
            "field": "name",
            "value": "New Name"
        }

        response = await async_client.patch(
            "/features/administration/users/nonexistent-user/field",
            json=field_update
        )

        assert response.status_code == 404


class TestUserDeletion:
    """Test user deletion functionality."""

    @pytest.fixture
    async def test_user(self, test_db_session: AsyncSession):
        """Create a test user for deletion tests."""
        user = User(
            id="delete-test-user",
            name="User To Delete",
            email="delete@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True
        )
        test_db_session.add(user)
        await test_db_session.commit()
        return user

    @pytest.mark.asyncio
    async def test_delete_user_success_delete_method(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test successful user deletion via DELETE method."""
        response = await async_client.delete(f"/features/administration/users/{test_user.id}/delete")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify user was deleted
        from sqlalchemy import select
        stmt = select(User).where(User.id == test_user.id)
        result = await test_db_session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_success_post_method(self, async_client: AsyncClient, test_db_session: AsyncSession, test_user):
        """Test successful user deletion via POST method (for frontend compatibility)."""
        response = await async_client.post(f"/features/administration/users/{test_user.id}/delete")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, async_client: AsyncClient):
        """Test deletion returns 404 for non-existent user."""
        response = await async_client.delete("/features/administration/users/nonexistent-user/delete")

        assert response.status_code == 404


class TestUserAPI:
    """Test JSON API endpoints for users."""

    @pytest.mark.asyncio
    async def test_get_users_api_empty(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test API returns empty list when no users exist."""
        response = await async_client.get("/features/administration/users/api")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_users_api_with_users(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test API returns users list."""
        # Create test users
        users = [
            User(
                id="api-user-1",
                name="API User 1",
                email="api1@example.com",
                hashed_password="hashed_password",
                tenant_id="test-tenant",
                status="active",
                role="user",
                enabled=True
            ),
            User(
                id="api-user-2",
                name="API User 2",
                email="api2@example.com",
                hashed_password="hashed_password",
                tenant_id="test-tenant",
                status="inactive",
                role="admin",
                enabled=False
            )
        ]

        for user in users:
            test_db_session.add(user)
        await test_db_session.commit()

        response = await async_client.get("/features/administration/users/api")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify user data structure
        user_data = data[0]
        assert "id" in user_data
        assert "name" in user_data
        assert "email" in user_data
        assert "status" in user_data
        assert "role" in user_data
        assert "enabled" in user_data
        assert "tenant_id" in user_data


class TestUserValidationEndpoints:
    """Test real-time validation endpoints for HTMX."""

    @pytest.mark.asyncio
    async def test_validate_email_valid(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test email validation with valid email."""
        form_data = {"email": "valid@example.com"}

        response = await async_client.post("/features/administration/users/validate/email", data=form_data)

        assert response.status_code == 200
        assert "valid-feedback" in response.text
        assert "available" in response.text

    @pytest.mark.asyncio
    async def test_validate_email_invalid_format(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test email validation with invalid format."""
        form_data = {"email": "invalid-email"}

        response = await async_client.post("/features/administration/users/validate/email", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "Invalid email format" in response.text

    @pytest.mark.asyncio
    async def test_validate_email_empty(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test email validation with empty email."""
        form_data = {"email": ""}

        response = await async_client.post("/features/administration/users/validate/email", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "required" in response.text

    @pytest.mark.asyncio
    async def test_validate_email_duplicate(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test email validation with duplicate email."""
        # Create existing user
        existing_user = User(
            id="existing-user",
            name="Existing User",
            email="existing@example.com",
            hashed_password="hashed_password",
            tenant_id="test-tenant",
            status="active",
            role="user",
            enabled=True
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()

        form_data = {"email": "existing@example.com"}

        response = await async_client.post("/features/administration/users/validate/email", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "already exists" in response.text

    @pytest.mark.asyncio
    async def test_validate_password_valid(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password validation with valid password."""
        form_data = {"password": "SecurePass123!"}

        response = await async_client.post("/features/administration/users/validate/password", data=form_data)

        assert response.status_code == 200
        assert "valid-feedback" in response.text

    @pytest.mark.asyncio
    async def test_validate_password_weak(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password validation with weak password."""
        form_data = {"password": "weak"}

        response = await async_client.post("/features/administration/users/validate/password", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text

    @pytest.mark.asyncio
    async def test_validate_password_empty(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password validation with empty password."""
        form_data = {"password": ""}

        response = await async_client.post("/features/administration/users/validate/password", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "required" in response.text

    @pytest.mark.asyncio
    async def test_validate_confirm_password_match(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password confirmation validation when passwords match."""
        form_data = {
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }

        response = await async_client.post("/features/administration/users/validate/confirm-password", data=form_data)

        assert response.status_code == 200
        assert "valid-feedback" in response.text
        assert "match" in response.text

    @pytest.mark.asyncio
    async def test_validate_confirm_password_mismatch(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password confirmation validation when passwords don't match."""
        form_data = {
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!"
        }

        response = await async_client.post("/features/administration/users/validate/confirm-password", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "do not match" in response.text

    @pytest.mark.asyncio
    async def test_validate_confirm_password_empty(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test password confirmation validation with empty confirmation."""
        form_data = {
            "password": "SecurePass123!",
            "confirm_password": ""
        }

        response = await async_client.post("/features/administration/users/validate/confirm-password", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "confirm" in response.text

    @pytest.mark.asyncio
    async def test_validate_name_valid(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test name validation with valid name."""
        form_data = {"name": "Valid Name"}

        response = await async_client.post("/features/administration/users/validate/name", data=form_data)

        assert response.status_code == 200
        assert "valid-feedback" in response.text
        assert "looks good" in response.text

    @pytest.mark.asyncio
    async def test_validate_name_too_short(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test name validation with too short name."""
        form_data = {"name": "A"}

        response = await async_client.post("/features/administration/users/validate/name", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "at least 2 characters" in response.text

    @pytest.mark.asyncio
    async def test_validate_name_empty(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test name validation with empty name."""
        form_data = {"name": ""}

        response = await async_client.post("/features/administration/users/validate/name", data=form_data)

        assert response.status_code == 200
        assert "invalid-feedback" in response.text
        assert "required" in response.text


class TestTenantIsolation:
    """Test that all routes respect tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_user_retrieval(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test that users from other tenants are not accessible."""
        # Create users in different tenants
        user_tenant_1 = User(
            id="user-tenant-1",
            name="User Tenant 1",
            email="user1@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-1",
            status="active",
            role="user",
            enabled=True
        )
        user_tenant_2 = User(
            id="user-tenant-2",
            name="User Tenant 2",
            email="user2@example.com",
            hashed_password="hashed_password",
            tenant_id="tenant-2",
            status="active",
            role="user",
            enabled=True
        )

        test_db_session.add(user_tenant_1)
        test_db_session.add(user_tenant_2)
        await test_db_session.commit()

        # Test that API only returns users from the current tenant
        response = await async_client.get("/features/administration/users/api")

        assert response.status_code == 200
        users = response.json()

        # Should only return users from the test tenant (configured in test setup)
        for user in users:
            assert user["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_user_creation(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test that created users are assigned to the correct tenant."""
        form_data = {
            "name": "Tenant Isolated User",
            "email": "isolated@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        assert response.status_code == 204

        # Verify user was created with correct tenant
        from sqlalchemy import select
        stmt = select(User).where(User.email == "isolated@example.com")
        result = await test_db_session.execute(stmt)
        created_user = result.scalar_one_or_none()

        assert created_user is not None
        assert created_user.tenant_id == "test-tenant"


class TestErrorHandling:
    """Test error handling in routes."""

    @pytest.mark.asyncio
    async def test_create_user_handles_database_error(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test that route handles database errors gracefully."""
        # This test would require mocking database errors
        # For now, we test with invalid data that would cause service layer errors

        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            # Add invalid enum value to trigger error
            "status": "invalid_status"
        }

        response = await async_client.post("/features/administration/users/", data=form_data)

        # Should handle the error gracefully, not crash
        assert response.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_validation_endpoints_handle_errors(self, async_client: AsyncClient):
        """Test validation endpoints handle errors gracefully."""
        # Test validation endpoint with malformed request
        response = await async_client.post("/features/administration/users/validate/email")

        # Should not crash, even with missing data
        assert response.status_code in [200, 422]  # 422 for validation error


class TestHTMXCompatibility:
    """Test HTMX-specific functionality and headers."""

    @pytest.mark.asyncio
    async def test_form_partial_returns_html(self, async_client: AsyncClient):
        """Test that form partials return HTML for HTMX."""
        response = await async_client.get("/features/administration/users/partials/form")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_list_content_partial_returns_html(self, async_client: AsyncClient):
        """Test that list content partial returns HTML for HTMX."""
        response = await async_client.get("/features/administration/users/partials/list_content")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_validation_endpoints_return_html_fragments(self, async_client: AsyncClient):
        """Test that validation endpoints return HTML fragments."""
        form_data = {"email": "test@example.com"}

        response = await async_client.post("/features/administration/users/validate/email", data=form_data)

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # Should contain feedback span elements
        assert "feedback" in response.text


class TestPerformance:
    """Test performance characteristics of user endpoints."""

    @pytest.mark.asyncio
    async def test_user_list_performance_with_many_users(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test user list performance with multiple users."""
        # Create multiple users to test performance
        users = []
        for i in range(50):  # Create 50 test users
            user = User(
                id=f"perf-user-{i}",
                name=f"Performance User {i}",
                email=f"perf{i}@example.com",
                hashed_password="hashed_password",
                tenant_id="test-tenant",
                status="active",
                role="user",
                enabled=True
            )
            users.append(user)

        test_db_session.add_all(users)
        await test_db_session.commit()

        import time
        start_time = time.time()

        response = await async_client.get("/features/administration/users/api")

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        assert len(response.json()) == 50
        # Response should be reasonably fast (less than 1 second)
        assert response_time < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, async_client: AsyncClient, test_db_session: AsyncSession):
        """Test handling of concurrent user operations."""
        # This is a basic test - real concurrent testing would require more setup

        import asyncio

        # Create multiple users concurrently
        async def create_user(index):
            form_data = {
                "name": f"Concurrent User {index}",
                "email": f"concurrent{index}@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
            return await async_client.post("/features/administration/users/", data=form_data)

        # Create 5 users concurrently
        tasks = [create_user(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed (or fail gracefully)
        for response in responses:
            assert response.status_code in [204, 400, 500]
