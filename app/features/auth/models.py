"""
User model for authentication with tenant isolation and user management.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, func, Index
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class User(Base, AuditMixin):
    """User model with tenant isolation, role-based access, and management features."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="user")

    # User management fields matching demo pattern
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    enabled = Column(Boolean, default=True, nullable=False)
    tags = Column(JSON, default=list)

    # Legacy field mapping
    is_active = Column(Boolean, nullable=False, default=True)
    # Note: created_at and updated_at are now provided by AuditMixin

    # Ensure email is unique per tenant
    __table_args__ = (
        Index('idx_users_email_tenant', 'email', 'tenant_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON responses (excludes password)."""
        base_dict = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "enabled": self.enabled,
            "tags": self.tags or [],
            "tenant_id": self.tenant_id,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # Add audit information
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        """String representation of user."""
        try:
            # Safely access attributes without triggering lazy loading during error states
            id_val = getattr(self, 'id', '<unknown>')
            name_val = getattr(self, 'name', '<unknown>')
            email_val = getattr(self, 'email', '<unknown>')
            tenant_val = getattr(self, 'tenant_id', '<unknown>')
            return f"<User(id={id_val}, name={name_val}, email={email_val}, tenant={tenant_val})>"
        except Exception:
            # Fallback for any error scenarios to prevent recursion
            return f"<User(id={getattr(self, 'id', '<unknown>')})>"


class PasswordResetToken(Base):
    """Password reset token model for secure password reset workflow."""

    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, index=True)

    # Token lifecycle
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Security tracking
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)

    # Ensure email is scoped per tenant for token uniqueness
    __table_args__ = (
        Index('idx_reset_tokens_email_tenant', 'email', 'tenant_id'),
        Index('idx_reset_tokens_user_tenant', 'user_id', 'tenant_id'),
    )

    @classmethod
    def create_token(
        cls,
        user_id: str,
        tenant_id: str,
        email: str,
        expires_in_hours: int = 24,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> "PasswordResetToken":
        """Create a new password reset token."""
        import secrets

        # Generate a secure random token
        token = secrets.token_urlsafe(32)

        # Set expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        return cls(
            user_id=user_id,
            tenant_id=tenant_id,
            token=token,
            email=email,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        now = datetime.now(timezone.utc)
        return not self.is_used and self.expires_at > now

    def mark_as_used(self) -> None:
        """Mark token as used."""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """String representation of password reset token."""
        return f"<PasswordResetToken(id={self.id}, email={self.email}, tenant={self.tenant_id}, valid={self.is_valid()})>"
