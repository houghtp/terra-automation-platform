"""
Unified test database configuration.

This replaces all the scattered test database configurations across slices
with a single, consistent PostgreSQL-based test setup.
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.features.core.database import Base

# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@localhost:5433/fastapi_template_test"
)

# Create test engine with special configuration
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Disable SQL logging in tests for cleaner output
    poolclass=NullPool,  # Disable connection pooling for tests
    future=True
)

# Create test session maker
TestAsyncSession = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_database():
    """Set up the test database schema once per test session."""
    async with test_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.

    Uses transaction rollback to ensure test isolation.
    """
    async with test_engine.connect() as conn:
        # Start a transaction
        trans = await conn.begin()

        # Create session bound to the transaction
        session = AsyncSession(bind=conn, expire_on_commit=False)

        try:
            yield session
        finally:
            await session.close()
            # Rollback transaction to clean up test data
            await trans.rollback()


# Alternative fixture for tests that need real commits
@pytest.fixture
async def test_db_session_commit(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session that allows real commits.

    Use this for integration tests that need to test transaction behavior.
    Less isolated but necessary for some tests.
    """
    async with TestAsyncSession() as session:
        try:
            yield session
        finally:
            # Clean up by deleting all data
            async with test_engine.begin() as conn:
                # Delete data from all tables in reverse dependency order
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())


@pytest.fixture
async def clean_test_database():
    """
    Fixture to ensure a completely clean database state.

    Use this for tests that need guaranteed isolation.
    """
    async with test_engine.begin() as conn:
        # Drop and recreate all tables
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)