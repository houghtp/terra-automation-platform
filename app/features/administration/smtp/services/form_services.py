"""
SMTP form services implementing FastAPI/SQLAlchemy best practices.
🏆 GOLD STANDARD form handling and validation patterns.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.features.administration.smtp.models import SMTPConfiguration, SMTPTestResult
from app.features.core.security import security_manager

logger = get_logger(__name__)


class SMTPFormService(BaseService[SMTPConfiguration]):
    """
    🏆 GOLD STANDARD SMTP form service implementation.

    Demonstrates:
    - Enhanced BaseService inheritance for forms
    - Type-safe query building
    - Proper error handling and logging
    - SMTP testing and validation methods
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def test_smtp_configuration(self, config_id: str, test_email: Optional[str] = None) -> SMTPTestResult:
        """
        Test SMTP configuration by attempting to connect and optionally send a test email.

        Args:
            config_id: ID of the SMTP configuration to test
            test_email: Optional email address to send test email to

        Returns:
            SMTPTestResult: Test results with success status and details
        """
        try:
            # Get configuration from database
            configuration = await self.get_by_id(SMTPConfiguration, config_id)
            if not configuration:
                return SMTPTestResult(
                    success=False,
                    message="SMTP configuration not found",
                    tested_at=datetime.now(timezone.utc).isoformat()
                )

            # Test the SMTP connection
            test_result = await self._test_smtp_connection(
                host=configuration.host,
                port=configuration.port,
                username=configuration.username,
                password=configuration.hashed_password,  # This is encrypted, will be decrypted in _test_smtp_connection
                use_tls=configuration.use_tls,
                use_ssl=configuration.use_ssl,
                from_email=configuration.from_email,
                test_email=test_email
            )

            # Update the configuration with test results
            configuration.last_tested_at = datetime.now(timezone.utc)
            configuration.test_status = "success" if test_result.success else "failed"
            configuration.error_message = None if test_result.success else test_result.message
            configuration.is_verified = test_result.success

            await self.db.flush()

            return test_result

        except Exception as e:
            logger.error(f"Failed to test SMTP configuration {config_id}: {e}")
            return SMTPTestResult(
                success=False,
                message=f"Test failed: {str(e)}",
                tested_at=datetime.now(timezone.utc).isoformat()
            )

    async def _test_smtp_connection(self, host: str, port: int, username: str, password: str,
                                  use_tls: bool, use_ssl: bool, from_email: str,
                                  test_email: Optional[str] = None) -> SMTPTestResult:
        """
        Test SMTP connection and optionally send test email.

        Args:
            host: SMTP server hostname
            port: SMTP server port
            username: SMTP username
            password: Encrypted password
            use_tls: Whether to use TLS
            use_ssl: Whether to use SSL
            from_email: From email address
            test_email: Optional test email recipient

        Returns:
            SMTPTestResult: Test results with connection details
        """
        try:
            # Decrypt the password
            try:
                decrypted_password = security_manager.decrypt_password(password)
            except Exception as e:
                return SMTPTestResult(
                    success=False,
                    message=f"Password decryption failed: {str(e)}",
                    tested_at=datetime.now(timezone.utc).isoformat()
                )

            # Create SMTP connection
            if use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, context=context)
            else:
                server = smtplib.SMTP(host, port)
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            # Authenticate
            server.login(username, decrypted_password)

            details = {
                "host": host,
                "port": port,
                "tls": use_tls,
                "ssl": use_ssl,
                "auth": True
            }

            # If test email provided, send a test message
            if test_email:
                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = test_email
                msg['Subject'] = "SMTP Configuration Test"

                body = "This is a test email to verify SMTP configuration."
                msg.attach(MIMEText(body, 'plain'))

                server.sendmail(from_email, test_email, msg.as_string())
                details["test_email_sent"] = True

            server.quit()

            return SMTPTestResult(
                success=True,
                message="SMTP connection successful" + (" and test email sent" if test_email else ""),
                details=details,
                tested_at=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            return SMTPTestResult(
                success=False,
                message=f"SMTP connection failed: {str(e)}",
                tested_at=datetime.now(timezone.utc).isoformat()
            )

    async def validate_smtp_configuration(self, config_data: dict) -> Dict[str, List[str]]:
        """
        Validate SMTP configuration data for forms.

        Args:
            config_data: Dictionary containing SMTP configuration fields

        Returns:
            Dictionary with field names as keys and list of error messages as values
        """
        errors = {}

        # Validate required fields
        required_fields = ['name', 'host', 'port', 'username', 'from_email']
        for field in required_fields:
            if not config_data.get(field):
                errors.setdefault(field, []).append(f"{field.replace('_', ' ').title()} is required")

        # Validate port is numeric and in valid range
        port = config_data.get('port')
        if port:
            try:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    errors.setdefault('port', []).append("Port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.setdefault('port', []).append("Port must be a valid number")

        # Validate email addresses
        from_email = config_data.get('from_email')
        if from_email and not self._is_valid_email(from_email):
            errors.setdefault('from_email', []).append("Invalid email address format")

        reply_to = config_data.get('reply_to')
        if reply_to and not self._is_valid_email(reply_to):
            errors.setdefault('reply_to', []).append("Invalid email address format")

        # Validate password confirmation
        password = config_data.get('password')
        confirm_password = config_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            errors.setdefault('confirm_password', []).append("Passwords do not match")

        return errors

    async def get_available_tenants_for_smtp_forms(self) -> List[Dict[str, Any]]:
        """
        Get active tenants for SMTP form dropdowns (global admin only).
        Uses enhanced BaseService query patterns.

        Returns:
            List of tenant dictionaries with id and name
        """
        try:
            from app.features.administration.tenants.db_models import Tenant

            stmt = select(
                Tenant.id,
                Tenant.name
            ).where(
                Tenant.status == 'active'
            ).order_by(Tenant.name)

            result = await self.db.execute(stmt)
            tenants = result.fetchall()

            tenant_list = [
                {"id": str(tenant.id), "name": tenant.name}
                for tenant in tenants
            ]

            logger.info(f"Retrieved {len(tenant_list)} active tenants for SMTP forms")
            return tenant_list

        except Exception as e:
            logger.error(f"Failed to get available tenants for SMTP forms: {e}")
            raise

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None