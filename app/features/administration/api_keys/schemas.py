"""
Pydantic schemas for the administration API keys slice.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    """Request to create new API key."""

    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    description: Optional[str] = Field(None, max_length=1000, description="API key description")
    tenant_id: str = Field(..., description="Tenant ID for the API key")
    scopes: List[str] = Field(..., min_items=1, description="List of permission scopes")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration")
    rate_limit_per_hour: int = Field(1000, ge=1, le=10000, description="Requests per hour limit")
    rate_limit_per_day: int = Field(10000, ge=1, le=100000, description="Requests per day limit")


class APIKeyResponse(BaseModel):
    """API key information response."""

    id: int
    key_id: str
    name: str
    description: Optional[str]
    tenant_id: str
    scopes: List[str]
    status: str
    is_active: bool
    rate_limit_per_hour: int
    rate_limit_per_day: int
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    secret: Optional[str] = None  # Only include secret on creation

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class APIKeyListResponse(BaseModel):
    """API key list item (without secret)."""

    id: int
    key_id: str
    name: str
    description: Optional[str]
    tenant_id: str
    scopes: List[str]
    status: str
    is_active: bool
    last_used_at: Optional[datetime]
    usage_count: int
    success_rate: float
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class APIKeyStatsResponse(BaseModel):
    """API key usage statistics."""

    total_keys: int
    active_keys: int
    revoked_keys: int
    expired_keys: int
    total_requests_today: int
    top_tenants: List[dict]


__all__ = [
    "APIKeyCreateRequest",
    "APIKeyListResponse",
    "APIKeyResponse",
    "APIKeyStatsResponse",
]
