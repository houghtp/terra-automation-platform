"""
SMTP configuration models and schemas for administration interface.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, func, Index, Integer
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class SMTPStatus(str, Enum):
    """SMTP configuration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    FAILED = "failed"


class SMTPConfiguration(Base, AuditMixin):
    """SMTP configuration model with tenant isolation and encryption."""

    __tablename__ = "smtp_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    # Configuration details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # SMTP Settings
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=587, nullable=False)
    use_tls = Column(Boolean, default=True, nullable=False)
    use_ssl = Column(Boolean, default=False, nullable=False)

    # Authentication (password will be encrypted)
    username = Column(String(255), nullable=False)
    hashed_password = Column(String(500), nullable=False)  # Encrypted password

    # From Address Configuration
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(100), nullable=False)
    reply_to = Column(String(255), nullable=True)

    # Status & Management
    status = Column(String(50), default=SMTPStatus.INACTIVE)
    enabled = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)  # Only one active per tenant
    is_verified = Column(Boolean, default=False, nullable=False)

    # Testing & Validation
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    test_status = Column(String(50), nullable=True)  # "success", "failed"
    error_message = Column(Text, nullable=True)

    # Management fields matching user pattern
    tags = Column(JSON, default=list)

    # Ensure only one active config per tenant and unique names per tenant
    __table_args__ = (
        Index('idx_smtp_name_tenant', 'name', 'tenant_id', unique=True),
        Index('idx_smtp_active_tenant', 'tenant_id', 'is_active'),
    )

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON responses (excludes password)."""
        base_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "host": self.host,
            "port": self.port,
            "use_tls": self.use_tls,
            "use_ssl": self.use_ssl,
            "username": self.username,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "reply_to": self.reply_to,
            "status": self.status,
            "enabled": self.enabled,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "tags": self.tags or [],
            "tenant_id": self.tenant_id,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "test_status": self.test_status,
            "error_message": self.error_message,
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        """String representation of SMTP configuration."""
        return f"<SMTPConfiguration(id={self.id}, name={self.name}, host={self.host}, tenant={self.tenant_id})>"


class SMTPConfigurationCreate(BaseModel):
    """Schema for creating a new SMTP configuration."""
    name: str = Field(..., min_length=2, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    host: str = Field(..., min_length=1, max_length=255, description="SMTP host")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    use_ssl: bool = Field(default=False, description="Use SSL encryption")
    username: str = Field(..., min_length=1, max_length=255, description="SMTP username")
    password: str = Field(..., min_length=1, description="SMTP password")
    confirm_password: str = Field(..., description="Password confirmation")
    from_email: EmailStr = Field(..., description="From email address")
    from_name: str = Field(..., min_length=1, max_length=100, description="From name")
    reply_to: Optional[EmailStr] = Field(None, description="Reply-to email address")
    status: SMTPStatus = Field(default=SMTPStatus.INACTIVE, description="Configuration status")
    enabled: bool = Field(default=True, description="Whether configuration is enabled")
    tags: Optional[List[str]] = Field(default_factory=list, description="Configuration tags")

    @validator('use_ssl', 'use_tls')
    def validate_encryption(cls, v, values):
        """Ensure TLS and SSL are not both enabled."""
        if 'use_tls' in values and values['use_tls'] and v:
            raise ValueError("Cannot use both TLS and SSL")
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class SMTPConfigurationUpdate(BaseModel):
    """Schema for updating an SMTP configuration."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=1)
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = Field(None, min_length=1, max_length=100)
    reply_to: Optional[EmailStr] = None
    status: Optional[SMTPStatus] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class SMTPConfigurationResponse(BaseModel):
    """Schema for SMTP configuration API responses."""
    id: str
    name: str
    description: Optional[str] = None
    host: str
    port: int
    use_tls: bool
    use_ssl: bool
    username: str
    from_email: str
    from_name: str
    reply_to: Optional[str] = None
    status: str
    enabled: bool
    is_active: bool
    is_verified: bool
    tags: Optional[List[str]] = None
    tenant_id: str
    last_tested_at: Optional[str] = None
    test_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SMTPTestResult(BaseModel):
    """Schema for SMTP connection test results."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    tested_at: str


class SMTPConfigurationStats(BaseModel):
    """Schema for SMTP configuration statistics."""
    id: str
    name: str
    host: str
    status: str
    is_active: bool
    is_verified: bool
    last_tested_at: Optional[str] = None
    created_at: str


class SMTPSearchFilter(BaseModel):
    """Schema for SMTP configuration search and filtering."""
    search: Optional[str] = None
    status: Optional[SMTPStatus] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class SMTPDashboardStats(BaseModel):
    """Schema for SMTP configuration dashboard statistics."""
    total_configurations: int
    active_configurations: int
    verified_configurations: int
    failed_configurations: int
    configurations_by_status: Dict[str, int]
    recent_configurations: List[SMTPConfigurationResponse]