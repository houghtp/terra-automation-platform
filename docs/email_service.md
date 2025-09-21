# 📧 Email Service Documentation

The TerraAutomationPlatform includes a comprehensive email service that integrates with tenant-specific SMTP configurations to send emails.

## Overview

The email service provides:
- ✉️ **Template-based emails** with HTML and text versions
- 🔧 **SMTP configuration management** per tenant
- 🔐 **Secure password encryption** for SMTP credentials
- 📋 **Pre-built email templates** (welcome, password reset, admin alerts)
- 🔄 **Background task integration** with Celery
- 📊 **Email testing and validation**

## Components

### 1. Email Service (`app/features/core/email_service.py`)

The main email service class that handles:
- Loading active SMTP configurations per tenant
- Rendering email templates with Jinja2
- Sending emails via SMTP
- Managing attachments and email formatting

```python
from app.features.core.email_service import get_email_service

# Get email service for a tenant
async with get_async_session() as db:
    email_service = await get_email_service(db, "my-tenant")

    # Send welcome email
    result = await email_service.send_welcome_email(
        user_email="user@example.com",
        user_name="John Doe"
    )
```

### 2. SMTP Configuration (`app/features/administration/smtp/`)

Web interface and API for managing SMTP settings:
- Create/edit SMTP configurations per tenant
- Test SMTP connections and send test emails
- Secure password encryption/decryption
- Activate/deactivate configurations

### 3. Email Templates (`app/features/core/templates/email/`)

Pre-built Jinja2 templates:
- `welcome.html` / `welcome.txt` - Welcome emails for new users
- `password_reset.html` / `password_reset.txt` - Password reset emails
- `admin_alert.html` / `admin_alert.txt` - System alerts for administrators

### 4. Background Tasks (`app/features/tasks/email_tasks.py`)

Celery tasks for asynchronous email sending:
- `send_welcome_email` - Send welcome emails in background
- `send_password_reset_email` - Send password reset emails
- `send_admin_alert` - Send administrative alerts

## Usage Examples

### Basic Email Sending

```python
from app.features.core.email_service import get_email_service

async def send_notification(db: AsyncSession, tenant_id: str):
    email_service = await get_email_service(db, tenant_id)

    result = await email_service.send_email(
        to_emails="user@example.com",
        subject="Notification",
        html_body="<h1>Hello!</h1><p>This is a notification.</p>",
        text_body="Hello! This is a notification."
    )

    if result.success:
        print(f"Email sent: {result.message}")
    else:
        print(f"Email failed: {result.error}")
```

### Template-Based Emails

```python
# Send welcome email using template
result = await email_service.send_template_email(
    to_emails="newuser@example.com",
    template_name="welcome",
    template_data={
        "user_name": "Jane Doe",
        "user_email": "newuser@example.com",
        "login_url": "https://myapp.com/login"
    }
)
```

### Background Email Tasks

```python
from app.features.core.task_manager import send_welcome_email_async

# Queue welcome email for background processing
task_id = send_welcome_email_async(
    user_email="user@example.com",
    user_name="John Doe",
    tenant_id="my-tenant"
)
```

### Admin Alerts

```python
# Send admin alert
result = await email_service.send_admin_alert(
    alert_type="security",
    message="Suspicious login detected from new location",
    severity="warning"
)
```

## SMTP Configuration

### Setting up SMTP

1. Navigate to `/features/administration/smtp` in the web interface
2. Click "Add SMTP Configuration"
3. Fill in your SMTP details:
   - **Host**: SMTP server hostname (e.g., `smtp.gmail.com`)
   - **Port**: SMTP port (e.g., `587` for TLS, `465` for SSL)
   - **Username**: SMTP username/email
   - **Password**: SMTP password (encrypted automatically)
   - **From Email**: Default sender email address
   - **From Name**: Default sender name

### Popular SMTP Providers

**Gmail:**
```
Host: smtp.gmail.com
Port: 587
Use TLS: Yes
Use SSL: No
```

**SendGrid:**
```
Host: smtp.sendgrid.net
Port: 587
Username: apikey
Password: [Your SendGrid API Key]
```

**AWS SES:**
```
Host: email-smtp.[region].amazonaws.com
Port: 587
Username: [Your SMTP Username]
Password: [Your SMTP Password]
```

### Testing SMTP Configuration

Use the built-in test functionality:

```bash
# Test SMTP connection
curl -X POST http://localhost:8090/features/administration/smtp/{config_id}/test \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "test_email=test@example.com"

# Test email service
curl -X POST http://localhost:8090/features/administration/smtp/send-test-email \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "test_email=test@example.com&email_type=welcome"
```

## Security

### Password Encryption

SMTP passwords are encrypted using Fernet symmetric encryption:
- Passwords are encrypted before storage in the database
- Decrypted only when needed for SMTP authentication
- Encryption key managed via `ENCRYPTION_KEY` environment variable

### Environment Variables

Required for email functionality:

```bash
# Encryption key for SMTP passwords (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here

# Optional: Admin email addresses for alerts
ADMIN_EMAILS=admin@example.com,security@example.com

# Optional: Base URL for email links
APP_BASE_URL=https://myapp.com
```

## Email Templates

### Creating Custom Templates

1. Create template files in `app/features/core/templates/email/`:
   - `{template_name}.html` - HTML version
   - `{template_name}.txt` - Plain text version
   - `{template_name}_subject.txt` - Email subject

2. Use in code:
```python
result = await email_service.send_template_email(
    to_emails="user@example.com",
    template_name="your_template",
    template_data={
        "variable1": "value1",
        "variable2": "value2"
    }
)
```

### Template Variables

Common variables available in all templates:
- `tenant_id` - Current tenant identifier
- `user_name` - Recipient's name
- `user_email` - Recipient's email
- `timestamp` - Current timestamp

## API Endpoints

### SMTP Management

- `GET /features/administration/smtp` - SMTP configuration interface
- `POST /features/administration/smtp` - Create SMTP configuration
- `PUT /features/administration/smtp/{id}` - Update SMTP configuration
- `DELETE /features/administration/smtp/{id}` - Delete SMTP configuration
- `POST /features/administration/smtp/{id}/test` - Test SMTP connection
- `POST /features/administration/smtp/send-test-email` - Test email service

### Email Testing

Access the SMTP interface at: `http://localhost:8090/features/administration/smtp`

Test different email types:
- **Welcome Email** - Test new user welcome email
- **Password Reset** - Test password reset email
- **Admin Alert** - Test administrative alert email
- **Custom** - Send custom test email

## Troubleshooting

### Common Issues

**"No active SMTP configuration"**
- Ensure you have an SMTP configuration set to "Active" status
- Check that the configuration is enabled

**"Password decryption failed"**
- Verify `ENCRYPTION_KEY` environment variable is set
- Ensure the key matches what was used to encrypt passwords

**"SMTP authentication failed"**
- Verify SMTP credentials are correct
- Check if 2FA or app passwords are required (Gmail, etc.)
- Ensure correct host and port settings

**"Template not found"**
- Check template files exist in `app/features/core/templates/email/`
- Verify template name matches exactly (case-sensitive)

### Debugging

Enable detailed logging:

```python
import logging
logging.getLogger("app.features.core.email_service").setLevel(logging.DEBUG)
```

Check email service status:

```python
# Test email service directly
from app.features.core.email_service import get_email_service

async with get_async_session() as db:
    service = await get_email_service(db, "your-tenant")
    smtp_config = await service.get_active_smtp_config()
    print(f"Active SMTP: {smtp_config.name if smtp_config else 'None'}")
```

## Integration with Other Features

### User Registration

Automatically send welcome emails when users are created:

```python
# In user creation service
user = await create_user(...)
if user:
    # Queue welcome email
    send_welcome_email_async(
        user_email=user.email,
        user_name=user.name,
        tenant_id=user.tenant_id
    )
```

### Password Reset

Send reset emails with secure tokens:

```python
# Generate reset token
reset_token = generate_secure_token()

# Send reset email
result = await email_service.send_password_reset_email(
    user_email=user.email,
    user_name=user.name,
    reset_token=reset_token
)
```

### System Monitoring

Send alerts for critical system events:

```python
# In monitoring middleware
if critical_event:
    send_admin_alert_async(
        alert_type="security",
        message="Critical security event detected",
        severity="critical",
        tenant_id=tenant_id
    )
```

## Next Steps

1. **Set up SMTP configuration** for your tenant
2. **Configure environment variables** for encryption and admin emails
3. **Test email functionality** using the web interface
4. **Customize email templates** for your brand
5. **Integrate email sending** into your application workflows

The email service is designed to be production-ready with proper error handling, security, and scalability considerations.
