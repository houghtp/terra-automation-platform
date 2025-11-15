"""
User management models and schemas for administration interface.
"""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
# Import the User model from auth - no duplicate SQLAlchemy models
from app.features.auth.models import User

from app.features.core.schemas import PaginatedRequest


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    name: str = Field(..., min_length=2, max_length=255, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    description: Optional[str] = Field(None, max_length=1000, description="User description")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User status")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    enabled: bool = Field(default=True, description="Whether user is enabled")
    tags: Optional[List[str]] = Field(default_factory=list, description="User tags")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class UserResponse(BaseModel):
    """Schema for user API responses."""
    id: str
    name: str
    email: str
    description: Optional[str] = None
    status: str
    role: str
    enabled: bool
    tags: Optional[List[str]] = None
    tenant_id: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserStats(BaseModel):
    """Schema for user statistics."""
    id: str
    name: str
    email: str
    status: str
    role: str
    enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserSearchFilter(PaginatedRequest):
    """Schema for user search and filtering."""
    search: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None
    enabled: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class UserDashboardStats(BaseModel):
    """Schema for user management dashboard statistics."""
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    users_by_role: Dict[str, int]
    recent_users: List[UserResponse]


__all__ = [
    "UserStatus",
    "UserRole",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserStats",
    "UserSearchFilter",
    "UserDashboardStats",
]
