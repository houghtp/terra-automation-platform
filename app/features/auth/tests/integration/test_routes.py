"""
Tests for authentication routes.
"""
import pytest
import json
from httpx import AsyncClient
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.auth.services import AuthService
from app.features.auth.models import User


@pytest.fixture
def auth_service():
    """Create auth service instance."""
    return AuthService()


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_db_session: AsyncSession):
    """Test successful user registration."""
    registration_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "role": "user"
    }

    response = await client.post(
        "/auth/register",
        json=registration_data,
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_db_session: AsyncSession):
    """Test registration with duplicate email."""
    registration_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "role": "user"
    }

    # First registration
    response1 = await client.post(
        "/auth/register",
        json=registration_data,
        headers={"x-tenant-id": "test-tenant"}
    )
    assert response1.status_code == 200

    # Second registration with same email
    response2 = await client.post(
        "/auth/register",
        json=registration_data,
        headers={"x-tenant-id": "test-tenant"}
    )
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_register_different_tenants(client: AsyncClient, test_db_session: AsyncSession):
    """Test registration with same email in different tenants."""
    registration_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "role": "user"
    }

    # Register in tenant 1
    response1 = await client.post(
        "/auth/register",
        json=registration_data,
        headers={"x-tenant-id": "tenant-1"}
    )
    assert response1.status_code == 200

    # Register with same email in tenant 2
    response2 = await client.post(
        "/auth/register",
        json=registration_data,
        headers={"x-tenant-id": "tenant-2"}
    )
    assert response2.status_code == 200


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test successful login."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Login
    login_data = {
        "email": email,
        "password": password
    }

    response = await client.post(
        "/auth/login",
        json=login_data,
        headers={"x-tenant-id": tenant_id}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test login with wrong password."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Login with wrong password
    login_data = {
        "email": email,
        "password": "wrongpassword"
    }

    response = await client.post(
        "/auth/login",
        json=login_data,
        headers={"x-tenant-id": tenant_id}
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password"
    }

    response = await client.post(
        "/auth/login",
        json=login_data,
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test successful token refresh."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    user = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Create tokens
    access_token, refresh_token = auth_service.create_tokens(user)

    # Refresh access token
    refresh_data = {
        "refresh_token": refresh_token
    }

    response = await client.post("/auth/refresh", json=refresh_data)

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != access_token  # New token should be different


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test refresh with invalid token."""
    refresh_data = {
        "refresh_token": "invalid.token.here"
    }

    response = await client.post("/auth/refresh", json=refresh_data)

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_success(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test getting current user information."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    user = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="admin"
    )
    await test_db_session.commit()

    # Create access token
    access_token, _ = auth_service.create_tokens(user)

    # Get current user
    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": tenant_id
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == email
    assert data["tenant_id"] == tenant_id
    assert data["role"] == "admin"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test getting current user without token."""
    response = await client.get(
        "/auth/me",
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test getting current user with invalid token."""
    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid.token.here",
            "x-tenant-id": "test-tenant"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_status_authenticated(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test auth status for authenticated user."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    user = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Create access token
    access_token, _ = auth_service.create_tokens(user)

    # Check auth status
    response = await client.get(
        "/auth/status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": tenant_id
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["authenticated"] is True
    assert "user" in data
    assert data["user"]["email"] == email


@pytest.mark.asyncio
async def test_auth_status_not_authenticated(client: AsyncClient):
    """Test auth status for unauthenticated user."""
    response = await client.get(
        "/auth/status",
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["authenticated"] is False
    assert "user" not in data or data["user"] is None


@pytest.mark.asyncio
async def test_login_form_page(client: AsyncClient):
    """Test login form page loads."""
    response = await client.get(
        "/auth/login",
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_register_form_page(client: AsyncClient):
    """Test register form page loads."""
    response = await client.get(
        "/auth/register",
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_login_form_submit_success(client: AsyncClient, auth_service: AuthService, test_db_session: AsyncSession):
    """Test login form submission."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Submit login form
    form_data = {
        "email": email,
        "password": password
    }

    response = await client.post(
        "/auth/login/form",
        data=form_data,
        headers={"x-tenant-id": tenant_id}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should contain success message or tokens
    content = response.text
    assert "successful" in content.lower() or "token" in content.lower()


@pytest.mark.asyncio
async def test_register_form_submit_success(client: AsyncClient):
    """Test register form submission."""
    form_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123",
        "role": "user"
    }

    response = await client.post(
        "/auth/register/form",
        data=form_data,
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should contain success message
    content = response.text
    assert "successful" in content.lower() or "welcome" in content.lower()


@pytest.mark.asyncio
async def test_register_form_submit_password_mismatch(client: AsyncClient):
    """Test register form submission with password mismatch."""
    form_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "confirm_password": "differentpassword",
        "role": "user"
    }

    response = await client.post(
        "/auth/register/form",
        data=form_data,
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should contain error message
    content = response.text
    assert "not match" in content.lower() or "error" in content.lower()


@pytest.mark.asyncio
async def test_login_form_submit_invalid_credentials(client: AsyncClient):
    """Test login form submission with invalid credentials."""
    form_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }

    response = await client.post(
        "/auth/login/form",
        data=form_data,
        headers={"x-tenant-id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should contain error message
    content = response.text
    assert "invalid" in content.lower() or "error" in content.lower()
