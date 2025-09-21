"""Audit Log model for tracking system activities."""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Dict, Any, Optional

from app.features.core.database import Base


class AuditLog(Base):
    """
    Immutable audit log for tracking all system activities.

    This model captures user actions, admin actions, and system changes
    for compliance and security monitoring purposes.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Tenant isolation
    tenant_id = Column(String(255), nullable=False, index=True)

    # Audit metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "USER_LOGIN", "DATA_CREATED"
    category = Column(String(50), nullable=False, index=True)  # e.g., "AUTH", "DATA", "ADMIN"
    severity = Column(String(20), nullable=False, default="INFO")  # INFO, WARNING, ERROR, CRITICAL

    # User context
    user_id = Column(String(255), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(100), nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)
    request_id = Column(String(255), nullable=True)

    # Action details
    resource_type = Column(String(100), nullable=True)  # e.g., "user", "secret", "demo_item"
    resource_id = Column(String(255), nullable=True)
    old_values = Column(JSON, nullable=True)  # Previous state for updates/deletes
    new_values = Column(JSON, nullable=True)  # New state for creates/updates

    # Additional context
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Flexible additional data (renamed from metadata)

    # System context
    source_module = Column(String(100), nullable=True)  # Which module generated the log
    endpoint = Column(String(255), nullable=True)  # API endpoint accessed
    method = Column(String(10), nullable=True)  # HTTP method

    # Performance indexes
    __table_args__ = (
        Index('idx_audit_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_action_timestamp', 'action', 'timestamp'),
        Index('idx_audit_category_severity', 'category', 'severity'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "category": self.category,
            "severity": self.severity,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "description": self.description,
            "extra_data": self.extra_data,
            "source_module": self.source_module,
            "endpoint": self.endpoint,
            "method": self.method,
        }

    def __repr__(self) -> str:
        """String representation of audit log."""
        return (
            f"<AuditLog(id={self.id}, tenant={self.tenant_id}, "
            f"action={self.action}, user={self.user_email}, "
            f"timestamp={self.timestamp})>"
        )

    @classmethod
    def get_severity_color(cls, severity: str) -> str:
        """Get Bootstrap color class for severity level."""
        severity_colors = {
            "INFO": "blue",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "dark"
        }
        return severity_colors.get(severity.upper(), "gray")

    @classmethod
    def get_category_icon(cls, category: str) -> str:
        """Get Tabler icon for category."""
        category_icons = {
            "AUTH": "ti-shield-check",
            "DATA": "ti-database",
            "ADMIN": "ti-settings",
            "SECURITY": "ti-lock",
            "SYSTEM": "ti-cpu",
            "API": "ti-api",
            "USER": "ti-user"
        }
        return category_icons.get(category.upper(), "ti-file-text")
