"""
Factory classes for generating test data for Users slice.

Provides consistent, realistic test data generation using Factory Boy.
Template users should create similar factories for their slices.
"""

import factory
import factory.fuzzy
from datetime import datetime, timedelta
from typing import List

from app.features.auth.models import User
from app.features.administration.users.models import (
    UserCreate, UserUpdate, UserResponse, UserStatus, UserRole
)


class UserFactory(factory.Factory):
    """Factory for creating User model instances."""

    class Meta:
        model = User

    id = factory.LazyFunction(lambda: f"user-{factory.Faker('uuid4')}")
    name = factory.Faker('name')
    email = factory.Faker('email')
    hashed_password = factory.LazyFunction(lambda: "hashed_" + factory.Faker('password')())
    tenant_id = "test-tenant"
    role = factory.fuzzy.FuzzyChoice([role.value for role in UserRole])
    status = factory.fuzzy.FuzzyChoice([status.value for status in UserStatus])
    enabled = factory.Faker('boolean', chance_of_getting_true=80)
    description = factory.Faker('text', max_nb_chars=200)
    tags = factory.LazyFunction(lambda: factory.Faker('words', nb=3)())
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

    status = UserStatus.ACTIVE.value
    enabled = True
    is_active = True


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    role = UserRole.ADMIN.value
    status = UserStatus.ACTIVE.value
    enabled = True
    is_active = True


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""

    status = UserStatus.INACTIVE.value
    enabled = False
    is_active = False


class UserCreateFactory(factory.Factory):
    """Factory for creating UserCreate schema instances."""

    class Meta:
        model = UserCreate

    name = factory.Faker('name')
    email = factory.Faker('email')
    password = factory.LazyFunction(lambda: "SecurePass123!")
    confirm_password = factory.LazyAttribute(lambda obj: obj.password)
    description = factory.Faker('text', max_nb_chars=200)
    status = factory.fuzzy.FuzzyChoice(list(UserStatus))
    role = factory.fuzzy.FuzzyChoice(list(UserRole))
    enabled = factory.Faker('boolean', chance_of_getting_true=80)
    tags = factory.LazyFunction(lambda: factory.Faker('words', nb=3)())


class ValidUserCreateFactory(UserCreateFactory):
    """Factory for creating valid UserCreate instances with strong passwords."""

    password = "StrongPass123!@#"
    confirm_password = "StrongPass123!@#"
    status = UserStatus.ACTIVE
    role = UserRole.USER
    enabled = True


class UserUpdateFactory(factory.Factory):
    """Factory for creating UserUpdate schema instances."""

    class Meta:
        model = UserUpdate

    name = factory.Faker('name')
    email = factory.Faker('email')
    description = factory.Faker('text', max_nb_chars=200)
    status = factory.fuzzy.FuzzyChoice(list(UserStatus))
    role = factory.fuzzy.FuzzyChoice(list(UserRole))
    enabled = factory.Faker('boolean')
    tags = factory.LazyFunction(lambda: factory.Faker('words', nb=2)())


class UserResponseFactory(factory.Factory):
    """Factory for creating UserResponse schema instances."""

    class Meta:
        model = UserResponse

    id = factory.LazyFunction(lambda: f"user-{factory.Faker('uuid4')}")
    name = factory.Faker('name')
    email = factory.Faker('email')
    description = factory.Faker('text', max_nb_chars=200)
    status = factory.fuzzy.FuzzyChoice([status.value for status in UserStatus])
    role = factory.fuzzy.FuzzyChoice([role.value for role in UserRole])
    enabled = factory.Faker('boolean', chance_of_getting_true=80)
    tags = factory.LazyFunction(lambda: factory.Faker('words', nb=3)())
    tenant_id = "test-tenant"
    is_active = factory.Faker('boolean', chance_of_getting_true=90)
    created_at = factory.Faker('iso8601')
    updated_at = factory.Faker('iso8601')


# Specialized factory methods for common test scenarios

def create_user_batch(count: int = 5, **kwargs) -> List[User]:
    """Create a batch of users with optional overrides."""
    return UserFactory.create_batch(count, **kwargs)


def create_admin_user(**kwargs) -> User:
    """Create a single admin user."""
    return AdminUserFactory.create(**kwargs)


def create_test_user_hierarchy() -> List[User]:
    """Create a hierarchy of users for testing role-based features."""
    return [
        AdminUserFactory.create(
            name="System Admin",
            email="admin@test.com",
            role=UserRole.ADMIN.value
        ),
        UserFactory.create(
            name="Moderator User",
            email="moderator@test.com",
            role=UserRole.MODERATOR.value
        ),
        ActiveUserFactory.create(
            name="Regular User",
            email="user@test.com",
            role=UserRole.USER.value
        )
    ]


def create_users_with_different_statuses() -> List[User]:
    """Create users with all different status types."""
    return [
        ActiveUserFactory.create(status=UserStatus.ACTIVE.value),
        InactiveUserFactory.create(status=UserStatus.INACTIVE.value),
        UserFactory.create(status=UserStatus.SUSPENDED.value),
        UserFactory.create(status=UserStatus.PENDING.value)
    ]


def create_user_with_tags(tags: List[str], **kwargs) -> User:
    """Create a user with specific tags."""
    return UserFactory.create(tags=tags, **kwargs)


def create_user_create_with_weak_password() -> UserCreate:
    """Create UserCreate with weak password for testing validation."""
    return UserCreateFactory.build(
        password="weak",
        confirm_password="weak"
    )


def create_user_create_with_mismatched_passwords() -> UserCreate:
    """Create UserCreate with mismatched passwords."""
    return UserCreateFactory.build(
        password="FirstPassword123!",
        confirm_password="SecondPassword123!"
    )


def create_user_create_with_invalid_email() -> UserCreate:
    """Create UserCreate with invalid email format."""
    return UserCreateFactory.build(email="invalid-email-format")


# Form data generators for UI tests

def generate_valid_user_form_data() -> dict:
    """Generate valid form data for user creation."""
    fake_user = UserCreateFactory.build()
    return {
        "name": fake_user.name,
        "email": fake_user.email,
        "password": fake_user.password,
        "confirm_password": fake_user.confirm_password,
        "description": fake_user.description,
        "status": fake_user.status.value,
        "role": fake_user.role.value,
        "enabled": "true" if fake_user.enabled else "false",
        "tags": fake_user.tags
    }


def generate_invalid_user_form_data() -> dict:
    """Generate invalid form data for testing validation."""
    return {
        "name": "A",  # Too short
        "email": "invalid-email",
        "password": "weak",
        "confirm_password": "different",
        "description": "A" * 1001,  # Too long
        "status": "invalid_status",
        "role": "invalid_role",
        "enabled": "invalid_boolean",
        "tags": []
    }


def generate_user_update_form_data() -> dict:
    """Generate form data for user updates."""
    fake_update = UserUpdateFactory.build()
    return {
        "name": fake_update.name,
        "email": fake_update.email,
        "description": fake_update.description,
        "status": fake_update.status.value if fake_update.status else "active",
        "role": fake_update.role.value if fake_update.role else "user",
        "enabled": "true" if fake_update.enabled else "false",
        "tags": fake_update.tags or []
    }


# Database seeding functions for integration tests

async def seed_test_users(db_session, count: int = 10, tenant_id: str = "test-tenant"):
    """Seed database with test users for integration tests."""
    users = UserFactory.create_batch(count, tenant_id=tenant_id)

    for user in users:
        db_session.add(user)

    await db_session.commit()
    return users


async def seed_user_scenario_data(db_session, tenant_id: str = "test-tenant"):
    """Seed database with comprehensive test scenario data."""
    # Create users with different roles
    admin = AdminUserFactory.create(
        tenant_id=tenant_id,
        name="Test Admin",
        email="admin@testscenario.com"
    )

    # Create users with different statuses
    status_users = create_users_with_different_statuses()
    for user in status_users:
        user.tenant_id = tenant_id

    # Create users with various tags
    tagged_users = [
        create_user_with_tags(["developer", "frontend"], tenant_id=tenant_id),
        create_user_with_tags(["designer", "ui/ux"], tenant_id=tenant_id),
        create_user_with_tags(["manager", "team-lead"], tenant_id=tenant_id)
    ]

    all_users = [admin] + status_users + tagged_users

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
    def with_recent_activity():
        """Trait for users with recent activity."""
        return {
            'updated_at': factory.Faker('date_time_between', start_date='-7d', end_date='now'),
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
    def with_no_tags():
        """Trait for users with no tags."""
        return {'tags': []}

    @staticmethod
    def with_many_tags():
        """Trait for users with many tags."""
        return {'tags': factory.Faker('words', nb=10)()}

    @staticmethod
    def with_long_description():
        """Trait for users with long descriptions."""
        return {'description': factory.Faker('text', max_nb_chars=900)()}


# Helper functions for test assertions

def assert_user_matches_create_data(user: User, create_data: UserCreate):
    """Assert that a User model matches UserCreate data."""
    assert user.name == create_data.name
    assert user.email == create_data.email
    assert user.description == create_data.description
    assert user.status == create_data.status.value
    assert user.role == create_data.role.value
    assert user.enabled == create_data.enabled
    assert user.tags == create_data.tags


def assert_user_response_complete(user_response: UserResponse):
    """Assert that a UserResponse has all required fields."""
    assert user_response.id is not None
    assert user_response.name is not None
    assert user_response.email is not None
    assert user_response.status is not None
    assert user_response.role is not None
    assert user_response.enabled is not None
    assert user_response.tenant_id is not None
    assert user_response.is_active is not None