# Gold Standard Route Imports - SMTP Dashboard
from app.features.core.route_imports import (
    # Core FastAPI components
    APIRouter, Depends,
    # Database and dependencies
    AsyncSession, get_db,
    # Tenant and auth
    tenant_dependency, get_current_user, User,
    # Request/Response types
    Request, HTTPException,
    # Response types
    JSONResponse,
    # Logging and error handling
    get_logger, handle_route_error,
    # Transaction and response utilities
    commit_transaction, create_success_response,
    # Form handling
    FormHandler
)

from app.features.administration.smtp.services import SMTPConfigurationService

logger = get_logger(__name__)

router = APIRouter(tags=["smtp-dashboard"])

# --- SMTP DASHBOARD ACTION ROUTES ---

@router.post("/{config_id}/activate")
async def activate_smtp_configuration(config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Activate SMTP configuration."""
    service = SMTPConfigurationService(db, tenant)
    config = await service.activate_smtp_configuration(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    await db.commit()
    return {"success": True, "message": f"SMTP configuration '{config.name}' activated"}

@router.post("/{config_id}/deactivate")
async def deactivate_smtp_configuration(config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Deactivate SMTP configuration."""
    service = SMTPConfigurationService(db, tenant)
    config = await service.deactivate_smtp_configuration(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    await db.commit()
    return {"success": True, "message": f"SMTP configuration '{config.name}' deactivated"}

@router.post("/{config_id}/test")
async def test_smtp_configuration(request: Request, config_id: str, db: AsyncSession = Depends(get_db), tenant: str = Depends(tenant_dependency), current_user: User = Depends(get_current_user)):
    """Test SMTP configuration."""
    try:
        # Parse form data for test email
        form_handler = FormHandler(request)
        await form_handler.parse_form()

        test_email = form_handler.form_data.get("test_email")

        service = SMTPConfigurationService(db, tenant)
        test_result = await service.test_smtp_configuration(config_id, test_email)

        await db.commit()  # Save test results

        if test_result.success:
            return JSONResponse({
                "success": True,
                "message": test_result.message,
                "details": test_result.details
            })
        else:
            return JSONResponse({
                "success": False,
                "message": test_result.message
            }, status_code=400)

    except Exception as e:
        logger.error(f"Failed to test SMTP configuration: {e}")
        return JSONResponse({
            "success": False,
            "message": f"Test failed: {str(e)}"
        }, status_code=500)