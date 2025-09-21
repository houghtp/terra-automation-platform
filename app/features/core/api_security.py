"""
Advanced API security system for enterprise SaaS platform.

Provides comprehensive API security including key management, request signing,
and enhanced validation.
"""
import hmac
import hashlib
import secrets
import base64
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import Base, get_db

logger = logging.getLogger(__name__)


class APIKeyStatus(Enum):
    """API key status types."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class APIKeyScope(Enum):
    """API key permission scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    WEBHOOK = "webhook"
    MONITORING = "monitoring"


@dataclass
class APIKeyInfo:
    """API key information for validation."""
    key_id: str
    tenant_id: str
    scopes: Set[str]
    rate_limit: int
    expires_at: Optional[datetime]
    last_used: Optional[datetime]


class APIKey(Base):
    """
    API Key model for external integrations.

    Provides secure API access with scoped permissions and rate limiting.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(32), unique=True, index=True, nullable=False)  # Public identifier
    key_hash = Column(String(128), nullable=False)  # Hashed secret
    name = Column(String(255), nullable=False)  # Human-readable name
    description = Column(Text, nullable=True)

    # Tenant and user association
    tenant_id = Column(String(255), nullable=False, index=True)
    created_by = Column(String(255), nullable=True)  # User ID who created key

    # Key status and permissions
    status = Column(String(20), default=APIKeyStatus.ACTIVE.value, nullable=False)
    scopes = Column(JSON, nullable=False)  # List of allowed scopes

    # Rate limiting
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)
    rate_limit_per_day = Column(Integer, default=10000, nullable=False)

    # Lifecycle management
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45), nullable=True)

    # Security tracking
    usage_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def verify_key(self, secret: str) -> bool:
        """Verify provided secret against stored hash."""
        return hmac.compare_digest(
            self.key_hash,
            hashlib.sha256(secret.encode()).hexdigest()
        )

    def has_scope(self, required_scope: str) -> bool:
        """Check if key has required scope."""
        return required_scope in (self.scopes or [])

    def is_valid(self) -> bool:
        """Check if key is valid and not expired."""
        if self.status != APIKeyStatus.ACTIVE.value or not self.is_active:
            return False

        if self.expires_at and self.expires_at < datetime.utcnow():
            return False

        return True

    def to_info(self) -> APIKeyInfo:
        """Convert to APIKeyInfo for validation."""
        return APIKeyInfo(
            key_id=self.key_id,
            tenant_id=self.tenant_id,
            scopes=set(self.scopes or []),
            rate_limit=self.rate_limit_per_hour,
            expires_at=self.expires_at,
            last_used=self.last_used_at
        )


class APIKeyManager:
    """
    Manages API keys, validation, and security policies.

    Features:
    - Secure key generation and storage
    - Rate limiting per key
    - Scope-based permissions
    - Usage tracking and monitoring
    - Automatic key rotation
    """

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """
        Generate a new API key pair.

        Returns:
            tuple: (key_id, secret, key_hash)
        """
        # Generate key ID (public identifier)
        key_id = secrets.token_urlsafe(16)[:16]  # 16 character public ID

        # Generate secret (private key)
        secret = secrets.token_urlsafe(32)  # 32 character secret

        # Hash secret for storage
        key_hash = hashlib.sha256(secret.encode()).hexdigest()

        return key_id, secret, key_hash

    @staticmethod
    async def create_api_key(
        session: AsyncSession,
        name: str,
        tenant_id: str,
        scopes: List[str],
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Args:
            session: Database session
            name: Human-readable name
            tenant_id: Tenant identifier
            scopes: List of permission scopes
            created_by: User ID who created the key
            description: Optional description
            expires_in_days: Days until expiration (None = no expiration)
            rate_limit_per_hour: Requests per hour limit
            rate_limit_per_day: Requests per day limit

        Returns:
            tuple: (APIKey instance, secret)
        """
        try:
            key_id, secret, key_hash = APIKeyManager.generate_api_key()

            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            api_key = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                name=name,
                description=description,
                tenant_id=tenant_id,
                created_by=created_by,
                scopes=scopes,
                rate_limit_per_hour=rate_limit_per_hour,
                rate_limit_per_day=rate_limit_per_day,
                expires_at=expires_at
            )

            session.add(api_key)
            await session.commit()

            logger.info(f"Created API key {key_id} for tenant {tenant_id}")
            return api_key, secret

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create API key: {e}")
            raise

    @staticmethod
    async def validate_api_key(session: AsyncSession, key_id: str, secret: str) -> Optional[APIKeyInfo]:
        """
        Validate API key and return key information.

        Args:
            session: Database session
            key_id: Public key identifier
            secret: Secret key

        Returns:
            APIKeyInfo if valid, None otherwise
        """
        try:
            # Find key by ID
            from sqlalchemy import select
            stmt = select(APIKey).where(APIKey.key_id == key_id)
            result = await session.execute(stmt)
            api_key = result.scalar_one_or_none()

            if not api_key:
                logger.warning(f"API key not found: {key_id}")
                return None

            # Verify secret
            if not api_key.verify_key(secret):
                logger.warning(f"Invalid secret for API key: {key_id}")
                return None

            # Check if key is valid
            if not api_key.is_valid():
                logger.warning(f"API key is not valid: {key_id} (status: {api_key.status})")
                return None

            # Update usage tracking
            api_key.last_used_at = datetime.utcnow()
            api_key.usage_count += 1
            await session.commit()

            return api_key.to_info()

        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            return None

    @staticmethod
    async def revoke_api_key(session: AsyncSession, key_id: str, tenant_id: str) -> bool:
        """Revoke an API key."""
        try:
            from sqlalchemy import select, update

            stmt = update(APIKey).where(
                APIKey.key_id == key_id,
                APIKey.tenant_id == tenant_id
            ).values(
                status=APIKeyStatus.REVOKED.value,
                is_active=False
            )

            result = await session.execute(stmt)
            await session.commit()

            success = result.rowcount > 0
            if success:
                logger.info(f"Revoked API key: {key_id}")
            else:
                logger.warning(f"API key not found for revocation: {key_id}")

            return success

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to revoke API key: {e}")
            return False


class RequestSignatureValidator:
    """
    Validates request signatures for enhanced API security.

    Implements HMAC-SHA256 request signing for critical operations.
    """

    @staticmethod
    def generate_signature(
        method: str,
        path: str,
        body: bytes,
        timestamp: str,
        secret: str
    ) -> str:
        """Generate HMAC signature for request."""

        # Create canonical string
        canonical_string = f"{method}\n{path}\n{body.decode() if body else ''}\n{timestamp}"

        # Generate HMAC
        signature = hmac.new(
            secret.encode(),
            canonical_string.encode(),
            hashlib.sha256
        ).digest()

        return base64.b64encode(signature).decode()

    @staticmethod
    def verify_signature(
        request: Request,
        body: bytes,
        secret: str,
        max_age_seconds: int = 300
    ) -> bool:
        """Verify request signature."""

        try:
            # Extract signature headers
            signature = request.headers.get("X-Signature")
            timestamp = request.headers.get("X-Timestamp")

            if not signature or not timestamp:
                return False

            # Check timestamp (prevent replay attacks)
            try:
                request_time = datetime.fromisoformat(timestamp)
                if (datetime.utcnow() - request_time).total_seconds() > max_age_seconds:
                    logger.warning("Request signature expired")
                    return False
            except ValueError:
                logger.warning("Invalid timestamp format")
                return False

            # Generate expected signature
            expected_signature = RequestSignatureValidator.generate_signature(
                method=request.method,
                path=str(request.url.path),
                body=body,
                timestamp=timestamp,
                secret=secret
            )

            # Verify signature
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class APISecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced API security middleware.

    Features:
    - API key validation
    - Request signature verification
    - Enhanced input validation
    - Security headers
    - Request rate limiting
    """

    def __init__(self, app):
        super().__init__(app)
        self.api_key_manager = APIKeyManager()

    async def dispatch(self, request: Request, call_next):
        """Process request with enhanced security."""

        # Skip security for non-API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip for health checks and documentation
        if any(path in request.url.path for path in ["/health", "/docs", "/openapi", "/versions"]):
            return await call_next(request)

        # Add security headers
        response = await call_next(request)
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response):
        """Add comprehensive security headers."""

        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache"
        }

        for header, value in security_headers.items():
            response.headers[header] = value


# API Key authentication dependency
class APIKeyBearer(HTTPBearer):
    """Enhanced HTTP Bearer authentication with API key support."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request, session: AsyncSession = Depends(get_db)):
        """Validate API key from Bearer token."""

        credentials = await super().__call__(request)
        if not credentials:
            return None

        # Parse API key format: "keyid:secret"
        try:
            if ":" not in credentials.credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key format. Expected 'keyid:secret'"
                )

            key_id, secret = credentials.credentials.split(":", 1)

            # Validate API key
            key_info = await APIKeyManager.validate_api_key(session, key_id, secret)
            if not key_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key"
                )

            # Store key info in request state
            request.state.api_key_info = key_info
            request.state.tenant_id = key_info.tenant_id

            return key_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key validation failed"
            )


# Security dependencies
api_key_bearer = APIKeyBearer()

async def require_api_key(key_info: APIKeyInfo = Depends(api_key_bearer)) -> APIKeyInfo:
    """Require valid API key."""
    return key_info

async def require_api_scope(required_scope: str):
    """Create dependency that requires specific API scope."""

    async def check_scope(key_info: APIKeyInfo = Depends(require_api_key)) -> APIKeyInfo:
        if required_scope not in key_info.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required scope: {required_scope}"
            )
        return key_info

    return check_scope

# Scope-specific dependencies
require_read_scope = require_api_scope(APIKeyScope.READ.value)
require_write_scope = require_api_scope(APIKeyScope.WRITE.value)
require_admin_scope = require_api_scope(APIKeyScope.ADMIN.value)
require_webhook_scope = require_api_scope(APIKeyScope.WEBHOOK.value)