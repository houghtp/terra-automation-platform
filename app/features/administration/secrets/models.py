"""
Tenant-aware secrets management models.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from app.features.core.database import Base


class SecretType(str, Enum):
    """Types of secrets that can be stored."""
    API_KEY = "api_key"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    DATABASE_URL = "database_url"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    OTHER = "other"


class TenantSecret(Base):
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=True)  # User who created the secret
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
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "secret_type": self.secret_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "rotation_interval_days": self.rotation_interval_days,
            "has_value": bool(self.encrypted_value),  # Indicate if secret exists without exposing it
        }


# Pydantic models for API
class SecretCreate(BaseModel):
    """Schema for creating a new secret."""
    name: str = Field(..., min_length=1, max_length=255, description="Secret name")
    description: Optional[str] = Field(None, max_length=1000, description="Secret description")
    secret_type: SecretType = Field(SecretType.OTHER, description="Type of secret")
    value: str = Field(..., min_length=1, description="Secret value to encrypt")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")
    rotation_interval_days: Optional[int] = Field(None, ge=1, le=365, description="Auto-rotation interval in days")


class SecretUpdate(BaseModel):
    """Schema for updating an existing secret."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Secret name")
    description: Optional[str] = Field(None, max_length=1000, description="Secret description")
    secret_type: Optional[SecretType] = Field(None, description="Type of secret")
    value: Optional[str] = Field(None, min_length=1, description="New secret value")
    is_active: Optional[bool] = Field(None, description="Active status")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")
    rotation_interval_days: Optional[int] = Field(None, ge=1, le=365, description="Auto-rotation interval in days")


class SecretResponse(BaseModel):
    """Schema for secret responses (without the actual secret value)."""
    id: int
    tenant_id: str
    name: str
    description: Optional[str]
    secret_type: SecretType
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    last_accessed: Optional[datetime]
    access_count: int
    expires_at: Optional[datetime]
    rotation_interval_days: Optional[int]
    has_value: bool

    class Config:
        from_attributes = True


class SecretValue(BaseModel):
    """Schema for returning decrypted secret value (use carefully)."""
    value: str
    accessed_at: datetime
