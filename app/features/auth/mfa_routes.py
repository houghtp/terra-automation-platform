"""
Multi-Factor Authentication (MFA) API endpoints.

Provides user-facing MFA management and verification endpoints.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.mfa import MFAManager, MFAMethod, TOTPSetup
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mfa", tags=["mfa"])


# Request/Response Models
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
    last_used: Optional[str]
    is_locked: bool
    locked_until: Optional[str]


class MFAChallengeResponse(BaseModel):
    """MFA challenge response."""
    challenge_id: str
    method: str
    expires_in: int  # seconds


# MFA Setup Endpoints
@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get current user's MFA status and configuration."""
    try:
        status_info = await MFAManager.get_user_mfa_status(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve MFA status"
            )

        return MFAStatusResponse(
            enabled=status_info["enabled"],
            status=status_info["status"],
            required=status_info.get("required", False),
            methods=[method.value for method in status_info["methods"]],
            recovery_codes_remaining=status_info["recovery_codes_remaining"],
            last_used=status_info["last_used"].isoformat() if status_info["last_used"] else None,
            is_locked=status_info["is_locked"],
            locked_until=status_info["locked_until"].isoformat() if status_info["locked_until"] else None
        )

    except Exception as e:
        logger.error(f"Failed to get MFA status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve MFA status"
        )


@router.post("/setup/totp", response_model=TOTPSetupResponse)
async def setup_totp(
    request: TOTPSetupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Initiate TOTP setup for the current user.

    Returns QR code and backup codes. User must verify with /verify/totp to enable.
    """
    try:
        totp_setup = await MFAManager.setup_totp_for_user(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            user_email=current_user.email
        )

        return TOTPSetupResponse(
            qr_code_url=totp_setup.qr_code_url,
            manual_entry_key=totp_setup.secret,
            backup_codes=totp_setup.backup_codes,
            issuer=totp_setup.issuer
        )

    except Exception as e:
        logger.error(f"Failed to setup TOTP for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup TOTP"
        )


@router.post("/verify/totp")
async def verify_totp_setup(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Verify TOTP code and enable MFA for the user.

    This completes the TOTP enrollment process.
    """
    try:
        success = await MFAManager.verify_totp_and_enable(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            totp_code=request.code
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP code. Please check your authenticator app."
            )

        return {
            "message": "TOTP enabled successfully",
            "mfa_enabled": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify TOTP for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify TOTP"
        )


# MFA Challenge and Verification (for login flows)
@router.post("/challenge", response_model=MFAChallengeResponse)
async def create_mfa_challenge(
    request: MFAChallengeRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Create an MFA challenge for authentication.

    Used during login flows when MFA is required.
    """
    try:
        # Validate method
        try:
            method = MFAMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MFA method: {request.method}"
            )

        # Get client IP
        client_ip = req.client.host if req.client else None

        challenge_id = await MFAManager.create_mfa_challenge(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            method=method,
            ip_address=client_ip
        )

        if not challenge_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create MFA challenge"
            )

        return MFAChallengeResponse(
            challenge_id=challenge_id,
            method=method.value,
            expires_in=300  # 5 minutes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create MFA challenge for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create MFA challenge"
        )


@router.post("/verify")
async def verify_mfa(
    request: MFAVerifyRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Verify MFA challenge with provided code.

    Used to complete MFA verification during authentication.
    """
    try:
        # Validate method
        try:
            method = MFAMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MFA method: {request.method}"
            )

        success = await MFAManager.verify_mfa_challenge(
            session=session,
            challenge_id=request.challenge_id,
            code=request.code,
            method=method
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code or expired challenge"
            )

        return {
            "message": "MFA verification successful",
            "verified": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify MFA challenge {request.challenge_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA"
        )


@router.post("/disable")
async def disable_mfa(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Disable MFA for the current user.

    This removes all MFA methods and recovery codes.
    """
    try:
        success = await MFAManager.disable_mfa_for_user(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No MFA configuration found"
            )

        return {
            "message": "MFA disabled successfully",
            "mfa_enabled": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable MFA for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable MFA"
        )


@router.post("/regenerate-recovery-codes")
async def regenerate_recovery_codes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Regenerate recovery codes for the user.

    This invalidates all existing recovery codes.
    """
    try:
        # For now, we'll regenerate by setting up TOTP again
        # In a full implementation, you'd want a dedicated method
        totp_setup = await MFAManager.setup_totp_for_user(
            session=session,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            user_email=current_user.email
        )

        return {
            "message": "Recovery codes regenerated successfully",
            "backup_codes": totp_setup.backup_codes
        }

    except Exception as e:
        logger.error(f"Failed to regenerate recovery codes for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate recovery codes"
        )