"""
Comprehensive unit tests for Tenants slice service layer.

Tests all business logic, tenant management operations, user assignment,
and service methods with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.administration.tenants.services import TenantManagementService
from app.features.administration.tenants.models import (
    TenantCreate, TenantUpdate, TenantResponse, TenantSearchFilter,
    TenantStatus, TenantTier, TenantDashboardStats, TenantUserResponse
)
from app.features.administration.tenants.db_models import Tenant
from app.features.auth.models import User


class TestTenantManagementServiceInitialization:
    """Test service initialization and setup."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        mock_session = AsyncMock(spec=AsyncSession)

        service = TenantManagementService(mock_session)

        assert service.db == mock_session


class TestTenantCreation:
    """Test tenant creation functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_session):
        """Create service instance with mock session."""
        return TenantManagementService(mock_session)

    @pytest.fixture
    def valid_tenant_create(self):
        """Create valid tenant creation data."""
        return TenantCreate(
            name="Test Corporation",
            description="A test corporation",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.PROFESSIONAL,
            contact_email="admin@testcorp.com",
            contact_name="Admin User",
            website="https://testcorp.com",
            max_users=100,
            features={"feature1": True},
            settings={"setting1": "value1"}
        )

    async def test_create_tenant_success(self, service, mock_session, valid_tenant_create):
        """Test successful tenant creation."""
        # Mock that no existing tenant exists
        service.get_tenant_by_name = AsyncMock(return_value=None)

        # Mock user count query
        service._get_tenant_user_count = AsyncMock(return_value=0)

        # Mock created tenant
        created_tenant = Tenant(
            id=1,
            name=valid_tenant_create.name,
            description=valid_tenant_create.description,
            status=valid_tenant_create.status.value,
            tier=valid_tenant_create.tier.value,
            contact_email=valid_tenant_create.contact_email,
            contact_name=valid_tenant_create.contact_name,
            website=valid_tenant_create.website,
            max_users=valid_tenant_create.max_users,
            features=valid_tenant_create.features,
            settings=valid_tenant_create.settings
        )
        created_tenant.created_at = datetime.utcnow()
        created_tenant.updated_at = datetime.utcnow()

        mock_session.refresh.return_value = None

        result = await service.create_tenant(valid_tenant_create)

        # Verify tenant was added to session
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify result is TenantResponse
        assert isinstance(result, TenantResponse)

    async def test_create_tenant_duplicate_name(self, service, valid_tenant_create):
        """Test tenant creation fails when name already exists."""
        # Mock that tenant with name already exists
        existing_tenant = TenantResponse(
            id=1,
            name=valid_tenant_create.name,
            status="active"
        )
        service.get_tenant_by_name = AsyncMock(return_value=existing_tenant)

        with pytest.raises(ValueError) as exc_info:
            await service.create_tenant(valid_tenant_create)

        assert f"Tenant with name '{valid_tenant_create.name}' already exists" in str(exc_info.value)

    async def test_create_tenant_database_error(self, service, mock_session, valid_tenant_create):
        """Test tenant creation handles database errors."""
        service.get_tenant_by_name = AsyncMock(return_value=None)

        # Mock database error
        mock_session.add.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            await service.create_tenant(valid_tenant_create)

        assert "Database connection failed" in str(exc_info.value)
        mock_session.rollback.assert_called_once()


class TestTenantRetrieval:
    """Test tenant retrieval functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_get_tenant_by_id_success(self, service):
        """Test successful tenant retrieval by ID."""
        # Mock database response
        mock_tenant = Tenant(
            id=1,
            name="Test Corp",
            status="active",
            tier="professional"
        )
        mock_tenant.created_at = datetime.utcnow()
        mock_tenant.updated_at = datetime.utcnow()

        service.db.execute.return_value.scalar_one_or_none.return_value = mock_tenant
        service._get_tenant_user_count = AsyncMock(return_value=25)

        result = await service.get_tenant_by_id(1)

        assert isinstance(result, TenantResponse)
        assert result.id == 1
        assert result.name == "Test Corp"
        assert result.user_count == 25

    async def test_get_tenant_by_id_not_found(self, service):
        """Test tenant retrieval when tenant doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_tenant_by_id(999)

        assert result is None

    async def test_get_tenant_by_name_success(self, service):
        """Test successful tenant retrieval by name."""
        mock_tenant = Tenant(
            id=1,
            name="Search Corp",
            status="active"
        )
        mock_tenant.created_at = datetime.utcnow()

        service.db.execute.return_value.scalar_one_or_none.return_value = mock_tenant
        service._get_tenant_user_count = AsyncMock(return_value=10)

        result = await service.get_tenant_by_name("Search Corp")

        assert isinstance(result, TenantResponse)
        assert result.name == "Search Corp"
        assert result.user_count == 10

    async def test_get_tenant_by_name_not_found(self, service):
        """Test tenant retrieval by name when tenant doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.get_tenant_by_name("Nonexistent Corp")

        assert result is None


class TestTenantUpdate:
    """Test tenant update functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_update_tenant_success(self, service):
        """Test successful tenant update."""
        # Mock existing tenant
        existing_tenant = Tenant(
            id=1,
            name="Original Corp",
            status="active",
            tier="basic",
            max_users=50
        )
        existing_tenant.created_at = datetime.utcnow()
        existing_tenant.updated_at = datetime.utcnow()

        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=15)

        # Update data
        update_data = TenantUpdate(
            name="Updated Corp",
            tier=TenantTier.PROFESSIONAL,
            max_users=100
        )

        result = await service.update_tenant(1, update_data)

        assert isinstance(result, TenantResponse)
        service.db.flush.assert_called_once()
        service.db.refresh.assert_called_once()

    async def test_update_tenant_not_found(self, service):
        """Test update when tenant doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        update_data = TenantUpdate(name="Updated Name")
        result = await service.update_tenant(999, update_data)

        assert result is None

    async def test_update_tenant_enum_values(self, service):
        """Test update with enum values."""
        existing_tenant = Tenant(id=1, name="Enum Corp")
        existing_tenant.created_at = datetime.utcnow()

        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=5)

        update_data = TenantUpdate(
            status=TenantStatus.SUSPENDED,
            tier=TenantTier.ENTERPRISE
        )

        result = await service.update_tenant(1, update_data)

        assert isinstance(result, TenantResponse)
        service.db.flush.assert_called_once()

    async def test_update_tenant_database_error(self, service):
        """Test update handles database errors."""
        existing_tenant = Tenant(id=1, name="Error Corp")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service.db.flush.side_effect = Exception("Database error")

        update_data = TenantUpdate(name="Updated Name")

        with pytest.raises(Exception):
            await service.update_tenant(1, update_data)

        service.db.rollback.assert_called_once()


class TestTenantDeletion:
    """Test tenant deletion functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_delete_tenant_success(self, service):
        """Test successful tenant deletion."""
        existing_tenant = Tenant(
            id=1,
            name="Delete Corp"
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=0)  # No users

        result = await service.delete_tenant(1)

        assert result is True
        service.db.delete.assert_called_once_with(existing_tenant)
        service.db.flush.assert_called_once()

    async def test_delete_tenant_with_users(self, service):
        """Test deletion fails when tenant has users."""
        existing_tenant = Tenant(id=1, name="Has Users Corp")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=5)  # Has users

        with pytest.raises(ValueError) as exc_info:
            await service.delete_tenant(1)

        assert "Cannot delete tenant with 5 active users" in str(exc_info.value)
        service.db.delete.assert_not_called()

    async def test_delete_tenant_not_found(self, service):
        """Test deletion when tenant doesn't exist."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.delete_tenant(999)

        assert result is False
        service.db.delete.assert_not_called()

    async def test_delete_tenant_database_error(self, service):
        """Test deletion handles database errors."""
        existing_tenant = Tenant(id=1, name="Error Corp")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=0)
        service.db.delete.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.delete_tenant(1)

        service.db.rollback.assert_called_once()


class TestTenantListing:
    """Test tenant listing and search functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_list_tenants_no_filters(self, service):
        """Test listing tenants without filters."""
        mock_tenants = [
            Tenant(id=1, name="Corp 1", status="active"),
            Tenant(id=2, name="Corp 2", status="inactive")
        ]

        for tenant in mock_tenants:
            tenant.created_at = datetime.utcnow()

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_tenants
        service._get_tenant_user_count = AsyncMock(side_effect=[10, 5])

        result = await service.list_tenants()

        assert len(result) == 2
        assert all(isinstance(tenant, TenantResponse) for tenant in result)

    async def test_list_tenants_with_search_filter(self, service):
        """Test listing tenants with search filter."""
        search_filter = TenantSearchFilter(
            search="tech",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.PROFESSIONAL,
            limit=25,
            offset=0
        )

        mock_tenants = [
            Tenant(id=1, name="Tech Corp", status="active", tier="professional")
        ]
        mock_tenants[0].created_at = datetime.utcnow()

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_tenants
        service._get_tenant_user_count = AsyncMock(return_value=20)

        result = await service.list_tenants(search_filter)

        assert len(result) == 1
        assert result[0].name == "Tech Corp"

    async def test_list_tenants_with_user_filter(self, service):
        """Test listing tenants with has_users filter."""
        # Test filter for tenants WITH users
        search_filter = TenantSearchFilter(has_users=True)

        mock_tenants = [
            Tenant(id=1, name="Has Users Corp"),
            Tenant(id=2, name="Empty Corp")
        ]

        for tenant in mock_tenants:
            tenant.created_at = datetime.utcnow()

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_tenants
        service._get_tenant_user_count = AsyncMock(side_effect=[10, 0])

        result = await service.list_tenants(search_filter)

        # Should only return tenant with users
        assert len(result) == 1
        assert result[0].name == "Has Users Corp"

    async def test_list_tenants_with_date_filters(self, service):
        """Test listing tenants with date range filters."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 12, 31)

        search_filter = TenantSearchFilter(
            created_after=created_after,
            created_before=created_before
        )

        service.db.execute.return_value.scalars.return_value.all.return_value = []

        result = await service.list_tenants(search_filter)

        assert len(result) == 0

    async def test_list_tenants_database_error(self, service):
        """Test listing tenants handles database errors."""
        service.db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.list_tenants()


class TestTenantUserManagement:
    """Test tenant user management functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_get_tenant_users_success(self, service):
        """Test successful retrieval of tenant users."""
        # Mock tenant exists
        service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
            id=1, name="Test Corp", status="active"
        ))

        # Mock users
        mock_users = [
            User(
                id="user-1",
                name="User 1",
                email="user1@testcorp.com",
                role="user",
                status="active",
                enabled=True,
                tenant_id="1"
            ),
            User(
                id="user-2",
                name="User 2",
                email="user2@testcorp.com",
                role="admin",
                status="active",
                enabled=True,
                tenant_id="1"
            )
        ]

        for user in mock_users:
            user.created_at = datetime.utcnow()

        service.db.execute.return_value.scalars.return_value.all.return_value = mock_users

        result = await service.get_tenant_users(1)

        assert len(result) == 2
        assert all(isinstance(user, TenantUserResponse) for user in result)
        assert result[0].email == "user1@testcorp.com"
        assert result[1].role == "admin"

    async def test_get_tenant_users_tenant_not_found(self, service):
        """Test get tenant users when tenant doesn't exist."""
        service.get_tenant_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError) as exc_info:
            await service.get_tenant_users(999)

        assert "Tenant 999 not found" in str(exc_info.value)

    async def test_get_tenant_users_pagination(self, service):
        """Test tenant users with pagination."""
        service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
            id=1, name="Test Corp", status="active"
        ))

        service.db.execute.return_value.scalars.return_value.all.return_value = []

        result = await service.get_tenant_users(1, limit=10, offset=20)

        assert len(result) == 0

    async def test_assign_user_to_tenant_success(self, service):
        """Test successful user assignment to tenant."""
        # Mock tenant with capacity
        service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
            id=1, name="Test Corp", status="active", user_count=5, max_users=10
        ))

        # Mock user exists
        mock_user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="old-tenant"
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = mock_user

        result = await service.assign_user_to_tenant("user-123", 1, "admin")

        assert result is True
        service.db.flush.assert_called_once()

    async def test_assign_user_tenant_at_capacity(self, service):
        """Test user assignment fails when tenant at capacity."""
        # Mock tenant at capacity
        service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
            id=1, name="Full Corp", status="active", user_count=10, max_users=10
        ))

        with pytest.raises(ValueError) as exc_info:
            await service.assign_user_to_tenant("user-123", 1)

        assert "reached maximum user limit" in str(exc_info.value)

    async def test_assign_user_tenant_not_found(self, service):
        """Test user assignment when tenant doesn't exist."""
        service.get_tenant_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError) as exc_info:
            await service.assign_user_to_tenant("user-123", 999)

        assert "Tenant 999 not found" in str(exc_info.value)

    async def test_assign_user_user_not_found(self, service):
        """Test user assignment when user doesn't exist."""
        service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
            id=1, name="Test Corp", status="active", user_count=5, max_users=10
        ))

        service.db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await service.assign_user_to_tenant("nonexistent-user", 1)

        assert "User nonexistent-user not found" in str(exc_info.value)

    async def test_remove_user_from_tenant_success(self, service):
        """Test successful user removal from tenant."""
        mock_user = User(
            id="user-123",
            name="Test User",
            email="test@example.com",
            tenant_id="1",
            is_active=True
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = mock_user

        result = await service.remove_user_from_tenant("user-123", 1)

        assert result is True
        assert mock_user.is_active is False
        service.db.flush.assert_called_once()

    async def test_remove_user_from_tenant_not_found(self, service):
        """Test user removal when user not in tenant."""
        service.db.execute.return_value.scalar_one_or_none.return_value = None

        result = await service.remove_user_from_tenant("user-123", 1)

        assert result is False

    async def test_remove_user_database_error(self, service):
        """Test user removal handles database errors."""
        mock_user = User(id="user-123", tenant_id="1")
        service.db.execute.return_value.scalar_one_or_none.return_value = mock_user
        service.db.flush.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.remove_user_from_tenant("user-123", 1)

        service.db.rollback.assert_called_once()


class TestDashboardStats:
    """Test dashboard statistics functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_get_dashboard_stats_success(self, service):
        """Test successful dashboard stats retrieval."""
        # Mock status counts query
        status_result = MagicMock()
        status_result.fetchall.return_value = [("active", 80), ("inactive", 15), ("suspended", 5)]

        # Mock tier counts query
        tier_result = MagicMock()
        tier_result.fetchall.return_value = [("free", 60), ("basic", 25), ("professional", 10), ("enterprise", 5)]

        # Mock total users count
        total_users_result = MagicMock()
        total_users_result.scalar.return_value = 1500

        # Mock recent tenants query
        recent_tenants = [
            Tenant(id=1, name="Recent Corp 1", status="active"),
            Tenant(id=2, name="Recent Corp 2", status="active")
        ]
        for tenant in recent_tenants:
            tenant.created_at = datetime.utcnow()

        # Setup mock returns
        service.db.execute.side_effect = [
            status_result,
            tier_result,
            total_users_result,
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=recent_tenants))))
        ]

        service._get_tenant_user_count = AsyncMock(side_effect=[25, 30])

        result = await service.get_dashboard_stats()

        assert isinstance(result, TenantDashboardStats)
        assert result.total_tenants == 100
        assert result.active_tenants == 80
        assert result.inactive_tenants == 15
        assert result.suspended_tenants == 5
        assert result.total_users == 1500
        assert result.tenants_by_tier["free"] == 60
        assert result.tenants_by_tier["enterprise"] == 5
        assert len(result.recent_tenants) == 2

    async def test_get_dashboard_stats_database_error(self, service):
        """Test dashboard stats handles database errors."""
        service.db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.get_dashboard_stats()


class TestPrivateMethods:
    """Test private helper methods."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_get_tenant_user_count_success(self, service):
        """Test _get_tenant_user_count method."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = 25
        service.db.execute.return_value = result_mock

        result = await service._get_tenant_user_count(1)

        assert result == 25

    async def test_get_tenant_user_count_zero(self, service):
        """Test _get_tenant_user_count returns zero when no users."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        service.db.execute.return_value = result_mock

        result = await service._get_tenant_user_count(1)

        assert result == 0

    async def test_get_tenant_user_count_error(self, service):
        """Test _get_tenant_user_count handles errors gracefully."""
        service.db.execute.side_effect = Exception("Database error")

        result = await service._get_tenant_user_count(1)

        assert result == 0

    def test_tenant_to_response(self, service):
        """Test _tenant_to_response conversion method."""
        tenant = Tenant(
            id=1,
            name="Test Corp",
            description="Test description",
            status="active",
            tier="professional",
            contact_email="contact@testcorp.com",
            contact_name="Contact Person",
            website="https://testcorp.com",
            max_users=100,
            features={"feature1": True},
            settings={"setting1": "value1"}
        )
        tenant.created_at = datetime(2024, 1, 1, 12, 0, 0)
        tenant.updated_at = datetime(2024, 1, 2, 12, 0, 0)

        result = service._tenant_to_response(tenant, user_count=50)

        assert isinstance(result, TenantResponse)
        assert result.id == 1
        assert result.name == "Test Corp"
        assert result.description == "Test description"
        assert result.status == "active"
        assert result.tier == "professional"
        assert result.contact_email == "contact@testcorp.com"
        assert result.contact_name == "Contact Person"
        assert result.website == "https://testcorp.com"
        assert result.max_users == 100
        assert result.user_count == 50
        assert result.features == {"feature1": True}
        assert result.settings == {"setting1": "value1"}
        assert result.created_at == "2024-01-01T12:00:00"
        assert result.updated_at == "2024-01-02T12:00:00"

    def test_tenant_to_response_with_none_values(self, service):
        """Test _tenant_to_response with None values."""
        tenant = Tenant(
            id=1,
            name="Minimal Corp",
            status="active",
            features=None,
            settings=None
        )

        result = service._tenant_to_response(tenant)

        assert result.features == {}  # Should convert None to empty dict
        assert result.settings == {}  # Should convert None to empty dict
        assert result.user_count == 0  # Default user_count


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_service_handles_connection_errors(self, service):
        """Test service gracefully handles database connection errors."""
        service.db.execute.side_effect = Exception("Connection refused")

        with pytest.raises(Exception) as exc_info:
            await service.list_tenants()

        assert "Connection refused" in str(exc_info.value)

    async def test_service_handles_timeout_errors(self, service):
        """Test service handles database timeout errors."""
        service.db.execute.side_effect = Exception("Query timeout")

        with pytest.raises(Exception) as exc_info:
            await service.get_tenant_by_id(1)

        assert "Query timeout" in str(exc_info.value)


class TestBusinessLogicValidation:
    """Test business logic and validation rules."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    def test_enum_value_extraction(self, service):
        """Test that enum values are properly extracted in updates."""
        update_data = TenantUpdate(
            status=TenantStatus.SUSPENDED,
            tier=TenantTier.ENTERPRISE
        )

        update_fields = update_data.dict(exclude_unset=True)

        # In the actual service, these would be converted to .value
        assert update_fields["status"] == TenantStatus.SUSPENDED
        assert update_fields["tier"] == TenantTier.ENTERPRISE

    async def test_user_capacity_validation(self, service):
        """Test user capacity validation logic."""
        # Mock tenant at different capacity levels
        tenant_data = [
            {"user_count": 0, "max_users": 10, "should_allow": True},
            {"user_count": 5, "max_users": 10, "should_allow": True},
            {"user_count": 9, "max_users": 10, "should_allow": True},
            {"user_count": 10, "max_users": 10, "should_allow": False},
            {"user_count": 15, "max_users": 10, "should_allow": False},
        ]

        for data in tenant_data:
            service.get_tenant_by_id = AsyncMock(return_value=TenantResponse(
                id=1,
                name="Capacity Test",
                status="active",
                user_count=data["user_count"],
                max_users=data["max_users"]
            ))

            if data["should_allow"]:
                # Should not raise exception
                mock_user = User(id="test-user")
                service.db.execute.return_value.scalar_one_or_none.return_value = mock_user

                result = await service.assign_user_to_tenant("test-user", 1)
                assert result is True
            else:
                # Should raise capacity exception
                with pytest.raises(ValueError) as exc_info:
                    await service.assign_user_to_tenant("test-user", 1)
                assert "maximum user limit" in str(exc_info.value)

    async def test_concurrent_modification_handling(self, service):
        """Test handling of concurrent modifications."""
        # This test demonstrates the concept - actual implementation would
        # depend on database-level optimistic locking

        existing_tenant = Tenant(id=1, name="Concurrent Test")
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant

        # Simulate concurrent modification by having flush fail
        service.db.flush.side_effect = Exception("Concurrent modification detected")

        update_data = TenantUpdate(name="Updated Name")

        with pytest.raises(Exception) as exc_info:
            await service.update_tenant(1, update_data)

        assert "Concurrent modification detected" in str(exc_info.value)
        service.db.rollback.assert_called_once()


class TestTenantFeatureManagement:
    """Test tenant feature and settings management."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return TenantManagementService(mock_session)

    async def test_feature_flag_updates(self, service):
        """Test updating tenant feature flags."""
        existing_tenant = Tenant(
            id=1,
            name="Feature Corp",
            features={"basic": True, "premium": False}
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=10)

        # Update features
        update_data = TenantUpdate(
            features={"basic": True, "premium": True, "enterprise": True}
        )

        result = await service.update_tenant(1, update_data)

        assert isinstance(result, TenantResponse)
        service.db.flush.assert_called_once()

    async def test_settings_management(self, service):
        """Test updating tenant settings."""
        existing_tenant = Tenant(
            id=1,
            name="Settings Corp",
            settings={"theme": "light", "notifications": True}
        )
        service.db.execute.return_value.scalar_one_or_none.return_value = existing_tenant
        service._get_tenant_user_count = AsyncMock(return_value=5)

        # Update settings
        update_data = TenantUpdate(
            settings={
                "theme": "dark",
                "notifications": False,
                "timezone": "UTC",
                "language": "en"
            }
        )

        result = await service.update_tenant(1, update_data)

        assert isinstance(result, TenantResponse)
        service.db.flush.assert_called_once()

    def test_feature_inheritance_logic(self):
        """Test feature inheritance logic for different tiers."""
        # This would test the business logic for which features
        # are available at different tier levels

        tier_features = {
            "free": ["basic_support", "community_access"],
            "basic": ["basic_support", "community_access", "email_support"],
            "professional": ["basic_support", "community_access", "email_support", "phone_support", "advanced_analytics"],
            "enterprise": ["basic_support", "community_access", "email_support", "phone_support", "advanced_analytics", "custom_integrations", "dedicated_manager"]
        }

        # Test that enterprise includes all features
        enterprise_features = tier_features["enterprise"]
        professional_features = tier_features["professional"]

        assert all(feature in enterprise_features for feature in professional_features)

        # Test that free tier has minimal features
        free_features = tier_features["free"]
        assert len(free_features) == 2
        assert "basic_support" in free_features