"""
JWT token utilities for authentication.
"""
import os
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError


class TokenData(BaseModel):
    """JWT token payload structure."""
    user_id: str
    tenant_id: str
    role: str
    email: str


class JWTUtils:
    """JWT token creation and validation utilities."""

    @staticmethod
    def _get_secret_key() -> str:
        """Get JWT secret key from environment with enhanced security validation."""
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            raise ValueError("JWT_SECRET_KEY environment variable is required")

        # Security check: ensure secret is strong enough for production
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

        # Enhanced entropy check
        if len(set(secret)) < 8:
            raise ValueError("JWT_SECRET_KEY has insufficient character diversity")

        # Check for common patterns that indicate weak secrets
        if secret.isdigit():
            raise ValueError("JWT_SECRET_KEY cannot be all numbers")

        if secret.isalpha():
            raise ValueError("JWT_SECRET_KEY should contain mixed characters (letters, numbers, symbols)")

        # Check for sequential or repeated patterns
        if any(char * 3 in secret for char in set(secret)):
            raise ValueError("JWT_SECRET_KEY contains repeated character sequences")

        # Warn if using default/weak secrets (expanded list)
        weak_secrets = [
            "dev-secret-key-change-in-production",
            "secret",
            "password",
            "123456",
            "your-secret-key",
            "jwt-secret",
            "fastapi-secret",
            "change-me",
            "super-secret-key",
            "my-secret",
            "default",
            "test-secret"
        ]
        if secret.lower() in [s.lower() for s in weak_secrets]:
            raise ValueError("JWT_SECRET_KEY appears to be a weak/default value. Use a strong, random secret.")

        # Additional security: check for common dictionary words or patterns
        common_weak_patterns = ["admin", "user", "api", "key", "token", "pass"]
        if any(pattern in secret.lower() for pattern in common_weak_patterns):
            import logging
            logger = structlog.get_logger(__name__)
            logger.warning("JWT_SECRET_KEY contains common words that might reduce security")

        return secret

    @staticmethod
    def _get_algorithm() -> str:
        """Get JWT algorithm from environment with security validation."""
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # Security check: ensure algorithm is secure
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if algorithm not in allowed_algorithms:
            raise ValueError(f"JWT_ALGORITHM '{algorithm}' is not supported. Use one of: {allowed_algorithms}")

        # Warn about deprecated algorithms
        deprecated_algorithms = ["HS256"]  # Consider upgrading to HS512 or RS256
        if algorithm in deprecated_algorithms:
            import logging
            logger = structlog.get_logger(__name__)
            logger.info(f"JWT_ALGORITHM '{algorithm}' is functional but consider upgrading to HS512 or RS256 for enhanced security")

        return algorithm

    @staticmethod
    def _validate_expiration_time(minutes: int, token_type: str) -> int:
        """Validate token expiration times for security."""
        if token_type == "access":
            # Access tokens should be short-lived (5 min to 4 hours)
            if minutes < 5:
                raise ValueError("Access token expiration too short (minimum 5 minutes)")
            if minutes > 240:  # 4 hours
                import logging
                logger = structlog.get_logger(__name__)
                logger.warning(f"Access token expiration is long ({minutes} minutes). Consider shorter expiry for security.")
        elif token_type == "refresh":
            # Refresh tokens can be longer (1 hour to 30 days)
            if minutes < 60:
                raise ValueError("Refresh token expiration too short (minimum 1 hour)")
            if minutes > 43200:  # 30 days
                import logging
                logger = structlog.get_logger(__name__)
                logger.warning(f"Refresh token expiration is very long ({minutes} minutes). Consider shorter expiry for security.")

        return minutes

    @staticmethod
    def create_access_token(
        user_id: str,
        tenant_id: str,
        role: str,
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with user and tenant information."""
        if expires_delta is None:
            # Default to 30 minutes
            expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
            expire_minutes = JWTUtils._validate_expiration_time(expire_minutes, "access")
            expires_delta = timedelta(minutes=expire_minutes)

        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }

        return jwt.encode(
            payload,
            JWTUtils._get_secret_key(),
            algorithm=JWTUtils._get_algorithm()
        )

    @staticmethod
    def create_refresh_token(
        user_id: str,
        tenant_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token."""
        if expires_delta is None:
            # Default to 7 days
            expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
            expire_minutes = expire_days * 24 * 60  # Convert to minutes for validation
            expire_minutes = JWTUtils._validate_expiration_time(expire_minutes, "refresh")
            expires_delta = timedelta(minutes=expire_minutes)

        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }

        return jwt.encode(
            payload,
            JWTUtils._get_secret_key(),
            algorithm=JWTUtils._get_algorithm()
        )

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Verify and decode JWT access token."""
        try:
            payload = jwt.decode(
                token,
                JWTUtils._get_secret_key(),
                algorithms=[JWTUtils._get_algorithm()]
            )

            # Verify it's an access token
            if payload.get("type") != "access":
                return None

            # Create TokenData from payload
            token_data = TokenData(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                role=payload["role"],
                email=payload["email"]
            )

            return token_data

        except (JWTError, ValidationError, KeyError):
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT refresh token."""
        try:
            payload = jwt.decode(
                token,
                JWTUtils._get_secret_key(),
                algorithms=[JWTUtils._get_algorithm()]
            )

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                return None

            return {
                "user_id": payload["user_id"],
                "tenant_id": payload["tenant_id"]
            }

        except (JWTError, KeyError):
            return None
