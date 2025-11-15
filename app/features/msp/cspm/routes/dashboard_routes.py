"""
CSPM Dashboard Routes

Main pages for CSPM M365 compliance scanning interface.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.msp.cspm.services import CSPMScanService, TenantBenchmarkService

logger = get_logger(__name__)

router = APIRouter(prefix="/msp/cspm", tags=["cspm-dashboard"])


@router.get("/m365-tenants", response_class=HTMLResponse)
async def m365_tenants_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    M365 Tenant Management page.

    Lists all M365 tenants for the current platform tenant.
    """
    logger.info("Rendering M365 tenants page", user=current_user.name)

    return templates.TemplateResponse(
        "cspm/m365_tenants.html",
        {
            "request": request,
            "user": current_user,
            "is_global_admin": is_global_admin(current_user)
        }
    )


@router.get("/tenant-benchmarks", response_class=HTMLResponse)
async def tenant_benchmarks_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Tenant Benchmark Management page.

    Allows tenants to view and manage benchmark assignments.
    """
    logger.info("Rendering tenant benchmarks page", user=current_user.name)

    return templates.TemplateResponse(
        "cspm/tenant_benchmarks.html",
        {
            "request": request,
            "user": current_user,
            "is_global_admin": is_global_admin(current_user)
        }
    )


@router.get("/scans", response_class=HTMLResponse)
async def scans_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Scan Management page.

    Start new scans and view scan history.
    """
    logger.info("Rendering scans page", user=current_user.name)

    return templates.TemplateResponse(
        "cspm/scans.html",
        {
            "request": request,
            "user": current_user,
            "is_global_admin": is_global_admin(current_user)
        }
    )


@router.get("/scans/{scan_id}", response_class=HTMLResponse)
async def scan_detail_page(
    request: Request,
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Scan detail page with results.

    Shows scan progress, summary, and detailed check results.
    """
    logger.info("Rendering scan detail page", scan_id=scan_id, user=current_user.name)

    scan_service = CSPMScanService(db, tenant_id)
    tenant_benchmark_service = TenantBenchmarkService(db, tenant_id)

    status = await scan_service.get_scan_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")

    assignment = None
    assignment_config = {}
    if status.tenant_benchmark_id:
        try:
            assignment = await tenant_benchmark_service.get_assignment(status.tenant_benchmark_id)
            assignment_config = assignment.config or {}
        except Exception as exc:  # pragma: no cover - best effort enrichment
            logger.warning(
                "Failed to load tenant benchmark assignment",
                scan_id=scan_id,
                assignment_id=status.tenant_benchmark_id,
                error=str(exc)
            )

    # Get results if scan is completed
    results = []
    if status.status == "completed":
        results = await scan_service.get_scan_results(scan_id, limit=1000)

    return templates.TemplateResponse(
        "cspm/scan_detail.html",
        {
            "request": request,
            "scan": status,
            "assignment": assignment,
            "target_config": assignment_config,
            "results": results,
            "user": current_user
        }
    )
