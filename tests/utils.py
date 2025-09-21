"""
Test utilities and helper functions for the FastAPI template test suite.

This module provides common utilities for creating test data,
asserting responses, and performing common test operations.
"""

from typing import Any, Dict, List, Optional
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

# Demo module removed - using user models for test data
from app.features.auth.models import User


class TestDataFactory:
    """Factory for creating test data with realistic values."""

    @staticmethod
    def user_data(tenant_id: str, **overrides) -> Dict[str, Any]:
        """Create user data for testing."""
        default_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "tenant_id": tenant_id,
            "role": "user"
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def tenant_data(tenant_id: str, **overrides) -> Dict[str, Any]:
        """Create tenant data for testing."""
        default_data = {
            "id": tenant_id,
            "name": f"Test Tenant {tenant_id}",
            "metadata": {"plan": "test", "created_by": "test_suite"}
        }
        default_data.update(overrides)
        return default_data


class DatabaseTestHelper:
    """Helper class for database operations in tests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_test_users(self, tenant_id: str, count: int = 3) -> List[User]:
        """Create multiple test users for testing."""
        users = []
        for i in range(count):
            data = TestDataFactory.user_data(
                tenant_id,
                email=f"user{i+1}@{tenant_id}.com"
            )
            # Create user directly using User model
            from app.features.auth.services import AuthService
            auth_service = AuthService()
            user = await auth_service.create_user(
                session=self.session,
                email=data["email"],
                password=data["password"],
                tenant_id=tenant_id,
                role=data["role"]
            )
            users.append(user)

        # Commit all users at once to ensure they're persisted
        await self.session.commit()
        return users

    async def count_users(self, tenant_id: str) -> int:
        """Count users for a specific tenant."""
        from sqlalchemy import select, func
        result = await self.session.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant_id)
        )
        return result.scalar() or 0


class APITestHelper:
    """Helper class for API testing operations."""

    def __init__(self, client: AsyncClient):
        self.client = client

    async def get_with_tenant(self, url: str, tenant_id: str, **kwargs) -> Response:
        """Make GET request with tenant header."""
        headers = kwargs.pop("headers", {})
        headers["X-Tenant-ID"] = tenant_id
        return await self.client.get(url, headers=headers, **kwargs)

    async def post_with_tenant(self, url: str, tenant_id: str, **kwargs) -> Response:
        """Make POST request with tenant header."""
        headers = kwargs.pop("headers", {})
        headers["X-Tenant-ID"] = tenant_id

        # Handle data as form data if provided
        data = kwargs.pop("data", None)
        if data is not None:
            kwargs["data"] = data  # For form data submission

        return await self.client.post(url, headers=headers, **kwargs)

    async def delete_with_tenant(self, url: str, tenant_id: str, **kwargs) -> Response:
        """Make DELETE request with tenant header."""
        headers = kwargs.pop("headers", {})
        headers["X-Tenant-ID"] = tenant_id
        return await self.client.delete(url, headers=headers, **kwargs)

    async def create_demo_item_via_api(self, tenant_id: str, data: Optional[Dict] = None) -> Response:
        """Create demo item via API endpoint."""
        if data is None:
            data = TestDataFactory.demo_item_data(tenant_id)

        return await self.post_with_tenant("/demo/new", tenant_id, data=data)

    async def get_demo_items_via_api(self, tenant_id: str) -> Response:
        """Get demo items via API endpoint."""
        return await self.get_with_tenant("/demo/api/demo", tenant_id)


class ResponseAssertions:
    """Helper class for common response assertions."""

    @staticmethod
    def assert_success(response: Response, expected_status: int = 200):
        """Assert response is successful."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"

    @staticmethod
    def assert_json_response(response: Response) -> Dict[str, Any]:
        """Assert response is JSON and return parsed data."""
        ResponseAssertions.assert_success(response)
        assert response.headers.get("content-type", "").startswith("application/json")
        return response.json()

    @staticmethod
    def assert_html_response(response: Response) -> str:
        """Assert response is HTML and return content."""
        ResponseAssertions.assert_success(response)
        assert "text/html" in response.headers.get("content-type", "")
        return response.text

    @staticmethod
    def assert_tenant_isolation(tenant_a_data: List[Dict], tenant_b_data: List[Dict]):
        """Assert that tenant data is properly isolated."""
        # Ensure no data mixing between tenants
        tenant_a_ids = {item.get("id") for item in tenant_a_data if "id" in item}
        tenant_b_ids = {item.get("id") for item in tenant_b_data if "id" in item}

        assert tenant_a_ids.isdisjoint(tenant_b_ids), "Tenant data is not properly isolated"

    @staticmethod
    def assert_demo_item_structure(item_data: Dict[str, Any]):
        """Assert demo item has expected structure."""
        required_fields = ["id", "tenant_id", "name", "email", "status", "created_at", "updated_at"]
        for field in required_fields:
            assert field in item_data, f"Missing required field: {field}"

        # Validate field types
        assert isinstance(item_data["id"], int)
        assert isinstance(item_data["tenant_id"], str)
        assert isinstance(item_data["name"], str)
        assert item_data["status"] in ["active", "inactive", "pending"]


class TenantTestMixin:
    """Mixin class for tenant-aware testing."""

    def setup_tenant_test_data(self, tenant_ids: List[str]) -> Dict[str, Any]:
        """Set up test data for multiple tenants."""
        return {
            tenant_id: {
                "demo_items": [
                    TestDataFactory.demo_item_data(
                        tenant_id,
                        name=f"User {i}",
                        email=f"user{i}@{tenant_id}.com"
                    ) for i in range(1, 4)
                ]
            } for tenant_id in tenant_ids
        }


class MockTestData:
    """Predefined mock data for consistent testing."""

    TENANT_IDS = ["tenant-alpha", "tenant-beta", "tenant-gamma"]

    DEMO_ITEMS = {
        "tenant-alpha": [
            {"name": "Alice Alpha", "email": "alice@alpha.com", "status": "active"},
            {"name": "Bob Alpha", "email": "bob@alpha.com", "status": "pending"},
        ],
        "tenant-beta": [
            {"name": "Carol Beta", "email": "carol@beta.com", "status": "active"},
            {"name": "Dave Beta", "email": "dave@beta.com", "status": "inactive"},
        ]
    }

    TENANT_HEADERS = {
        tenant_id: {"X-Tenant-ID": tenant_id}
        for tenant_id in TENANT_IDS
    }


def assert_tenant_context_preserved(response: Response, expected_tenant_id: str):
    """Assert that tenant context is preserved in response headers."""
    tenant_header = response.headers.get("x-tenant-id")
    assert tenant_header == expected_tenant_id, f"Expected tenant {expected_tenant_id}, got {tenant_header}"
