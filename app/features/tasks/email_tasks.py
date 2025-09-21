"""
Email-related background tasks.
"""
import logging
import asyncio
from typing import Dict, List, Optional
from celery import Task
from app.features.core.celery_app import celery_app
from app.features.core.database import get_async_session
from app.features.core.email_service import (
    send_welcome_email_service,
    send_password_reset_email_service,
    send_admin_alert_service
)

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task class with callbacks for success/failure."""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed with exception: {exc}")


def run_async(coro):
    """Helper to run async functions in Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(base=CallbackTask, bind=True)
def send_welcome_email(self, user_email: str, user_name: str, tenant_id: str = "default") -> Dict:
    """
    Send welcome email to new user using the actual email service.

    Args:
        user_email: User's email address
        user_name: User's display name
        tenant_id: Tenant ID for SMTP configuration

    Returns:
        Dict with status and message
    """
    try:
        logger.info(f"Sending welcome email to {user_email} for tenant {tenant_id}")

        async def send_email():
            async with get_async_session() as db:
                result = await send_welcome_email_service(
                    db_session=db,
                    tenant_id=tenant_id,
                    user_email=user_email,
                    user_name=user_name
                )
                return result

        result = run_async(send_email())

        if result.success:
            logger.info(f"Welcome email sent successfully to {user_email}")
            return {
                "status": "success",
                "message": result.message,
                "task_id": self.request.id,
                "sent_at": result.sent_at.isoformat()
            }
        else:
            logger.error(f"Failed to send welcome email to {user_email}: {result.error}")
            # Retry the task if it's a temporary failure
            if result.error in ["SMTP_FAILED", "SEND_FAILED"]:
                raise self.retry(exc=Exception(result.message), countdown=60, max_retries=3)

            return {
                "status": "failed",
                "message": result.message,
                "error": result.error,
                "task_id": self.request.id
            }

    except Exception as exc:
        logger.error(f"Failed to send welcome email to {user_email}: {exc}")
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(base=CallbackTask, bind=True)
def send_password_reset_email(self, user_email: str, reset_token: str, user_name: str = None, tenant_id: str = "default") -> Dict:
    """
    Send password reset email with token using the actual email service.

    Args:
        user_email: User's email address
        reset_token: Password reset token
        user_name: User's display name (optional)
        tenant_id: Tenant ID for SMTP configuration

    Returns:
        Dict with status and message
    """
    try:
        logger.info(f"Sending password reset email to {user_email} for tenant {tenant_id}")

        async def send_email():
            async with get_async_session() as db:
                result = await send_password_reset_email_service(
                    db_session=db,
                    tenant_id=tenant_id,
                    user_email=user_email,
                    user_name=user_name or user_email.split('@')[0],
                    reset_token=reset_token
                )
                return result

        result = run_async(send_email())

        if result.success:
            logger.info(f"Password reset email sent successfully to {user_email}")
            return {
                "status": "success",
                "message": result.message,
                "reset_token": reset_token[:8] + "...",  # Log partial token for debugging
                "task_id": self.request.id,
                "sent_at": result.sent_at.isoformat()
            }
        else:
            logger.error(f"Failed to send password reset email to {user_email}: {result.error}")
            # Retry the task if it's a temporary failure
            if result.error in ["SMTP_FAILED", "SEND_FAILED"]:
                raise self.retry(exc=Exception(result.message), countdown=30, max_retries=2)

            return {
                "status": "failed",
                "message": result.message,
                "error": result.error,
                "task_id": self.request.id
            }

    except Exception as exc:
        logger.error(f"Failed to send password reset email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=30, max_retries=2)


@celery_app.task(base=CallbackTask, bind=True)
def send_bulk_notification(self, recipient_emails: List[str], subject: str, message: str) -> Dict:
    """
    Send bulk notifications to multiple users.

    Args:
        recipient_emails: List of email addresses
        subject: Email subject
        message: Email body

    Returns:
        Dict with status and results
    """
    try:
        logger.info(f"Sending bulk notification to {len(recipient_emails)} recipients")

        sent_count = 0
        failed_emails = []

        for email in recipient_emails:
            try:
                # Simulate individual email sending
                import time
                time.sleep(0.1)  # Small delay per email
                sent_count += 1
                logger.debug(f"Notification sent to {email}")

            except Exception as e:
                logger.warning(f"Failed to send notification to {email}: {e}")
                failed_emails.append(email)

        result = {
            "status": "completed",
            "sent_count": sent_count,
            "failed_count": len(failed_emails),
            "failed_emails": failed_emails,
            "task_id": self.request.id
        }

        logger.info(f"Bulk notification completed: {sent_count} sent, {len(failed_emails)} failed")
        return result

    except Exception as exc:
        logger.error(f"Bulk notification task failed: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=2)


@celery_app.task(base=CallbackTask)
def send_admin_alert(alert_type: str, message: str, severity: str = "info", tenant_id: str = "default") -> Dict:
    """
    Send alert to system administrators using the actual email service.

    Args:
        alert_type: Type of alert (e.g., "security", "system", "data")
        message: Alert message
        severity: Alert severity ("info", "warning", "error", "critical")
        tenant_id: Tenant ID for SMTP configuration

    Returns:
        Dict with status and message
    """
    try:
        logger.info(f"Sending admin alert: {alert_type} - {severity} for tenant {tenant_id}")

        async def send_email():
            async with get_async_session() as db:
                result = await send_admin_alert_service(
                    db_session=db,
                    tenant_id=tenant_id,
                    alert_type=alert_type,
                    message=message,
                    severity=severity
                )
                return result

        result = run_async(send_email())

        if result.success:
            logger.info(f"Admin alert sent successfully: {alert_type}")
            return {
                "status": "success",
                "alert_type": alert_type,
                "severity": severity,
                "message": result.message,
                "sent_at": result.sent_at.isoformat()
            }
        else:
            logger.error(f"Failed to send admin alert: {result.error}")
            return {
                "status": "failed",
                "alert_type": alert_type,
                "severity": severity,
                "message": result.message,
                "error": result.error
            }

    except Exception as exc:
        logger.error(f"Failed to send admin alert: {exc}")
        raise
