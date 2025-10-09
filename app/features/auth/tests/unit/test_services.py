"""
Tests for authentication services.
"""
import pytest
import jwt
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.auth.services import AuthService
from app.features.auth.jwt_utils import JWTUtils
from app.features.auth.models import User


@pytest.fixture
def auth_service():
    """Create auth service instance."""
    return AuthService()


@pytest.fixture
def jwt_utils():
    """Create JWT utils instance."""
    return JWTUtils()


@pytest.mark.asyncio
async def test_create_user_success(auth_service: AuthService, test_db_session: AsyncSession):
    """Test successful user creation."""
    user = await auth_service.create_user(
        session=test_db_session,
        email="test@example.com",
        password="securepassword123",
        tenant_id="test-tenant",
        role="user"
    )

    assert user is not None
    assert user.email == "test@example.com"
    assert user.tenant_id == "test-tenant"
    assert user.role == "user"
    assert user.is_active is True
    assert user.hashed_password != "securepassword123"  # Should be hashed
    assert auth_service.verify_password("securepassword123", user.hashed_password)


@pytest.mark.asyncio
async def test_create_user_duplicate_email(auth_service: AuthService, test_db_session: AsyncSession):
    """Test creating user with duplicate email in same tenant."""
    email = "test@example.com"
    tenant_id = "test-tenant"

    # Create first user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password="password1",
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Try to create second user with same email and tenant
    with pytest.raises(ValueError, match="Email already registered"):
        await auth_service.create_user(
            session=test_db_session,
            email=email,
            password="password2",
            tenant_id=tenant_id,
            role="user"
        )


@pytest.mark.asyncio
async def test_create_user_same_email_different_tenant(auth_service: AuthService, test_db_session: AsyncSession):
    """Test creating user with same email in different tenant."""
    email = "test@example.com"

    # Create user in tenant 1
    user1 = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password="password1",
        tenant_id="tenant-1",
        role="user"
    )

    # Create user with same email in tenant 2
    user2 = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password="password2",
        tenant_id="tenant-2",
        role="admin"
    )

    assert user1.email == user2.email == email
    assert user1.tenant_id != user2.tenant_id
    assert user1.id != user2.id


@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service: AuthService, test_db_session: AsyncSession):
    """Test successful user authentication."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Authenticate user
    user = await auth_service.authenticate_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id
    )

    assert user is not None
    assert user.email == email
    assert user.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(auth_service: AuthService, test_db_session: AsyncSession):
    """Test authentication with wrong password."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Try to authenticate with wrong password
    user = await auth_service.authenticate_user(
        session=test_db_session,
        email=email,
        password="wrongpassword",
        tenant_id=tenant_id
    )

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_tenant(auth_service: AuthService, test_db_session: AsyncSession):
    """Test authentication with wrong tenant."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )
    await test_db_session.commit()

    # Try to authenticate with wrong tenant
    user = await auth_service.authenticate_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id="wrong-tenant"
    )

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent(auth_service: AuthService, test_db_session: AsyncSession):
    """Test authentication with nonexistent user."""
    user = await auth_service.authenticate_user(
        session=test_db_session,
        email="nonexistent@example.com",
        password="password",
        tenant_id="test-tenant"
    )

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_inactive_user(auth_service: AuthService, test_db_session: AsyncSession):
    """Test authentication with inactive user."""
    email = "test@example.com"
    password = "securepassword123"
    tenant_id = "test-tenant"

    # Create user
    user = await auth_service.create_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id,
        role="user"
    )

    # Deactivate user
    user.is_active = False
    await test_db_session.commit()

    # Try to authenticate inactive user
    authenticated_user = await auth_service.authenticate_user(
        session=test_db_session,
        email=email,
        password=password,
        tenant_id=tenant_id
    )

    assert authenticated_user is None


def test_password_hashing(auth_service: AuthService):
    """Test password hashing and verification."""
    password = "securepassword123"

    # Hash password
    hashed = auth_service.hash_password(password)

    assert hashed != password
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpassword", hashed)


def test_create_tokens(auth_service: AuthService):
    """Test JWT token creation."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tenant_id="test-tenant",
        role="user"
    )

    access_token, refresh_token = auth_service.create_tokens(user)

    assert access_token is not None
    assert refresh_token is not None
    assert access_token != refresh_token


@pytest.mark.asyncio
async def test_refresh_access_token_success(auth_service: AuthService, test_db_session: AsyncSession):
    """Test successful access token refresh."""
    # Create user
    user = await auth_service.create_user(
        session=test_db_session,
        email="test@example.com",
        password="password",
        tenant_id="test-tenant",
        role="user"
    )
    await test_db_session.commit()

    # Create tokens
    access_token, refresh_token = auth_service.create_tokens(user)

    # Refresh access token
    new_access_token = await auth_service.refresh_access_token(
        session=test_db_session,
        refresh_token=refresh_token
    )

    assert new_access_token is not None
    assert new_access_token != access_token


@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token(auth_service: AuthService, test_db_session: AsyncSession):
    """Test refresh with invalid token."""
    new_access_token = await auth_service.refresh_access_token(
        session=test_db_session,
        refresh_token="invalid.token.here"
    )

    assert new_access_token is None


@pytest.mark.asyncio
async def test_refresh_access_token_nonexistent_user(auth_service: AuthService, test_db_session: AsyncSession):
    """Test refresh with token for nonexistent user."""
    # Create a valid token for a user that doesn't exist
    fake_user_id = str(uuid.uuid4())
    jwt_utils = JWTUtils()
    fake_refresh_token = jwt_utils.create_refresh_token(fake_user_id)

    new_access_token = await auth_service.refresh_access_token(
        session=test_db_session,
        refresh_token=fake_refresh_token
    )

    assert new_access_token is None


# JWT Utils Tests

def test_create_access_token(jwt_utils: JWTUtils):
    """Test access token creation."""
    user_id = str(uuid.uuid4())
    token = jwt_utils.create_access_token(user_id)

    assert token is not None

    # Verify token structure
    decoded = jwt_utils.verify_token(token)
    assert decoded["sub"] == user_id
    assert decoded["type"] == "access"


def test_create_refresh_token(jwt_utils: JWTUtils):
    """Test refresh token creation."""
    user_id = str(uuid.uuid4())
    token = jwt_utils.create_refresh_token(user_id)

    assert token is not None

    # Verify token structure
    decoded = jwt_utils.verify_token(token)
    assert decoded["sub"] == user_id
    assert decoded["type"] == "refresh"


def test_verify_valid_token(jwt_utils: JWTUtils):
    """Test token verification with valid token."""
    user_id = str(uuid.uuid4())
    token = jwt_utils.create_access_token(user_id)

    decoded = jwt_utils.verify_token(token)

    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["type"] == "access"


def test_verify_invalid_token(jwt_utils: JWTUtils):
    """Test token verification with invalid token."""
    decoded = jwt_utils.verify_token("invalid.token.here")
    assert decoded is None


def test_verify_expired_token(jwt_utils: JWTUtils):
    """Test token verification with expired token."""
    user_id = str(uuid.uuid4())

    # Create token with expired time
    with patch('app.features.auth.services.jwt_utils.datetime') as mock_datetime:
        # Mock datetime to create an already expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_datetime.utcnow.return_value = past_time

        expired_token = jwt_utils.create_access_token(user_id)

    # Verify expired token
    decoded = jwt_utils.verify_token(expired_token)
    assert decoded is None


def test_extract_user_id_from_token(jwt_utils: JWTUtils):
    """Test extracting user ID from token."""
    user_id = str(uuid.uuid4())
    token = jwt_utils.create_access_token(user_id)

    extracted_id = jwt_utils.extract_user_id(token)
    assert extracted_id == user_id


def test_extract_user_id_from_invalid_token(jwt_utils: JWTUtils):
    """Test extracting user ID from invalid token."""
    extracted_id = jwt_utils.extract_user_id("invalid.token.here")
    assert extracted_id is None


def test_token_type_validation(jwt_utils: JWTUtils):
    """Test token type validation."""
    user_id = str(uuid.uuid4())
    access_token = jwt_utils.create_access_token(user_id)
    refresh_token = jwt_utils.create_refresh_token(user_id)

    # Verify access token has correct type
    access_decoded = jwt_utils.verify_token(access_token)
    assert access_decoded["type"] == "access"

    # Verify refresh token has correct type
    refresh_decoded = jwt_utils.verify_token(refresh_token)
    assert refresh_decoded["type"] == "refresh"
