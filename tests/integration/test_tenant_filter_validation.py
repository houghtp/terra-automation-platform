"""
Integration tests for tenant filter validation (Option 3: Hybrid Enforcement).

Tests the BaseService.execute() method's tenant filter validation logic.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.enhanced_base_service import BaseService, TenantFilterError
from app.features.auth.models import User
from app.features.administration.tenants.db_models import Tenant
from app.features.auth.services import AuthService


@pytest.mark.integration
@pytest.mark.tenant_isolation
class TestTenantFilterValidation:
    """Test BaseService.execute() tenant filter validation."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_data(self, test_db_session):
        """Create test data for tenant isolation tests."""
        self.db = test_db_session
        auth_service = AuthService()

        # Create test users for two tenants
        await auth_service.create_user(
            session=self.db,
            email="user1@tenant-a.com",
            password="SecurePass123!",
            tenant_id="tenant-a",
            role="user",
            name="User 1"
        )
        await auth_service.create_user(
            session=self.db,
            email="user2@tenant-a.com",
            password="SecurePass123!",
            tenant_id="tenant-a",
            role="user",
            name="User 2"
        )
        await auth_service.create_user(
            session=self.db,
            email="user1@tenant-b.com",
            password="SecurePass123!",
            tenant_id="tenant-b",
            role="user",
            name="User 1 B"
        )
        await auth_service.create_user(
            session=self.db,
            email="user2@tenant-b.com",
            password="SecurePass123!",
            tenant_id="tenant-b",
            role="user",
            name="User 2 B"
        )
        await self.db.commit()

    async def test_execute_validates_tenant_filter_for_regular_users(self, test_db_session):
        """Test that execute() raises error when tenant filter is missing."""
        service = BaseService(test_db_session, "tenant-a")

        # Query without tenant filter (should fail)
        stmt = select(User).where(User.email.like("%@tenant-a.com"))

        with pytest.raises(TenantFilterError) as exc_info:
            await service.execute(stmt, User)

        assert "missing tenant filter" in str(exc_info.value).lower()
        assert "tenant-a" in str(exc_info.value)

    async def test_execute_passes_with_valid_tenant_filter(self, test_db_session):
        """Test that execute() passes when tenant filter is present."""
        service = BaseService(test_db_session, "tenant-a")

        # Query WITH tenant filter (should pass)
        stmt = select(User).where(User.tenant_id == "tenant-a")

        result = await service.execute(stmt, User)
        users = result.scalars().all()

        assert len(users) == 2
        assert all(u.tenant_id == "tenant-a" for u in users)

    async def test_execute_with_create_base_query_passes_validation(self, test_db_session):
        """Test that execute() works with create_base_query()."""
        service = BaseService(test_db_session, "tenant-a")

        # Use create_base_query (automatically adds tenant filter)
        stmt = service.create_base_query(User)

        result = await service.execute(stmt, User)
        users = result.scalars().all()

        assert len(users) == 2
        assert all(u.tenant_id == "tenant-a" for u in users)

    async def test_execute_auto_bypasses_for_global_admin(self, test_db_session):
        """Test that global admins bypass validation automatically."""
        service = BaseService(test_db_session, tenant_id="global")  # Global admin
        assert service.is_global_admin is True

        # Query without tenant filter (should pass for global admin)
        stmt = select(User)

        result = await service.execute(stmt, User)
        users = result.scalars().all()

        # Should see ALL users across all tenants
        assert len(users) == 4  # 2 from tenant-a + 2 from tenant-b
        assert any(u.tenant_id == "tenant-a" for u in users)
        assert any(u.tenant_id == "tenant-b" for u in users)

    async def test_execute_allows_cross_tenant_with_reason(self, test_db_session):
        """Test that allow_cross_tenant=True with reason bypasses validation."""
        service = BaseService(test_db_session, "tenant-a")

        # Cross-tenant query with explicit reason
        stmt = select(func.count(User.id)).group_by(User.tenant_id)

        result = await service.execute(
            stmt, User,
            allow_cross_tenant=True,
            reason="Testing cross-tenant aggregation for admin dashboard"
        )

        # Should work without error
        counts = result.all()
        assert len(counts) == 2  # Two tenants

    async def test_execute_requires_reason_for_cross_tenant(self, test_db_session):
        """Test that allow_cross_tenant=True without reason raises ValueError."""
        service = BaseService(test_db_session, "tenant-a")

        stmt = select(User)

        with pytest.raises(ValueError) as exc_info:
            await service.execute(stmt, User, allow_cross_tenant=True)  # Missing reason

        assert "reason" in str(exc_info.value).lower()
        assert "audit" in str(exc_info.value).lower()

    async def test_execute_handles_models_without_tenant_id(self, test_db_session):
        """Test that models without tenant_id field pass validation."""
        service = BaseService(test_db_session, "tenant-a")

        # Tenant model doesn't have tenant_id field
        stmt = select(Tenant).where(Tenant.name.like("%"))

        # Should not raise error (model has no tenant_id field)
        result = await service.execute(stmt, Tenant)
        # Query should work fine

    async def test_db_property_logs_deprecation_warning(self, test_db_session, caplog):
        """Test that using self.db.execute() logs deprecation warning."""
        import logging
        caplog.set_level(logging.WARNING)

        service = BaseService(test_db_session, "tenant-a")

        # Access db property (should log warning)
        stmt = service.create_base_query(User)
        _ = await service.db.execute(stmt)

        # Check warning was logged
        assert any("DEPRECATED" in record.message for record in caplog.records)
        assert any("self.db.execute()" in record.message for record in caplog.records)

    async def test_db_property_no_warning_for_global_admin(self, test_db_session, caplog):
        """Test that global admins don't get deprecation warnings."""
        import logging
        caplog.set_level(logging.WARNING)

        service = BaseService(test_db_session, tenant_id="global")

        # Access db property as global admin (should NOT log warning)
        stmt = select(User)
        _ = await service.db.execute(stmt)

        # Should not have deprecation warnings
        deprecation_warnings = [r for r in caplog.records if "DEPRECATED" in r.message]
        assert len(deprecation_warnings) == 0

    async def test_db_property_logs_warning_only_once(self, test_db_session, caplog):
        """Test that deprecation warning is only logged once per service instance."""
        import logging
        caplog.set_level(logging.WARNING)

        service = BaseService(test_db_session, "tenant-a")
        stmt = service.create_base_query(User)

        # Access db property multiple times
        _ = await service.db.execute(stmt)
        _ = await service.db.execute(stmt)
        _ = await service.db.execute(stmt)

        # Should only have ONE deprecation warning
        deprecation_warnings = [r for r in caplog.records if "DEPRECATED" in r.message and "db.execute" in r.message]
        assert len(deprecation_warnings) == 1

    async def test_execute_logs_cross_tenant_queries(self, test_db_session, caplog):
        """Test that cross-tenant queries are logged for audit trail."""
        import logging
        caplog.set_level(logging.WARNING)

        service = BaseService(test_db_session, "tenant-a")

        stmt = select(User)
        await service.execute(
            stmt, User,
            allow_cross_tenant=True,
            reason="Admin report - all tenants user count"
        )

        # Check audit log
        audit_logs = [r for r in caplog.records if "Cross-tenant query" in r.message]
        assert len(audit_logs) == 1
        assert "Admin report" in audit_logs[0].message

    async def test_legacy_execute_with_tenant_check_still_works(self, test_db_session):
        """Test that old execute_with_tenant_check() method still works (deprecated)."""
        service = BaseService(test_db_session, "tenant-a")

        stmt = service.create_base_query(User)

        # Old method should still work (with deprecation warning)
        result = await service.execute_with_tenant_check(stmt, User)
        users = result.scalars().all()

        assert len(users) == 2
        assert all(u.tenant_id == "tenant-a" for u in users)


@pytest.mark.integration
class TestTenantFilterErrorMessages:
    """Test that error messages are helpful and actionable."""

    async def test_error_message_includes_model_name(self, test_db_session):
        """Test that error message includes the model name."""
        service = BaseService(test_db_session, "tenant-a")
        stmt = select(User)

        with pytest.raises(TenantFilterError) as exc_info:
            await service.execute(stmt, User)

        assert "User" in str(exc_info.value)

    async def test_error_message_includes_tenant_id(self, test_db_session):
        """Test that error message includes current tenant ID."""
        service = BaseService(test_db_session, "tenant-xyz")
        stmt = select(User)

        with pytest.raises(TenantFilterError) as exc_info:
            await service.execute(stmt, User)

        assert "tenant-xyz" in str(exc_info.value)

    async def test_error_message_includes_solutions(self, test_db_session):
        """Test that error message includes actionable solutions."""
        service = BaseService(test_db_session, "tenant-a")
        stmt = select(User)

        with pytest.raises(TenantFilterError) as exc_info:
            await service.execute(stmt, User)

        error_msg = str(exc_info.value)
        assert "create_base_query" in error_msg
        assert "allow_cross_tenant" in error_msg
        assert "Solutions:" in error_msg
