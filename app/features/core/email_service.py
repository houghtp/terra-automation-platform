"""
Email service for sending emails using configured SMTP settings.
Provides a unified interface for sending emails with template support.
"""

import logging
import smtplib
import ssl
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.features.administration.smtp.models import SMTPConfiguration, SMTPStatus
from app.features.core.security import security_manager

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template data structure."""

    def __init__(self, subject: str, html_body: str, text_body: Optional[str] = None):
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body or self._html_to_text(html_body)

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (basic implementation)."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text


class EmailAttachment:
    """Email attachment data structure."""

    def __init__(self, filename: str, content: bytes, content_type: str = 'application/octet-stream'):
        self.filename = filename
        self.content = content
        self.content_type = content_type


class EmailResult:
    """Result of email sending operation."""

    def __init__(self, success: bool, message: str, message_id: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.message = message
        self.message_id = message_id
        self.error = error
        self.sent_at = datetime.utcnow()


class EmailService:
    """
    Email service that uses tenant SMTP configurations to send emails.
    Supports HTML/text templates, attachments, and bulk sending.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id
        self._template_env = None
        self._smtp_config = None

    async def get_active_smtp_config(self) -> Optional[SMTPConfiguration]:
        """Get the active SMTP configuration for the tenant."""
        if self._smtp_config:
            return self._smtp_config

        stmt = select(SMTPConfiguration).where(
            and_(
                SMTPConfiguration.tenant_id == self.tenant_id,
                SMTPConfiguration.is_active == True,
                SMTPConfiguration.enabled == True,
                SMTPConfiguration.status == SMTPStatus.ACTIVE
            )
        )
        result = await self.db.execute(stmt)
        self._smtp_config = result.scalar_one_or_none()

        if not self._smtp_config:
            logger.warning(f"No active SMTP configuration found for tenant {self.tenant_id}")

        return self._smtp_config

    def _get_template_env(self) -> Environment:
        """Get or create Jinja2 template environment."""
        if not self._template_env:
            template_dir = Path(__file__).parent / "templates" / "email"
            template_dir.mkdir(parents=True, exist_ok=True)

            self._template_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )

        return self._template_env

    async def send_email(
        self,
        to_emails: Union[str, List[str]],
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        priority: str = "normal"
    ) -> EmailResult:
        """
        Send an email using the tenant's active SMTP configuration.

        Args:
            to_emails: Recipient email address(es)
            subject: Email subject
            html_body: HTML email body (optional if using template)
            text_body: Plain text email body (optional)
            template_name: Name of email template to use
            template_data: Data to pass to template
            from_email: Override sender email
            from_name: Override sender name
            reply_to: Reply-to address
            attachments: List of email attachments
            priority: Email priority (high, normal, low)

        Returns:
            EmailResult with success status and details
        """
        try:
            # Get SMTP configuration
            smtp_config = await self.get_active_smtp_config()
            if not smtp_config:
                return EmailResult(
                    success=False,
                    message="No active SMTP configuration available",
                    error="SMTP_NOT_CONFIGURED"
                )

            # Prepare recipient list
            if isinstance(to_emails, str):
                to_emails = [to_emails]

            # Prepare email content
            if template_name and template_data:
                template = await self._render_template(template_name, template_data)
                subject = template.subject
                html_body = template.html_body
                text_body = template.text_body

            # Validate content
            if not html_body and not text_body:
                return EmailResult(
                    success=False,
                    message="No email content provided",
                    error="NO_CONTENT"
                )

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name or smtp_config.from_name} <{from_email or smtp_config.from_email}>"
            msg['To'] = ', '.join(to_emails)

            if reply_to:
                msg['Reply-To'] = reply_to
            elif smtp_config.reply_to:
                msg['Reply-To'] = smtp_config.reply_to

            # Set priority
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority == "low":
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'

            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)

            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment.filename}'
                    )
                    msg.attach(part)

            # Send email
            result = await self._send_via_smtp(smtp_config, msg, to_emails)

            # Log the result
            if result.success:
                logger.info(f"Email sent successfully to {len(to_emails)} recipients via {smtp_config.name}")
            else:
                logger.error(f"Failed to send email via {smtp_config.name}: {result.error}")

            return result

        except Exception as e:
            logger.exception(f"Email sending failed: {e}")
            return EmailResult(
                success=False,
                message=f"Email sending failed: {str(e)}",
                error="SEND_FAILED"
            )

    async def send_template_email(
        self,
        to_emails: Union[str, List[str]],
        template_name: str,
        template_data: Dict[str, Any],
        **kwargs
    ) -> EmailResult:
        """
        Send an email using a template.

        Args:
            to_emails: Recipient email address(es)
            template_name: Name of the email template
            template_data: Data to pass to the template
            **kwargs: Additional arguments passed to send_email

        Returns:
            EmailResult with success status and details
        """
        return await self.send_email(
            to_emails=to_emails,
            subject="",  # Will be set by template
            template_name=template_name,
            template_data=template_data,
            **kwargs
        )

    async def send_welcome_email(self, user_email: str, user_name: str, **kwargs) -> EmailResult:
        """Send welcome email to new user."""
        return await self.send_template_email(
            to_emails=user_email,
            template_name="welcome",
            template_data={
                "user_name": user_name,
                "user_email": user_email,
                "tenant_id": self.tenant_id,
                "login_url": f"{os.getenv('APP_BASE_URL', 'http://localhost:8000')}/auth/login"
            },
            **kwargs
        )

    async def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str,
        **kwargs
    ) -> EmailResult:
        """Send password reset email."""
        reset_url = f"{os.getenv('APP_BASE_URL', 'http://localhost:8000')}/auth/reset-password?token={reset_token}"

        return await self.send_template_email(
            to_emails=user_email,
            template_name="password_reset",
            template_data={
                "user_name": user_name,
                "user_email": user_email,
                "reset_url": reset_url,
                "reset_token": reset_token,
                "tenant_id": self.tenant_id
            },
            **kwargs
        )

    async def send_admin_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "info",
        admin_emails: Optional[List[str]] = None,
        **kwargs
    ) -> EmailResult:
        """Send alert email to administrators."""
        if not admin_emails:
            # Default to environment variable or fallback
            admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
            admin_emails = [email.strip() for email in admin_emails if email.strip()]

        if not admin_emails:
            return EmailResult(
                success=False,
                message="No admin emails configured",
                error="NO_ADMIN_EMAILS"
            )

        return await self.send_template_email(
            to_emails=admin_emails,
            template_name="admin_alert",
            template_data={
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "tenant_id": self.tenant_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            priority="high" if severity in ["error", "critical"] else "normal",
            **kwargs
        )

    async def _render_template(self, template_name: str, data: Dict[str, Any]) -> EmailTemplate:
        """Render email template with provided data."""
        try:
            env = self._get_template_env()

            # Try to load HTML template
            html_template_name = f"{template_name}.html"
            try:
                html_template = env.get_template(html_template_name)
                html_body = html_template.render(**data)
            except Exception:
                html_body = None

            # Try to load text template
            text_template_name = f"{template_name}.txt"
            try:
                text_template = env.get_template(text_template_name)
                text_body = text_template.render(**data)
            except Exception:
                text_body = None

            # Try to load subject template
            subject_template_name = f"{template_name}_subject.txt"
            try:
                subject_template = env.get_template(subject_template_name)
                subject = subject_template.render(**data).strip()
            except Exception:
                subject = data.get('subject', f"Notification from {self.tenant_id}")

            if not html_body and not text_body:
                # Fallback to basic template
                html_body = self._create_fallback_template(template_name, data)

            return EmailTemplate(subject=subject, html_body=html_body, text_body=text_body)

        except Exception as e:
            logger.error(f"Template rendering failed for {template_name}: {e}")
            # Return fallback template
            return EmailTemplate(
                subject=f"Notification from {self.tenant_id}",
                html_body=self._create_fallback_template(template_name, data)
            )

    def _create_fallback_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Create a basic fallback template when no template file exists."""
        return f"""
        <html>
            <body>
                <h2>{template_name.replace('_', ' ').title()}</h2>
                <p>This is an automated message from {self.tenant_id}.</p>
                <div>
                    {self._dict_to_html(data)}
                </div>
                <hr>
                <p><small>Generated at {datetime.utcnow().isoformat()}</small></p>
            </body>
        </html>
        """

    def _dict_to_html(self, data: Dict[str, Any]) -> str:
        """Convert dictionary data to HTML for fallback templates."""
        html_parts = []
        for key, value in data.items():
            if key not in ['tenant_id', 'timestamp']:
                html_parts.append(f"<p><strong>{key.replace('_', ' ').title()}:</strong> {value}</p>")
        return '\n'.join(html_parts)

    async def _send_via_smtp(
        self,
        smtp_config: SMTPConfiguration,
        message: MIMEMultipart,
        to_emails: List[str]
    ) -> EmailResult:
        """Send email via SMTP configuration."""
        try:
            # Decrypt password (in real implementation)
            # For now, we'll assume we have a way to decrypt the stored password
            password = self._decrypt_password(smtp_config.hashed_password)

            # Create SMTP connection
            if smtp_config.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context)
            else:
                server = smtplib.SMTP(smtp_config.host, smtp_config.port)
                if smtp_config.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            # Authenticate
            server.login(smtp_config.username, password)

            # Send message
            server.sendmail(smtp_config.from_email, to_emails, message.as_string())
            server.quit()

            return EmailResult(
                success=True,
                message=f"Email sent successfully to {len(to_emails)} recipients"
            )

        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            return EmailResult(
                success=False,
                message=f"SMTP sending failed: {str(e)}",
                error="SMTP_FAILED"
            )

    def _decrypt_password(self, hashed_password: str) -> str:
        """
        Decrypt the stored password using the security manager.

        Note: This assumes the password was encrypted, not hashed.
        For SMTP passwords, we need to decrypt them to use for authentication.
        """
        try:
            # Use the security manager to decrypt the password
            # This assumes we have an encryption method available
            return security_manager.decrypt_password(hashed_password)
        except Exception as e:
            logger.error(f"Failed to decrypt SMTP password: {e}")
            # For now, return a placeholder - this should be properly implemented
            # based on your security requirements
            return "password_decryption_failed"


async def get_email_service(db_session: AsyncSession, tenant_id: str) -> EmailService:
    """Factory function to create EmailService instance."""
    return EmailService(db_session, tenant_id)


# Convenience functions for common email operations
async def send_welcome_email_service(
    db_session: AsyncSession,
    tenant_id: str,
    user_email: str,
    user_name: str
) -> EmailResult:
    """Convenience function to send welcome email."""
    service = await get_email_service(db_session, tenant_id)
    return await service.send_welcome_email(user_email, user_name)


async def send_password_reset_email_service(
    db_session: AsyncSession,
    tenant_id: str,
    user_email: str,
    user_name: str,
    reset_token: str
) -> EmailResult:
    """Convenience function to send password reset email."""
    service = await get_email_service(db_session, tenant_id)
    return await service.send_password_reset_email(user_email, user_name, reset_token)


async def send_admin_alert_service(
    db_session: AsyncSession,
    tenant_id: str,
    alert_type: str,
    message: str,
    severity: str = "info"
) -> EmailResult:
    """Convenience function to send admin alert."""
    service = await get_email_service(db_session, tenant_id)
    return await service.send_admin_alert(alert_type, message, severity)
