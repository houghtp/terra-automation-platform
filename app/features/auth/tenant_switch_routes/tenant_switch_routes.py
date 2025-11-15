"""
API routes for tenant switching (global admin only).
"""

from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.features.core.database import get_async_session
from app.features.auth.tenant_switching.tenant_switch_service import TenantSwitchService
from app.features.auth.dependencies import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth/tenant-switch", tags=["tenant-switching"])


class TenantInfo(BaseModel):
    """Tenant information for switching."""
    id: str
    name: str
    is_active: bool


class SwitchTenantRequest(BaseModel):
    """Request to switch tenant."""
    tenant_id: str


class SwitchTenantResponse(BaseModel):
    """Response after switching tenant."""
    success: bool
    tenant_id: str
    message: str


@router.get("/available-tenants", response_model=List[TenantInfo])
async def get_available_tenants(
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get list of available tenants for switching.
    Only accessible to global admins.
    """
    # Verify global admin
    if current_user.role != 'global_admin':
        raise HTTPException(
            status_code=403,
            detail="Only global admins can access tenant list"
        )

    # Import here to avoid circular dependency
    from app.features.administration.tenants.services import TenantManagementService

    service = TenantManagementService(db)
    tenants = await service.list_tenants()

    return [
        TenantInfo(
            id=str(tenant.id),
            name=tenant.name,
            is_active=(tenant.status == "active")
        )
        for tenant in tenants
    ]


@router.post("/switch", response_model=SwitchTenantResponse)
async def switch_tenant(
    request: Request,
    switch_request: SwitchTenantRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Switch to a specific tenant context.
    Only accessible to global admins.
    """
    # Verify global admin
    if current_user.role != 'global_admin':
        raise HTTPException(
            status_code=403,
            detail="Only global admins can switch tenants"
        )

    # Validate tenant exists
    from app.features.administration.tenants.services import TenantManagementService

    service = TenantManagementService(db)
    tenant = await service.get_tenant_by_id(switch_request.tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant {switch_request.tenant_id} not found"
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Tenant {tenant.name} is not active"
        )

    # Switch tenant
    TenantSwitchService.set_switched_tenant(request, switch_request.tenant_id)

    logger.info(
        "Tenant switched successfully",
        user_email=current_user.email,
        tenant_id=switch_request.tenant_id,
        tenant_name=tenant.name
    )

    return SwitchTenantResponse(
        success=True,
        tenant_id=switch_request.tenant_id,
        message=f"Switched to tenant: {tenant.name}"
    )


@router.post("/clear")
async def clear_tenant_switch(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Clear tenant switch and return to global admin context.
    Only accessible to global admins.
    """
    # Verify global admin
    if current_user.role != 'global_admin':
        raise HTTPException(
            status_code=403,
            detail="Only global admins can clear tenant switch"
        )

    # Check if tenant is switched
    if not TenantSwitchService.is_tenant_switched(request):
        return {
            "success": True,
            "message": "No tenant switch to clear"
        }

    # Clear switch
    TenantSwitchService.clear_switched_tenant(request)

    logger.info(
        "Tenant switch cleared",
        user_email=current_user.email
    )

    return {
        "success": True,
        "message": "Returned to global admin context"
    }


@router.get("/current")
async def get_current_switched_tenant(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Get the currently switched tenant (if any).
    Only accessible to global admins.
    """
    # Verify global admin
    if current_user.role != 'global_admin':
        raise HTTPException(
            status_code=403,
            detail="Only global admins can check tenant switch status"
        )

    switched_tenant = TenantSwitchService.get_switched_tenant(request)

    return {
        "is_switched": switched_tenant is not None,
        "tenant_id": switched_tenant
    }
