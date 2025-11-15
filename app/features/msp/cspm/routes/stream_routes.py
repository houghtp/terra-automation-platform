"""
CSPM SSE Streaming Routes

Server-Sent Events (SSE) endpoint for real-time scan progress updates.
"""

import asyncio
import json
from typing import AsyncIterator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.msp.cspm.services import CSPMScanService

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["cspm-stream"])


async def scan_progress_generator(
    scan_id: str,
    db_session: AsyncSession,
    tenant_id: str,
    poll_interval: int = 2
) -> AsyncIterator[str]:
    """
    Generate SSE events for scan progress.

    Polls database every `poll_interval` seconds for scan updates.

    Args:
        scan_id: Scan UUID
        db_session: Database session
        tenant_id: Platform tenant ID
        poll_interval: Polling interval in seconds

    Yields:
        SSE formatted progress events
    """
    logger.info("Starting SSE stream", scan_id=scan_id)

    scan_service = CSPMScanService(db_session, tenant_id)
    last_progress = -1
    terminal_statuses = {"completed", "failed", "cancelled"}

    try:
        while True:
            # Get current scan status
            status = await scan_service.get_scan_status(scan_id)

            if not status:
                logger.warning("Scan not found during streaming", scan_id=scan_id)
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': 'Scan not found'})}\n\n"
                break

            # Only send update if progress changed or status is terminal
            if status.progress_percentage != last_progress or status.status in terminal_statuses:
                event_data = {
                    "scan_id": status.scan_id,
                    "status": status.status,
                    "progress_percentage": status.progress_percentage,
                    "current_check": status.current_check,
                    "total_checks": status.total_checks,
                    "passed": status.passed,
                    "failed": status.failed,
                    "errors": status.errors,
                    "started_at": status.started_at.isoformat() if status.started_at else None,
                    "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                    "error_message": status.error_message
                }

                yield f"event: progress\n"
                yield f"data: {json.dumps(event_data, default=str)}\n\n"

                last_progress = status.progress_percentage

                logger.debug(
                    "SSE progress event sent",
                    scan_id=scan_id,
                    progress=status.progress_percentage,
                    status=status.status
                )

            # If scan is in terminal state, send completion event and stop
            if status.status in terminal_statuses:
                logger.info(
                    "Scan reached terminal state, ending stream",
                    scan_id=scan_id,
                    status=status.status
                )

                yield f"event: complete\n"
                yield f"data: {json.dumps({'status': status.status, 'scan_id': scan_id})}\n\n"
                break

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled", scan_id=scan_id)
        yield f"event: cancelled\n"
        yield f"data: {json.dumps({'message': 'Stream cancelled'})}\n\n"

    except Exception as e:
        logger.error("SSE stream error", scan_id=scan_id, error=str(e), exc_info=True)
        yield f"event: error\n"
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

    finally:
        logger.info("SSE stream ended", scan_id=scan_id)


@router.get("/{scan_id}")
async def stream_scan_progress(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Stream real-time scan progress via Server-Sent Events (SSE).

    Connect to this endpoint from the browser using EventSource:

    ```javascript
    const eventSource = new EventSource('/msp/cspm/stream/{scan_id}');

    eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        console.log('Progress:', data.progress_percentage + '%');
        updateProgressBar(data.progress_percentage);
    });

    eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        console.log('Scan completed:', data.status);
        eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
        console.error('Stream error:', event.data);
        eventSource.close();
    });
    ```

    Args:
        scan_id: Scan UUID

    Returns:
        SSE stream with progress updates
    """
    logger.info("SSE stream requested", scan_id=scan_id, user_id=current_user.id)

    try:
        # Verify scan exists and belongs to tenant
        scan_service = CSPMScanService(db, tenant_id)
        status = await scan_service.get_scan_status(scan_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

        # Return SSE streaming response
        return StreamingResponse(
            scan_progress_generator(scan_id, db, tenant_id, poll_interval=2),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to start SSE stream", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start progress stream")
