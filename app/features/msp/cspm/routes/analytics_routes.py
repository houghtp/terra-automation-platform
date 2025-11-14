"""
CSPM Analytics API Routes

Provides JSON endpoints for analytics data to be consumed by chart widgets.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional

from app.features.core.route_imports import *
from app.features.msp.cspm.services.analytics_service import CSPMAnalyticsService
from app.features.core.database import get_db
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user

router = APIRouter(prefix="/msp/cspm/analytics", tags=["CSPM Analytics"])
logger = get_logger(__name__)


@router.get("/overview")
async def get_scans_overview(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get overview statistics for scans dashboard.

    Query params:
        - days: Number of days to look back (default: 30)

    Returns:
        - total_scans: Total scan count
        - completed_scans: Completed scan count
        - failed_scans: Failed scan count
        - running_scans: Running/pending scan count
        - avg_pass_rate: Average pass rate across completed scans
        - latest_scan: Latest scan info
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_scans_overview(days=days)
        return data
    except Exception as e:
        logger.error("Failed to get scans overview", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve overview data")


@router.get("/compliance-trend")
async def get_compliance_trend(
    days: int = 30,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get compliance trend data over time (for line chart).

    Query params:
        - days: Number of days to look back (default: 30)
        - limit: Maximum data points (default: 10)

    Returns:
        Dict with categories and values for chart-widget
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_compliance_over_time(days=days, limit=limit)
        return data
    except Exception as e:
        logger.error("Failed to get compliance trend", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve trend data")


@router.get("/status-distribution")
async def get_status_distribution(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get scan status distribution (for donut chart).

    Returns:
        Dict with items array for chart-widget
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_scan_status_distribution()
        return data
    except Exception as e:
        logger.error("Failed to get status distribution", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve status data")


@router.get("/scan/{scan_id}/results-breakdown")
async def get_scan_results_breakdown(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get results breakdown for a specific scan (for donut chart).

    Returns:
        - passed, failed, errors counts
        - pass_percentage, fail_percentage, error_percentage
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_scan_results_breakdown(scan_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get results breakdown", error=str(e), scan_id=scan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve results data")


@router.get("/scan/{scan_id}/by-section")
async def get_compliance_by_section(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get pass rate by section for a specific scan (for bar chart).

    Returns:
        Dict with categories and values for chart-widget
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_compliance_by_section(scan_id)
        return data
    except Exception as e:
        logger.error("Failed to get compliance by section", error=str(e), scan_id=scan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve section data")


@router.get("/scan/{scan_id}/by-level")
async def get_level_distribution(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get results distribution by level (L1/L2) for donut chart.

    Returns:
        Dict with items array for chart-widget
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_level_distribution(scan_id)
        return data
    except Exception as e:
        logger.error("Failed to get level distribution", error=str(e), scan_id=scan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve level data")


@router.get("/scan/{scan_id}/top-failures")
async def get_top_failures(
    scan_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get top failed checks for a specific scan.

    Query params:
        - limit: Maximum failures to return (default: 10)

    Returns:
        List of failed check details
    """
    try:
        service = CSPMAnalyticsService(db, tenant_id)
        data = await service.get_top_failures(scan_id, limit=limit)
        return data
    except Exception as e:
        logger.error("Failed to get top failures", error=str(e), scan_id=scan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve failure data")
