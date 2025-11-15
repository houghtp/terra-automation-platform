"""
Tenant management models and schemas for administration interface.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

from app.features.core.schemas import PaginatedRequest


class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TenantTier(str, Enum):
    """Tenant tier/plan enumeration."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    name: str = Field(..., min_length=2, max_length=255, description="Tenant name")
    description: Optional[str] = Field(None, max_length=1000, description="Tenant description")
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="Tenant status")
    tier: TenantTier = Field(default=TenantTier.FREE, description="Tenant tier/plan")

    # Metadata fields
    contact_email: Optional[EmailStr] = Field(None, description="Primary contact email")
    contact_name: Optional[str] = Field(None, max_length=255, description="Primary contact name")
    website: Optional[str] = Field(None, max_length=500, description="Tenant website")

    # Configuration
    max_users: Optional[int] = Field(default=10, ge=1, description="Maximum users allowed")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Feature flags")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tenant settings")


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TenantStatus] = None
    tier: Optional[TenantTier] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    max_users: Optional[int] = Field(None, ge=1)
    features: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Schema for tenant API responses."""
    id: int
    name: str
    description: Optional[str] = None
    status: str
    tier: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    website: Optional[str] = None
    max_users: Optional[int] = None
    user_count: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TenantStats(BaseModel):
    """Schema for tenant statistics."""
    id: int
    name: str
    status: str
    user_count: int
    max_users: int
    utilization: float  # user_count / max_users
    tier: str
    created_at: datetime
    last_activity: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserTenantAssignment(BaseModel):
    """Schema for assigning users to tenants."""
    user_id: str
    tenant_id: int
    role: str = Field(default="user", description="Role in the tenant")


class TenantUserResponse(BaseModel):
    """Schema for users within a tenant."""
    id: str
    name: str
    email: str
    role: str
    status: str
    enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TenantDashboardStats(BaseModel):
    """Schema for tenant management dashboard statistics."""
    total_tenants: int
    active_tenants: int
    inactive_tenants: int
    suspended_tenants: int
    total_users: int
    tenants_by_tier: Dict[str, int]
    recent_tenants: List[TenantResponse]


class TenantSearchFilter(PaginatedRequest):
    """Schema for tenant search and filtering."""
    search: Optional[str] = None
    status: Optional[TenantStatus] = None
    tier: Optional[TenantTier] = None
    has_users: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


__all__ = [
    "TenantStatus",
    "TenantTier",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantStats",
    "UserTenantAssignment",
    "TenantUserResponse",
    "TenantDashboardStats",
    "TenantSearchFilter",
]
