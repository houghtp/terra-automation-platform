"""
Authentication service containing business logic for user management.
"""
import os
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.features.auth.models import User
from app.features.auth.jwt_utils import JWTUtils
from app.features.core.security import security_manager


class AuthService:
    """Authentication business logic service."""

    def __init__(self):
        """Initialize auth service with shared security manager."""
        pass

    def hash_password(self, password: str) -> str:
        """Hash password using shared security manager."""
        return security_manager.hash_password(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password using shared security manager."""
        return security_manager.verify_password(plain_password, hashed_password)

    async def get_user_by_email(
        self,
        session: AsyncSession,
        email: str,
        tenant_id: str
    ) -> Optional[User]:
        """Get user by email within a specific tenant."""
        result = await session.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: str
    ) -> Optional[User]:
        """Get user by ID within a specific tenant."""
        result = await session.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        tenant_id: str,
        role: str = "user",
        name: Optional[str] = None
    ) -> User:
        """Create a new user with hashed password."""
        # Validate password complexity
        password_errors = security_manager.validate_password_complexity(password)
        if password_errors:
            error_msg = "Password validation failed: " + "; ".join(password_errors)
            raise ValueError(error_msg)
        
        # Check if user already exists
        existing_user = await self.get_user_by_email(session, email, tenant_id)
        if existing_user:
            raise ValueError(f"User with email {email} already exists in tenant {tenant_id}")

        # Create new user
        hashed_password = self.hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            role=role,
            name=name or email.split('@')[0].title()  # Default name from email prefix
        )

        session.add(user)
        await session.flush()  # Get the ID
        await session.refresh(user)

        return user

    async def authenticate_user(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        tenant_id: str
    ) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(session, email, tenant_id)
        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user

    def create_tokens(self, user: User) -> Tuple[str, str]:
        """Create access and refresh tokens for user."""
        access_token = JWTUtils.create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
            email=user.email
        )

        refresh_token = JWTUtils.create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id
        )

        return access_token, refresh_token

    async def refresh_access_token(
        self,
        session: AsyncSession,
        refresh_token: str
    ) -> Optional[str]:
        """Create new access token from refresh token."""
        token_data = JWTUtils.verify_refresh_token(refresh_token)
        if not token_data:
            return None

        # Get current user to ensure they're still active
        user = await self.get_user_by_id(
            session,
            token_data["user_id"],
            token_data["tenant_id"]
        )
        if not user:
            return None

        # Create new access token
        access_token = JWTUtils.create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
            email=user.email
        )

        return access_token
