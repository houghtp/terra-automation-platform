"""
Comprehensive unit tests for Dashboard slice services.

These tests provide world-class coverage of dashboard service functionality,
including data aggregation, analytics, and chart data generation.
Template users should follow these patterns for other slices.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from app.features.dashboard.services import DashboardService


class TestDashboardService:
    """Comprehensive tests for DashboardService functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_user_status_data(self):
        """Sample user status data for testing."""
        return [
            MagicMock(status="active", count=25),
            MagicMock(status="inactive", count=10),
            MagicMock(status="pending", count=5),
            MagicMock(status="suspended", count=2)
        ]

    @pytest.fixture
    def sample_enabled_data(self):
        """Sample enabled/disabled data for testing."""
        return [
            MagicMock(status="Enabled", count=35),
            MagicMock(status="Disabled", count=7)
        ]

    @pytest.fixture
    def sample_tag_data(self):
        """Sample tag data for testing."""
        return [
            MagicMock(tags='["developer", "frontend"]'),
            MagicMock(tags='["designer", "ui/ux"]'),
            MagicMock(tags='["developer", "backend"]'),
            MagicMock(tags='["manager", "team-lead"]'),
            MagicMock(tags='["developer", "fullstack"]')
        ]

    @pytest.fixture
    def sample_timeline_data(self):
        """Sample timeline data for testing."""
        base_date = datetime.now().date() - timedelta(days=5)
        return [
            MagicMock(date=str(base_date), count=3),
            MagicMock(date=str(base_date + timedelta(days=1)), count=5),
            MagicMock(date=str(base_date + timedelta(days=2)), count=2),
            MagicMock(date=str(base_date + timedelta(days=3)), count=8),
            MagicMock(date=str(base_date + timedelta(days=4)), count=4)
        ]

    @pytest.mark.asyncio
    async def test_get_user_status_breakdown_with_tenant(self, mock_db_session, sample_user_status_data):
        """Test user status breakdown with tenant filtering."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_user_status_data
        mock_db_session.execute.return_value = mock_result

        # Test with specific tenant
        result = await DashboardService.get_user_status_breakdown(mock_db_session, "test-tenant")

        # Verify database query was called
        mock_db_session.execute.assert_called_once()
        called_args = mock_db_session.execute.call_args

        # Verify query contains tenant filtering
        query_text = str(called_args[0][0])
        assert "tenant_id = :tenant" in query_text

        # Verify parameters
        assert called_args[1] == {"tenant": "test-tenant"}

        # Verify result structure
        assert "categories" in result
        assert "values" in result
        assert "total" in result

        # Verify data transformation
        expected_categories = ["Active", "Inactive", "Pending", "Suspended"]
        expected_values = [25, 10, 5, 2]
        expected_total = 42

        assert result["categories"] == expected_categories
        assert result["values"] == expected_values
        assert result["total"] == expected_total

    @pytest.mark.asyncio
    async def test_get_user_status_breakdown_global_admin(self, mock_db_session, sample_user_status_data):
        """Test user status breakdown for global admin (no tenant filtering)."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_user_status_data
        mock_db_session.execute.return_value = mock_result

        # Test with global admin tenant
        result = await DashboardService.get_user_status_breakdown(mock_db_session, "global")

        # Verify database query was called
        mock_db_session.execute.assert_called_once()
        called_args = mock_db_session.execute.call_args

        # Verify query does NOT contain tenant filtering
        query_text = str(called_args[0][0])
        assert "tenant_id = :tenant" not in query_text

        # Verify no parameters passed
        assert len(called_args) == 1  # Only the query, no parameters

        # Verify result
        assert result["total"] == 42

    @pytest.mark.asyncio
    async def test_get_user_status_breakdown_no_tenant(self, mock_db_session, sample_user_status_data):
        """Test user status breakdown with no tenant specified."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_user_status_data
        mock_db_session.execute.return_value = mock_result

        # Test with no tenant
        result = await DashboardService.get_user_status_breakdown(mock_db_session)

        # Verify no tenant filtering
        called_args = mock_db_session.execute.call_args
        query_text = str(called_args[0][0])
        assert "tenant_id = :tenant" not in query_text

        assert result["total"] == 42

    @pytest.mark.asyncio
    async def test_get_user_status_breakdown_empty_data(self, mock_db_session):
        """Test user status breakdown with empty data."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_status_breakdown(mock_db_session, "test-tenant")

        assert result["categories"] == []
        assert result["values"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_user_status_breakdown_error_handling(self, mock_db_session):
        """Test user status breakdown error handling."""
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await DashboardService.get_user_status_breakdown(mock_db_session, "test-tenant")

        # Should return empty data on error
        assert result["categories"] == []
        assert result["values"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_user_enabled_breakdown_success(self, mock_db_session, sample_enabled_data):
        """Test enabled/disabled user breakdown."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_enabled_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_enabled_breakdown(mock_db_session, "test-tenant")

        # Verify result structure
        assert "items" in result
        assert "total" in result

        # Verify data transformation
        assert len(result["items"]) == 2
        assert result["total"] == 42

        # Verify item structure and colors
        enabled_item = result["items"][0]
        assert enabled_item["name"] == "Enabled"
        assert enabled_item["value"] == 35
        assert "itemStyle" in enabled_item
        assert enabled_item["itemStyle"]["color"] == "#3b82f6"

        disabled_item = result["items"][1]
        assert disabled_item["name"] == "Disabled"
        assert disabled_item["value"] == 7
        assert disabled_item["itemStyle"]["color"] == "#ef4444"

    @pytest.mark.asyncio
    async def test_get_user_enabled_breakdown_with_global_admin(self, mock_db_session, sample_enabled_data):
        """Test enabled breakdown for global admin."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_enabled_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_enabled_breakdown(mock_db_session, "global")

        # Verify global admin query (no tenant filtering)
        called_args = mock_db_session.execute.call_args
        query_text = str(called_args[0][0])
        assert "tenant_id = :tenant" not in query_text

        assert result["total"] == 42

    @pytest.mark.asyncio
    async def test_get_user_tag_distribution_success(self, mock_db_session, sample_tag_data):
        """Test user tag distribution analysis."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_tag_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_tag_distribution(mock_db_session)

        # Verify result structure
        assert "items" in result
        assert "total" in result

        # Verify tag counting logic
        assert len(result["items"]) > 0
        assert result["total"] > 0

        # Verify top tag is "developer" (appears 3 times)
        developer_item = result["items"][0]
        assert developer_item["name"] == "Developer"
        assert developer_item["value"] == 3

        # Verify items have colors
        for item in result["items"]:
            assert "itemStyle" in item
            assert "color" in item["itemStyle"]

    @pytest.mark.asyncio
    async def test_get_user_tag_distribution_invalid_json(self, mock_db_session):
        """Test tag distribution with invalid JSON data."""
        sample_data = [
            MagicMock(tags='["valid", "json"]'),
            MagicMock(tags='invalid json'),
            MagicMock(tags='{"not": "array"}'),
            MagicMock(tags=None)
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_tag_distribution(mock_db_session)

        # Should only process valid JSON arrays
        assert len(result["items"]) == 2  # "valid" and "json"
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_get_user_tag_distribution_limit_to_top_10(self, mock_db_session):
        """Test that tag distribution limits to top 10 tags."""
        # Create data with 15 different tags
        tags_data = []
        for i in range(15):
            tag_name = f"tag{i}"
            # Create varying counts: tag0 appears 15 times, tag1 appears 14 times, etc.
            for j in range(15 - i):
                tags_data.append(MagicMock(tags=f'["{tag_name}"]'))

        mock_result = MagicMock()
        mock_result.fetchall.return_value = tags_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_tag_distribution(mock_db_session)

        # Should limit to top 10
        assert len(result["items"]) == 10

        # Should be sorted by count (highest first)
        counts = [item["value"] for item in result["items"]]
        assert counts == sorted(counts, reverse=True)

        # Top tag should be "Tag0" with 15 occurrences
        assert result["items"][0]["name"] == "Tag0"
        assert result["items"][0]["value"] == 15

    @pytest.mark.asyncio
    async def test_get_users_over_time_success(self, mock_db_session, sample_timeline_data):
        """Test users created over time analysis."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_timeline_data
        mock_db_session.execute.return_value = mock_result

        with patch('app.features.dashboard.services.dashboard_service.datetime') as mock_datetime:
            # Mock current time
            mock_now = datetime(2024, 1, 10, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await DashboardService.get_users_over_time(mock_db_session)

        # Verify result structure
        assert "categories" in result
        assert "values" in result
        assert "total" in result

        # Verify 30-day range
        assert len(result["categories"]) == 31  # 30 days + current day

        # Verify date formatting (MM/DD)
        for category in result["categories"]:
            assert "/" in category
            parts = category.split("/")
            assert len(parts) == 2
            assert 1 <= int(parts[0]) <= 12  # Month
            assert 1 <= int(parts[1]) <= 31  # Day

        # Verify total calculation
        assert result["total"] == sum(result["values"])

    @pytest.mark.asyncio
    async def test_get_users_over_time_fills_missing_dates(self, mock_db_session):
        """Test that timeline fills in missing dates with zero counts."""
        # Only provide data for a few specific dates
        sparse_data = [
            MagicMock(date="2024-01-05", count=3),
            MagicMock(date="2024-01-10", count=5)
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = sparse_data
        mock_db_session.execute.return_value = mock_result

        with patch('app.features.dashboard.services.dashboard_service.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await DashboardService.get_users_over_time(mock_db_session)

        # Should have 31 days of data
        assert len(result["values"]) == 31

        # Most values should be 0 (missing dates)
        zero_count = result["values"].count(0)
        assert zero_count == 29  # 31 total - 2 with data

        # Non-zero values should match our sample data
        non_zero_values = [v for v in result["values"] if v > 0]
        assert non_zero_values == [3, 5]

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_with_tenant(self, mock_db_session):
        """Test dashboard summary with tenant filtering."""
        # Mock multiple query results
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=100)),  # total
            MagicMock(scalar=MagicMock(return_value=75)),   # active
            MagicMock(scalar=MagicMock(return_value=85)),   # enabled
            MagicMock(scalar=MagicMock(return_value=25))    # due dates
        ]

        result = await DashboardService.get_dashboard_summary(mock_db_session, "test-tenant")

        # Verify all queries were made with tenant parameter
        assert mock_db_session.execute.call_count == 4

        # Verify result structure and calculations
        assert result["total_items"] == 100
        assert result["active_items"] == 75
        assert result["enabled_items"] == 85
        assert result["items_with_due_dates"] == 25
        assert result["completion_rate"] == 75.0  # 75/100 * 100

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_global_admin(self, mock_db_session):
        """Test dashboard summary for global admin."""
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=200)),  # total
            MagicMock(scalar=MagicMock(return_value=150)),  # active
            MagicMock(scalar=MagicMock(return_value=180)),  # enabled
            MagicMock(scalar=MagicMock(return_value=50))    # due dates
        ]

        result = await DashboardService.get_dashboard_summary(mock_db_session, "global")

        # Verify queries don't include tenant filtering
        for call_args in mock_db_session.execute.call_args_list:
            query_text = str(call_args[0][0])
            assert "tenant_id = :tenant" not in query_text

        assert result["completion_rate"] == 75.0  # 150/200 * 100

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_zero_division_handling(self, mock_db_session):
        """Test dashboard summary handles zero division in completion rate."""
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),   # total
            MagicMock(scalar=MagicMock(return_value=0)),   # active
            MagicMock(scalar=MagicMock(return_value=0)),   # enabled
            MagicMock(scalar=MagicMock(return_value=0))    # due dates
        ]

        result = await DashboardService.get_dashboard_summary(mock_db_session, "test-tenant")

        # Should handle zero division gracefully
        assert result["completion_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_error_handling(self, mock_db_session):
        """Test dashboard summary error handling."""
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await DashboardService.get_dashboard_summary(mock_db_session, "test-tenant")

        # Should return default values on error
        expected_defaults = {
            "total_items": 0,
            "active_items": 0,
            "enabled_items": 0,
            "items_with_due_dates": 0,
            "completion_rate": 0.0
        }

        assert result == expected_defaults

    @pytest.mark.asyncio
    async def test_all_methods_handle_database_errors_gracefully(self, mock_db_session):
        """Test that all service methods handle database errors gracefully."""
        # Mock database error for all methods
        mock_db_session.execute.side_effect = Exception("Database connection lost")

        methods_to_test = [
            ("get_user_status_breakdown", ["test-tenant"]),
            ("get_user_enabled_breakdown", ["test-tenant"]),
            ("get_user_tag_distribution", []),
            ("get_users_over_time", []),
            ("get_dashboard_summary", ["test-tenant"])
        ]

        for method_name, args in methods_to_test:
            method = getattr(DashboardService, method_name)
            result = await method(mock_db_session, *args)

            # All methods should return safe default values
            assert isinstance(result, dict)

            # Common fields that should be safe
            if "total" in result:
                assert result["total"] == 0
            if "categories" in result:
                assert result["categories"] == []
            if "values" in result:
                assert result["values"] == []
            if "items" in result:
                assert result["items"] == []

    @pytest.mark.asyncio
    async def test_service_methods_with_various_data_types(self, mock_db_session):
        """Test service methods handle various data types correctly."""
        # Test with different mock data types
        mixed_status_data = [
            MagicMock(status="active", count=10),
            MagicMock(status=None, count=5),  # None status
            MagicMock(status="", count=2),    # Empty status
            MagicMock(status="UPPERCASE", count=3)  # Uppercase
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mixed_status_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_status_breakdown(mock_db_session)

        # Should handle various data types gracefully
        assert len(result["categories"]) == 3  # None should be filtered out
        assert "Active" in result["categories"]
        assert "Uppercase" in result["categories"]

    @pytest.mark.asyncio
    async def test_tag_distribution_with_different_tag_formats(self, mock_db_session):
        """Test tag distribution with different tag data formats."""
        varied_tag_data = [
            MagicMock(tags='["normal", "tags"]'),                    # Normal JSON array
            MagicMock(tags=["python", "list"]),                     # Python list
            MagicMock(tags='[]'),                                    # Empty array
            MagicMock(tags='["single"]'),                           # Single tag
            MagicMock(tags='["tag-with-dash", "tag_with_underscore"]'),  # Special chars
            MagicMock(tags='["UPPERCASE", "lowercase"]')             # Mixed case
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = varied_tag_data
        mock_db_session.execute.return_value = mock_result

        result = await DashboardService.get_user_tag_distribution(mock_db_session)

        # Should process all valid tag formats
        tag_names = [item["name"] for item in result["items"]]

        # Check that various formats are handled
        assert len(result["items"]) > 0
        assert result["total"] > 0

        # Verify title case conversion
        for tag_name in tag_names:
            assert tag_name[0].isupper()  # Should be title case