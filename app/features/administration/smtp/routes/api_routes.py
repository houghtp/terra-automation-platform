# Gold Standard Route Imports - SMTP API
from app.features.core.route_imports import (
    # Core FastAPI components
    APIRouter, Depends,
    # Database and dependencies
    AsyncSession, get_db,
    # Tenant and auth
    tenant_dependency, get_current_user, User,
    # Request/Response types
    Request,
    # Response types
    JSONResponse,
    # Logging and error handling
    get_logger, handle_route_error,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Form handling
    FormHandler
)

logger = get_logger(__name__)

router = APIRouter(tags=["smtp-api"])

# --- EXTERNAL API ROUTES ---

@router.post("/send-test-email")
async def send_test_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Send a test email using the email service."""
    try:
        from app.features.core.email_service import get_email_service

        # Parse form data
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        test_email = form_handler.form_data.get("test_email")
        email_type = form_handler.form_data.get("email_type", "welcome")

        if not test_email:
            return JSONResponse({
                "success": False,
                "message": "Test email address is required"
            }, status_code=400)

        # Get email service
        email_service = await get_email_service(db, tenant)

        # Send test email based on type
        if email_type == "welcome":
            result = await email_service.send_welcome_email(
                user_email=test_email,
                user_name="Test User"
            )
        elif email_type == "password_reset":
            result = await email_service.send_password_reset_email(
                user_email=test_email,
                user_name="Test User",
                reset_token="test-token-123"
            )
        elif email_type == "admin_alert":
            result = await email_service.send_admin_alert(
                alert_type="system",
                message="This is a test admin alert email",
                severity="info",
                admin_emails=[test_email]
            )
        else:
            # Custom email
            result = await email_service.send_email(
                to_emails=test_email,
                subject=f"Test Email from {tenant}",
                html_body=f"""
                <h2>Test Email</h2>
                <p>This is a test email sent from the {tenant} email service.</p>
                <p>If you received this email, the email service is working correctly!</p>
                """,
                text_body=f"Test email from {tenant}. If you received this, the email service is working!"
            )

        if result.success:
            return JSONResponse({
                "success": True,
                "message": result.message,
                "sent_at": result.sent_at.isoformat()
            })
        else:
            return JSONResponse({
                "success": False,
                "message": result.message,
                "error": result.error
            }, status_code=400)

    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Test email failed: {str(e)}"
        }, status_code=500)