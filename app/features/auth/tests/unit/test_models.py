"""
Tests for authentication models.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.auth.models import User


@pytest.mark.asyncio
async def test_user_model_creation(test_db_session: AsyncSession):
    """Test creating a user model."""
    tenant_id = "test-tenant"

    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        tenant_id=tenant_id,
        role="user"
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password_123"
    assert user.tenant_id == tenant_id
    assert user.role == "user"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_user_unique_email_per_tenant(test_db_session: AsyncSession):
    """Test that email is unique per tenant."""
    email = "test@example.com"
    tenant1 = "tenant-1"
    tenant2 = "tenant-2"

    # Create user in tenant 1
    user1 = User(
        email=email,
        hashed_password="hashed_password_123",
        tenant_id=tenant1,
        role="user"
    )

    # Create user with same email in tenant 2 (should work)
    user2 = User(
        email=email,
        hashed_password="hashed_password_456",
        tenant_id=tenant2,
        role="user"
    )

    test_db_session.add(user1)
    test_db_session.add(user2)
    await test_db_session.commit()

    # Both users should be created successfully
    await test_db_session.refresh(user1)
    await test_db_session.refresh(user2)

    assert user1.id != user2.id
    assert user1.email == user2.email == email
    assert user1.tenant_id != user2.tenant_id


@pytest.mark.asyncio
async def test_user_duplicate_email_same_tenant(test_db_session: AsyncSession):
    """Test that duplicate email in same tenant raises error."""
    email = "test@example.com"
    tenant_id = "test-tenant"

    # Create first user
    user1 = User(
        email=email,
        hashed_password="hashed_password_123",
        tenant_id=tenant_id,
        role="user"
    )

    # Create second user with same email and tenant
    user2 = User(
        email=email,
        hashed_password="hashed_password_456",
        tenant_id=tenant_id,
        role="admin"
    )

    test_db_session.add(user1)
    test_db_session.add(user2)

    # This should raise an IntegrityError due to unique constraint
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        await test_db_session.commit()


@pytest.mark.asyncio
async def test_user_to_dict(test_db_session: AsyncSession):
    """Test user to_dict method."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        tenant_id="test-tenant",
        role="admin"
    )

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    user_dict = user.to_dict()

    assert "id" in user_dict
    assert user_dict["email"] == "test@example.com"
    assert user_dict["tenant_id"] == "test-tenant"
    assert user_dict["role"] == "admin"
    assert user_dict["is_active"] is True
    assert "created_at" in user_dict
    assert "updated_at" in user_dict
    assert "hashed_password" not in user_dict  # Should not include password


@pytest.mark.asyncio
async def test_user_role_validation(test_db_session: AsyncSession):
    """Test user role field accepts valid values."""
    valid_roles = ["user", "admin"]

    for role in valid_roles:
        user = User(
            email=f"test_{role}@example.com",
            hashed_password="hashed_password_123",
            tenant_id="test-tenant",
            role=role
        )

        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)

        assert user.role == role

        # Clean up for next iteration
        await test_db_session.delete(user)
        await test_db_session.commit()


@pytest.mark.asyncio
async def test_user_default_values(test_db_session: AsyncSession):
    """Test user model default values."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        tenant_id="test-tenant",
        role="user"
    )

    # Before saving to DB
    assert user.is_active is True  # Default value
    assert user.id is not None  # UUID generated automatically

    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    # After saving to DB
    assert user.is_active is True
    assert isinstance(user.id, uuid.UUID)
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)
