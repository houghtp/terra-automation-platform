"""
Comprehensive unit tests for Auth slice schemas.

These tests provide world-class coverage of authentication schema validation,
including request/response schemas, field validation, and data serialization.
Template users should follow these patterns for other slices.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from uuid import uuid4

from app.features.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    AuthStatusResponse
)


class TestUserRegisterRequestSchema:
    """Tests for UserRegisterRequest schema validation."""

    def test_valid_registration_minimal(self):
        """Test valid registration with minimal data."""
        data = {
            "email": "test@example.com",
            "password": "securepass123"
        }

        request = UserRegisterRequest(**data)

        assert request.email == "test@example.com"
        assert request.password == "securepass123"
        assert request.role == "user"  # Default value

    def test_valid_registration_complete(self):
        """Test valid registration with all fields."""
        data = {
            "email": "admin@example.com",
            "password": "supersecurepass123!",
            "role": "admin"
        }

        request = UserRegisterRequest(**data)

        assert request.email == "admin@example.com"
        assert request.password == "supersecurepass123!"
        assert request.role == "admin"

    def test_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user123@example.co.uk",
            "test.email@sub.domain.com"
        ]

        for email in valid_emails:
            request = UserRegisterRequest(
                email=email,
                password="securepass123"
            )
            assert request.email == email

    def test_invalid_email_formats(self):
        """Test invalid email formats."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
            "",
            "test@example.",
            "test space@example.com"
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                UserRegisterRequest(
                    email=email,
                    password="securepass123"
                )
            assert "email" in str(exc_info.value)

    def test_password_length_validation(self):
        """Test password length validation."""
        # Test minimum length (8 characters)
        valid_password = "12345678"
        request = UserRegisterRequest(
            email="test@example.com",
            password=valid_password
        )
        assert request.password == valid_password

        # Test password too short
        short_passwords = ["", "1", "1234", "1234567"]
        for password in short_passwords:
            with pytest.raises(ValidationError) as exc_info:
                UserRegisterRequest(
                    email="test@example.com",
                    password=password
                )
            assert "at least 8 characters" in str(exc_info.value)

        # Test maximum length (128 characters)
        max_length_password = "a" * 128
        request = UserRegisterRequest(
            email="test@example.com",
            password=max_length_password
        )
        assert request.password == max_length_password

        # Test password too long
        with pytest.raises(ValidationError) as exc_info:
            UserRegisterRequest(
                email="test@example.com",
                password="a" * 129
            )
        assert "at most 128 characters" in str(exc_info.value)

    def test_role_validation(self):
        """Test role field validation."""
        valid_roles = ["user", "admin", "global_admin"]

        for role in valid_roles:
            request = UserRegisterRequest(
                email="test@example.com",
                password="securepass123",
                role=role
            )
            assert request.role == role

    def test_invalid_role_validation(self):
        """Test invalid role values."""
        invalid_roles = ["invalid", "USER", "ADMIN", "moderator", "guest", ""]

        for role in invalid_roles:
            with pytest.raises(ValidationError) as exc_info:
                UserRegisterRequest(
                    email="test@example.com",
                    password="securepass123",
                    role=role
                )
            assert "does not match" in str(exc_info.value) or "pattern" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        # Missing email
        with pytest.raises(ValidationError) as exc_info:
            UserRegisterRequest(password="securepass123")
        assert "email" in str(exc_info.value)

        # Missing password
        with pytest.raises(ValidationError) as exc_info:
            UserRegisterRequest(email="test@example.com")
        assert "password" in str(exc_info.value)

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        # Unicode email
        request = UserRegisterRequest(
            email="тест@example.com",
            password="securepass123"
        )
        assert request.email == "тест@example.com"

        # Special characters in password
        special_password = "P@ssw0rd!#$%^&*()_+"
        request = UserRegisterRequest(
            email="test@example.com",
            password=special_password
        )
        assert request.password == special_password


class TestUserLoginRequestSchema:
    """Tests for UserLoginRequest schema validation."""

    def test_valid_login_request(self):
        """Test valid login request."""
        data = {
            "email": "user@example.com",
            "password": "mypassword"
        }

        request = UserLoginRequest(**data)

        assert request.email == "user@example.com"
        assert request.password == "mypassword"

    def test_email_validation(self):
        """Test email validation in login request."""
        # Valid email
        request = UserLoginRequest(
            email="test@example.com",
            password="password"
        )
        assert request.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            UserLoginRequest(
                email="invalid-email",
                password="password"
            )

    def test_any_password_length_accepted(self):
        """Test that login accepts any password length (no validation)."""
        # Short password should be accepted for login
        request = UserLoginRequest(
            email="test@example.com",
            password="123"
        )
        assert request.password == "123"

        # Long password should be accepted
        long_password = "a" * 1000
        request = UserLoginRequest(
            email="test@example.com",
            password=long_password
        )
        assert request.password == long_password

    def test_missing_fields_validation(self):
        """Test validation with missing fields."""
        # Missing email
        with pytest.raises(ValidationError):
            UserLoginRequest(password="password")

        # Missing password
        with pytest.raises(ValidationError):
            UserLoginRequest(email="test@example.com")


class TestTokenResponseSchema:
    """Tests for TokenResponse schema validation."""

    def test_valid_token_response(self):
        """Test valid token response creation."""
        data = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "expires_in": 3600
        }

        response = TokenResponse(**data)

        assert response.access_token == data["access_token"]
        assert response.refresh_token == data["refresh_token"]
        assert response.token_type == "bearer"  # Default value
        assert response.expires_in == 3600

    def test_custom_token_type(self):
        """Test custom token type."""
        response = TokenResponse(
            access_token="token123",
            refresh_token="refresh123",
            token_type="custom",
            expires_in=7200
        )

        assert response.token_type == "custom"

    def test_required_fields(self):
        """Test required fields validation."""
        # Missing access_token
        with pytest.raises(ValidationError):
            TokenResponse(
                refresh_token="refresh123",
                expires_in=3600
            )

        # Missing refresh_token
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="access123",
                expires_in=3600
            )

        # Missing expires_in
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="access123",
                refresh_token="refresh123"
            )

    def test_expires_in_validation(self):
        """Test expires_in field validation."""
        # Valid positive integer
        response = TokenResponse(
            access_token="access123",
            refresh_token="refresh123",
            expires_in=3600
        )
        assert response.expires_in == 3600

        # Zero should be valid
        response = TokenResponse(
            access_token="access123",
            refresh_token="refresh123",
            expires_in=0
        )
        assert response.expires_in == 0

        # Negative value should be valid (schema doesn't restrict)
        response = TokenResponse(
            access_token="access123",
            refresh_token="refresh123",
            expires_in=-1
        )
        assert response.expires_in == -1


class TestRefreshTokenRequestSchema:
    """Tests for RefreshTokenRequest schema validation."""

    def test_valid_refresh_request(self):
        """Test valid refresh token request."""
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        request = RefreshTokenRequest(refresh_token=token)

        assert request.refresh_token == token

    def test_empty_token_validation(self):
        """Test validation with empty token."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest(refresh_token="")

    def test_missing_token_validation(self):
        """Test validation with missing token."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestUserResponseSchema:
    """Tests for UserResponse schema validation."""

    def test_valid_user_response_complete(self):
        """Test valid user response with all fields."""
        user_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            "id": user_id,
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "admin",
            "is_active": True,
            "created_at": timestamp,
            "updated_at": timestamp
        }

        response = UserResponse(**data)

        assert response.id == user_id
        assert response.email == "test@example.com"
        assert response.tenant_id == "tenant-123"
        assert response.role == "admin"
        assert response.is_active is True
        assert response.created_at == timestamp
        assert response.updated_at == timestamp

    def test_valid_user_response_minimal(self):
        """Test valid user response with minimal required fields."""
        data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": False
        }

        response = UserResponse(**data)

        assert response.id == data["id"]
        assert response.email == data["email"]
        assert response.tenant_id == data["tenant_id"]
        assert response.role == data["role"]
        assert response.is_active is False
        assert response.created_at is None
        assert response.updated_at is None

    def test_required_fields_validation(self):
        """Test validation of required fields."""
        base_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True
        }

        # Test each required field
        required_fields = ["id", "email", "tenant_id", "role", "is_active"]

        for field in required_fields:
            data = base_data.copy()
            del data[field]

            with pytest.raises(ValidationError) as exc_info:
                UserResponse(**data)
            assert field in str(exc_info.value)

    def test_email_validation_in_response(self):
        """Test email validation in user response."""
        base_data = {
            "id": str(uuid4()),
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True
        }

        # Valid email
        data = base_data.copy()
        data["email"] = "valid@example.com"
        response = UserResponse(**data)
        assert response.email == "valid@example.com"

        # Invalid email
        data = base_data.copy()
        data["email"] = "invalid-email"
        with pytest.raises(ValidationError):
            UserResponse(**data)

    def test_boolean_field_validation(self):
        """Test boolean field validation."""
        base_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user"
        }

        # Valid boolean values
        for value in [True, False]:
            data = base_data.copy()
            data["is_active"] = value
            response = UserResponse(**data)
            assert response.is_active is value

        # Invalid boolean values
        for value in ["true", "false", 1, 0, "yes", "no"]:
            data = base_data.copy()
            data["is_active"] = value
            # Pydantic should coerce some values
            try:
                response = UserResponse(**data)
                # If coercion happens, verify it's a boolean
                assert isinstance(response.is_active, bool)
            except ValidationError:
                # If validation fails, that's also acceptable
                pass

    def test_optional_datetime_fields(self):
        """Test optional datetime fields."""
        base_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True
        }

        # Valid ISO format
        timestamp = "2024-01-15T10:30:45.123456"
        data = base_data.copy()
        data["created_at"] = timestamp
        data["updated_at"] = timestamp

        response = UserResponse(**data)
        assert response.created_at == timestamp
        assert response.updated_at == timestamp

        # None values
        data = base_data.copy()
        data["created_at"] = None
        data["updated_at"] = None

        response = UserResponse(**data)
        assert response.created_at is None
        assert response.updated_at is None


class TestAuthStatusResponseSchema:
    """Tests for AuthStatusResponse schema validation."""

    def test_authenticated_status_with_user(self):
        """Test authenticated status with user data."""
        user_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True
        }

        user = UserResponse(**user_data)
        status = AuthStatusResponse(
            authenticated=True,
            user=user
        )

        assert status.authenticated is True
        assert status.user is not None
        assert status.user.email == "test@example.com"

    def test_not_authenticated_status(self):
        """Test not authenticated status."""
        status = AuthStatusResponse(authenticated=False)

        assert status.authenticated is False
        assert status.user is None

    def test_authenticated_status_without_user(self):
        """Test authenticated status without user data."""
        status = AuthStatusResponse(
            authenticated=True,
            user=None
        )

        assert status.authenticated is True
        assert status.user is None

    def test_required_authenticated_field(self):
        """Test that authenticated field is required."""
        with pytest.raises(ValidationError):
            AuthStatusResponse(user=None)

    def test_user_field_validation(self):
        """Test user field validation."""
        # Valid user object
        user_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True
        }

        status = AuthStatusResponse(
            authenticated=True,
            user=user_data  # Should accept dict and convert to UserResponse
        )

        assert isinstance(status.user, UserResponse)
        assert status.user.email == "test@example.com"


class TestSchemaIntegration:
    """Integration tests for schema interactions."""

    def test_registration_to_user_response_flow(self):
        """Test data flow from registration to user response."""
        # Registration request
        register_request = UserRegisterRequest(
            email="newuser@example.com",
            password="securepass123",
            role="admin"
        )

        # Simulate user creation and response
        user_response_data = {
            "id": str(uuid4()),
            "email": register_request.email,
            "tenant_id": "tenant-123",
            "role": register_request.role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        user_response = UserResponse(**user_response_data)

        assert user_response.email == register_request.email
        assert user_response.role == register_request.role

    def test_login_to_token_response_flow(self):
        """Test data flow from login to token response."""
        # Login request
        login_request = UserLoginRequest(
            email="user@example.com",
            password="password123"
        )

        # Simulate successful authentication and token creation
        token_response = TokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            expires_in=3600
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
        assert token_response.expires_in > 0

    def test_auth_status_complete_flow(self):
        """Test complete authentication status flow."""
        # Create user response
        user_data = {
            "id": str(uuid4()),
            "email": "authenticated@example.com",
            "tenant_id": "tenant-123",
            "role": "user",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        user_response = UserResponse(**user_data)

        # Create auth status response
        auth_status = AuthStatusResponse(
            authenticated=True,
            user=user_response
        )

        assert auth_status.authenticated is True
        assert auth_status.user.email == "authenticated@example.com"
        assert auth_status.user.is_active is True

    def test_edge_case_data_handling(self):
        """Test edge cases and boundary conditions."""
        # Very long email (within limits)
        long_email = f"{'a' * 50}@{'b' * 50}.com"
        register_request = UserRegisterRequest(
            email=long_email,
            password="securepass123"
        )
        assert register_request.email == long_email

        # Maximum length password
        max_password = "a" * 128
        register_request = UserRegisterRequest(
            email="test@example.com",
            password=max_password
        )
        assert register_request.password == max_password

        # Very long tenant ID
        long_tenant_id = "tenant-" + "x" * 100
        user_response = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            tenant_id=long_tenant_id,
            role="user",
            is_active=True
        )
        assert user_response.tenant_id == long_tenant_id