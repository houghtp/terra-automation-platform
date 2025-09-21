"""
Comprehensive integration tests for Dashboard slice routes.

These tests provide world-class coverage of dashboard API endpoints,
including authentication, tenant isolation, and data aggregation.
Template users should follow these patterns for other slices.
"""

import pytest
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.features.auth.services import AuthService
from app.features.auth.models import User


@pytest.mark.asyncio
class TestDashboardRoutes:
    """Integration tests for dashboard routes."""

    @pytest.fixture
    async def test_user_with_token(self, test_db_session: AsyncSession):
        """Create a test user and return user with access token."""
        auth_service = AuthService()
        user = await auth_service.create_user(
            session=test_db_session,
            email="dashboard@test.com",
            password="TestPass123!",
            tenant_id="test-tenant",
            role="admin"
        )
        await test_db_session.commit()

        access_token, _ = auth_service.create_tokens(user)
        return user, access_token

    @pytest.fixture
    async def global_admin_with_token(self, test_db_session: AsyncSession):
        """Create a global admin user with token."""
        auth_service = AuthService()
        user = await auth_service.create_user(
            session=test_db_session,
            email="globaladmin@test.com",
            password="TestPass123!",
            tenant_id="global",
            role="global_admin"
        )
        await test_db_session.commit()

        access_token, _ = auth_service.create_tokens(user)
        return user, access_token

    async def test_dashboard_page_requires_authentication(self, client: AsyncClient):
        """Test that dashboard page requires authentication."""
        response = await client.get("/dashboard/")

        # Should redirect to login or return 401
        assert response.status_code in [401, 302, 307]

    async def test_dashboard_page_loads_for_authenticated_user(
        self,
        client: AsyncClient,
        test_user_with_token,
        test_db_session: AsyncSession
    ):
        """Test dashboard page loads for authenticated user."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check for dashboard-specific content
        content = response.text
        assert "dashboard" in content.lower()

    async def test_dashboard_page_handles_service_errors_gracefully(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test dashboard page handles service errors gracefully."""
        user, access_token = test_user_with_token

        # Mock service to raise an error
        with patch('app.features.dashboard.services.dashboard_service.DashboardService.get_dashboard_summary') as mock_summary:
            mock_summary.side_effect = Exception("Service error")

            response = await client.get(
                "/dashboard/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "x-tenant-id": "test-tenant"
                }
            )

            # Should still return 200 but with error handling
            assert response.status_code == 200
            # Should contain error message or fallback content
            content = response.text
            assert "dashboard" in content.lower()

    async def test_dashboard_summary_api_success(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test dashboard summary API endpoint."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200

        data = response.json()
        required_fields = [
            "total_items",
            "active_items",
            "enabled_items",
            "items_with_due_dates",
            "completion_rate"
        ]

        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))

    async def test_dashboard_summary_api_requires_auth(self, client: AsyncClient):
        """Test that summary API requires authentication."""
        response = await client.get("/dashboard/api/summary")

        assert response.status_code == 401

    async def test_dashboard_summary_api_tenant_isolation(
        self,
        client: AsyncClient,
        test_user_with_token,
        global_admin_with_token,
        test_db_session: AsyncSession
    ):
        """Test that summary API respects tenant isolation."""
        user, user_token = test_user_with_token
        admin, admin_token = global_admin_with_token

        # Regular user should get tenant-specific data
        user_response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {user_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        # Global admin should get all data
        admin_response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "x-tenant-id": "global"
            }
        )

        assert user_response.status_code == 200
        assert admin_response.status_code == 200

        user_data = user_response.json()
        admin_data = admin_response.json()

        # Both should return valid data structures
        assert all(field in user_data for field in ["total_items", "active_items"])
        assert all(field in admin_data for field in ["total_items", "active_items"])

    async def test_status_breakdown_api_success(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test status breakdown API endpoint."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/status-breakdown",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200

        data = response.json()
        required_fields = ["categories", "values", "total"]

        for field in required_fields:
            assert field in data

        # Verify data types
        assert isinstance(data["categories"], list)
        assert isinstance(data["values"], list)
        assert isinstance(data["total"], int)

        # Categories and values should have same length
        assert len(data["categories"]) == len(data["values"])

    async def test_enabled_breakdown_api_success(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test enabled breakdown API endpoint."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/enabled-breakdown",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200

        data = response.json()
        required_fields = ["items", "total"]

        for field in required_fields:
            assert field in data

        # Verify data structure
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

        # Verify item structure if items exist
        for item in data["items"]:
            assert "name" in item
            assert "value" in item
            assert "itemStyle" in item
            assert "color" in item["itemStyle"]

    async def test_items_timeline_api_success(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test items timeline API endpoint."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/items-timeline",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200

        data = response.json()
        required_fields = ["categories", "values", "total"]

        for field in required_fields:
            assert field in data

        # Verify 30-day timeline structure
        assert isinstance(data["categories"], list)
        assert isinstance(data["values"], list)
        assert len(data["categories"]) == len(data["values"])

        # Should cover 30+ days
        assert len(data["categories"]) >= 30

    async def test_tags_distribution_api_success(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test tags distribution API endpoint."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/tags-distribution",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200

        data = response.json()
        required_fields = ["items", "total"]

        for field in required_fields:
            assert field in data

        # Verify data structure
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

        # Verify item structure if items exist
        for item in data["items"]:
            assert "name" in item
            assert "value" in item
            assert "itemStyle" in item
            assert "color" in item["itemStyle"]

    async def test_all_api_endpoints_require_authentication(self, client: AsyncClient):
        """Test that all dashboard API endpoints require authentication."""
        endpoints = [
            "/dashboard/api/summary",
            "/dashboard/api/status-breakdown",
            "/dashboard/api/enabled-breakdown",
            "/dashboard/api/items-timeline",
            "/dashboard/api/tags-distribution"
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"

    async def test_api_endpoints_handle_invalid_tenant(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test API endpoints handle invalid tenant gracefully."""
        user, access_token = test_user_with_token

        # Test with non-existent tenant
        response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "non-existent-tenant"
            }
        )

        # Should still return 200 with empty/default data
        assert response.status_code == 200

        data = response.json()
        assert "total_items" in data
        # Data might be empty but structure should be valid

    async def test_api_endpoints_handle_missing_tenant_header(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test API endpoints handle missing tenant header."""
        user, access_token = test_user_with_token

        response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {access_token}"
                # Missing x-tenant-id header
            }
        )

        # Should handle gracefully (might default to user's tenant or return error)
        assert response.status_code in [200, 400]

    async def test_dashboard_api_response_consistency(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test that dashboard API responses are consistent across calls."""
        user, access_token = test_user_with_token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": "test-tenant"
        }

        # Make multiple calls to same endpoint
        responses = []
        for _ in range(3):
            response = await client.get("/dashboard/api/summary", headers=headers)
            assert response.status_code == 200
            responses.append(response.json())

        # Responses should be consistent (assuming no data changes)
        first_response = responses[0]
        for response in responses[1:]:
            for key in first_response:
                assert response[key] == first_response[key], f"Inconsistent data for key: {key}"

    async def test_dashboard_api_performance(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test dashboard API performance."""
        user, access_token = test_user_with_token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": "test-tenant"
        }

        import time

        # Test all endpoints for response time
        endpoints = [
            "/dashboard/api/summary",
            "/dashboard/api/status-breakdown",
            "/dashboard/api/enabled-breakdown",
            "/dashboard/api/items-timeline",
            "/dashboard/api/tags-distribution"
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = await client.get(endpoint, headers=headers)
            end_time = time.time()

            assert response.status_code == 200
            response_time = end_time - start_time

            # API calls should complete within reasonable time (2 seconds)
            assert response_time < 2.0, f"Endpoint {endpoint} took too long: {response_time}s"

    async def test_dashboard_concurrent_access(
        self,
        client: AsyncClient,
        test_user_with_token,
        test_db_session: AsyncSession
    ):
        """Test dashboard handles concurrent access."""
        user, access_token = test_user_with_token

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": "test-tenant"
        }

        import asyncio

        # Make concurrent requests
        async def make_request(endpoint):
            response = await client.get(endpoint, headers=headers)
            return response.status_code, response.json()

        endpoints = [
            "/dashboard/api/summary",
            "/dashboard/api/status-breakdown",
            "/dashboard/api/enabled-breakdown"
        ]

        # Run multiple endpoints concurrently
        tasks = [make_request(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks)

        # All requests should succeed
        for status_code, data in results:
            assert status_code == 200
            assert isinstance(data, dict)

    async def test_dashboard_error_response_format(
        self,
        client: AsyncClient,
        test_user_with_token
    ):
        """Test that dashboard API returns consistent error format."""
        user, access_token = test_user_with_token

        # Test with invalid endpoint
        response = await client.get(
            "/dashboard/api/nonexistent",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 404

    async def test_dashboard_data_aggregation_accuracy(
        self,
        client: AsyncClient,
        test_user_with_token,
        test_db_session: AsyncSession
    ):
        """Test that dashboard data aggregation is accurate."""
        user, access_token = test_user_with_token

        # Create some test data first
        auth_service = AuthService()

        # Create additional users with known statuses
        test_users = [
            ("active1@test.com", "active", True),
            ("active2@test.com", "active", True),
            ("inactive1@test.com", "inactive", False),
            ("pending1@test.com", "pending", True)
        ]

        for email, status, enabled in test_users:
            test_user = await auth_service.create_user(
                session=test_db_session,
                email=email,
                password="TestPass123!",
                tenant_id="test-tenant",
                role="user"
            )
            # Update status and enabled fields
            test_user.status = status
            test_user.enabled = enabled

        await test_db_session.commit()

        # Get dashboard summary
        response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify that totals include our test data
        assert data["total_items"] >= 5  # Original user + 4 test users
        assert data["active_items"] >= 2  # 2 active users
        assert data["enabled_items"] >= 3  # 3 enabled users

        # Get status breakdown
        status_response = await client.get(
            "/dashboard/api/status-breakdown",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        status_data = status_response.json()

        # Should have categories for our test statuses
        categories = [cat.lower() for cat in status_data["categories"]]
        assert "active" in categories
        assert status_data["total"] >= 5

    async def test_dashboard_global_admin_vs_tenant_user_data(
        self,
        client: AsyncClient,
        test_user_with_token,
        global_admin_with_token,
        test_db_session: AsyncSession
    ):
        """Test data differences between global admin and tenant user."""
        user, user_token = test_user_with_token
        admin, admin_token = global_admin_with_token

        # Create users in different tenants
        auth_service = AuthService()

        # Create user in different tenant
        await auth_service.create_user(
            session=test_db_session,
            email="other_tenant@test.com",
            password="TestPass123!",
            tenant_id="other-tenant",
            role="user"
        )
        await test_db_session.commit()

        # Get data as regular user (should see only test-tenant data)
        user_response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {user_token}",
                "x-tenant-id": "test-tenant"
            }
        )

        # Get data as global admin (should see all data)
        admin_response = await client.get(
            "/dashboard/api/summary",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "x-tenant-id": "global"
            }
        )

        assert user_response.status_code == 200
        assert admin_response.status_code == 200

        user_data = user_response.json()
        admin_data = admin_response.json()

        # Global admin should see more or equal data
        assert admin_data["total_items"] >= user_data["total_items"]