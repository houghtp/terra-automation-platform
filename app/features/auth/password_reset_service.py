"""
Password reset service for secure password reset functionality.
"""
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from app.features.auth.models import User
from app.features.auth.models import PasswordResetToken
from app.features.core.security import security_manager


logger = structlog.get_logger(__name__)


class PasswordResetService:
    """Service for handling password reset workflow with tenant isolation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def request_password_reset(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Request a password reset for a user.

        Args:
            email: User's email address
            ip_address: Client IP address for security tracking
            user_agent: Client user agent for security tracking

        Returns:
            bool: Always returns True for security (don't reveal if email exists)
        """
        try:
            # Find user by email across all tenants (email should be unique globally)
            result = await self.session.execute(
                select(User).where(
                    and_(
                        User.email == email,
                        User.is_active == True
                    )
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                # Don't reveal that email doesn't exist - return True for security
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True

            # Invalidate any existing reset tokens for this user
            await self._invalidate_existing_tokens(user.id, user.tenant_id)

            # Create new reset token
            reset_token = PasswordResetToken.create_token(
                user_id=user.id,
                tenant_id=user.tenant_id,
                email=user.email,
                expires_in_hours=24,  # Token expires in 24 hours
                ip_address=ip_address,
                user_agent=user_agent
            )

            self.session.add(reset_token)
            await self.session.commit()

            logger.info(f"Password reset token created for user {user.email} in tenant {user.tenant_id}")

            # TODO: Send password reset email
            await self._send_password_reset_email(user, reset_token.token)

            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create password reset token for {email}: {e}")
            # Return True for security - don't reveal internal errors
            return True

    async def verify_reset_token(self, token: str) -> Optional[dict]:
        """
        Verify a password reset token.

        Args:
            token: Reset token to verify

        Returns:
            dict: User info if token is valid, None otherwise
        """
        try:
            result = await self.session.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.token == token
                )
            )
            reset_token = result.scalar_one_or_none()

            if not reset_token or not reset_token.is_valid():
                return None

            # Get user information
            user_result = await self.session.execute(
                select(User).where(
                    and_(
                        User.id == reset_token.user_id,
                        User.tenant_id == reset_token.tenant_id,
                        User.is_active == True
                    )
                )
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return None

            return {
                "user_id": user.id,
                "email": user.email,
                "tenant_id": user.tenant_id,
                "token_id": reset_token.id
            }

        except Exception as e:
            logger.error(f"Failed to verify reset token: {e}")
            return None

    async def reset_password(
        self,
        token: str,
        new_password: str,
        confirm_password: str
    ) -> bool:
        """
        Reset user password using a valid token.

        Args:
            token: Valid reset token
            new_password: New password
            confirm_password: Confirmation of new password

        Returns:
            bool: True if password was reset successfully
        """
        try:
            # Validate passwords match
            if new_password != confirm_password:
                logger.warning("Password reset attempt with mismatched passwords")
                return False

            # Validate password complexity
            password_errors = security_manager.validate_password_complexity(new_password)
            if password_errors:
                logger.warning(f"Password reset attempt with weak password: {password_errors}")
                return False

            # Verify token
            token_info = await self.verify_reset_token(token)
            if not token_info:
                logger.warning(f"Password reset attempt with invalid token")
                return False

            # Get the reset token record
            result = await self.session.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.token == token
                )
            )
            reset_token = result.scalar_one_or_none()

            if not reset_token:
                return False

            # Get user
            user_result = await self.session.execute(
                select(User).where(
                    and_(
                        User.id == token_info["user_id"],
                        User.tenant_id == token_info["tenant_id"],
                        User.is_active == True
                    )
                )
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return False

            # Update user password
            user.hashed_password = security_manager.hash_password(new_password)

            # Mark token as used
            reset_token.mark_as_used()

            # Invalidate all other reset tokens for this user
            await self._invalidate_existing_tokens(user.id, user.tenant_id, exclude_token_id=reset_token.id)

            await self.session.commit()

            logger.info(f"Password reset successful for user {user.email} in tenant {user.tenant_id}")

            # TODO: Send password reset confirmation email
            await self._send_password_reset_confirmation_email(user)

            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to reset password: {e}")
            return False

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired password reset tokens.

        Returns:
            int: Number of tokens cleaned up
        """
        try:
            now = datetime.now(timezone.utc)

            # Delete expired tokens
            result = await self.session.execute(
                delete(PasswordResetToken).where(
                    or_(
                        PasswordResetToken.expires_at < now,
                        PasswordResetToken.is_used == True
                    )
                )
            )

            deleted_count = result.rowcount
            await self.session.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired password reset tokens")

            return deleted_count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0

    async def _invalidate_existing_tokens(
        self,
        user_id: str,
        tenant_id: str,
        exclude_token_id: Optional[str] = None
    ) -> None:
        """Invalidate existing reset tokens for a user."""
        try:
            conditions = [
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.tenant_id == tenant_id,
                PasswordResetToken.is_used == False
            ]

            if exclude_token_id:
                conditions.append(PasswordResetToken.id != exclude_token_id)

            # Mark existing tokens as used
            result = await self.session.execute(
                select(PasswordResetToken).where(and_(*conditions))
            )
            existing_tokens = result.scalars().all()

            for token in existing_tokens:
                token.mark_as_used()

            if existing_tokens:
                logger.info(f"Invalidated {len(existing_tokens)} existing reset tokens for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to invalidate existing tokens: {e}")
            raise

    async def _send_password_reset_email(self, user: User, token: str) -> None:
        """
        Send password reset email to user using the tenant's SMTP configuration.
        """
        try:
            from app.features.core.email_service import get_email_service

            # Get email service for the user's tenant
            email_service = await get_email_service(self.session, user.tenant_id)

            # Send password reset email
            result = await email_service.send_password_reset_email(
                user_email=user.email,
                user_name=user.first_name or user.email.split('@')[0],
                reset_token=token
            )

            if result.success:
                logger.info(f"Password reset email sent successfully to {user.email} in tenant {user.tenant_id}")
            else:
                logger.error(f"Failed to send password reset email to {user.email}: {result.message}")
                # Continue execution - don't fail the reset request due to email issues

        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {e}")
            # Continue execution - don't fail the reset request due to email issues

    async def _send_password_reset_confirmation_email(self, user: User) -> None:
        """
        Send password reset confirmation email to user using the tenant's SMTP configuration.
        """
        try:
            from app.features.core.email_service import get_email_service

            # Get email service for the user's tenant
            email_service = await get_email_service(self.session, user.tenant_id)

            # Send confirmation email using generic email method since no specific template exists
            result = await email_service.send_email(
                to_emails=user.email,
                subject="Password Reset Successful",
                html_body=f"""
                <html>
                    <body>
                        <h2>Password Reset Confirmation</h2>
                        <p>Hello {user.first_name or user.email.split('@')[0]},</p>
                        <p>Your password has been successfully reset.</p>
                        <p>If you did not request this password reset, please contact support immediately.</p>
                        <p>For security reasons, we recommend:</p>
                        <ul>
                            <li>Using a strong, unique password</li>
                            <li>Enabling two-factor authentication if available</li>
                            <li>Logging out of all devices and logging back in</li>
                        </ul>
                        <hr>
                        <p><small>This is an automated message from {user.tenant_id}. Please do not reply to this email.</small></p>
                    </body>
                </html>
                """,
                text_body=f"""
Password Reset Confirmation

Hello {user.first_name or user.email.split('@')[0]},

Your password has been successfully reset.

If you did not request this password reset, please contact support immediately.

For security reasons, we recommend:
- Using a strong, unique password
- Enabling two-factor authentication if available
- Logging out of all devices and logging back in

This is an automated message from {user.tenant_id}. Please do not reply to this email.
                """
            )

            if result.success:
                logger.info(f"Password reset confirmation email sent successfully to {user.email} in tenant {user.tenant_id}")
            else:
                logger.error(f"Failed to send password reset confirmation email to {user.email}: {result.message}")

        except Exception as e:
            logger.error(f"Error sending password reset confirmation email to {user.email}: {e}")
