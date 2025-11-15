"""
SMTP configuration models for administration interface.
"""

import uuid
from typing import Dict, Any
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

    def to_dict(self) -> Dict[str, Any]:
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
