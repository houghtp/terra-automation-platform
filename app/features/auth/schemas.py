"""
Pydantic schemas for authentication requests and responses.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """User registration request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[str] = Field(default="user", pattern="^(user|admin|global_admin)$")


class UserLoginRequest(BaseModel):
    """User login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response schema (safe for API responses)."""
    id: str
    email: str
    tenant_id: str
    role: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AuthStatusResponse(BaseModel):
    """Authentication status response."""
    authenticated: bool
    user: Optional[UserResponse] = None


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    """Password reset response schema."""
    message: str
    success: bool


class TOTPSetupRequest(BaseModel):
    """Request to initiate TOTP setup."""

    pass


class TOTPSetupResponse(BaseModel):
    """Response for TOTP setup initiation."""

    qr_code_url: str = Field(..., description="Data URL for QR code image")
    manual_entry_key: str = Field(..., description="Secret key for manual entry")
    backup_codes: List[str] = Field(..., description="Recovery codes (save these!)")
    issuer: str = Field(..., description="Service issuer name")


class TOTPVerifyRequest(BaseModel):
    """Request to verify TOTP and enable MFA."""

    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class MFAChallengeRequest(BaseModel):
    """Request to create MFA challenge."""

    method: str = Field(..., description="MFA method (totp, recovery_code)")


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA challenge."""

    challenge_id: str = Field(..., description="Challenge identifier")
    code: str = Field(..., description="Verification code")
    method: str = Field(..., description="MFA method used")


class MFAStatusResponse(BaseModel):
    """MFA status information."""

    enabled: bool
    status: str
    required: bool
    methods: List[str]
    recovery_codes_remaining: int
    last_used: Optional[datetime]
    is_locked: bool
    locked_until: Optional[datetime]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MFAChallengeResponse(BaseModel):
    """MFA challenge response."""

    challenge_id: str
    method: str
    expires_in: int  # seconds
