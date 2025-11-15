"""
Tenant-aware secrets management models.
"""
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class SecretType(str, Enum):
    """Types of secrets that can be stored."""
    API_KEY = "api_key"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    DATABASE_URL = "database_url"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    OTHER = "other"


class TenantSecret(Base, AuditMixin):
    """
    Tenant-aware secrets storage with encryption.
    Integrates with existing bcrypt infrastructure for secure storage.
    """
    __tablename__ = "tenant_secrets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)

    # Secret identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    secret_type = Column(String(50), nullable=False, default=SecretType.OTHER)

    # Encrypted secret value (using bcrypt from existing infrastructure)
    encrypted_value = Column(Text, nullable=False)

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    # Note: created_at, updated_at, and created_by are now provided by AuditMixin
    last_accessed = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Expiration and rotation
    expires_at = Column(DateTime, nullable=True)
    rotation_interval_days = Column(Integer, nullable=True)

    # Database constraints and indexes
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_secret_name'),
        Index('idx_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_tenant_type', 'tenant_id', 'secret_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_expires_at', 'expires_at'),
    )

    @property
    def has_value(self) -> bool:
        """Check if secret has a value without exposing it."""
        return bool(self.encrypted_value)

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding sensitive data."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "secret_type": self.secret_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "rotation_interval_days": self.rotation_interval_days,
            "has_value": bool(self.encrypted_value),  # Indicate if secret exists without exposing it
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

