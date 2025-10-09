"""
Application logs model for storing structured logs in database with tenant isolation.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class ApplicationLog(Base, AuditMixin):
    """
    Database model for storing application logs with tenant isolation.

    This table stores critical logs (errors, security events, audit trails)
    for real-time querying and tenant-specific filtering.
    """
    __tablename__ = "application_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")
    request_id = Column(String(50), nullable=True, index=True)

    # Log metadata
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(255), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Log content
    message = Column(Text, nullable=False)
    exception_type = Column(String(255), nullable=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Request context
    user_id = Column(String(50), nullable=True, index=True)
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Additional structured data
    extra_data = Column(JSONB, nullable=True)

    # Composite indexes for efficient tenant-based queries
    __table_args__ = (
        Index('idx_logs_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_logs_tenant_level', 'tenant_id', 'level'),
        Index('idx_logs_tenant_request', 'tenant_id', 'request_id'),
        Index('idx_logs_level_timestamp', 'level', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for API responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "level": self.level,
            "logger_name": self.logger_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "message": self.message,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "stack_trace": self.stack_trace,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "extra_data": self.extra_data,
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        return f"<ApplicationLog(id={self.id}, tenant_id='{self.tenant_id}', level='{self.level}', timestamp='{self.timestamp}')>"
