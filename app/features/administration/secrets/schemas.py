"""
Pydantic schemas for the secrets administration slice.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import SecretType


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
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    updated_by_email: Optional[str]
    updated_by_name: Optional[str]
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


__all__ = ["SecretCreate", "SecretResponse", "SecretUpdate", "SecretValue"]
