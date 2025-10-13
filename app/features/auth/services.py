"""
Authentication service containing business logic for user management.

Uses centralized imports and structured logging for consistency.
"""
from typing import Optional, Tuple

from app.features.core.sqlalchemy_imports import *
from app.features.auth.models import User
from app.features.auth.jwt_utils import JWTUtils
from app.features.core.security import security_manager

logger = get_logger(__name__)


class AuthService:
    """
    Authentication business logic service.

    Note: This service does NOT inherit from BaseService because:
    1. It operates across tenants during login (user provides email, not tenant)
    2. Needs raw queries for performance-critical auth operations
    3. Has unique security requirements that don't fit BaseService patterns

    Tenant isolation is handled explicitly in each method.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize auth service with database session.

        Args:
            db_session: SQLAlchemy async session
        """
        self.db = db_session

    def hash_password(self, password: str) -> str:
        """
        Hash password using shared security manager.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return security_manager.hash_password(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password using shared security manager.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hashed password

        Returns:
            True if password matches, False otherwise
        """
        return security_manager.verify_password(plain_password, hashed_password)

    async def get_user_by_email(
        self,
        email: str,
        tenant_id: str
    ) -> Optional[User]:
        """
        Get user by email within a specific tenant.

        Args:
            email: User email address
            tenant_id: Tenant ID for isolation

        Returns:
            User if found and active, None otherwise
        """
        try:
            result = await self.db.execute(
                select(User).where(
                    User.email == email,
                    User.tenant_id == tenant_id,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()

            if user:
                logger.debug("Found user by email", email=email, user_id=user.id, tenant_id=tenant_id)

            return user
        except Exception as e:
            logger.error("Failed to get user by email", email=email, tenant_id=tenant_id, error=str(e))
            raise

    async def get_user_by_id(
        self,
        user_id: str,
        tenant_id: str
    ) -> Optional[User]:
        """
        Get user by ID within a specific tenant.

        Args:
            user_id: User ID
            tenant_id: Tenant ID for isolation

        Returns:
            User if found and active, None otherwise
        """
        try:
            result = await self.db.execute(
                select(User).where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    User.is_active == True
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=user_id, tenant_id=tenant_id, error=str(e))
            raise

    async def create_user(
        self,
        email: str,
        password: str,
        tenant_id: str,
        role: str = "user",
        name: Optional[str] = None
    ) -> User:
        """
        Create a new user with hashed password.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            tenant_id: Tenant ID
            role: User role (default: "user")
            name: Optional display name

        Returns:
            Created User instance

        Raises:
            ValueError: If password validation fails or user already exists
        """
        try:
            # Validate password complexity
            password_errors = security_manager.validate_password_complexity(password)
            if password_errors:
                error_msg = "Password validation failed: " + "; ".join(password_errors)
                logger.warning("Password validation failed", email=email, tenant_id=tenant_id)
                raise ValueError(error_msg)

            # Check if user already exists
            existing_user = await self.get_user_by_email(email, tenant_id)
            if existing_user:
                logger.warning("User already exists", email=email, tenant_id=tenant_id)
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

            self.db.add(user)
            await self.db.flush()  # Get the ID
            await self.db.refresh(user)

            logger.info("User created", user_id=user.id, email=email, tenant_id=tenant_id, role=role)

            return user

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error("Failed to create user", email=email, tenant_id=tenant_id, error=str(e))
            raise

    async def authenticate_user(
        self,
        email: str,
        password: str,
        tenant_id: str
    ) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email address
            password: Plain text password
            tenant_id: Tenant ID

        Returns:
            User if authentication successful, None otherwise
        """
        try:
            user = await self.get_user_by_email(email, tenant_id)
            if not user:
                logger.info("Authentication failed - user not found", email=email, tenant_id=tenant_id)
                return None

            if not self.verify_password(password, user.hashed_password):
                logger.warning("Authentication failed - invalid password",
                             email=email, user_id=user.id, tenant_id=tenant_id)
                return None

            logger.info("User authenticated successfully",
                       user_id=user.id, email=email, tenant_id=tenant_id)

            return user

        except Exception as e:
            logger.error("Authentication error", email=email, tenant_id=tenant_id, error=str(e))
            return None

    def create_tokens(self, user: User) -> Tuple[str, str]:
        """
        Create access and refresh tokens for user.

        Args:
            user: Authenticated user

        Returns:
            Tuple of (access_token, refresh_token)
        """
        try:
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

            logger.debug("Tokens created", user_id=user.id, tenant_id=user.tenant_id)

            return access_token, refresh_token

        except Exception as e:
            logger.error("Failed to create tokens", user_id=user.id, error=str(e))
            raise

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Optional[str]:
        """
        Create new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        try:
            token_data = JWTUtils.verify_refresh_token(refresh_token)
            if not token_data:
                logger.info("Token refresh failed - invalid token")
                return None

            # Get current user to ensure they're still active
            user = await self.get_user_by_id(
                token_data["user_id"],
                token_data["tenant_id"]
            )
            if not user:
                logger.warning("Token refresh failed - user not found or inactive",
                             user_id=token_data.get("user_id"),
                             tenant_id=token_data.get("tenant_id"))
                return None

            # Create new access token
            access_token = JWTUtils.create_access_token(
                user_id=user.id,
                tenant_id=user.tenant_id,
                role=user.role,
                email=user.email
            )

            logger.info("Access token refreshed", user_id=user.id, tenant_id=user.tenant_id)

            return access_token

        except Exception as e:
            logger.error("Token refresh error", error=str(e))
            return None
