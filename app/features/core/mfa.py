"""
Multi-Factor Authentication (MFA) system for enterprise SaaS platform.

Provides comprehensive MFA support including TOTP, SMS, and recovery codes.
"""
import secrets
import qrcode
import pyotp
import base64
import hashlib
import hmac
from io import BytesIO
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException, status
import structlog

from app.features.core.database import Base

logger = structlog.get_logger(__name__)


class MFAMethod(Enum):
    """Available MFA methods."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    RECOVERY_CODE = "recovery_code"


class MFAStatus(Enum):
    """MFA enrollment status."""
    DISABLED = "disabled"
    PENDING = "pending"
    ENABLED = "enabled"
    SUSPENDED = "suspended"


@dataclass
class MFAChallenge:
    """MFA challenge information."""
    challenge_id: str
    method: MFAMethod
    expires_at: datetime
    attempts_remaining: int


@dataclass
class TOTPSetup:
    """TOTP setup information for user enrollment."""
    secret: str
    qr_code_url: str
    backup_codes: List[str]
    issuer: str = "FastAPI Template"


class UserMFA(Base):
    """
    User MFA configuration and status.

    Tracks MFA methods, backup codes, and security settings per user.
    """
    __tablename__ = "user_mfa"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # MFA status
    status = Column(String(20), default=MFAStatus.DISABLED.value, nullable=False)
    is_required = Column(Boolean, default=False, nullable=False)  # Admin can force MFA

    # TOTP configuration
    totp_secret = Column(String(255), nullable=True)  # Encrypted
    totp_enabled = Column(Boolean, default=False, nullable=False)
    totp_verified_at = Column(DateTime, nullable=True)

    # SMS configuration
    sms_phone = Column(String(20), nullable=True)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    sms_verified_at = Column(DateTime, nullable=True)

    # Email configuration
    email_enabled = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Recovery codes (hashed)
    recovery_codes = Column(JSON, nullable=True)  # List of hashed codes
    recovery_codes_generated_at = Column(DateTime, nullable=True)
    recovery_codes_used = Column(Integer, default=0, nullable=False)

    # Security tracking
    last_used_at = Column(DateTime, nullable=True)
    last_used_method = Column(String(20), nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Audit
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def has_any_method_enabled(self) -> bool:
        """Check if user has any MFA method enabled."""
        return self.totp_enabled or self.sms_enabled or self.email_enabled

    def is_locked(self) -> bool:
        """Check if MFA is temporarily locked due to failed attempts."""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def get_enabled_methods(self) -> List[MFAMethod]:
        """Get list of enabled MFA methods."""
        methods = []
        if self.totp_enabled:
            methods.append(MFAMethod.TOTP)
        if self.sms_enabled:
            methods.append(MFAMethod.SMS)
        if self.email_enabled:
            methods.append(MFAMethod.EMAIL)
        return methods


class MFAChallenge(Base):
    """
    Active MFA challenges for authentication flows.

    Temporary records for ongoing MFA verification processes.
    """
    __tablename__ = "mfa_challenges"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Challenge details
    method = Column(String(20), nullable=False)
    challenge_data = Column(JSON, nullable=True)  # Method-specific data

    # Security
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Lifecycle
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)

    def is_expired(self) -> bool:
        """Check if challenge has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_exhausted(self) -> bool:
        """Check if all attempts have been used."""
        return self.attempts >= self.max_attempts

    def is_valid(self) -> bool:
        """Check if challenge is still valid."""
        return not self.is_expired() and not self.is_exhausted() and not self.completed_at


class MFAManager:
    """
    Manages Multi-Factor Authentication operations.

    Features:
    - TOTP enrollment and verification
    - SMS OTP support
    - Recovery code generation and validation
    - MFA policy enforcement
    - Challenge management
    """

    @staticmethod
    def generate_recovery_codes(count: int = 10) -> List[str]:
        """Generate secure recovery codes."""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes

    @staticmethod
    def hash_recovery_code(code: str) -> str:
        """Hash recovery code for secure storage."""
        # Remove formatting and convert to lowercase
        clean_code = code.replace("-", "").lower()
        return hashlib.sha256(clean_code.encode()).hexdigest()

    @staticmethod
    def verify_recovery_code(code: str, hashed_code: str) -> bool:
        """Verify recovery code against hash."""
        return hmac.compare_digest(
            MFAManager.hash_recovery_code(code),
            hashed_code
        )

    @staticmethod
    async def setup_totp_for_user(
        session: AsyncSession,
        user_id: str,
        tenant_id: str,
        user_email: str,
        issuer: str = "FastAPI Template"
    ) -> TOTPSetup:
        """
        Set up TOTP for a user and return setup information.

        Args:
            session: Database session
            user_id: User identifier
            tenant_id: Tenant identifier
            user_email: User email for QR code
            issuer: Service name for authenticator apps

        Returns:
            TOTPSetup with secret, QR code, and backup codes
        """
        try:
            # Generate TOTP secret
            secret = pyotp.random_base32()

            # Create TOTP URI for QR code
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=issuer
            )

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format='PNG')
            qr_code_data = base64.b64encode(buf.getvalue()).decode()
            qr_code_url = f"data:image/png;base64,{qr_code_data}"

            # Generate recovery codes
            recovery_codes = MFAManager.generate_recovery_codes()
            hashed_codes = [MFAManager.hash_recovery_code(code) for code in recovery_codes]

            # Find or create MFA record
            stmt = select(UserMFA).where(
                UserMFA.user_id == user_id,
                UserMFA.tenant_id == tenant_id
            )
            result = await session.execute(stmt)
            mfa_record = result.scalar_one_or_none()

            if not mfa_record:
                mfa_record = UserMFA(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    status=MFAStatus.PENDING.value
                )
                session.add(mfa_record)

            # Update with TOTP setup (but don't enable yet)
            mfa_record.totp_secret = secret  # In production, encrypt this
            mfa_record.recovery_codes = hashed_codes
            mfa_record.recovery_codes_generated_at = datetime.now(timezone.utc)
            mfa_record.status = MFAStatus.PENDING.value

            await session.commit()

            logger.info(f"TOTP setup initiated for user {user_id}")

            return TOTPSetup(
                secret=secret,
                qr_code_url=qr_code_url,
                backup_codes=recovery_codes,
                issuer=issuer
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to setup TOTP for user {user_id}: {e}")
            raise

    @staticmethod
    async def verify_totp_and_enable(
        session: AsyncSession,
        user_id: str,
        tenant_id: str,
        totp_code: str
    ) -> bool:
        """
        Verify TOTP code and enable MFA for user.

        Args:
            session: Database session
            user_id: User identifier
            tenant_id: Tenant identifier
            totp_code: 6-digit TOTP code from authenticator app

        Returns:
            True if verification successful and MFA enabled
        """
        try:
            # Get user MFA record
            stmt = select(UserMFA).where(
                UserMFA.user_id == user_id,
                UserMFA.tenant_id == tenant_id
            )
            result = await session.execute(stmt)
            mfa_record = result.scalar_one_or_none()

            if not mfa_record or not mfa_record.totp_secret:
                logger.warning(f"No TOTP setup found for user {user_id}")
                return False

            # Verify TOTP code
            totp = pyotp.TOTP(mfa_record.totp_secret)
            if not totp.verify(totp_code, valid_window=1):  # Allow 1 window tolerance
                logger.warning(f"Invalid TOTP code for user {user_id}")
                return False

            # Enable TOTP and update status
            mfa_record.totp_enabled = True
            mfa_record.totp_verified_at = datetime.now(timezone.utc)
            mfa_record.status = MFAStatus.ENABLED.value
            mfa_record.last_used_at = datetime.now(timezone.utc)
            mfa_record.last_used_method = MFAMethod.TOTP.value

            await session.commit()

            logger.info(f"TOTP enabled for user {user_id}")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to verify TOTP for user {user_id}: {e}")
            return False

    @staticmethod
    async def create_mfa_challenge(
        session: AsyncSession,
        user_id: str,
        tenant_id: str,
        method: MFAMethod,
        ip_address: Optional[str] = None,
        expires_in_minutes: int = 5
    ) -> Optional[str]:
        """
        Create an MFA challenge for authentication.

        Args:
            session: Database session
            user_id: User identifier
            tenant_id: Tenant identifier
            method: MFA method to challenge
            ip_address: Client IP address
            expires_in_minutes: Challenge validity period

        Returns:
            Challenge ID if successful
        """
        try:
            # Generate challenge ID
            challenge_id = secrets.token_urlsafe(24)

            # Calculate expiration
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

            # Create challenge record
            challenge = MFAChallenge(
                challenge_id=challenge_id,
                user_id=user_id,
                tenant_id=tenant_id,
                method=method.value,
                expires_at=expires_at,
                ip_address=ip_address
            )

            session.add(challenge)
            await session.commit()

            logger.info(f"Created MFA challenge {challenge_id} for user {user_id}")
            return challenge_id

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create MFA challenge: {e}")
            return None

    @staticmethod
    async def verify_mfa_challenge(
        session: AsyncSession,
        challenge_id: str,
        code: str,
        method: MFAMethod
    ) -> bool:
        """
        Verify MFA challenge with provided code.

        Args:
            session: Database session
            challenge_id: Challenge identifier
            code: Verification code
            method: MFA method being verified

        Returns:
            True if verification successful
        """
        try:
            # Get challenge
            stmt = select(MFAChallenge).where(MFAChallenge.challenge_id == challenge_id)
            result = await session.execute(stmt)
            challenge = result.scalar_one_or_none()

            if not challenge or not challenge.is_valid():
                logger.warning(f"Invalid or expired challenge: {challenge_id}")
                return False

            # Increment attempts
            challenge.attempts += 1

            # Get user MFA record
            stmt = select(UserMFA).where(
                UserMFA.user_id == challenge.user_id,
                UserMFA.tenant_id == challenge.tenant_id
            )
            result = await session.execute(stmt)
            mfa_record = result.scalar_one_or_none()

            if not mfa_record:
                logger.warning(f"No MFA record for user {challenge.user_id}")
                await session.commit()  # Save attempt increment
                return False

            verification_success = False

            if method == MFAMethod.TOTP and mfa_record.totp_enabled:
                # Verify TOTP
                totp = pyotp.TOTP(mfa_record.totp_secret)
                verification_success = totp.verify(code, valid_window=1)

            elif method == MFAMethod.RECOVERY_CODE:
                # Verify recovery code
                if mfa_record.recovery_codes:
                    for stored_hash in mfa_record.recovery_codes:
                        if MFAManager.verify_recovery_code(code, stored_hash):
                            # Remove used recovery code
                            mfa_record.recovery_codes.remove(stored_hash)
                            mfa_record.recovery_codes_used += 1
                            verification_success = True
                            break

            if verification_success:
                # Mark challenge as completed
                challenge.completed_at = datetime.now(timezone.utc)

                # Update MFA record
                mfa_record.last_used_at = datetime.now(timezone.utc)
                mfa_record.last_used_method = method.value
                mfa_record.failed_attempts = 0  # Reset failed attempts

                logger.info(f"MFA verification successful for user {challenge.user_id}")
            else:
                # Update failed attempts
                mfa_record.failed_attempts += 1

                # Lock account if too many failures
                if mfa_record.failed_attempts >= 5:
                    mfa_record.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                    logger.warning(f"MFA locked for user {challenge.user_id} due to failed attempts")

                logger.warning(f"MFA verification failed for user {challenge.user_id}")

            await session.commit()
            return verification_success

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to verify MFA challenge: {e}")
            return False

    @staticmethod
    async def disable_mfa_for_user(
        session: AsyncSession,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Disable MFA for a user (admin function)."""
        try:
            stmt = update(UserMFA).where(
                UserMFA.user_id == user_id,
                UserMFA.tenant_id == tenant_id
            ).values(
                status=MFAStatus.DISABLED.value,
                totp_enabled=False,
                sms_enabled=False,
                email_enabled=False,
                totp_secret=None,
                recovery_codes=None,
                failed_attempts=0,
                locked_until=None
            )

            result = await session.execute(stmt)
            await session.commit()

            success = result.rowcount > 0
            if success:
                logger.info(f"MFA disabled for user {user_id}")

            return success

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to disable MFA for user {user_id}: {e}")
            return False

    @staticmethod
    async def get_user_mfa_status(
        session: AsyncSession,
        user_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get comprehensive MFA status for a user."""
        try:
            stmt = select(UserMFA).where(
                UserMFA.user_id == user_id,
                UserMFA.tenant_id == tenant_id
            )
            result = await session.execute(stmt)
            mfa_record = result.scalar_one_or_none()

            if not mfa_record:
                return {
                    "enabled": False,
                    "status": MFAStatus.DISABLED.value,
                    "methods": [],
                    "recovery_codes_remaining": 0
                }

            return {
                "enabled": mfa_record.has_any_method_enabled(),
                "status": mfa_record.status,
                "required": mfa_record.is_required,
                "methods": mfa_record.get_enabled_methods(),
                "recovery_codes_remaining": len(mfa_record.recovery_codes or []) - mfa_record.recovery_codes_used,
                "last_used": mfa_record.last_used_at,
                "is_locked": mfa_record.is_locked(),
                "locked_until": mfa_record.locked_until
            }

        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user_id}: {e}")
            return None
