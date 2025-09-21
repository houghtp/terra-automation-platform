"""
Factory classes for generating test data for Auth slice.

Provides consistent, realistic test data generation using Factory Boy.
Template users should create similar factories for their slices.
"""

import factory
import factory.fuzzy
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4

from app.features.auth.models import User
from app.features.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    AuthStatusResponse
)


class UserFactory(factory.Factory):
    """Factory for creating User model instances."""

    class Meta:
        model = User

    id = factory.LazyFunction(lambda: str(uuid4()))
    email = factory.Faker('email')
    hashed_password = factory.LazyFunction(lambda: "hashed_" + factory.Faker('password')())
    tenant_id = "test-tenant"
    role = factory.fuzzy.FuzzyChoice(["user", "admin", "global_admin"])
    is_active = factory.Faker('boolean', chance_of_getting_true=90)
    created_at = factory.Faker(
        'date_time_between',
        start_date='-1y',
        end_date='now'
    )
    updated_at = factory.LazyAttribute(
        lambda obj: factory.Faker(
            'date_time_between',
            start_date=obj.created_at,
            end_date='now'
        ).generate({})
    )


class ActiveUserFactory(UserFactory):
    """Factory for creating active users."""

    is_active = True
    role = "user"


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    role = "admin"
    is_active = True


class GlobalAdminUserFactory(UserFactory):
    """Factory for creating global admin users."""

    role = "global_admin"
    is_active = True


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""

    is_active = False


class UserRegisterRequestFactory(factory.Factory):
    """Factory for creating UserRegisterRequest schema instances."""

    class Meta:
        model = UserRegisterRequest

    email = factory.Faker('email')
    password = factory.LazyFunction(lambda: "SecurePass123!")
    role = factory.fuzzy.FuzzyChoice(["user", "admin", "global_admin"])


class ValidUserRegisterRequestFactory(UserRegisterRequestFactory):
    """Factory for creating valid UserRegisterRequest instances."""

    password = "StrongPassword123!@#"
    role = "user"


class UserLoginRequestFactory(factory.Factory):
    """Factory for creating UserLoginRequest schema instances."""

    class Meta:
        model = UserLoginRequest

    email = factory.Faker('email')
    password = factory.LazyFunction(lambda: "LoginPass123!")


class TokenResponseFactory(factory.Factory):
    """Factory for creating TokenResponse schema instances."""

    class Meta:
        model = TokenResponse

    access_token = factory.LazyFunction(
        lambda: f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{factory.Faker('uuid4')().replace('-', '')}.signature"
    )
    refresh_token = factory.LazyFunction(
        lambda: f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{factory.Faker('uuid4')().replace('-', '')}.refresh_sig"
    )
    token_type = "bearer"
    expires_in = factory.fuzzy.FuzzyInteger(3600, 7200)  # 1-2 hours


class RefreshTokenRequestFactory(factory.Factory):
    """Factory for creating RefreshTokenRequest schema instances."""

    class Meta:
        model = RefreshTokenRequest

    refresh_token = factory.LazyFunction(
        lambda: f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{factory.Faker('uuid4')().replace('-', '')}.refresh_sig"
    )


class UserResponseFactory(factory.Factory):
    """Factory for creating UserResponse schema instances."""

    class Meta:
        model = UserResponse

    id = factory.LazyFunction(lambda: str(uuid4()))
    email = factory.Faker('email')
    tenant_id = "test-tenant"
    role = factory.fuzzy.FuzzyChoice(["user", "admin", "global_admin"])
    is_active = factory.Faker('boolean', chance_of_getting_true=90)
    created_at = factory.Faker('iso8601')
    updated_at = factory.Faker('iso8601')


class AuthStatusResponseFactory(factory.Factory):
    """Factory for creating AuthStatusResponse schema instances."""

    class Meta:
        model = AuthStatusResponse

    authenticated = factory.Faker('boolean', chance_of_getting_true=70)
    user = factory.SubFactory(UserResponseFactory)


class AuthenticatedStatusFactory(AuthStatusResponseFactory):
    """Factory for authenticated status responses."""

    authenticated = True


class UnauthenticatedStatusFactory(AuthStatusResponseFactory):
    """Factory for unauthenticated status responses."""

    authenticated = False
    user = None


# Specialized factory methods for common test scenarios

def create_user_with_credentials(email: str = None, password: str = None, **kwargs) -> tuple[User, str]:
    """Create a user with known credentials for testing."""
    email = email or factory.Faker('email')()
    password = password or "TestPassword123!"

    # Hash the password (you'll need to import your hash function)
    from app.features.auth.services import AuthService
    auth_service = AuthService()
    hashed_password = auth_service.hash_password(password)

    user = UserFactory.create(
        email=email,
        hashed_password=hashed_password,
        **kwargs
    )

    return user, password


def create_user_batch(count: int = 5, **kwargs) -> List[User]:
    """Create a batch of users with optional overrides."""
    return UserFactory.create_batch(count, **kwargs)


def create_admin_user(**kwargs) -> User:
    """Create a single admin user."""
    return AdminUserFactory.create(**kwargs)


def create_test_user_hierarchy() -> List[User]:
    """Create a hierarchy of users for testing role-based features."""
    return [
        GlobalAdminUserFactory.create(
            email="global@test.com",
            role="global_admin"
        ),
        AdminUserFactory.create(
            email="admin@test.com",
            role="admin"
        ),
        ActiveUserFactory.create(
            email="user@test.com",
            role="user"
        )
    ]


def create_users_with_different_roles() -> List[User]:
    """Create users with all different role types."""
    return [
        ActiveUserFactory.create(role="user"),
        AdminUserFactory.create(role="admin"),
        GlobalAdminUserFactory.create(role="global_admin")
    ]


def create_users_with_different_statuses() -> List[User]:
    """Create users with different active statuses."""
    return [
        ActiveUserFactory.create(is_active=True),
        InactiveUserFactory.create(is_active=False)
    ]


def create_user_for_tenant(tenant_id: str, **kwargs) -> User:
    """Create a user for a specific tenant."""
    return UserFactory.create(tenant_id=tenant_id, **kwargs)


def create_register_request_with_weak_password() -> UserRegisterRequest:
    """Create UserRegisterRequest with weak password for testing validation."""
    return UserRegisterRequestFactory.build(password="weak")


def create_register_request_with_invalid_email() -> UserRegisterRequest:
    """Create UserRegisterRequest with invalid email format."""
    return UserRegisterRequestFactory.build(email="invalid-email-format")


def create_register_request_with_invalid_role() -> UserRegisterRequest:
    """Create UserRegisterRequest with invalid role."""
    return UserRegisterRequestFactory.build(role="invalid_role")


def create_expired_token_response() -> TokenResponse:
    """Create TokenResponse with expired timestamps."""
    return TokenResponseFactory.build(expires_in=0)


def create_long_lived_token_response() -> TokenResponse:
    """Create TokenResponse with long expiry."""
    return TokenResponseFactory.build(expires_in=86400)  # 24 hours


# Form data generators for UI tests

def generate_valid_registration_form_data() -> Dict[str, Any]:
    """Generate valid form data for user registration."""
    fake_request = UserRegisterRequestFactory.build()
    return {
        "email": fake_request.email,
        "password": fake_request.password,
        "confirm_password": fake_request.password,
        "role": fake_request.role
    }


def generate_invalid_registration_form_data() -> Dict[str, Any]:
    """Generate invalid form data for testing validation."""
    return {
        "email": "invalid-email",
        "password": "weak",
        "confirm_password": "different",
        "role": "invalid_role"
    }


def generate_login_form_data(email: str = None, password: str = None) -> Dict[str, Any]:
    """Generate form data for user login."""
    fake_login = UserLoginRequestFactory.build()
    return {
        "email": email or fake_login.email,
        "password": password or fake_login.password
    }


def generate_password_mismatch_form_data() -> Dict[str, Any]:
    """Generate registration form data with password mismatch."""
    return {
        "email": factory.Faker('email')(),
        "password": "FirstPassword123!",
        "confirm_password": "SecondPassword123!",
        "role": "user"
    }


# Database seeding functions for integration tests

async def seed_test_users(db_session, count: int = 10, tenant_id: str = "test-tenant"):
    """Seed database with test users for integration tests."""
    users = UserFactory.create_batch(count, tenant_id=tenant_id)

    for user in users:
        db_session.add(user)

    await db_session.commit()
    return users


async def seed_auth_scenario_data(db_session, tenant_id: str = "test-tenant"):
    """Seed database with comprehensive auth test scenario data."""
    # Create users with different roles
    global_admin = GlobalAdminUserFactory.create(
        tenant_id=tenant_id,
        email="globaladmin@testscenario.com"
    )

    admin = AdminUserFactory.create(
        tenant_id=tenant_id,
        email="admin@testscenario.com"
    )

    # Create users with different statuses
    status_users = create_users_with_different_statuses()
    for user in status_users:
        user.tenant_id = tenant_id

    # Create users for different tenants
    multi_tenant_users = [
        create_user_for_tenant("tenant-1", email="user1@tenant1.com"),
        create_user_for_tenant("tenant-2", email="user2@tenant2.com"),
        create_user_for_tenant("tenant-3", email="user3@tenant3.com")
    ]

    all_users = [global_admin, admin] + status_users + multi_tenant_users

    for user in all_users:
        db_session.add(user)

    await db_session.commit()
    return all_users


# Performance testing data generators

def create_performance_test_users(count: int = 1000, tenant_id: str = "test-tenant") -> List[User]:
    """Create large batch of users for performance testing."""
    return UserFactory.build_batch(count, tenant_id=tenant_id)


# Trait classes for more complex scenarios

class UserTraits:
    """Trait mixins for creating users with specific characteristics."""

    @staticmethod
    def with_recent_login():
        """Trait for users with recent login activity."""
        return {
            'updated_at': factory.Faker('date_time_between', start_date='-1d', end_date='now'),
            'is_active': True
        }

    @staticmethod
    def with_old_account():
        """Trait for users with old accounts."""
        return {
            'created_at': factory.Faker('date_time_between', start_date='-2y', end_date='-1y'),
            'updated_at': factory.Faker('date_time_between', start_date='-1y', end_date='-6m')
        }

    @staticmethod
    def with_complex_email():
        """Trait for users with complex email addresses."""
        complex_emails = [
            "user.with.dots@example.com",
            "user+tag@example.com",
            "user123@sub.domain.co.uk",
            "special-chars_123@example-domain.org"
        ]
        return {'email': factory.fuzzy.FuzzyChoice(complex_emails)()}

    @staticmethod
    def with_secure_password():
        """Trait for users with secure passwords."""
        secure_passwords = [
            "VerySecure123!@#",
            "Complex$Pass789&*",
            "Ultra#Secure456%^"
        ]
        from app.features.auth.services import AuthService
        auth_service = AuthService()
        password = factory.fuzzy.FuzzyChoice(secure_passwords)()
        return {'hashed_password': auth_service.hash_password(password)}


# Helper functions for test assertions

def assert_user_matches_register_data(user: User, register_data: UserRegisterRequest):
    """Assert that a User model matches UserRegisterRequest data."""
    assert user.email == register_data.email
    assert user.role == register_data.role
    # Note: Don't compare password directly as it should be hashed


def assert_user_response_complete(user_response: UserResponse):
    """Assert that a UserResponse has all required fields."""
    assert user_response.id is not None
    assert user_response.email is not None
    assert user_response.tenant_id is not None
    assert user_response.role is not None
    assert user_response.is_active is not None


def assert_token_response_valid(token_response: TokenResponse):
    """Assert that a TokenResponse is valid."""
    assert token_response.access_token is not None
    assert token_response.refresh_token is not None
    assert token_response.token_type == "bearer"
    assert token_response.expires_in > 0


def assert_auth_status_authenticated(auth_status: AuthStatusResponse):
    """Assert that AuthStatusResponse shows authenticated state."""
    assert auth_status.authenticated is True
    assert auth_status.user is not None
    assert auth_status.user.email is not None


def assert_auth_status_unauthenticated(auth_status: AuthStatusResponse):
    """Assert that AuthStatusResponse shows unauthenticated state."""
    assert auth_status.authenticated is False
    assert auth_status.user is None


# Security testing helpers

def create_malicious_registration_data() -> Dict[str, Any]:
    """Create registration data with potential security issues for testing."""
    return {
        "email": "<script>alert('xss')</script>@example.com",
        "password": "'; DROP TABLE users; --",
        "confirm_password": "'; DROP TABLE users; --",
        "role": "<img src=x onerror=alert('xss')>"
    }


def create_sql_injection_login_data() -> Dict[str, Any]:
    """Create login data with SQL injection attempts."""
    return {
        "email": "' OR '1'='1' --",
        "password": "' UNION SELECT * FROM users --"
    }


def create_brute_force_login_attempts(count: int = 10) -> List[Dict[str, Any]]:
    """Create multiple login attempts for brute force testing."""
    return [
        {
            "email": "bruteforce@example.com",
            "password": f"attempt{i}"
        }
        for i in range(count)
    ]