"""
CSPM Compliance Scan Routes

API endpoints for starting, monitoring, and retrieving compliance scans.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError as KombuOperationalError
import redis.exceptions

from app.features.core.route_imports import *
from app.features.core.config import get_settings
from app.features.msp.cspm.schemas import (
    ComplianceScanRequest,
    ComplianceScanResponse,
    ScanStatusResponse,
    ComplianceResultResponse,
    SuccessResponse
)
from app.features.msp.cspm.services import CSPMScanService, M365TenantService, async_scan_runtime
from app.features.msp.cspm.services.websocket_manager import websocket_manager
from app.features.msp.cspm.tasks import run_cspm_compliance_scan
from app.features.core.audit_mixin import AuditContext

logger = get_logger(__name__)

router = APIRouter(prefix="/scans", tags=["cspm-scans"])

settings = get_settings()

BROKER_EXCEPTIONS = (
    CeleryError,
    KombuOperationalError,
    redis.exceptions.ConnectionError,
    TimeoutError,
)


async def _prepare_scan_context(
    scan_request: ComplianceScanRequest,
    db: AsyncSession,
    tenant_id: str,
    current_user: User,
) -> Tuple[M365TenantService, Any, str, Dict[str, Any]]:
    """
    Validate scan inputs and resolve tenant context.

    Returns:
        (m365_service, m365_tenant, target_tenant_id, scan_options)
    """
    m365_service = M365TenantService(db, tenant_id)

    # For testing: Allow scans without M365 tenant (uses hardcoded creds in PowerShell)
    if scan_request.m365_tenant_id:
        m365_tenant = await m365_service.get_m365_tenant(scan_request.m365_tenant_id)
        if not m365_tenant:
            raise HTTPException(
                status_code=404,
                detail=f"M365 tenant {scan_request.m365_tenant_id} not found",
            )

        try:
            credentials_info = await m365_service.get_tenant_credentials_info(
                scan_request.m365_tenant_id
            )
            has_auth = (
                credentials_info.has_client_secret
                or credentials_info.has_certificate
                or credentials_info.has_username_password
            )
            if not has_auth:
                raise ValueError("No authentication credentials configured")
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"M365 tenant credentials incomplete: {str(exc)}",
            ) from exc
    else:
        # No M365 tenant - create a placeholder for scan record
        m365_tenant = None
        logger.warning("Running scan without M365 tenant - PowerShell will use hardcoded credentials")

    if m365_tenant:
        target_tenant_id = m365_tenant.tenant_id or (
            None if tenant_id == "global" else tenant_id
        )
        if not target_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Unable to resolve tenant for scan execution",
            )

        if not scan_request.tenant_benchmark_id:
            scan_request.tenant_benchmark_id = m365_tenant.tenant_benchmark_id
        if not scan_request.tech_type:
            scan_request.tech_type = m365_tenant.tech_type or "M365"
    else:
        # No M365 tenant - use current tenant
        target_tenant_id = None if tenant_id == "global" else tenant_id
        if not scan_request.tech_type:
            scan_request.tech_type = "M365"

    scan_options = {
        "l1_only": scan_request.l1_only,
        "check_ids": scan_request.check_ids or [],
        "output_format": scan_request.output_format,
    }

    logger.info(
        "Prepared scan context",
        scan_id=scan_request.m365_tenant_id,
        tenant_id=target_tenant_id,
        user=current_user.email,
    )

    return m365_service, m365_tenant, target_tenant_id, scan_options


@router.post("/start", response_model=ComplianceScanResponse)
async def start_compliance_scan(
    scan_request: ComplianceScanRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Start new M365 CIS compliance scan.

    This endpoint:
    1. Validates M365 tenant exists and has credentials
    2. Creates scan record in database
    3. Enqueues Celery task for background execution
    4. Returns scan ID for status polling

    Args:
        scan_request: Scan configuration (M365 tenant, L1/L2, filters)

    Returns:
        Created scan with pending status and Celery task ID
    """
    logger.info(
        "Starting compliance scan",
        m365_tenant_id=scan_request.m365_tenant_id,
        tenant_id=tenant_id
    )

    try:
        _m365_service, _m365_tenant, target_tenant_id, scan_options = await _prepare_scan_context(
            scan_request,
            db,
            tenant_id,
            current_user,
        )
        scan_service = CSPMScanService(db, target_tenant_id)

        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")

        # Create scan record (Celery task ID will be populated after enqueue)
        scan = await scan_service.create_scan(
            scan_request,
            celery_task_id="pending",
            created_by_user=current_user
        )

        await db.commit()

        progress_callback_url = f"{base_url}/msp/cspm/webhook/progress/{scan.scan_id}"

        try:
            real_task = run_cspm_compliance_scan.apply_async(
                args=[
                    scan.scan_id,
                    target_tenant_id,
                    scan_request.m365_tenant_id,
                    scan_options,
                    progress_callback_url
                ]
            )

            # Update scan with real task ID
            scan_update = await scan_service._get_scan_by_scan_id(scan.scan_id)
            scan_update.celery_task_id = real_task.id
            audit_ctx = AuditContext.from_user(current_user)
            scan_update.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            scan_update.updated_at = datetime.now()
            await db.commit()

            logger.info(
                "Compliance scan started",
                scan_id=scan.scan_id,
                celery_task_id=real_task.id,
                m365_tenant_id=scan_request.m365_tenant_id
            )

            scan.celery_task_id = real_task.id
            return scan

        except BROKER_EXCEPTIONS as broker_error:
            message = (
                "Unable to enqueue scan. Celery broker/back-end is unavailable. "
                "Ensure Redis and the Celery worker are running."
            )
            logger.error(
                "Celery broker unavailable",
                error=str(broker_error),
                scan_id=scan.scan_id,
                tenant_id=target_tenant_id,
                exc_info=True
            )

            await scan_service.update_scan_status(
                scan.scan_id,
                "failed",
                error_message=message
            )
            await db.commit()

            raise HTTPException(
                status_code=503,
                detail=message
            )

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error("Failed to start scan", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.post("/async", response_model=ComplianceScanResponse)
async def start_async_compliance_scan(
    scan_request: ComplianceScanRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Start a compliance scan using the in-process async runtime.

    This avoids the Celery/Redis dependency and is suitable for lightweight
    environments or local development.
    """
    logger.info(
        "Starting async compliance scan",
        m365_tenant_id=scan_request.m365_tenant_id,
        tenant_id=tenant_id,
    )

    try:
        _m365_service, _m365_tenant, target_tenant_id, scan_options = await _prepare_scan_context(
            scan_request,
            db,
            tenant_id,
            current_user,
        )

        scan_service = CSPMScanService(db, target_tenant_id)
        scan = await scan_service.create_scan(
            scan_request,
            celery_task_id=f"async-runtime-{scan_request.m365_tenant_id}",
            created_by_user=current_user,
        )
        await db.commit()

        try:
            await async_scan_runtime.start_scan(
                scan_id=scan.scan_id,
                tenant_id=target_tenant_id,
                m365_tenant_db_id=scan_request.m365_tenant_id,
                scan_options=scan_options,
            )
        except Exception as runtime_exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to start async runtime scan",
                scan_id=scan.scan_id,
                tenant_id=target_tenant_id,
                error=str(runtime_exc),
                exc_info=True,
            )
            await scan_service.update_scan_status(
                scan.scan_id,
                "failed",
                error_message="Async runtime could not start the scan",
            )
            await db.commit()
            raise HTTPException(
                status_code=503,
                detail="Unable to start scan runner. See logs for details.",
            ) from runtime_exc

        logger.info("Async scan started", scan_id=scan.scan_id, runtime="in-process")

        return scan

    except HTTPException:
        await db.rollback()
        raise

    except Exception as exc:
        await db.rollback()
        logger.error("Failed to start async scan", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(exc)}")


@router.get("/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get current scan status and progress.

    Use this endpoint to poll scan progress during execution.

    Args:
        scan_id: Scan UUID

    Returns:
        Current scan status with progress percentage and summary metrics
    """
    logger.debug("Getting scan status", scan_id=scan_id)

    try:
        scan_service = CSPMScanService(db, tenant_id)
        status = await scan_service.get_scan_status(scan_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

        return status

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to get scan status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get scan status")


@router.websocket("/ws/{scan_id}")
async def scan_progress_ws(
    websocket: WebSocket,
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    WebSocket endpoint for real-time scan progress updates.

    Connects client to WebSocketManager which receives broadcasts from
    webhook progress updates during Celery task execution.

    SECURITY: Requires authentication and validates scan belongs to user's tenant.
    """
    await websocket.accept()

    try:
        # Register connection with WebSocketManager
        await websocket_manager.connect(scan_id, websocket)

        logger.info(
            "WebSocket client connected",
            scan_id=scan_id,
            user=current_user.email,
            tenant_id=tenant_id
        )

        # Send initial scan status snapshot with tenant validation
        scan_service = CSPMScanService(db, tenant_id)
        try:
            # This will 404 if scan doesn't belong to user's tenant (tenant filtering)
            scan = await scan_service._get_scan_by_scan_id(scan_id)
            if scan:
                await websocket.send_json({
                    "event": "snapshot",
                    "scan_id": scan_id,
                    "status": scan.status,
                    "progress_percentage": scan.progress_percentage or 0,
                    "started_at": scan.started_at.isoformat() if scan.started_at else None,
                    "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                })
        except Exception as e:
            logger.warning("Failed to send initial snapshot", scan_id=scan_id, error=str(e))

        # Keep connection alive - messages will be sent via websocket_manager.broadcast()
        while True:
            # Wait for client messages (ping/pong for keepalive)
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.debug("Scan WebSocket disconnected", scan_id=scan_id)
    except Exception as exc:
        logger.error("WebSocket streaming error", scan_id=scan_id, error=str(exc), exc_info=True)
    finally:
        # Unregister connection
        await websocket_manager.disconnect(scan_id, websocket)


@router.get("/{scan_id}/results", response_model=List[ComplianceResultResponse])
async def get_scan_results(
    scan_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status (Pass, Fail, Error)"),
    category_filter: Optional[str] = Query(None, description="Filter by category (L1, L2)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get compliance check results for a specific scan.

    Args:
        scan_id: Scan UUID
        status_filter: Filter by Pass/Fail/Error (optional)
        category_filter: Filter by L1/L2 (optional)
        limit: Maximum results (default: 100, max: 1000)
        offset: Results offset for pagination

    Returns:
        List of compliance check results
    """
    logger.info(
        "Getting scan results",
        scan_id=scan_id,
        status=status_filter,
        category=category_filter
    )

    try:
        scan_service = CSPMScanService(db, tenant_id)

        results = await scan_service.get_scan_results(
            scan_id,
            status_filter=status_filter,
            category_filter=category_filter,
            limit=limit,
            offset=offset
        )

        return results

    except Exception as e:
        logger.error("Failed to get scan results", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get scan results")


@router.get("", response_model=List[ComplianceScanResponse])
async def list_scans(
    m365_tenant_id: Optional[str] = Query(None, description="Filter by M365 tenant"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    List compliance scans with optional filters.

    Args:
        m365_tenant_id: Filter by M365 tenant (optional)
        status: Filter by status (pending, running, completed, failed, cancelled)
        limit: Maximum results (default: 50, max: 200)
        offset: Results offset for pagination

    Returns:
        List of scans ordered by creation date (newest first)
    """
    logger.info(
        "Listing scans",
        m365_tenant_id=m365_tenant_id,
        status=status,
        tenant_id=tenant_id
    )

    try:
        scan_service = CSPMScanService(db, tenant_id)

        scans = await scan_service.list_scans(
            m365_tenant_id=m365_tenant_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return scans

    except Exception as e:
        logger.error("Failed to list scans", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list scans")


@router.get("/api/list", response_class=JSONResponse)
async def list_scans_api(
    m365_tenant_id: Optional[str] = Query(None, description="Filter by M365 tenant"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    List compliance scans (API endpoint for front-end tables).
    Returns a plain list for Tabulator consumption.
    """
    logger.info(
        "Listing scans (api)",
        m365_tenant_id=m365_tenant_id,
        status=status,
        tenant_id=tenant_id
    )

    try:
        scan_service = CSPMScanService(db, tenant_id)
        scans = await scan_service.list_scans(
            m365_tenant_id=m365_tenant_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return JSONResponse(
            [scan.model_dump(mode="json") for scan in scans]
        )

    except Exception as e:
        logger.error("Failed to list scans (api)", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list scans")


@router.delete("/{scan_id}/cancel", response_model=SuccessResponse)
async def cancel_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running scan.

    Only scans with status 'pending' or 'running' can be cancelled.

    Args:
        scan_id: Scan UUID

    Returns:
        Success confirmation
    """
    logger.info("Cancelling scan", scan_id=scan_id)

    try:
        scan_service = CSPMScanService(db, tenant_id)

        await scan_service.cancel_scan(scan_id)
        await db.commit()

        # TODO: Revoke Celery task if possible
        # This requires accessing the Celery app and calling task.revoke()

        logger.info("Scan cancelled successfully", scan_id=scan_id)

        return SuccessResponse(
            success=True,
            message=f"Scan {scan_id} cancelled successfully"
        )

    except ValueError as e:
        await db.rollback()
        logger.warning("Scan cancellation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        await db.rollback()
        logger.error("Failed to cancel scan", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel scan")
