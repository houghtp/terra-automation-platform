"""
CSPM Compliance Scanning Background Tasks

Celery tasks for executing PowerShell compliance scans asynchronously.
"""

import structlog
import asyncio
from typing import Dict, List, Optional, Any
from celery import Task

from app.features.core.celery_app import celery_app
from app.features.core.database import get_async_session
from app.features.msp.cspm.services import (
    PowerShellExecutorService,
    M365TenantService,
    CSPMScanService
)
from app.features.msp.cspm.services.websocket_manager import websocket_manager

logger = structlog.get_logger(__name__)


class CallbackTask(Task):
    """Base task class with callbacks for success/failure."""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed with exception: {exc}")


def run_async(coro):
    """Helper to run async functions in Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(base=CallbackTask, bind=True, time_limit=7200, soft_time_limit=7000)
def run_cspm_compliance_scan(
    self,
    scan_id: str,
    tenant_id: str,
    m365_tenant_db_id: str,
    scan_options: Dict[str, Any],
    progress_callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute M365 CIS compliance scan via PowerShell.

    This task:
    1. Retrieves M365 credentials from secrets
    2. Executes Start-Checks.ps1 PowerShell script
    3. Parses results from output JSON
    4. Bulk inserts results into database
    5. Updates scan status

    Args:
        scan_id: Unique scan identifier
        tenant_id: Platform tenant ID
        m365_tenant_db_id: M365 tenant database record ID
        scan_options: Scan configuration (l1_only, check_ids, output_format)
        progress_callback_url: URL for progress webhooks

    Returns:
        Dict with scan results summary

    Time Limits:
        - Hard limit: 7200 seconds (2 hours)
        - Soft limit: 7000 seconds (triggers cleanup before hard limit)
    """
    logger.info(
        "Starting CSPM compliance scan task",
        scan_id=scan_id,
        tenant_id=tenant_id,
        m365_tenant_id=m365_tenant_db_id,
        task_id=self.request.id
    )

    async def execute_scan():
        """Async function to execute the scan."""
        session_maker = get_async_session()
        async with session_maker() as db:
            scan_service = CSPMScanService(db, tenant_id)
            m365_service = M365TenantService(db, tenant_id)
            ps_executor = PowerShellExecutorService()

            try:
                # Update scan status to running
                await scan_service.update_scan_status(scan_id, "running")
                await db.commit()

                logger.info("Scan status updated to running", scan_id=scan_id)

                # Broadcast scan started to WebSocket clients
                await websocket_manager.broadcast(
                    scan_id,
                    {
                        "event": "status",  # Changed from "status_change" to match JS handler
                        "scan_id": scan_id,
                        "status": "running",
                        "progress_percentage": 0,
                        "current_check": None
                    }
                )

                scan_record = await scan_service._get_scan_by_scan_id(scan_id)
                if not scan_record:
                    raise ValueError(f"Scan {scan_id} not found after status update")

                # Retrieve M365 credentials
                auth_params = await m365_service.get_tenant_credentials(m365_tenant_db_id)

                logger.info(
                    "M365 credentials retrieved",
                    scan_id=scan_id,
                    m365_tenant_id=auth_params.get("TenantId")
                )

                # Execute PowerShell script
                result = await ps_executor.execute_start_checks(
                    auth_params=auth_params,
                    scan_id=scan_id,
                    progress_callback_url=progress_callback_url,
                    tech=scan_record.tech_type or "M365",
                    output_format=scan_options.get("output_format", "json"),
                    check_ids=scan_options.get("check_ids"),
                    l1_only=scan_options.get("l1_only", False),
                    timeout=6900  # Leave 100 seconds buffer before soft limit
                )

                logger.info(
                    "PowerShell scan completed",
                    scan_id=scan_id,
                    status=result.get("status"),
                    checks_executed=result.get("checks_executed", 0)
                )

                # Check if scan was successful
                if result.get("status") != "Success":
                    error_msg = result.get("error", "PowerShell scan failed")
                    await scan_service.update_scan_status(
                        scan_id,
                        "failed",
                        error_message=error_msg
                    )
                    await db.commit()

                    # Broadcast scan failed to WebSocket clients
                    await websocket_manager.broadcast(
                        scan_id,
                        {
                            "event": "status",  # Changed from "status_change" to match JS handler
                            "scan_id": scan_id,
                            "status": "failed",
                            "current_check": None,  # Clear check name on failure
                            "error": error_msg
                        }
                    )

                    return {
                        "scan_id": scan_id,
                        "status": "failed",
                        "error": error_msg,
                        "checks_executed": 0
                    }

                # Bulk insert results
                results_list = result.get("results", [])
                if results_list:
                    inserted_count = await scan_service.bulk_insert_results(
                        scan_id,
                        results_list
                    )
                    await db.commit()

                    logger.info(
                        "Results inserted",
                        scan_id=scan_id,
                        count=inserted_count
                    )
                else:
                    logger.warning("No results to insert", scan_id=scan_id)

                # Update scan status to completed
                await scan_service.update_scan_status(scan_id, "completed")
                await db.commit()

                logger.info("Scan completed successfully", scan_id=scan_id)

                # Get updated scan record with all fields
                scan_record = await scan_service._get_scan_by_scan_id(scan_id)

                # Broadcast scan completed to WebSocket clients with full data
                await websocket_manager.broadcast(
                    scan_id,
                    {
                        "event": "status",
                        "scan_id": scan_id,
                        "status": "completed",
                        "progress_percentage": 100,
                        "current_check": None,
                        "total_checks": scan_record.total_checks if scan_record else None,
                        "passed": scan_record.passed if scan_record else None,
                        "failed": scan_record.failed if scan_record else None,
                        "errors": scan_record.errors if scan_record else None,
                        "started_at": scan_record.started_at.isoformat() if scan_record and scan_record.started_at else None,
                        "completed_at": scan_record.completed_at.isoformat() if scan_record and scan_record.completed_at else None
                    }
                )

                return {
                    "scan_id": scan_id,
                    "status": "completed",
                    "checks_executed": result.get("checks_executed", 0),
                    "results_count": len(results_list),
                    "output_path": result.get("output_path")
                }

            except asyncio.TimeoutError:
                logger.error("Scan execution timeout", scan_id=scan_id)
                await scan_service.update_scan_status(
                    scan_id,
                    "failed",
                    error_message="Scan execution timed out"
                )
                await db.commit()

                return {
                    "scan_id": scan_id,
                    "status": "failed",
                    "error": "Execution timeout"
                }

            except Exception as e:
                logger.error(
                    "Scan execution failed",
                    scan_id=scan_id,
                    error=str(e),
                    exc_info=True
                )

                try:
                    await scan_service.update_scan_status(
                        scan_id,
                        "failed",
                        error_message=str(e)
                    )
                    await db.commit()
                except Exception as db_error:
                    logger.error(
                        "Failed to update scan status after error",
                        scan_id=scan_id,
                        db_error=str(db_error)
                    )

                return {
                    "scan_id": scan_id,
                    "status": "failed",
                    "error": str(e)
                }

    # Execute async function
    try:
        return run_async(execute_scan())
    except Exception as e:
        logger.error(
            "Task execution failed",
            scan_id=scan_id,
            error=str(e),
            exc_info=True
        )
        return {
            "scan_id": scan_id,
            "status": "failed",
            "error": f"Task execution failed: {str(e)}"
        }


@celery_app.task(base=CallbackTask)
def test_powershell_environment() -> Dict[str, Any]:
    """
    Test PowerShell environment and module availability.

    Returns:
        Dict with test results
    """
    logger.info("Testing PowerShell environment")

    async def test_env():
        ps_executor = PowerShellExecutorService()
        return await ps_executor.test_powershell_environment()

    return run_async(test_env())


@celery_app.task(base=CallbackTask)
def test_m365_connection(
    tenant_id: str,
    m365_tenant_db_id: str
) -> Dict[str, Any]:
    """
    Test M365 connection for a specific tenant.

    Args:
        tenant_id: Platform tenant ID
        m365_tenant_db_id: M365 tenant database record ID

    Returns:
        Dict with connection test results
    """
    logger.info("Testing M365 connection", m365_tenant_id=m365_tenant_db_id)

    async def test_connection():
        async with get_async_session() as db:
            m365_service = M365TenantService(db, tenant_id)
            return await m365_service.test_connection(m365_tenant_db_id)

    return run_async(test_connection())
