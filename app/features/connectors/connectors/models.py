"""
Connector models and schemas for business automation platform.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, func, Index, Integer, ForeignKey
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class ConnectorCategory(str, Enum):
    """Connector category enumeration."""
    SOCIAL_MEDIA = "social_media"
    CMS = "cms"
    EMAIL_MARKETING = "email_marketing"
    MARKETING = "marketing"
    ECOMMERCE = "ecommerce"
    CRM = "crm"
    ANALYTICS = "analytics"
    STORAGE = "storage"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    AI_ML = "ai_ml"
    DATA_EXTRACTION = "data_extraction"
    OTHER = "other"


class ConnectorStatus(str, Enum):
    """Connector status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING_SETUP = "pending_setup"


class AvailableConnector(Base):
    """Pre-defined connector types available for users to add."""

    __tablename__ = "available_connectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic Information
    name = Column(String(100), nullable=False, unique=True)  # "wordpress", "twitter", "linkedin"
    display_name = Column(String(255), nullable=False)  # "WordPress", "Twitter", "LinkedIn"
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default=ConnectorCategory.OTHER)

    # Visual & UI
    icon_url = Column(String(500), nullable=True)  # URL to connector icon/logo
    icon_class = Column(String(100), nullable=True)  # CSS class for icon (e.g., 'fab fa-wordpress')
    brand_color = Column(String(7), nullable=True)  # Hex color code for branding

    # Configuration Schema
    schema_definition = Column(JSON, nullable=False)  # Defines required fields for this connector
    default_configuration = Column(JSON, nullable=True)  # Default values for configuration

    # Management
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)  # For ordering in picker

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_available_connector_category', 'category'),
        Index('idx_available_connector_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON responses."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "icon_url": self.icon_url,
            "icon_class": self.icon_class,
            "brand_color": self.brand_color,
            "schema_definition": self.schema_definition or {},
            "default_configuration": self.default_configuration or {},
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation of available connector."""
        return f"<AvailableConnector(id={self.id}, name={self.name}, category={self.category})>"


class TenantConnector(Base, AuditMixin):
    """Tenant-specific configured connector instances."""

    __tablename__ = "tenant_connectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    available_connector_id = Column(String(36), ForeignKey('available_connectors.id'), nullable=False)

    # Instance Configuration
    instance_name = Column(String(255), nullable=False)  # User-defined name like "My WordPress Blog"
    description = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=False)  # Flexible config based on connector type
    secrets_references = Column(JSON, nullable=True)  # References to secrets slice entries

    # Status & Health
    status = Column(String(50), default=ConnectorStatus.PENDING_SETUP, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    health_check_url = Column(String(500), nullable=True)

    # Management fields
    tags = Column(JSON, default=list)

    # Audit fields
    # Note: created_at, updated_at, and created_by are now provided by AuditMixin

    __table_args__ = (
        Index('idx_tenant_connector_name_tenant', 'instance_name', 'tenant_id', unique=True),
        Index('idx_tenant_connector_status', 'status'),
        Index('idx_tenant_connector_available', 'available_connector_id'),
    )

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "available_connector_id": self.available_connector_id,
            "instance_name": self.instance_name,
            "description": self.description,
            "configuration": self.configuration or {},
            "secrets_references": self.secrets_references or {},
            "status": self.status,
            "is_enabled": self.is_enabled,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_error": self.last_error,
            "health_check_url": self.health_check_url,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        """String representation of tenant connector."""
        return f"<TenantConnector(id={self.id}, name={self.instance_name}, tenant={self.tenant_id})>"


# Pydantic Schemas

class AvailableConnectorResponse(BaseModel):
    """Schema for available connector API responses."""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    icon_url: Optional[str] = None
    icon_class: Optional[str] = None
    brand_color: Optional[str] = None
    schema_definition: Dict[str, Any]
    default_configuration: Dict[str, Any]
    is_active: bool
    sort_order: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TenantConnectorCreate(BaseModel):
    """Schema for creating a new tenant connector."""
    available_connector_id: str = Field(..., description="ID of the available connector to instantiate")
    instance_name: str = Field(..., min_length=2, max_length=255, description="Name for this connector instance")
    description: Optional[str] = Field(None, max_length=1000, description="Connector instance description")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Connector configuration")
    secrets_references: Optional[Dict[str, Any]] = Field(default_factory=dict, description="References to secrets")
    health_check_url: Optional[str] = Field(None, max_length=500, description="Health check URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="Connector tags")


class TenantConnectorUpdate(BaseModel):
    """Schema for updating a tenant connector."""
    instance_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    configuration: Optional[Dict[str, Any]] = None
    secrets_references: Optional[Dict[str, Any]] = None
    status: Optional[ConnectorStatus] = None
    is_enabled: Optional[bool] = None
    health_check_url: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None


class TenantConnectorResponse(BaseModel):
    """Schema for tenant connector API responses."""
    id: str
    tenant_id: str
    available_connector_id: str
    instance_name: str
    description: Optional[str] = None
    configuration: Dict[str, Any]
    secrets_references: Dict[str, Any]
    status: str
    is_enabled: bool
    last_sync: Optional[str] = None
    last_error: Optional[str] = None
    health_check_url: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None

    # Joined fields from available_connector
    connector_name: Optional[str] = None
    connector_display_name: Optional[str] = None
    connector_icon_url: Optional[str] = None
    connector_icon_class: Optional[str] = None
    connector_brand_color: Optional[str] = None
    connector_category: Optional[str] = None

    class Config:
        from_attributes = True


class ConnectorSearchFilter(BaseModel):
    """Schema for connector search and filtering."""
    search: Optional[str] = None
    category: Optional[ConnectorCategory] = None
    status: Optional[ConnectorStatus] = None
    is_enabled: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class ConnectorDashboardStats(BaseModel):
    """Schema for connector dashboard statistics."""
    total_connectors: int
    active_connectors: int
    error_connectors: int
    pending_setup_connectors: int
    connectors_by_category: Dict[str, int]
    connectors_by_status: Dict[str, int]
    recent_connectors: List[TenantConnectorResponse]

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, func, Index, Integer
from app.features.core.database import Base


class CONNECTORSStatus(str, Enum):
    """CONNECTORS configuration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    FAILED = "failed"


class CONNECTORSConfiguration(Base, AuditMixin):
    """CONNECTORS configuration model with tenant isolation and encryption."""

    __tablename__ = "connectors_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    # Configuration details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # CONNECTORS Settings
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
    status = Column(String(50), default=CONNECTORSStatus.INACTIVE)
    enabled = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)  # Only one active per tenant
    is_verified = Column(Boolean, default=False, nullable=False)

    # Testing & Validation
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    test_status = Column(String(50), nullable=True)  # "success", "failed"
    error_message = Column(Text, nullable=True)

    # Management fields matching user pattern
    tags = Column(JSON, default=list)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Ensure only one active config per tenant and unique names per tenant
    __table_args__ = (
        Index('idx_connectors_name_tenant', 'name', 'tenant_id', unique=True),
        Index('idx_connectors_active_tenant', 'tenant_id', 'is_active'),
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # Add audit information with human-readable data
        base_dict.update(self.get_audit_info())
        return base_dict

    def __repr__(self) -> str:
        """String representation of CONNECTORS configuration."""
        return f"<CONNECTORSConfiguration(id={self.id}, name={self.name}, host={self.host}, tenant={self.tenant_id})>"


class CONNECTORSConfigurationCreate(BaseModel):
    """Schema for creating a new CONNECTORS configuration."""
    name: str = Field(..., min_length=2, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    host: str = Field(..., min_length=1, max_length=255, description="CONNECTORS host")
    port: int = Field(default=587, ge=1, le=65535, description="CONNECTORS port")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    use_ssl: bool = Field(default=False, description="Use SSL encryption")
    username: str = Field(..., min_length=1, max_length=255, description="CONNECTORS username")
    password: str = Field(..., min_length=1, description="CONNECTORS password")
    confirm_password: str = Field(..., description="Password confirmation")
    from_email: EmailStr = Field(..., description="From email address")
    from_name: str = Field(..., min_length=1, max_length=100, description="From name")
    reply_to: Optional[EmailStr] = Field(None, description="Reply-to email address")
    status: CONNECTORSStatus = Field(default=CONNECTORSStatus.INACTIVE, description="Configuration status")
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


class CONNECTORSConfigurationUpdate(BaseModel):
    """Schema for updating an CONNECTORS configuration."""
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
    status: Optional[CONNECTORSStatus] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class CONNECTORSConfigurationResponse(BaseModel):
    """Schema for CONNECTORS configuration API responses."""
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


class CONNECTORSTestResult(BaseModel):
    """Schema for CONNECTORS connection test results."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    tested_at: str


class CONNECTORSConfigurationStats(BaseModel):
    """Schema for CONNECTORS configuration statistics."""
    id: str
    name: str
    host: str
    status: str
    is_active: bool
    is_verified: bool
    last_tested_at: Optional[str] = None
    created_at: str


class CONNECTORSSearchFilter(BaseModel):
    """Schema for CONNECTORS configuration search and filtering."""
    search: Optional[str] = None
    status: Optional[CONNECTORSStatus] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class CONNECTORSDashboardStats(BaseModel):
    """Schema for CONNECTORS configuration dashboard statistics."""
    total_configurations: int
    active_configurations: int
    verified_configurations: int
    failed_configurations: int
    configurations_by_status: Dict[str, int]
    recent_configurations: List[CONNECTORSConfigurationResponse]
