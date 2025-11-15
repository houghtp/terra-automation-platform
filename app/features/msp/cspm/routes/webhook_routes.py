"""
CSPM Webhook Routes

Receives progress updates from PowerShell scripts during scan execution.

SECURITY NOTE: This endpoint receives updates from PowerShell scripts which cannot
send JWT authentication. We validate the scan_id exists before processing to prevent
malicious updates. For production environments, consider implementing webhook tokens
or IP whitelisting for additional security.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.msp.cspm.schemas import ScanProgressUpdate
from app.features.msp.cspm.services import CSPMScanService
from app.features.msp.cspm.services.websocket_manager import websocket_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["cspm-webhook"])


@router.post("/progress/{scan_id}")
async def receive_progress_update(
    scan_id: str,
    progress_update: ScanProgressUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive progress updates from PowerShell script.

    This endpoint is called by Start-Checks.ps1 via ProgressCallbackUrl parameter.

    SECURITY: No JWT authentication (PowerShell can't send auth tokens).
    We validate scan_id exists before processing to prevent malicious updates.

    Args:
        scan_id: Scan UUID to update
        progress_update: Progress data from PowerShell

    Returns:
        Success confirmation

    Raises:
        HTTPException 404: If scan_id not found (prevents malicious updates)
        HTTPException 500: If update fails
    """
    logger.info(
        "Received webhook progress update",
        scan_id=scan_id,
        progress=progress_update.progress_percentage
    )

    try:
        # Initialize service without tenant filtering for webhook access
        # The scan_id UUID provides implicit security (hard to guess)
        scan_service = CSPMScanService(db, tenant_id=None)

        # SECURITY: Verify scan exists before accepting update
        # This prevents malicious actors from creating fake progress updates
        scan = await scan_service._get_scan_by_scan_id(scan_id)
        if not scan:
            logger.warning(
                "Webhook received update for non-existent scan - potential malicious activity",
                scan_id=scan_id,
                source_ip=None  # Could add request.client.host for IP logging
            )
            raise HTTPException(
                status_code=404,
                detail=f"Scan {scan_id} not found"
            )

        # Update scan progress (now that we've validated it exists)
        await scan_service.update_scan_progress(scan_id, progress_update)
        await db.commit()

        logger.debug(
            "Progress updated successfully",
            scan_id=scan_id,
            progress=progress_update.progress_percentage,
            current_check=progress_update.current_check
        )

        # Broadcast to connected WebSocket clients for live UI updates
        broadcast_payload = {
            "event": "status",  # Changed from "progress" to match JS handler
            "scan_id": scan_id,
            "progress_percentage": progress_update.progress_percentage,
            "current_check": progress_update.current_check,
            "status": progress_update.status if progress_update.status else "running"
        }

        logger.info(
            "Broadcasting progress to WebSocket",
            scan_id=scan_id,
            payload=broadcast_payload,
            active_connections=len(websocket_manager._connections.get(scan_id, []))
        )

        await websocket_manager.broadcast(scan_id, broadcast_payload)

        return {
            "status": "success",
            "scan_id": scan_id,
            "progress_percentage": progress_update.progress_percentage
        }

    except ValueError as e:
        logger.warning("Scan not found for progress update", scan_id=scan_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    except Exception as e:
        logger.error(
            "Failed to update scan progress",
            scan_id=scan_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update progress: {str(e)}"
        )
