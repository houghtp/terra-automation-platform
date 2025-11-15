"""
CSPM Tenant Benchmark Routes

CRUD routes for managing benchmark assignments per tenant.
"""

from typing import List

from app.features.core.route_imports import *
from app.features.msp.cspm.schemas import (
    CSPMTenantBenchmarkCreate,
    CSPMTenantBenchmarkResponse,
    CSPMTenantBenchmarkUpdate,
    SuccessResponse,
)
from app.features.msp.cspm.services import TenantBenchmarkService

logger = get_logger(__name__)

router = APIRouter(prefix="/tenant-benchmarks/api", tags=["cspm-tenant-benchmarks"])


@router.get("", response_model=List[CSPMTenantBenchmarkResponse])
async def list_tenant_benchmarks(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """List benchmark assignments for the current tenant."""
    logger.info("Listing tenant benchmarks", tenant_id=tenant_id)
    service = TenantBenchmarkService(db, tenant_id)
    try:
        assignments = await service.list_assignments()
        return assignments
    except Exception as exc:
        logger.error("Failed to list tenant benchmarks", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tenant benchmarks")


@router.post("", response_model=CSPMTenantBenchmarkResponse)
async def create_tenant_benchmark(
    assignment_request: CSPMTenantBenchmarkCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """Create a new benchmark assignment."""
    logger.info("Creating tenant benchmark", benchmark_id=assignment_request.benchmark_id)

    if assignment_request.target_tenant_id and not is_global_admin(current_user):
        raise HTTPException(status_code=403, detail="Only global admins can target another tenant.")

    service = TenantBenchmarkService(db, tenant_id)

    try:
        assignment = await service.create_assignment(
            assignment_request,
            created_by_user=current_user,
            target_tenant_id=assignment_request.target_tenant_id,
        )
        await db.commit()
        return assignment
    except ValueError as exc:
        await db.rollback()
        logger.warning("Tenant benchmark creation failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to create tenant benchmark", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create tenant benchmark")


@router.get("/{assignment_id}", response_model=CSPMTenantBenchmarkResponse)
async def get_tenant_benchmark(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a benchmark assignment."""
    logger.info("Getting tenant benchmark", assignment_id=assignment_id)
    service = TenantBenchmarkService(db, tenant_id)
    try:
        assignment = await service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Benchmark assignment not found")
        return assignment
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get tenant benchmark", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get tenant benchmark")


@router.put("/{assignment_id}", response_model=CSPMTenantBenchmarkResponse)
async def update_tenant_benchmark(
    assignment_id: str,
    update_data: CSPMTenantBenchmarkUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """Update a benchmark assignment."""
    logger.info("Updating tenant benchmark", assignment_id=assignment_id)
    service = TenantBenchmarkService(db, tenant_id)
    try:
        assignment = await service.update_assignment(
            assignment_id,
            update_data,
            updated_by_user=current_user,
        )
        await db.commit()
        return assignment
    except ValueError as exc:
        await db.rollback()
        logger.warning("Tenant benchmark update failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to update tenant benchmark", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update tenant benchmark")


@router.delete("/{assignment_id}", response_model=SuccessResponse)
async def delete_tenant_benchmark(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """Delete or deactivate a benchmark assignment."""
    logger.info("Deleting tenant benchmark", assignment_id=assignment_id)
    service = TenantBenchmarkService(db, tenant_id)
    try:
        await service.delete_assignment(assignment_id, deleted_by_user=current_user)
        await db.commit()
        return SuccessResponse(success=True, message="Benchmark assignment removed.")
    except ValueError as exc:
        await db.rollback()
        logger.warning("Tenant benchmark deletion failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to delete tenant benchmark", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete tenant benchmark")
