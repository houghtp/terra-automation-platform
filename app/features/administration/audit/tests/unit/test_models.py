"""
Comprehensive unit tests for Audit slice models and schemas.

These tests provide world-class coverage of audit log functionality,
including model validation, JSON serialization, and UI helper methods.
Template users should follow these patterns for other slices.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from app.features.administration.audit.models import AuditLog
from app.features.administration.audit.services import AuditService


class TestAuditLogModel:
    """Comprehensive tests for AuditLog model functionality."""

    def test_audit_log_creation_minimal(self):
        """Test basic audit log creation with minimal required fields."""
        log = AuditLog(
            tenant_id="test_tenant",
            action="USER_LOGIN",
            category="AUTH",
            severity="INFO"
        )

        assert log.tenant_id == "test_tenant"
        assert log.action == "USER_LOGIN"
        assert log.category == "AUTH"
        assert log.severity == "INFO"
        assert log.user_email is None
        assert log.ip_address is None
        assert log.description is None

    def test_audit_log_creation_complete(self):
        """Test audit log creation with all fields populated."""
        timestamp = datetime.now(timezone.utc)
        old_values = {"name": "Old Name", "status": "inactive"}
        new_values = {"name": "New Name", "status": "active"}
        extra_data = {"source": "admin_panel", "session_id": "sess_123"}

        log = AuditLog(
            tenant_id="test_tenant",
            action="USER_UPDATED",
            category="DATA",
            severity="INFO",
            user_email="admin@example.com",
            ip_address="192.168.1.100",
            description="User profile updated by admin",
            resource_type="User",
            resource_id="user_456",
            old_values=old_values,
            new_values=new_values,
            extra_data=extra_data,
            timestamp=timestamp
        )

        assert log.tenant_id == "test_tenant"
        assert log.action == "USER_UPDATED"
        assert log.category == "DATA"
        assert log.severity == "INFO"
        assert log.user_email == "admin@example.com"
        assert log.ip_address == "192.168.1.100"
        assert log.description == "User profile updated by admin"
        assert log.resource_type == "User"
        assert log.resource_id == "user_456"
        assert log.old_values == old_values
        assert log.new_values == new_values
        assert log.extra_data == extra_data
        assert log.timestamp == timestamp

    def test_audit_log_with_complex_json_data(self):
        """Test audit log with complex JSON data structures."""
        complex_old = {
            "user": {
                "name": "John Doe",
                "permissions": ["read", "write"],
                "metadata": {"last_login": "2024-01-01T00:00:00Z"}
            },
            "settings": {"theme": "dark", "notifications": True}
        }

        complex_new = {
            "user": {
                "name": "John Smith",
                "permissions": ["read", "write", "admin"],
                "metadata": {"last_login": "2024-01-02T00:00:00Z"}
            },
            "settings": {"theme": "light", "notifications": False}
        }

        log = AuditLog(
            tenant_id="test",
            action="COMPLEX_UPDATE",
            category="DATA",
            severity="INFO",
            old_values=complex_old,
            new_values=complex_new
        )

        assert log.old_values == complex_old
        assert log.new_values == complex_new

    def test_audit_log_with_unicode_data(self):
        """Test audit log with unicode characters in various fields."""
        log = AuditLog(
            tenant_id="test",
            action="UNICODE_TEST",
            category="DATA",
            severity="INFO",
            user_email="用户@测试.com",
            description="Test with émojis 🔒 and spëcial chars",
            old_values={"name": "João", "city": "São Paulo"},
            new_values={"name": "José", "city": "México"}
        )

        assert log.user_email == "用户@测试.com"
        assert log.description == "Test with émojis 🔒 and spëcial chars"
        assert log.old_values["name"] == "João"
        assert log.new_values["city"] == "México"

    def test_audit_log_category_validation(self):
        """Test different audit categories."""
        categories = ["AUTH", "DATA", "ADMIN", "SECURITY", "SYSTEM"]

        for category in categories:
            log = AuditLog(
                tenant_id="test",
                action=f"TEST_{category}",
                category=category,
                severity="INFO"
            )
            assert log.category == category

    def test_audit_log_severity_validation(self):
        """Test different severity levels."""
        severities = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for severity in severities:
            log = AuditLog(
                tenant_id="test",
                action="TEST_ACTION",
                category="DATA",
                severity=severity
            )
            assert log.severity == severity

    def test_audit_log_to_dict(self):
        """Test audit log dictionary conversion."""
        timestamp = datetime.now(timezone.utc)
        log = AuditLog(
            id=1,
            tenant_id="test_tenant",
            timestamp=timestamp,
            action="DATA_CREATED",
            category="DATA",
            severity="INFO",
            description="Test log entry"
        )

        result = log.to_dict()

        assert result["id"] == 1
        assert result["tenant_id"] == "test_tenant"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["action"] == "DATA_CREATED"
        assert result["category"] == "DATA"
        assert result["severity"] == "INFO"
        assert result["description"] == "Test log entry"

    def test_audit_log_edge_cases(self):
        """Test audit log with edge case values."""
        log = AuditLog(
            tenant_id="",
            action="",
            category="DATA",
            severity="INFO",
            description="",
            old_values={},
            new_values={},
            extra_data={}
        )

        assert log.tenant_id == ""
        assert log.action == ""
        assert log.description == ""
        assert log.old_values == {}
        assert log.new_values == {}
        assert log.extra_data == {}

    def test_audit_log_none_values(self):
        """Test audit log with None values for optional fields."""
        log = AuditLog(
            tenant_id="test",
            action="TEST",
            category="DATA",
            severity="INFO",
            user_email=None,
            ip_address=None,
            description=None,
            resource_type=None,
            resource_id=None,
            old_values=None,
            new_values=None,
            extra_data=None
        )

        assert log.user_email is None
        assert log.ip_address is None
        assert log.description is None
        assert log.resource_type is None
        assert log.resource_id is None
        assert log.old_values is None
        assert log.new_values is None
        assert log.extra_data is None


class TestAuditLogUIHelpers:
    """Test UI helper methods for AuditLog model."""

    def test_severity_color_mapping_all_levels(self):
        """Test severity color mapping for all severity levels."""
        expected_colors = {
            "DEBUG": "secondary",
            "INFO": "blue",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "dark"
        }

        for severity, expected_color in expected_colors.items():
            assert AuditLog.get_severity_color(severity) == expected_color

    def test_severity_color_mapping_unknown(self):
        """Test severity color mapping for unknown severities."""
        unknown_severities = ["UNKNOWN", "INVALID", "", None, "random"]

        for severity in unknown_severities:
            assert AuditLog.get_severity_color(severity) == "gray"

    def test_category_icon_mapping_all_categories(self):
        """Test category icon mapping for all categories."""
        expected_icons = {
            "AUTH": "ti-shield-check",
            "DATA": "ti-database",
            "ADMIN": "ti-settings",
            "SECURITY": "ti-shield-lock",
            "SYSTEM": "ti-server"
        }

        for category, expected_icon in expected_icons.items():
            assert AuditLog.get_category_icon(category) == expected_icon

    def test_category_icon_mapping_unknown(self):
        """Test category icon mapping for unknown categories."""
        unknown_categories = ["UNKNOWN", "INVALID", "", None, "random"]

        for category in unknown_categories:
            assert AuditLog.get_category_icon(category) == "ti-file-text"

    def test_severity_badge_class(self):
        """Test severity badge CSS class generation."""
        expected_classes = {
            "DEBUG": "badge-secondary",
            "INFO": "badge-blue",
            "WARNING": "badge-orange",
            "ERROR": "badge-red",
            "CRITICAL": "badge-dark"
        }

        for severity, expected_class in expected_classes.items():
            log = AuditLog(
                tenant_id="test",
                action="TEST",
                category="DATA",
                severity=severity
            )
            assert log.get_severity_badge_class() == expected_class

    def test_formatted_timestamp(self):
        """Test formatted timestamp display."""
        timestamp = datetime(2024, 1, 15, 14, 30, 45)
        log = AuditLog(
            tenant_id="test",
            action="TEST",
            category="DATA",
            severity="INFO",
            timestamp=timestamp
        )

        formatted = log.get_formatted_timestamp()
        assert "2024-01-15" in formatted
        assert "14:30:45" in formatted

    def test_formatted_timestamp_none(self):
        """Test formatted timestamp when timestamp is None."""
        log = AuditLog(
            tenant_id="test",
            action="TEST",
            category="DATA",
            severity="INFO",
            timestamp=None
        )

        formatted = log.get_formatted_timestamp()
        assert formatted == "N/A"

    def test_short_description(self):
        """Test short description truncation."""
        long_description = "This is a very long description that should be truncated because it exceeds the maximum length limit for display purposes in the UI"

        log = AuditLog(
            tenant_id="test",
            action="TEST",
            category="DATA",
            severity="INFO",
            description=long_description
        )

        short_desc = log.get_short_description(50)
        assert len(short_desc) <= 53  # 50 + "..."
        assert short_desc.endswith("...")

    def test_short_description_no_truncation(self):
        """Test short description when no truncation needed."""
        short_description = "Short description"

        log = AuditLog(
            tenant_id="test",
            action="TEST",
            category="DATA",
            severity="INFO",
            description=short_description
        )

        result = log.get_short_description(50)
        assert result == short_description

    def test_is_security_related(self):
        """Test identification of security-related audit logs."""
        security_actions = [
            "LOGIN_FAILED",
            "UNAUTHORIZED_ACCESS",
            "PASSWORD_CHANGED",
            "PERMISSION_ESCALATION",
            "SUSPICIOUS_ACTIVITY"
        ]

        for action in security_actions:
            log = AuditLog(
                tenant_id="test",
                action=action,
                category="SECURITY",
                severity="WARNING"
            )
            assert log.is_security_related() is True

        # Non-security log
        log = AuditLog(
            tenant_id="test",
            action="USER_CREATED",
            category="DATA",
            severity="INFO"
        )
        assert log.is_security_related() is False


class TestAuditService:
    """Test AuditService functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def audit_service(self, mock_db_session):
        """Create AuditService with mock session."""
        return AuditService(mock_db_session)

    @pytest.mark.asyncio
    async def test_get_audit_logs_basic(self, audit_service, mock_db_session):
        """Test basic audit logs retrieval."""
        # Mock database response
        mock_result = MagicMock()
        mock_logs = [
            AuditLog(id=1, tenant_id="test", action="LOGIN", category="AUTH"),
            AuditLog(id=2, tenant_id="test", action="LOGOUT", category="AUTH")
        ]
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        # Test the service
        logs = await audit_service.get_audit_logs("test", limit=10)

        assert len(logs) == 2
        assert logs[0].action == "LOGIN"
        assert logs[1].action == "LOGOUT"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self, audit_service, mock_db_session):
        """Test audit logs retrieval with filters."""
        mock_result = MagicMock()
        mock_logs = [AuditLog(id=1, tenant_id="test", action="LOGIN", category="AUTH")]
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        # Test with filters
        logs = await audit_service.get_audit_logs(
            "test",
            category_filter="AUTH",
            severity_filter="INFO",
            user_filter="user@test.com"
        )

        assert len(logs) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_stats(self, audit_service, mock_db_session):
        """Test audit statistics retrieval."""
        # Mock multiple query results
        mock_db_session.execute.side_effect = [
            # Total logs
            MagicMock(scalar=MagicMock(return_value=100)),
            # Recent 24h
            MagicMock(scalar=MagicMock(return_value=25)),
            # Recent 7d
            MagicMock(scalar=MagicMock(return_value=75)),
            # Security events
            MagicMock(scalar=MagicMock(return_value=5)),
            # Category breakdown
            MagicMock(scalars=MagicMock(return_value=[
                MagicMock(category="AUTH", count=50),
                MagicMock(category="DATA", count=30)
            ])),
            # Severity breakdown
            MagicMock(scalars=MagicMock(return_value=[
                MagicMock(severity="INFO", count=80),
                MagicMock(severity="WARNING", count=15)
            ])),
            # Top users
            MagicMock(scalars=MagicMock(return_value=[
                MagicMock(user_email="user1@test.com", count=10),
                MagicMock(user_email="user2@test.com", count=8)
            ]))
        ]

        stats = await audit_service.get_audit_stats("test")

        assert stats["total_logs"] == 100
        assert stats["recent_24h"] == 25
        assert stats["recent_7d"] == 75
        assert stats["security_events"] == 5
        assert stats["by_category"]["AUTH"] == 50
        assert stats["by_category"]["DATA"] == 30
        assert stats["by_severity"]["INFO"] == 80
        assert len(stats["top_users"]) == 2

    @pytest.mark.asyncio
    async def test_get_audit_log_by_id(self, audit_service, mock_db_session):
        """Test retrieving specific audit log by ID."""
        mock_log = AuditLog(id=1, tenant_id="test", action="LOGIN")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_log
        mock_db_session.execute.return_value = mock_result

        log = await audit_service.get_audit_log_by_id("test", 1)

        assert log is not None
        assert log.id == 1
        assert log.action == "LOGIN"

    @pytest.mark.asyncio
    async def test_search_audit_logs(self, audit_service, mock_db_session):
        """Test audit logs search functionality."""
        mock_result = MagicMock()
        mock_logs = [AuditLog(id=1, tenant_id="test", action="LOGIN", description="User login")]
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db_session.execute.return_value = mock_result

        logs = await audit_service.search_audit_logs("test", "login")

        assert len(logs) == 1
        assert logs[0].action == "LOGIN"

    @pytest.mark.asyncio
    async def test_get_audit_timeline(self, audit_service, mock_db_session):
        """Test audit timeline retrieval."""
        mock_result = MagicMock()
        mock_timeline_data = [
            MagicMock(day=datetime.now(timezone.utc).date(), category="AUTH", count=10),
            MagicMock(day=datetime.now(timezone.utc).date(), category="DATA", count=5)
        ]
        mock_result.scalars.return_value = mock_timeline_data
        mock_db_session.execute.return_value = mock_result

        timeline = await audit_service.get_audit_timeline("test", 7)

        assert len(timeline) == 2
        assert timeline[0]["category"] == "AUTH"
        assert timeline[0]["count"] == 10
