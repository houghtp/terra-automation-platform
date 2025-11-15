"""
M365 Tenant Management Routes

CRUD operations for M365 tenant configuration and credentials.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.msp.cspm.schemas import (
    M365TenantCreate,
    M365TenantCreateRequest,
    M365TenantUpdate,
    M365TenantResponse,
    M365TenantCredentials,
    TestConnectionResponse,
    SuccessResponse
)
from app.features.msp.cspm.services import M365TenantService

logger = get_logger(__name__)

router = APIRouter(prefix="/m365-tenants", tags=["m365-tenants"])


@router.get("", response_model=List[M365TenantResponse])
async def list_m365_tenants(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    List all M365 tenants for current platform tenant (JSON API).
    """
    logger.info("Listing M365 tenants", tenant_id=tenant_id)

    try:
        service = M365TenantService(db, tenant_id)
        tenants = await service.list_m365_tenants()
        return tenants
    except Exception as e:
        logger.error("Failed to list M365 tenants", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list M365 tenants")


@router.get("/list", response_model=List[M365TenantResponse])
async def list_m365_tenants_alias(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    List all M365 tenants for current platform tenant.

    Returns:
        List of M365 tenant configurations
    """
    return await list_m365_tenants(db, tenant_id, current_user)


@router.post("", response_model=M365TenantResponse)
async def create_m365_tenant(
    tenant_request: M365TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Create new M365 tenant configuration with credentials.

    Args:
        tenant_data: M365 tenant creation data including credentials

    Returns:
        Created M365 tenant
    """
    logger.info(
        "Creating M365 tenant",
        m365_tenant_id=tenant_request.m365_tenant_id,
        tenant_id=tenant_id
    )

    try:
        service = M365TenantService(db, tenant_id)

        tenant_data = M365TenantCreate.model_validate(
            tenant_request.model_dump(exclude={"target_tenant_id"})
        )

        tenant = await service.create_m365_tenant(
            tenant_data,
            created_by_user=current_user,
            target_tenant_id=tenant_request.target_tenant_id
        )

        await db.commit()

        logger.info(
            "M365 tenant created successfully",
            m365_tenant_id=tenant.m365_tenant_id,
            id=tenant.id
        )

        return tenant

    except ValueError as e:
        await db.rollback()
        logger.warning("M365 tenant creation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        await db.rollback()
        logger.error("Failed to create M365 tenant", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create M365 tenant")


@router.get("/{m365_tenant_id}", response_model=M365TenantResponse)
async def get_m365_tenant(
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get M365 tenant by ID.

    Args:
        m365_tenant_id: M365 tenant database ID

    Returns:
        M365 tenant details
    """
    logger.info("Getting M365 tenant", m365_tenant_id=m365_tenant_id)

    try:
        service = M365TenantService(db, tenant_id)
        tenant = await service.get_m365_tenant(m365_tenant_id)

        if not tenant:
            raise HTTPException(status_code=404, detail="M365 tenant not found")

        return tenant

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get M365 tenant", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get M365 tenant")


@router.put("/{m365_tenant_id}", response_model=M365TenantResponse)
async def update_m365_tenant(
    m365_tenant_id: str,
    tenant_data: M365TenantUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Update M365 tenant configuration and optionally update credentials.

    Args:
        m365_tenant_id: M365 tenant database ID
        tenant_data: Update data

    Returns:
        Updated M365 tenant
    """
    logger.info("Updating M365 tenant", m365_tenant_id=m365_tenant_id)

    try:
        service = M365TenantService(db, tenant_id)

        tenant = await service.update_m365_tenant(
            m365_tenant_id,
            tenant_data,
            updated_by_user=current_user
        )

        await db.commit()

        logger.info("M365 tenant updated successfully", m365_tenant_id=m365_tenant_id)

        return tenant

    except ValueError as e:
        await db.rollback()
        logger.warning("M365 tenant update failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        await db.rollback()
        logger.error("Failed to update M365 tenant", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update M365 tenant")


@router.delete("/{m365_tenant_id}", response_model=SuccessResponse)
async def delete_m365_tenant(
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Delete M365 tenant and associated credentials.

    Args:
        m365_tenant_id: M365 tenant database ID

    Returns:
        Success confirmation
    """
    logger.info("Deleting M365 tenant", m365_tenant_id=m365_tenant_id)

    try:
        service = M365TenantService(db, tenant_id)
        await service.delete_m365_tenant(m365_tenant_id)
        await db.commit()

        logger.info("M365 tenant deleted successfully", m365_tenant_id=m365_tenant_id)

        return SuccessResponse(
            success=True,
            message=f"M365 tenant {m365_tenant_id} deleted successfully"
        )

    except ValueError as e:
        await db.rollback()
        logger.warning("M365 tenant deletion failed", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete M365 tenant", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete M365 tenant")


@router.get("/{m365_tenant_id}/credentials", response_model=M365TenantCredentials)
async def get_tenant_credentials_info(
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get information about configured credentials (without revealing secrets).

    Args:
        m365_tenant_id: M365 tenant database ID

    Returns:
        Credentials configuration info (masked)
    """
    logger.info("Getting credentials info", m365_tenant_id=m365_tenant_id)

    try:
        service = M365TenantService(db, tenant_id)
        credentials_info = await service.get_tenant_credentials_info(m365_tenant_id)

        return credentials_info

    except ValueError as e:
        logger.warning("Failed to get credentials info", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error("Failed to get credentials info", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get credentials info")


@router.post("/{m365_tenant_id}/test-connection", response_model=TestConnectionResponse)
async def test_m365_connection(
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Test M365 connection with stored credentials.

    This executes a PowerShell test to verify credentials work.

    Args:
        m365_tenant_id: M365 tenant database ID

    Returns:
        Connection test result
    """
    logger.info("Testing M365 connection", m365_tenant_id=m365_tenant_id)

    try:
        service = M365TenantService(db, tenant_id)
        test_result = await service.test_connection(m365_tenant_id)
        await db.commit()

        logger.info(
            "Connection test completed",
            m365_tenant_id=m365_tenant_id,
            success=test_result["success"]
        )

        return TestConnectionResponse(**test_result)

    except ValueError as e:
        await db.rollback()
        logger.warning("Connection test failed", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        await db.rollback()
        logger.error("Connection test failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {str(e)}"
        )
