"""
Comprehensive unit tests for Users slice models and schemas.

Tests all Pydantic models, enums, validation logic, and data transformations
without database dependencies.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from app.features.administration.users.models import (
    UserStatus, UserRole, UserCreate, UserUpdate, UserResponse,
    UserStats, UserSearchFilter, UserDashboardStats
)
from app.features.auth.models import User


class TestUserEnums:
    """Test user enumeration classes."""

    def test_user_status_values(self):
        """Test UserStatus enum has correct values."""
        assert UserStatus.ACTIVE == "active"
        assert UserStatus.INACTIVE == "inactive"
        assert UserStatus.SUSPENDED == "suspended"
        assert UserStatus.PENDING == "pending"

    def test_user_role_values(self):
        """Test UserRole enum has correct values."""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"
        assert UserRole.MODERATOR == "moderator"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert "active" in UserStatus
        assert "invalid_status" not in UserStatus
        assert "admin" in UserRole
        assert "super_admin" not in UserRole


class TestUserCreateSchema:
    """Test UserCreate schema validation and functionality."""

    def test_valid_user_creation(self):
        """Test creating a valid user."""
        user_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            description="Test user description",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
            enabled=True,
            tags=["tag1", "tag2"]
        )

        assert user_data.name == "Test User"
        assert user_data.email == "test@example.com"
        assert user_data.password == "SecurePass123!"
        assert user_data.confirm_password == "SecurePass123!"
        assert user_data.description == "Test user description"
        assert user_data.status == UserStatus.ACTIVE
        assert user_data.role == UserRole.USER
        assert user_data.enabled is True
        assert user_data.tags == ["tag1", "tag2"]

    def test_minimal_user_creation(self):
        """Test creating user with only required fields."""
        user_data = UserCreate(
            name="Minimal User",
            email="minimal@example.com",
            password="password123",
            confirm_password="password123"
        )

        assert user_data.name == "Minimal User"
        assert user_data.email == "minimal@example.com"
        assert user_data.description is None
        assert user_data.status == UserStatus.ACTIVE  # Default
        assert user_data.role == UserRole.USER  # Default
        assert user_data.enabled is True  # Default
        assert user_data.tags == []  # Default empty list

    def test_name_validation(self):
        """Test name field validation."""
        # Too short name
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="a",  # Too short (min 2)
                email="test@example.com",
                password="password123",
                confirm_password="password123"
            )
        assert "at least 2 characters" in str(exc_info.value)

        # Too long name
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="a" * 256,  # Too long (max 255)
                email="test@example.com",
                password="password123",
                confirm_password="password123"
            )
        assert "at most 255 characters" in str(exc_info.value)

    def test_email_validation(self):
        """Test email field validation."""
        # Invalid email format
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="Test User",
                email="invalid-email",
                password="password123",
                confirm_password="password123"
            )
        assert "email" in str(exc_info.value).lower()

    def test_password_validation(self):
        """Test password field validation."""
        # Too short password
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="short",  # Too short (min 8)
                confirm_password="short"
            )
        assert "at least 8 characters" in str(exc_info.value)

    def test_description_validation(self):
        """Test description field validation."""
        # Too long description
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="password123",
                confirm_password="password123",
                description="a" * 1001  # Too long (max 1000)
            )
        assert "at most 1000 characters" in str(exc_info.value)

    def test_enum_validation(self):
        """Test enum field validation."""
        # Invalid status
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="password123",
                confirm_password="password123",
                status="invalid_status"
            )

        # Invalid role
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test User",
                email="test@example.com",
                password="password123",
                confirm_password="password123",
                role="invalid_role"
            )


class TestUserUpdateSchema:
    """Test UserUpdate schema validation and functionality."""

    def test_empty_update(self):
        """Test creating empty update schema."""
        update_data = UserUpdate()
        update_dict = update_data.model_dump(exclude_unset=True)
        assert update_dict == {}

    def test_partial_update(self):
        """Test partial user update."""
        update_data = UserUpdate(
            name="Updated Name",
            status=UserStatus.INACTIVE
        )

        assert update_data.name == "Updated Name"
        assert update_data.status == UserStatus.INACTIVE
        assert update_data.email is None
        assert update_data.description is None

    def test_full_update(self):
        """Test full user update."""
        update_data = UserUpdate(
            name="Updated User",
            email="updated@example.com",
            description="Updated description",
            status=UserStatus.SUSPENDED,
            role=UserRole.ADMIN,
            enabled=False,
            tags=["updated", "tags"]
        )

        assert update_data.name == "Updated User"
        assert update_data.email == "updated@example.com"
        assert update_data.description == "Updated description"
        assert update_data.status == UserStatus.SUSPENDED
        assert update_data.role == UserRole.ADMIN
        assert update_data.enabled is False
        assert update_data.tags == ["updated", "tags"]

    def test_update_validation(self):
        """Test update field validation."""
        # Invalid name length
        with pytest.raises(ValidationError):
            UserUpdate(name="a")  # Too short

        # Invalid email format
        with pytest.raises(ValidationError):
            UserUpdate(email="invalid-email")

        # Invalid description length
        with pytest.raises(ValidationError):
            UserUpdate(description="a" * 1001)  # Too long


class TestUserResponseSchema:
    """Test UserResponse schema functionality."""

    def test_user_response_creation(self):
        """Test creating user response schema."""
        response = UserResponse(
            id="user-123",
            name="Test User",
            email="test@example.com",
            description="Test description",
            status="active",
            role="user",
            enabled=True,
            tags=["tag1", "tag2"],
            tenant_id="tenant-123",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00"
        )

        assert response.id == "user-123"
        assert response.name == "Test User"
        assert response.email == "test@example.com"
        assert response.description == "Test description"
        assert response.status == "active"
        assert response.role == "user"
        assert response.enabled is True
        assert response.tags == ["tag1", "tag2"]
        assert response.tenant_id == "tenant-123"
        assert response.is_active is True
        assert response.created_at == "2024-01-01T00:00:00"
        assert response.updated_at == "2024-01-02T00:00:00"

    def test_user_response_minimal(self):
        """Test creating minimal user response."""
        response = UserResponse(
            id="user-123",
            name="Test User",
            email="test@example.com",
            status="active",
            role="user",
            enabled=True,
            tenant_id="tenant-123",
            is_active=True
        )

        assert response.id == "user-123"
        assert response.description is None
        assert response.tags is None
        assert response.created_at is None
        assert response.updated_at is None


class TestUserSearchFilter:
    """Test UserSearchFilter schema functionality."""

    def test_default_filter(self):
        """Test default search filter values."""
        filter_data = UserSearchFilter()

        assert filter_data.search is None
        assert filter_data.status is None
        assert filter_data.role is None
        assert filter_data.enabled is None
        assert filter_data.created_after is None
        assert filter_data.created_before is None
        assert filter_data.limit == 50
        assert filter_data.offset == 0

    def test_custom_filter(self):
        """Test custom search filter."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 12, 31)

        filter_data = UserSearchFilter(
            search="john",
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            enabled=True,
            created_after=created_after,
            created_before=created_before,
            limit=100,
            offset=50
        )

        assert filter_data.search == "john"
        assert filter_data.status == UserStatus.ACTIVE
        assert filter_data.role == UserRole.ADMIN
        assert filter_data.enabled is True
        assert filter_data.created_after == created_after
        assert filter_data.created_before == created_before
        assert filter_data.limit == 100
        assert filter_data.offset == 50

    def test_filter_validation(self):
        """Test search filter validation."""
        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            UserSearchFilter(limit=101)

        # Invalid offset (negative)
        with pytest.raises(ValidationError):
            UserSearchFilter(offset=-1)


class TestUserDashboardStats:
    """Test UserDashboardStats schema functionality."""

    def test_dashboard_stats_creation(self):
        """Test creating dashboard stats."""
        recent_users = [
            UserResponse(
                id="user-1",
                name="User 1",
                email="user1@example.com",
                status="active",
                role="user",
                enabled=True,
                tenant_id="tenant-1",
                is_active=True
            )
        ]

        stats = UserDashboardStats(
            total_users=100,
            active_users=80,
            inactive_users=15,
            suspended_users=5,
            users_by_role={"user": 85, "admin": 10, "moderator": 5},
            recent_users=recent_users
        )

        assert stats.total_users == 100
        assert stats.active_users == 80
        assert stats.inactive_users == 15
        assert stats.suspended_users == 5
        assert stats.users_by_role == {"user": 85, "admin": 10, "moderator": 5}
        assert len(stats.recent_users) == 1
        assert stats.recent_users[0].name == "User 1"


class TestUserModelIntegration:
    """Test User SQLAlchemy model functionality."""

    def test_user_to_dict(self):
        """Test User model to_dict method."""
        # Create a mock user with all fields
        user = User(
            id="user-123",
            email="test@example.com",
            name="Test User",
            description="Test description",
            status="active",
            enabled=True,
            tags=["tag1", "tag2"],
            tenant_id="tenant-123",
            role="user",
            is_active=True,
            hashed_password="hashed_password_here"
        )

        # Set timestamps manually for testing
        now = datetime.now(timezone.utc)
        user.created_at = now
        user.updated_at = now

        user_dict = user.to_dict()

        # Check all expected fields are present
        expected_fields = {
            "id", "email", "name", "description", "status", "enabled",
            "tags", "tenant_id", "role", "is_active", "created_at", "updated_at"
        }
        assert set(user_dict.keys()) == expected_fields

        # Check values
        assert user_dict["id"] == "user-123"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["name"] == "Test User"
        assert user_dict["description"] == "Test description"
        assert user_dict["status"] == "active"
        assert user_dict["enabled"] is True
        assert user_dict["tags"] == ["tag1", "tag2"]
        assert user_dict["tenant_id"] == "tenant-123"
        assert user_dict["role"] == "user"
        assert user_dict["is_active"] is True

        # Check that password is NOT included
        assert "hashed_password" not in user_dict
        assert "password" not in user_dict

        # Check timestamp formatting
        assert user_dict["created_at"] == now.isoformat()
        assert user_dict["updated_at"] == now.isoformat()

    def test_user_to_dict_with_none_values(self):
        """Test User model to_dict with None values."""
        user = User(
            id="user-123",
            email="test@example.com",
            name="Test User",
            hashed_password="hashed_password_here",
            tenant_id="tenant-123"
        )

        user_dict = user.to_dict()

        # Check None values are handled correctly
        assert user_dict["description"] is None
        assert user_dict["tags"] == []  # Default empty list
        assert user_dict["created_at"] is None
        assert user_dict["updated_at"] is None

    def test_user_repr(self):
        """Test User model __repr__ method."""
        user = User(
            id="user-123",
            email="test@example.com",
            name="Test User",
            tenant_id="tenant-123",
            hashed_password="hashed_password_here"
        )

        repr_str = repr(user)
        assert "User(" in repr_str
        assert "id=user-123" in repr_str
        assert "name=Test User" in repr_str
        assert "email=test@example.com" in repr_str
        assert "tenant=tenant-123" in repr_str


class TestDataTransformations:
    """Test data transformation and mapping functionality."""

    def test_user_create_to_user_model_mapping(self):
        """Test mapping UserCreate data to User model fields."""
        create_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="SecurePass123!",
            confirm_password="SecurePass123!",
            description="Test description",
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            enabled=True,
            tags=["tag1", "tag2"]
        )

        # Verify the mapping would work (this would be done in the service layer)
        expected_user_fields = {
            "name": create_data.name,
            "email": create_data.email,
            "description": create_data.description,
            "status": create_data.status.value,
            "role": create_data.role.value,
            "enabled": create_data.enabled,
            "tags": create_data.tags
        }

        assert expected_user_fields["name"] == "Test User"
        assert expected_user_fields["email"] == "test@example.com"
        assert expected_user_fields["status"] == "active"
        assert expected_user_fields["role"] == "admin"
        assert expected_user_fields["enabled"] is True
        assert expected_user_fields["tags"] == ["tag1", "tag2"]

    def test_user_update_field_extraction(self):
        """Test extracting only updated fields from UserUpdate."""
        update_data = UserUpdate(
            name="Updated Name",
            status=UserStatus.INACTIVE
        )

        # Extract only the fields that were actually set
        update_fields = update_data.model_dump(exclude_unset=True)

        assert "name" in update_fields
        assert "status" in update_fields
        assert "email" not in update_fields
        assert "description" not in update_fields
        assert "role" not in update_fields
        assert "enabled" not in update_fields
        assert "tags" not in update_fields

        assert update_fields["name"] == "Updated Name"
        assert update_fields["status"] == UserStatus.INACTIVE


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_tags_list(self):
        """Test handling empty tags list."""
        user_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="password123",
            confirm_password="password123",
            tags=[]
        )

        assert user_data.tags == []

    def test_unicode_names(self):
        """Test handling unicode characters in names."""
        user_data = UserCreate(
            name="José María Azéñar-Gómez",
            email="jose@example.com",
            password="password123",
            confirm_password="password123"
        )

        assert user_data.name == "José María Azéñar-Gómez"

    def test_special_characters_in_description(self):
        """Test handling special characters in description."""
        description = "Test with special chars: @#$%^&*()[]{}|\\:;\"'<>?,./"
        user_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="password123",
            confirm_password="password123",
            description=description
        )

        assert user_data.description == description

    def test_boundary_values(self):
        """Test boundary values for field lengths."""
        # Minimum valid values
        user_data = UserCreate(
            name="Ab",  # Minimum 2 chars
            email="a@b.c",  # Minimum valid email
            password="12345678",  # Minimum 8 chars
            confirm_password="12345678"
        )

        assert user_data.name == "Ab"
        assert user_data.email == "a@b.c"
        assert user_data.password == "12345678"

        # Maximum valid values
        max_name = "a" * 255
        max_desc = "a" * 1000

        user_data_max = UserCreate(
            name=max_name,
            email="test@example.com",
            password="password123",
            confirm_password="password123",
            description=max_desc
        )

        assert len(user_data_max.name) == 255
        assert len(user_data_max.description) == 1000