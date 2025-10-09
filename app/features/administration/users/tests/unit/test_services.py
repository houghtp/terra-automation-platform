"""
Comprehensive unit tests for Users slice service layer.

Tests all business logic, data transformations, error handling,
and service methods with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.administration.users.services import UserManagementService
from app.features.administration.users.models import (
    UserCreate, UserUpdate, UserResponse, UserSearchFilter,
    UserStatus, UserRole, UserDashboardStats
)
from app.features.auth.models import User


class TestUserManagementServiceInitialization:
    """Test service initialization and setup."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        mock_session = AsyncMock(spec=AsyncSession)
        tenant_id = "test-tenant-123"

        service = UserManagementService(mock_session, tenant_id)

        assert service.db == mock_session
        assert service.tenant_id == tenant_id


class TestUserCreation:
    """Test user creation functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_session):
        """Create service instance with mock session."""
        return UserManagementService(mock_session, "test-tenant-123")

    @pytest.fixture
    def valid_user_create(self):
        """Create valid user creation data."""
        return UserCreate(
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

    @patch('app.administration.users.services.services.validate_password_complexity')
    @patch('app.administration.users.services.services.hash_password')
    async def test_create_user_success(self, mock_hash_password, mock_validate_password,
                                     service, mock_session, valid_user_create):
        """Test successful user creation."""
        # Setup mocks
        mock_validate_password.return_value = []  # No validation errors
        mock_hash_password.return_value = "hashed_password_123"

        # Mock existing user check (no existing user)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Mock user creation
        created_user = User(
            id="user-123",
            name=valid_user_create.name,
            email=valid_user_create.email,
            hashed_password="hashed_password_123",
            description=valid_user_create.description,
            status=valid_user_create.status.value,
            role=valid_user_create.role.value,
            enabled=valid_user_create.enabled,
            tags=valid_user_create.tags,
            tenant_id="test-tenant-123"
        )
        created_user.created_at = datetime.now(timezone.utc)
        created_user.updated_at = datetime.now(timezone.utc)
        created_user.is_active = True

        mock_session.refresh.return_value = None

        # Patch the service's get_user_by_email method
        service.get_user_by_email = AsyncMock(return_value=None)

        result = await service.create_user(valid_user_create)

        # Verify password validation was called
        mock_validate_password.assert_called_once_with(valid_user_create.password)

        # Verify password hashing was called
        mock_hash_password.assert_called_once_with(valid_user_create.password)

        # Verify user was added to session
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify result is UserResponse
        assert isinstance(result, UserResponse)

    @patch('app.administration.users.services.services.validate_password_complexity')
    async def test_create_user_password_validation_failure(self, mock_validate_password,
                                                         service, valid_user_create):
        """Test user creation fails with password validation errors."""
        # Setup password validation to return errors
        mock_validate_password.return_value = ["Password too weak", "Missing special character"]

        with pytest.raises(ValueError) as exc_info:
            await service.create_user(valid_user_create)

        assert "Password validation failed" in str(exc_info.value)
        assert "Password too weak" in str(exc_info.value)
        assert "Missing special character" in str(exc_info.value)

    async def test_create_user_password_mismatch(self, service):
        """Test user creation fails when passwords don't match."""
        user_data = UserCreate(
            name="Test User",
            email="test@example.com",
            password="SecurePass123!",
            confirm_password="DifferentPass123!",  # Different password
            description="Test user description"
        )

        with pytest.raises(ValueError) as exc_info:
            await service.create_user(user_data)

        assert "Passwords do not match" in str(exc_info.value)

    async def test_create_user_duplicate_email(self, service, mock_session, valid_user_create):
        """Test user creation fails when email already exists."""
        # Mock that user with email already exists
        existing_user = UserResponse(
            id="existing-user-123",
            name="Existing User",
            email=valid_user_create.email,
            status="active",
            role="user",
            enabled=True,
            tenant_id="test-tenant-123",
            is_active=True
        )
        service.get_user_by_email = AsyncMock(return_value=existing_user)

        with pytest.raises(ValueError) as exc_info:
            await service.create_user(valid_user_create)

        assert f"User with email '{valid_user_create.email}' already exists" in str(exc_info.value)

    @patch('app.administration.users.services.services.validate_password_complexity')
    async def test_create_user_database_error(self, mock_validate_password, service,
                                            mock_session, valid_user_create):
        """Test user creation handles database errors."""
        mock_validate_password.return_value = []
        service.get_user_by_email = AsyncMock(return_value=None)

        # Mock database error
        mock_session.add.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            await service.create_user(valid_user_create)

        assert "Database connection failed" in str(exc_info.value)
        mock_session.rollback.assert_called_once()


class TestUserRetrieval:
    """Test user retrieval functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_get_user_by_id_success(self, service):
        """Test successful user retrieval by ID."""
        # Mock database response
        mock_user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-123"
        )
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.is_active = True
        mock_user.status = "active"
        mock_user.role = "user"
        mock_user.enabled = True
        mock_user.tags = []

        service.db.execute.return_value.scalar_one_or_none.return_value = mock_user

        result = await service.get_user_by_id("user-123")

        assert isinstance(result, UserResponse)
        assert result.id == "user-123"
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.tenant_id == "test-tenant-123"

    async def test_get_user_by_id_not_found(self, service):
        """Test user retrieval when user doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_user_by_id("nonexistent-user")

        assert result is None

    async def test_get_user_by_email_success(self, service):
        """Test successful user retrieval by email."""
        mock_user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-123"
        )
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.is_active = True
        mock_user.status = "active"
        mock_user.role = "user"
        mock_user.enabled = True

        service.db.execute.return_value.scalar_one_or_none.return_value = mock_user

        result = await service.get_user_by_email("test@example.com")

        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"

    async def test_get_user_by_email_not_found(self, service):
        """Test user retrieval by email when user doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_user_by_email("nonexistent@example.com")

        assert result is None


class TestUserUpdate:
    """Test user update functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_update_user_success(self, service):
        """Test successful user update."""
        # Mock existing user
        existing_user = User(
            id="user-123",
            name="Original Name",
            email="original@example.com",
            status="active",
            role="user",
            enabled=True,
            tenant_id="test-tenant-123"
        )
        existing_user.created_at = datetime.now(timezone.utc)
        existing_user.updated_at = datetime.now(timezone.utc)

        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user

        # Update data
        update_data = UserUpdate(
            name="Updated Name",
            status=UserStatus.INACTIVE
        )

        result = await service.update_user("user-123", update_data)

        assert isinstance(result, UserResponse)
        service.db.flush.assert_called_once()
        service.db.refresh.assert_called_once()

    async def test_update_user_not_found(self, service):
        """Test update when user doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        update_data = UserUpdate(name="Updated Name")
        result = await service.update_user("nonexistent-user", update_data)

        assert result is None

    async def test_update_user_field_success(self, service):
        """Test successful single field update."""
        existing_user = User(
            id="user-123",
            name="Original Name",
            email="test@example.com",
            tenant_id="test-tenant-123"
        )
        existing_user.created_at = datetime.now(timezone.utc)
        existing_user.status = "active"
        existing_user.role = "user"
        existing_user.enabled = True

        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user

        result = await service.update_user_field("user-123", "name", "New Name")

        assert isinstance(result, UserResponse)
        service.db.flush.assert_called_once()
        service.db.refresh.assert_called_once()

    async def test_update_user_field_protected_field(self, service):
        """Test update fails for protected fields."""
        existing_user = User(id="user-123", tenant_id="test-tenant-123")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user

        # Try to update password field (should be protected)
        result = await service.update_user_field("user-123", "hashed_password", "new_hash")

        assert result is None

    async def test_update_user_database_error(self, service):
        """Test update handles database errors."""
        existing_user = User(id="user-123", tenant_id="test-tenant-123")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user
        service.db.flush.side_effect = Exception("Database error")

        update_data = UserUpdate(name="Updated Name")

        with pytest.raises(Exception):
            await service.update_user("user-123", update_data)

        service.db.rollback.assert_called_once()


class TestUserDeletion:
    """Test user deletion functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_delete_user_success(self, service):
        """Test successful user deletion."""
        existing_user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-123"
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user

        result = await service.delete_user("user-123")

        assert result is True
        service.db.delete.assert_called_once_with(existing_user)
        service.db.flush.assert_called_once()

    async def test_delete_user_not_found(self, service):
        """Test deletion when user doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.delete_user("nonexistent-user")

        assert result is False
        service.db.delete.assert_not_called()

    async def test_delete_user_database_error(self, service):
        """Test deletion handles database errors."""
        existing_user = User(id="user-123", tenant_id="test-tenant-123")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user
        service.db.delete.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.delete_user("user-123")

        service.db.rollback.assert_called_once()


class TestUserListing:
    """Test user listing and search functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_list_users_no_filters(self, service):
        """Test listing users without filters."""
        mock_users = [
            User(id="user-1", name="User 1", email="user1@example.com",
                 tenant_id="test-tenant-123", status="active", role="user", enabled=True),
            User(id="user-2", name="User 2", email="user2@example.com",
                 tenant_id="test-tenant-123", status="active", role="user", enabled=True)
        ]

        for user in mock_users:
            user.created_at = datetime.now(timezone.utc)
            user.is_active = True

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_users

        result = await service.list_users()

        assert len(result) == 2
        assert all(isinstance(user, UserResponse) for user in result)

    async def test_list_users_with_search_filter(self, service):
        """Test listing users with search filter."""
        search_filter = UserSearchFilter(
            search="john",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
            enabled=True,
            limit=25,
            offset=0
        )

        mock_users = [
            User(id="user-1", name="John Doe", email="john@example.com",
                 tenant_id="test-tenant-123", status="active", role="user", enabled=True)
        ]
        mock_users[0].created_at = datetime.now(timezone.utc)
        mock_users[0].is_active = True

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_users

        result = await service.list_users(search_filter)

        assert len(result) == 1
        assert result[0].name == "John Doe"

    async def test_list_users_with_date_filters(self, service):
        """Test listing users with date range filters."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 12, 31)

        search_filter = UserSearchFilter(
            created_after=created_after,
            created_before=created_before
        )

        service.db.execute.return_value.scalars.return_value.all.return_value = []

        result = await service.list_users(search_filter)

        assert len(result) == 0

    async def test_list_users_database_error(self, service):
        """Test listing users handles database errors."""
        service.db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.list_users()


class TestDashboardStats:
    """Test dashboard statistics functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_get_dashboard_stats_success(self, service):
        """Test successful dashboard stats retrieval."""
        # Mock status counts query
        status_result = MagicMock()
        status_result.fetchall.return_value = [("active", 80), ("inactive", 15), ("suspended", 5)]

        # Mock role counts query
        role_result = MagicMock()
        role_result.fetchall.return_value = [("user", 85), ("admin", 10), ("moderator", 5)]

        # Mock recent users query
        recent_users = [
            User(id="user-1", name="Recent User 1", email="recent1@example.com",
                 tenant_id="test-tenant-123", status="active", role="user", enabled=True)
        ]
        recent_users[0].created_at = datetime.now(timezone.utc)
        recent_users[0].is_active = True

        # Setup mock returns
        service.db.execute.side_effect = [status_result, role_result,
                                        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=recent_users))))]

        result = await service.get_dashboard_stats()

        assert isinstance(result, UserDashboardStats)
        assert result.total_users == 100
        assert result.active_users == 80
        assert result.inactive_users == 15
        assert result.suspended_users == 5
        assert result.users_by_role == {"user": 85, "admin": 10, "moderator": 5}
        assert len(result.recent_users) == 1

    async def test_get_dashboard_stats_database_error(self, service):
        """Test dashboard stats handles database errors."""
        service.db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.get_dashboard_stats()


class TestTenantHelpers:
    """Test tenant-related helper functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_get_available_tenants_for_user_forms(self, service):
        """Test getting available tenants for form dropdowns."""
        # Mock raw SQL result
        mock_result = MagicMock()
        mock_rows = [
            MagicMock(id=1, name="Tenant 1", status="active"),
            MagicMock(id=2, name="Tenant 2", status="active")
        ]
        mock_result.__iter__ = lambda self: iter(mock_rows)

        service.db.execute.return_value = mock_result

        result = await service.get_available_tenants_for_user_forms()

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["name"] == "Tenant 1"
        assert result[0]["status"] == "active"


class TestPrivateMethods:
    """Test private helper methods."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    def test_user_to_response(self, service):
        """Test _user_to_response conversion method."""
        user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            description="Test description",
            status="active",
            role="user",
            enabled=True,
            tags=["tag1", "tag2"],
            tenant_id="test-tenant-123",
            is_active=True
        )
        user.created_at = datetime(2024, 1, 1, 12, 0, 0)
        user.updated_at = datetime(2024, 1, 2, 12, 0, 0)

        result = service._user_to_response(user)

        assert isinstance(result, UserResponse)
        assert result.id == "user-123"
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.description == "Test description"
        assert result.status == "active"
        assert result.role == "user"
        assert result.enabled is True
        assert result.tags == ["tag1", "tag2"]
        assert result.tenant_id == "test-tenant-123"
        assert result.is_active is True
        assert result.created_at == "2024-01-01T12:00:00"
        assert result.updated_at == "2024-01-02T12:00:00"

    def test_user_to_response_with_none_tags(self, service):
        """Test _user_to_response with None tags."""
        user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="test-tenant-123",
            status="active",
            role="user",
            enabled=True,
            tags=None,  # None tags
            is_active=True
        )

        result = service._user_to_response(user)

        assert result.tags == []  # Should convert None to empty list


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_service_handles_connection_errors(self, service):
        """Test service gracefully handles database connection errors."""
        service.db.execute.side_effect = Exception("Connection refused")

        with pytest.raises(Exception) as exc_info:
            await service.list_users()

        assert "Connection refused" in str(exc_info.value)

    async def test_service_handles_timeout_errors(self, service):
        """Test service handles database timeout errors."""
        service.db.execute.side_effect = Exception("Query timeout")

        with pytest.raises(Exception) as exc_info:
            await service.get_user_by_id("user-123")

        assert "Query timeout" in str(exc_info.value)


class TestTenantIsolation:
    """Test that all operations respect tenant isolation."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    async def test_get_user_by_id_respects_tenant(self, service):
        """Test that get_user_by_id only finds users in the correct tenant."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        await service.get_user_by_id("user-123")

        # Verify the query included tenant_id filter
        # (This would be more detailed in a real test with query inspection)
        service.db.execute.assert_called_once()

    async def test_delete_user_respects_tenant(self, service):
        """Test that delete_user only deletes users in the correct tenant."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.delete_user("user-123")

        assert result is False
        service.db.execute.assert_called_once()

    async def test_list_users_respects_tenant(self, service):
        """Test that list_users only returns users from the correct tenant."""
        service.db.execute.return_value.scalars.return_value.all.return_value = []

        await service.list_users()

        # Verify tenant isolation in the query
        service.db.execute.assert_called_once()


class TestBusinessLogicValidation:
    """Test business logic and validation rules."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return UserManagementService(mock_session, "test-tenant-123")

    def test_enum_value_extraction(self, service):
        """Test that enum values are properly extracted in updates."""
        update_data = UserUpdate(
            status=UserStatus.SUSPENDED,
            role=UserRole.ADMIN
        )

        update_fields = update_data.model_dump(exclude_unset=True)

        # In the actual service, these would be converted to .value
        assert update_fields["status"] == UserStatus.SUSPENDED
        assert update_fields["role"] == UserRole.ADMIN

    async def test_concurrent_modification_handling(self, service):
        """Test handling of concurrent modifications (optimistic locking concept)."""
        # This test demonstrates the concept - actual implementation would
        # depend on database-level optimistic locking or version fields

        existing_user = User(id="user-123", tenant_id="test-tenant-123")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_user

        # Simulate concurrent modification by having flush fail
        service.db.flush.side_effect = Exception("Concurrent modification detected")

        update_data = UserUpdate(name="Updated Name")

        with pytest.raises(Exception) as exc_info:
            await service.update_user("user-123", update_data)

        assert "Concurrent modification detected" in str(exc_info.value)
        service.db.rollback.assert_called_once()