"""
Connector models for the Connectors slice.

Implements the PRP specification for:
- connector_catalog (GLOBAL seed data, read-only)
- connectors (TENANT-scoped installed instances)
"""

import uuid
from typing import Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, func, Index, ForeignKey
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


# === ENUMERATIONS ===

class AuthType(str, Enum):
    """Authentication type for connectors."""
    OAUTH = "oauth"
    API_KEY = "api_key"
    BASIC = "basic"
    NONE = "none"


class ConnectorStatus(str, Enum):
    """Connector instance status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"


# === DATABASE MODELS ===

class ConnectorCatalog(Base):
    """
    Global catalog of available connector types (read-only at runtime).
    Seeded via app/seed_connectors.py
    """
    __tablename__ = "connector_catalog"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identifier fields
    key = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "twitter", "wordpress"
    name = Column(String(255), nullable=False)  # Display name
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # e.g., "Social", "Web", "Video"

    # Visual & metadata
    icon = Column(String(100), nullable=True)  # Icon name/class (e.g., "brand-x", "brand-wordpress")
    auth_type = Column(String(20), nullable=False, default=AuthType.API_KEY.value)

    # Capabilities and configuration
    capabilities = Column(JSON, default=dict)  # e.g., {"post_text": true, "max_length": 280}
    default_config_schema = Column(JSON, default=dict)  # JSON Schema for config validation

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_connector_catalog_key', 'key', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "auth_type": self.auth_type,
            "capabilities": self.capabilities or {},
            "default_config_schema": self.default_config_schema or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ConnectorCatalog(key={self.key}, name={self.name})>"


class Connector(Base, AuditMixin):
    """
    Tenant-scoped installed connector instances.
    Each instance is configured with specific config and auth (encrypted).
    """
    __tablename__ = "connectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    catalog_id = Column(String(36), ForeignKey('connector_catalog.id'), nullable=False)

    # Instance configuration
    name = Column(String(255), nullable=False)  # User-defined label (e.g., "Marketing Twitter")
    status = Column(String(20), nullable=False, default=ConnectorStatus.INACTIVE.value)

    # Configuration and auth (JSONB)
    config = Column(JSON, default=dict)  # Validated against catalog's default_config_schema
    auth = Column(JSON, default=dict)  # Encrypted at rest (tokens, keys, etc.)

    # Metadata
    tags = Column(JSON, default=list)

    # AuditMixin provides: created_at, updated_at, created_by, updated_by, created_by_name, updated_by_name

    __table_args__ = (
        Index('idx_connectors_tenant', 'tenant_id'),
        Index('idx_connectors_catalog', 'catalog_id'),
        Index('idx_connectors_name_tenant', 'name', 'tenant_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON responses (excludes raw auth)."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "catalog_id": self.catalog_id,
            "name": self.name,
            "status": self.status,
            "config": self.config or {},
            "auth_configured": bool(self.auth),  # Indicate if auth exists without exposing it
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        return f"<Connector(name={self.name}, tenant={self.tenant_id}, status={self.status})>"

