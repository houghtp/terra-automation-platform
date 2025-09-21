"""
Comprehensive unit tests for Tenants slice models and schemas.

Tests all Pydantic models, enums, validation logic, and data transformations
without database dependencies.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from app.features.administration.tenants.models import (
    TenantStatus, TenantTier, TenantCreate, TenantUpdate, TenantResponse,
    TenantStats, TenantSearchFilter, TenantDashboardStats, TenantUserResponse,
    UserTenantAssignment
)


class TestTenantEnums:
    """Test tenant enumeration classes."""

    def test_tenant_status_values(self):
        """Test TenantStatus enum has correct values."""
        assert TenantStatus.ACTIVE == "active"
        assert TenantStatus.INACTIVE == "inactive"
        assert TenantStatus.SUSPENDED == "suspended"
        assert TenantStatus.PENDING == "pending"

    def test_tenant_tier_values(self):
        """Test TenantTier enum has correct values."""
        assert TenantTier.FREE == "free"
        assert TenantTier.BASIC == "basic"
        assert TenantTier.PROFESSIONAL == "professional"
        assert TenantTier.ENTERPRISE == "enterprise"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert "active" in TenantStatus
        assert "invalid_status" not in TenantStatus
        assert "enterprise" in TenantTier
        assert "super_premium" not in TenantTier


class TestTenantCreateSchema:
    """Test TenantCreate schema validation and functionality."""

    def test_valid_tenant_creation(self):
        """Test creating a valid tenant."""
        tenant_data = TenantCreate(
            name="Test Corporation",
            description="A test corporation for unit testing",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.PROFESSIONAL,
            contact_email="admin@testcorp.com",
            contact_name="John Administrator",
            website="https://testcorp.com",
            max_users=100,
            features={"feature1": True, "feature2": False},
            settings={"theme": "dark", "notifications": True}
        )

        assert tenant_data.name == "Test Corporation"
        assert tenant_data.description == "A test corporation for unit testing"
        assert tenant_data.status == TenantStatus.ACTIVE
        assert tenant_data.tier == TenantTier.PROFESSIONAL
        assert tenant_data.contact_email == "admin@testcorp.com"
        assert tenant_data.contact_name == "John Administrator"
        assert tenant_data.website == "https://testcorp.com"
        assert tenant_data.max_users == 100
        assert tenant_data.features == {"feature1": True, "feature2": False}
        assert tenant_data.settings == {"theme": "dark", "notifications": True}

    def test_minimal_tenant_creation(self):
        """Test creating tenant with only required fields."""
        tenant_data = TenantCreate(name="Minimal Corp")

        assert tenant_data.name == "Minimal Corp"
        assert tenant_data.description is None
        assert tenant_data.status == TenantStatus.ACTIVE  # Default
        assert tenant_data.tier == TenantTier.FREE  # Default
        assert tenant_data.contact_email is None
        assert tenant_data.contact_name is None
        assert tenant_data.website is None
        assert tenant_data.max_users == 10  # Default
        assert tenant_data.features == {}  # Default empty dict
        assert tenant_data.settings == {}  # Default empty dict

    def test_name_validation(self):
        """Test name field validation."""
        # Too short name
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(name="a")  # Too short (min 2)
        assert "at least 2 characters" in str(exc_info.value)

        # Too long name
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(name="a" * 256)  # Too long (max 255)
        assert "at most 255 characters" in str(exc_info.value)

    def test_description_validation(self):
        """Test description field validation."""
        # Too long description
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                description="a" * 1001  # Too long (max 1000)
            )
        assert "at most 1000 characters" in str(exc_info.value)

    def test_email_validation(self):
        """Test email field validation."""
        # Invalid email format
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                contact_email="invalid-email"
            )
        assert "email" in str(exc_info.value).lower()

    def test_max_users_validation(self):
        """Test max_users field validation."""
        # Zero users (invalid)
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                max_users=0  # Must be >= 1
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        # Negative users (invalid)
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                max_users=-5
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_contact_name_validation(self):
        """Test contact_name field validation."""
        # Too long contact name
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                contact_name="a" * 256  # Too long (max 255)
            )
        assert "at most 255 characters" in str(exc_info.value)

    def test_website_validation(self):
        """Test website field validation."""
        # Too long website
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(
                name="Test Corp",
                website="https://" + "a" * 500  # Too long (max 500)
            )
        assert "at most 500 characters" in str(exc_info.value)

    def test_enum_validation(self):
        """Test enum field validation."""
        # Invalid status
        with pytest.raises(ValidationError):
            TenantCreate(
                name="Test Corp",
                status="invalid_status"
            )

        # Invalid tier
        with pytest.raises(ValidationError):
            TenantCreate(
                name="Test Corp",
                tier="invalid_tier"
            )


class TestTenantUpdateSchema:
    """Test TenantUpdate schema validation and functionality."""

    def test_empty_update(self):
        """Test creating empty update schema."""
        update_data = TenantUpdate()
        update_dict = update_data.dict(exclude_unset=True)
        assert update_dict == {}

    def test_partial_update(self):
        """Test partial tenant update."""
        update_data = TenantUpdate(
            name="Updated Corp",
            status=TenantStatus.SUSPENDED
        )

        assert update_data.name == "Updated Corp"
        assert update_data.status == TenantStatus.SUSPENDED
        assert update_data.description is None
        assert update_data.tier is None

    def test_full_update(self):
        """Test full tenant update."""
        update_data = TenantUpdate(
            name="Updated Corporation",
            description="Updated description",
            status=TenantStatus.INACTIVE,
            tier=TenantTier.ENTERPRISE,
            contact_email="updated@corp.com",
            contact_name="Jane Administrator",
            website="https://updated-corp.com",
            max_users=500,
            features={"advanced": True},
            settings={"updated": True}
        )

        assert update_data.name == "Updated Corporation"
        assert update_data.description == "Updated description"
        assert update_data.status == TenantStatus.INACTIVE
        assert update_data.tier == TenantTier.ENTERPRISE
        assert update_data.contact_email == "updated@corp.com"
        assert update_data.contact_name == "Jane Administrator"
        assert update_data.website == "https://updated-corp.com"
        assert update_data.max_users == 500
        assert update_data.features == {"advanced": True}
        assert update_data.settings == {"updated": True}

    def test_update_validation(self):
        """Test update field validation."""
        # Invalid name length
        with pytest.raises(ValidationError):
            TenantUpdate(name="a")  # Too short

        # Invalid email format
        with pytest.raises(ValidationError):
            TenantUpdate(contact_email="invalid-email")

        # Invalid max_users
        with pytest.raises(ValidationError):
            TenantUpdate(max_users=0)  # Must be >= 1


class TestTenantResponseSchema:
    """Test TenantResponse schema functionality."""

    def test_tenant_response_creation(self):
        """Test creating tenant response schema."""
        response = TenantResponse(
            id=1,
            name="Response Corp",
            description="Response description",
            status="active",
            tier="professional",
            contact_email="contact@response.com",
            contact_name="Contact Person",
            website="https://response.com",
            max_users=200,
            user_count=50,
            features={"feature1": True},
            settings={"setting1": "value1"},
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00"
        )

        assert response.id == 1
        assert response.name == "Response Corp"
        assert response.description == "Response description"
        assert response.status == "active"
        assert response.tier == "professional"
        assert response.contact_email == "contact@response.com"
        assert response.contact_name == "Contact Person"
        assert response.website == "https://response.com"
        assert response.max_users == 200
        assert response.user_count == 50
        assert response.features == {"feature1": True}
        assert response.settings == {"setting1": "value1"}
        assert response.created_at == "2024-01-01T00:00:00"
        assert response.updated_at == "2024-01-02T00:00:00"

    def test_tenant_response_minimal(self):
        """Test creating minimal tenant response."""
        response = TenantResponse(
            id=1,
            name="Minimal Corp",
            status="active"
        )

        assert response.id == 1
        assert response.name == "Minimal Corp"
        assert response.status == "active"
        assert response.description is None
        assert response.tier is None
        assert response.contact_email is None
        assert response.contact_name is None
        assert response.website is None
        assert response.max_users is None
        assert response.user_count is None
        assert response.features is None
        assert response.settings is None
        assert response.created_at is None
        assert response.updated_at is None


class TestTenantSearchFilter:
    """Test TenantSearchFilter schema functionality."""

    def test_default_filter(self):
        """Test default search filter values."""
        filter_data = TenantSearchFilter()

        assert filter_data.search is None
        assert filter_data.status is None
        assert filter_data.tier is None
        assert filter_data.has_users is None
        assert filter_data.created_after is None
        assert filter_data.created_before is None
        assert filter_data.limit == 50
        assert filter_data.offset == 0

    def test_custom_filter(self):
        """Test custom search filter."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 12, 31)

        filter_data = TenantSearchFilter(
            search="corp",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.ENTERPRISE,
            has_users=True,
            created_after=created_after,
            created_before=created_before,
            limit=100,
            offset=25
        )

        assert filter_data.search == "corp"
        assert filter_data.status == TenantStatus.ACTIVE
        assert filter_data.tier == TenantTier.ENTERPRISE
        assert filter_data.has_users is True
        assert filter_data.created_after == created_after
        assert filter_data.created_before == created_before
        assert filter_data.limit == 100
        assert filter_data.offset == 25

    def test_filter_validation(self):
        """Test search filter validation."""
        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            TenantSearchFilter(limit=101)

        # Invalid offset (negative)
        with pytest.raises(ValidationError):
            TenantSearchFilter(offset=-1)


class TestTenantDashboardStats:
    """Test TenantDashboardStats schema functionality."""

    def test_dashboard_stats_creation(self):
        """Test creating dashboard stats."""
        recent_tenants = [
            TenantResponse(
                id=1,
                name="Recent Corp",
                status="active"
            )
        ]

        stats = TenantDashboardStats(
            total_tenants=100,
            active_tenants=80,
            inactive_tenants=15,
            suspended_tenants=5,
            total_users=1500,
            tenants_by_tier={
                "free": 60,
                "basic": 25,
                "professional": 10,
                "enterprise": 5
            },
            recent_tenants=recent_tenants
        )

        assert stats.total_tenants == 100
        assert stats.active_tenants == 80
        assert stats.inactive_tenants == 15
        assert stats.suspended_tenants == 5
        assert stats.total_users == 1500
        assert stats.tenants_by_tier["free"] == 60
        assert stats.tenants_by_tier["enterprise"] == 5
        assert len(stats.recent_tenants) == 1
        assert stats.recent_tenants[0].name == "Recent Corp"


class TestTenantUserResponse:
    """Test TenantUserResponse schema functionality."""

    def test_tenant_user_response_creation(self):
        """Test creating tenant user response."""
        user_response = TenantUserResponse(
            id="user-123",
            name="Tenant User",
            email="user@tenant.com",
            role="admin",
            status="active",
            enabled=True,
            created_at="2024-01-01T00:00:00",
            last_login="2024-01-15T10:30:00"
        )

        assert user_response.id == "user-123"
        assert user_response.name == "Tenant User"
        assert user_response.email == "user@tenant.com"
        assert user_response.role == "admin"
        assert user_response.status == "active"
        assert user_response.enabled is True
        assert user_response.created_at == "2024-01-01T00:00:00"
        assert user_response.last_login == "2024-01-15T10:30:00"

    def test_tenant_user_response_minimal(self):
        """Test creating minimal tenant user response."""
        user_response = TenantUserResponse(
            id="user-456",
            name="Minimal User",
            email="minimal@tenant.com",
            role="user",
            status="active",
            enabled=True,
            created_at="2024-01-01T00:00:00"
        )

        assert user_response.id == "user-456"
        assert user_response.last_login is None


class TestUserTenantAssignment:
    """Test UserTenantAssignment schema functionality."""

    def test_user_tenant_assignment_creation(self):
        """Test creating user tenant assignment."""
        assignment = UserTenantAssignment(
            user_id="user-789",
            tenant_id=42,
            role="moderator"
        )

        assert assignment.user_id == "user-789"
        assert assignment.tenant_id == 42
        assert assignment.role == "moderator"

    def test_user_tenant_assignment_default_role(self):
        """Test user tenant assignment with default role."""
        assignment = UserTenantAssignment(
            user_id="user-101",
            tenant_id=99
        )

        assert assignment.user_id == "user-101"
        assert assignment.tenant_id == 99
        assert assignment.role == "user"  # Default role


class TestTenantStats:
    """Test TenantStats schema functionality."""

    def test_tenant_stats_creation(self):
        """Test creating tenant stats."""
        stats = TenantStats(
            id=1,
            name="Stats Corp",
            status="active",
            user_count=75,
            max_users=100,
            utilization=0.75,
            tier="professional",
            created_at="2024-01-01T00:00:00",
            last_activity="2024-01-15T14:30:00"
        )

        assert stats.id == 1
        assert stats.name == "Stats Corp"
        assert stats.status == "active"
        assert stats.user_count == 75
        assert stats.max_users == 100
        assert stats.utilization == 0.75
        assert stats.tier == "professional"
        assert stats.created_at == "2024-01-01T00:00:00"
        assert stats.last_activity == "2024-01-15T14:30:00"

    def test_tenant_stats_no_activity(self):
        """Test tenant stats with no last activity."""
        stats = TenantStats(
            id=2,
            name="Inactive Corp",
            status="inactive",
            user_count=0,
            max_users=10,
            utilization=0.0,
            tier="free",
            created_at="2024-01-01T00:00:00"
        )

        assert stats.last_activity is None
        assert stats.utilization == 0.0


class TestDataTransformations:
    """Test data transformation and mapping functionality."""

    def test_tenant_create_to_tenant_model_mapping(self):
        """Test mapping TenantCreate data to Tenant model fields."""
        create_data = TenantCreate(
            name="Transform Corp",
            description="Test transformation",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.BASIC,
            contact_email="transform@corp.com",
            contact_name="Transform Manager",
            website="https://transform.corp.com",
            max_users=50,
            features={"transform": True},
            settings={"mode": "test"}
        )

        # Verify the mapping would work (this would be done in the service layer)
        expected_tenant_fields = {
            "name": create_data.name,
            "description": create_data.description,
            "status": create_data.status.value,
            "tier": create_data.tier.value,
            "contact_email": create_data.contact_email,
            "contact_name": create_data.contact_name,
            "website": create_data.website,
            "max_users": create_data.max_users,
            "features": create_data.features,
            "settings": create_data.settings
        }

        assert expected_tenant_fields["name"] == "Transform Corp"
        assert expected_tenant_fields["status"] == "active"
        assert expected_tenant_fields["tier"] == "basic"
        assert expected_tenant_fields["max_users"] == 50

    def test_tenant_update_field_extraction(self):
        """Test extracting only updated fields from TenantUpdate."""
        update_data = TenantUpdate(
            name="Updated Name",
            tier=TenantTier.ENTERPRISE
        )

        # Extract only the fields that were actually set
        update_fields = update_data.dict(exclude_unset=True)

        assert "name" in update_fields
        assert "tier" in update_fields
        assert "description" not in update_fields
        assert "status" not in update_fields
        assert "contact_email" not in update_fields

        assert update_fields["name"] == "Updated Name"
        assert update_fields["tier"] == TenantTier.ENTERPRISE

    def test_utilization_calculation(self):
        """Test utilization calculation logic."""
        # Normal utilization
        utilization = 75 / 100
        assert utilization == 0.75

        # Full utilization
        utilization = 100 / 100
        assert utilization == 1.0

        # Over-utilization (should not happen, but test edge case)
        utilization = 105 / 100
        assert utilization == 1.05

        # Zero utilization
        utilization = 0 / 100
        assert utilization == 0.0

        # Handle division by zero
        max_users = 0
        user_count = 0
        utilization = user_count / max_users if max_users > 0 else 0
        assert utilization == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_features_and_settings(self):
        """Test handling empty features and settings dictionaries."""
        tenant_data = TenantCreate(
            name="Empty Features Corp",
            features={},
            settings={}
        )

        assert tenant_data.features == {}
        assert tenant_data.settings == {}

    def test_none_optional_fields(self):
        """Test handling None values for optional fields."""
        tenant_data = TenantCreate(
            name="None Fields Corp",
            description=None,
            contact_email=None,
            contact_name=None,
            website=None
        )

        assert tenant_data.description is None
        assert tenant_data.contact_email is None
        assert tenant_data.contact_name is None
        assert tenant_data.website is None

    def test_unicode_names_and_descriptions(self):
        """Test handling unicode characters in names and descriptions."""
        tenant_data = TenantCreate(
            name="Üñïçödé Çorp™",
            description="Déscription with spéciål characters: ñäëïöü",
            contact_name="Jöhn Döe"
        )

        assert tenant_data.name == "Üñïçödé Çorp™"
        assert tenant_data.description == "Déscription with spéciål characters: ñäëïöü"
        assert tenant_data.contact_name == "Jöhn Döe"

    def test_special_characters_in_website(self):
        """Test handling special characters in website URLs."""
        website = "https://test-corp.co.uk/path?param=value&other=123#section"
        tenant_data = TenantCreate(
            name="Special URL Corp",
            website=website
        )

        assert tenant_data.website == website

    def test_complex_features_and_settings(self):
        """Test handling complex nested features and settings."""
        complex_features = {
            "analytics": {
                "enabled": True,
                "retention_days": 90,
                "events": ["login", "logout", "purchase"]
            },
            "integrations": {
                "stripe": {"enabled": True, "public_key": "pk_test_123"},
                "slack": {"enabled": False}
            },
            "limits": {
                "api_calls_per_hour": 1000,
                "storage_gb": 100
            }
        }

        complex_settings = {
            "ui": {
                "theme": "dark",
                "language": "en",
                "timezone": "UTC",
                "notifications": {
                    "email": True,
                    "push": False,
                    "frequency": "daily"
                }
            },
            "security": {
                "2fa_required": True,
                "session_timeout_minutes": 60,
                "allowed_ip_ranges": ["192.168.1.0/24"]
            }
        }

        tenant_data = TenantCreate(
            name="Complex Corp",
            features=complex_features,
            settings=complex_settings
        )

        assert tenant_data.features["analytics"]["enabled"] is True
        assert tenant_data.features["integrations"]["stripe"]["enabled"] is True
        assert tenant_data.settings["ui"]["theme"] == "dark"
        assert tenant_data.settings["security"]["2fa_required"] is True

    def test_boundary_values(self):
        """Test boundary values for field lengths and numbers."""
        # Minimum valid values
        tenant_data = TenantCreate(
            name="AB",  # Minimum 2 chars
            max_users=1  # Minimum 1 user
        )

        assert tenant_data.name == "AB"
        assert tenant_data.max_users == 1

        # Maximum valid values
        max_name = "A" * 255
        max_desc = "A" * 1000
        max_contact_name = "A" * 255
        max_website = "https://" + "a" * 490  # 500 total chars

        tenant_data_max = TenantCreate(
            name=max_name,
            description=max_desc,
            contact_name=max_contact_name,
            website=max_website,
            max_users=999999  # Large but reasonable number
        )

        assert len(tenant_data_max.name) == 255
        assert len(tenant_data_max.description) == 1000
        assert len(tenant_data_max.contact_name) == 255
        assert len(tenant_data_max.website) == 500
        assert tenant_data_max.max_users == 999999

    def test_feature_flag_scenarios(self):
        """Test various feature flag scenarios."""
        # All features disabled
        all_disabled = TenantCreate(
            name="Disabled Features Corp",
            features={
                "analytics": False,
                "billing": False,
                "integrations": False,
                "advanced_search": False
            }
        )

        assert all(not value for value in all_disabled.features.values())

        # Mixed feature states
        mixed_features = TenantCreate(
            name="Mixed Features Corp",
            features={
                "basic": True,
                "premium": False,
                "beta": True,
                "deprecated": False
            }
        )

        enabled_features = [k for k, v in mixed_features.features.items() if v]
        assert enabled_features == ["basic", "beta"]

    def test_tier_upgrade_scenarios(self):
        """Test scenarios related to tier upgrades."""
        # Free tier limitations
        free_tier = TenantCreate(
            name="Free Corp",
            tier=TenantTier.FREE,
            max_users=5,  # Typical free tier limit
            features={"basic_support": True, "premium_features": False}
        )

        assert free_tier.tier == TenantTier.FREE
        assert free_tier.max_users == 5

        # Enterprise tier capabilities
        enterprise_tier = TenantCreate(
            name="Enterprise Corp",
            tier=TenantTier.ENTERPRISE,
            max_users=1000,  # High enterprise limit
            features={
                "priority_support": True,
                "custom_integrations": True,
                "advanced_analytics": True,
                "white_labeling": True
            }
        )

        assert enterprise_tier.tier == TenantTier.ENTERPRISE
        assert enterprise_tier.max_users == 1000
        assert enterprise_tier.features["white_labeling"] is True