"""
Global pytest configuration and fixtures for the FastAPI template.

This file provides shared fixtures and configuration for all tests,
including database setup, client fixtures, and tenant isolation testing.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
import httpx
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.features.core.database import Base, get_db
from app.main import app
from app.features.auth.services import AuthService


# Test database configuration - Now using PostgreSQL for consistency
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dev_user:dev_password@localhost:5434/fastapi_template_dev"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create a test database engine with PostgreSQL."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        poolclass=StaticPool,
        future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database dependency override."""

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client

    # Clean up dependency override
    del app.dependency_overrides[get_db]


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Alias for test_client for backward compatibility."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client

    # Clean up dependency override
    del app.dependency_overrides[get_db]


@pytest_asyncio.fixture
async def auth_service() -> AuthService:
    """Create an auth service instance for testing."""
    return AuthService()


@pytest.fixture(scope="function")
def sync_test_client() -> Generator[TestClient, None, None]:
    """Create a synchronous test client for simple tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "tenant_a": {
            "id": "tenant-a",
            "name": "Tenant A Corp",
            "metadata": {"plan": "premium", "region": "us-east"}
        },
        "tenant_b": {
            "id": "tenant-b",
            "name": "Tenant B LLC",
            "metadata": {"plan": "basic", "region": "eu-west"}
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "tenant_a_users": [
            {
                "email": "alice@tenanta.com",
                "role": "admin",
                "tenant_id": "tenant-a"
            },
            {
                "email": "bob@tenanta.com",
                "role": "user",
                "tenant_id": "tenant-a"
            }
        ],
        "tenant_b_users": [
            {
                "email": "carol@tenantb.com",
                "role": "user",
                "tenant_id": "tenant-b"
            }
        ]
    }


@pytest_asyncio.fixture
async def sample_test_users(test_db_session: AsyncSession):
    """Create sample test users for testing."""
    from tests.utils import DatabaseTestHelper

    db_helper = DatabaseTestHelper(test_db_session)

    # Create users for different tenants
    tenant_a_users = await db_helper.create_test_users("test-tenant", 3)
    tenant_b_users = await db_helper.create_test_users("other-tenant", 2)

    return {
        "test-tenant": tenant_a_users,
        "other-tenant": tenant_b_users
    }


@pytest_asyncio.fixture
async def multi_tenant_test_users(test_db_session: AsyncSession):
    """Create test users across multiple tenants for isolation testing."""
    from tests.utils import DatabaseTestHelper

    db_helper = DatabaseTestHelper(test_db_session)

    # Create users for multiple tenants
    alpha_users = await db_helper.create_test_users("tenant-alpha", 3)
    beta_users = await db_helper.create_test_users("tenant-beta", 2)
    gamma_users = await db_helper.create_test_users("tenant-gamma", 1)

    return {
        "tenant-alpha": alpha_users,
        "tenant-beta": beta_users,
        "tenant-gamma": gamma_users
    }


@pytest_asyncio.fixture
async def mock_provider_credentials():
    """Mock provider credentials for testing integrations."""
    mock_store = AsyncMock()
    mock_store.get_credentials.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_at": "2025-12-31T23:59:59Z"
    }
    mock_store.store_credentials.return_value = None
    mock_store.delete_credentials.return_value = None
    return mock_store


@pytest.fixture
def mock_request_factory():
    """Factory for creating mock FastAPI Request objects."""

    class MockRequest:
        def __init__(self, headers: dict = None, path: str = "/", method: str = "GET"):
            self.headers = {k.lower(): v for k, v in (headers or {}).items()}
            self.path = path
            self.method = method

        def get(self, key: str, default=None):
            return self.headers.get(key.lower(), default)

    return MockRequest


@pytest.fixture
def tenant_headers():
    """Factory for creating tenant-specific headers."""
    def _make_headers(tenant_id: str, **extra_headers):
        headers = {"X-Tenant-ID": tenant_id}
        headers.update(extra_headers)
        return headers
    return _make_headers


# Markers for test organization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.tenant_isolation = pytest.mark.tenant_isolation
pytest.mark.api = pytest.mark.api
pytest.mark.auth = pytest.mark.auth
pytest.mark.provider = pytest.mark.provider


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "tenant_isolation: Tenant isolation tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "provider: Provider integration tests")


# Environment setup for testing
@pytest.fixture(autouse=True)
def setup_test_env():
    """Automatically set up test environment variables."""
    original_env = os.environ.copy()

    # Set test-specific environment variables
    os.environ.update({
        "ENVIRONMENT": "test",
        "DATABASE_URL": TEST_DATABASE_URL,
        "LOG_LEVEL": "INFO",
        "SECRET_KEY": "test-secret-key-not-for-production",
    })

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
