"""
Async Scan Runtime

Provides an in-process runner for CSPM scans without relying on Celery.
Manages scan execution, status tracking, and progress notifications for
WebSocket subscribers.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, Optional, Set

import structlog

from app.features.core.database import get_async_session
from app.features.msp.cspm.services.cspm_scan_service import CSPMScanService
from app.features.msp.cspm.services.m365_tenant_service import M365TenantService
from app.features.msp.cspm.services.powershell_executor import PowerShellExecutorService

logger = structlog.get_logger(__name__)


class AsyncScanRuntime:
    """Coordinator for in-process CSPM scan execution."""

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._listeners: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def start_scan(
        self,
        *,
        scan_id: str,
        tenant_id: str,
        m365_tenant_db_id: str,
        scan_options: Dict[str, Any],
    ) -> None:
        """Launch scan execution for the given scan."""
        async with self._lock:
            if scan_id in self._tasks:
                logger.warning("Scan already running", scan_id=scan_id)
                return

            task = asyncio.create_task(
                self._run_scan(
                    scan_id=scan_id,
                    tenant_id=tenant_id,
                    m365_tenant_db_id=m365_tenant_db_id,
                    scan_options=scan_options,
                ),
                name=f"cspm-scan-{scan_id}",
            )
            self._tasks[scan_id] = task
            task.add_done_callback(lambda _: asyncio.create_task(self._cleanup(scan_id)))

    async def subscribe(self, scan_id: str) -> asyncio.Queue:
        """Register a listener queue for scan progress updates."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._listeners[scan_id].add(queue)
        return queue

    async def unsubscribe(self, scan_id: str, queue: asyncio.Queue) -> None:
        """Remove listener queue for scan updates."""
        async with self._lock:
            listeners = self._listeners.get(scan_id)
            if listeners and queue in listeners:
                listeners.remove(queue)
            if listeners and not listeners:
                self._listeners.pop(scan_id, None)

    async def _cleanup(self, scan_id: str) -> None:
        """Remove finished task from registry."""
        async with self._lock:
            self._tasks.pop(scan_id, None)

    async def _publish(self, scan_id: str, payload: Dict[str, Any]) -> None:
        """Send an update payload to all listeners for a scan."""
        async with self._lock:
            listeners = list(self._listeners.get(scan_id, []))

        if not listeners:
            return

        for queue in listeners:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Dropping progress update (queue full)", scan_id=scan_id)

    async def get_scan_snapshot(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest persisted scan status."""
        session_factory = get_async_session()
        async with session_factory() as db:
            scan_service = CSPMScanService(db, None)  # Global view
            status = await scan_service.get_scan_status(scan_id)
            return status.model_dump(mode="json") if status else None

    async def _run_scan(
        self,
        *,
        scan_id: str,
        tenant_id: str,
        m365_tenant_db_id: str,
        scan_options: Dict[str, Any],
    ) -> None:
        """Execute the scan and update status/results."""
        await self._publish(scan_id, {"event": "scan-started", "scan_id": scan_id})

        session_factory = get_async_session()
        async with session_factory() as db:
            scan_service = CSPMScanService(db, tenant_id)
            m365_service = M365TenantService(db, tenant_id)
            ps_executor = PowerShellExecutorService()

            try:
                await scan_service.update_scan_status(scan_id, "running")
                await db.commit()
                await self._publish(
                    scan_id,
                    {"event": "status", "status": "running", "scan_id": scan_id},
                )

                scan_record = await scan_service._get_scan_by_scan_id(scan_id)
                if not scan_record:
                    raise ValueError(f"Scan {scan_id} not found after status update")

                # STAGE 1 TEST: Force empty auth_params to use PowerShell hardcoded credentials
                # TODO: Remove this after testing - restore credential retrieval
                auth_params = {}  # TEMPORARY: Skip database credential lookup

                # ORIGINAL CODE (commented out for testing):
                # # For testing: If m365_tenant_db_id is None or empty, use empty auth_params
                # # This allows PowerShell to use hardcoded credentials in Start-Checks.ps1
                # if m365_tenant_db_id:
                #     auth_params = await m365_service.get_tenant_credentials(m365_tenant_db_id)
                # else:
                #     # Empty auth params - PowerShell will use hardcoded defaults
                #     auth_params = {}

                await self._publish(
                    scan_id,
                    {
                        "event": "credentials-resolved",
                        "scan_id": scan_id,
                        "m365_tenant": auth_params.get("TenantId"),
                    },
                )

                result = await ps_executor.execute_start_checks(
                    auth_params=auth_params,
                    scan_id=scan_id,
                    progress_callback_url=None,
                    tech=scan_record.tech_type or "M365",
                    output_format=scan_options.get("output_format", "json"),
                    check_ids=scan_options.get("check_ids"),
                    l1_only=scan_options.get("l1_only", False),
                    timeout=86400,  # 24 hours
                )

                await self._publish(
                    scan_id,
                    {
                        "event": "powershell-finished",
                        "scan_id": scan_id,
                        "status": result.get("status"),
                        "checks_executed": result.get("checks_executed", 0),
                    },
                )

                if result.get("status") != "Success":
                    error_msg = result.get("error", "PowerShell scan failed")
                    await scan_service.update_scan_status(
                        scan_id,
                        "failed",
                        error_message=error_msg,
                    )
                    await db.commit()
                    await self._publish(
                        scan_id,
                        {
                            "event": "status",
                            "status": "failed",
                            "scan_id": scan_id,
                            "error": error_msg,
                        },
                    )
                    return

                results_list = result.get("results", [])
                if results_list:
                    inserted_count = await scan_service.bulk_insert_results(
                        scan_id,
                        results_list,
                    )
                    await db.commit()
                    await self._publish(
                        scan_id,
                        {
                            "event": "results-inserted",
                            "scan_id": scan_id,
                            "count": inserted_count,
                        },
                    )
                else:
                    await self._publish(
                        scan_id,
                        {
                            "event": "results-inserted",
                            "scan_id": scan_id,
                            "count": 0,
                        },
                    )

                await scan_service.update_scan_status(scan_id, "completed")
                await db.commit()
                await self._publish(
                    scan_id,
                    {"event": "status", "status": "completed", "scan_id": scan_id},
                )

            except asyncio.TimeoutError:
                await scan_service.update_scan_status(
                    scan_id,
                    "failed",
                    error_message="Scan execution timed out",
                )
                await db.commit()
                await self._publish(
                    scan_id,
                    {
                        "event": "status",
                        "status": "failed",
                        "scan_id": scan_id,
                        "error": "Execution timeout",
                    },
                )

            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "Async scan execution failed",
                    scan_id=scan_id,
                    error=str(exc),
                    exc_info=True,
                )
                await scan_service.update_scan_status(
                    scan_id,
                    "failed",
                    error_message=str(exc),
                )
                await db.commit()
                await self._publish(
                    scan_id,
                    {
                        "event": "status",
                        "status": "failed",
                        "scan_id": scan_id,
                        "error": str(exc),
                    },
                )


# Singleton runtime instance
async_scan_runtime = AsyncScanRuntime()
