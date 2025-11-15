"""
Pydantic schemas for the SMTP administration slice.

Separating these from the SQLAlchemy models keeps request/response contracts
co-located with the feature while avoiding tight coupling to persistence code.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.features.core.schemas import PaginatedRequest
from .models import SMTPStatus


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

    @validator("use_ssl", "use_tls")
    def validate_encryption(cls, v, values):
        """Ensure TLS and SSL are not both enabled."""
        if "use_tls" in values and values["use_tls"] and v:
            raise ValueError("Cannot use both TLS and SSL")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        """Ensure passwords match."""
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
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
    last_tested_at: Optional[datetime] = None
    test_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SMTPTestResult(BaseModel):
    """Schema for SMTP connection test results."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    tested_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SMTPConfigurationStats(BaseModel):
    """Schema for high-level SMTP configuration statistics."""

    total_configurations: int
    active_configurations: int
    verified_configurations: int
    failed_configurations: int
    configurations_by_status: Dict[str, int]
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SMTPSearchFilter(PaginatedRequest):
    """Schema for SMTP configuration search and filtering."""

    search: Optional[str] = None
    status: Optional[SMTPStatus] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class SMTPDashboardStats(BaseModel):
    """Schema for SMTP configuration dashboard statistics."""

    total_configurations: int
    active_configurations: int
    verified_configurations: int
    failed_configurations: int
    configurations_by_status: Dict[str, int]
    recent_configurations: List[SMTPConfigurationResponse]


__all__ = [
    "SMTPConfigurationCreate",
    "SMTPConfigurationResponse",
    "SMTPConfigurationStats",
    "SMTPConfigurationUpdate",
    "SMTPDashboardStats",
    "SMTPSearchFilter",
    "SMTPTestResult",
]
