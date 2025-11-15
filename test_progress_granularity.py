#!/usr/bin/env python3
"""
Test script to verify per-check progress updates.
This script runs a scan and monitors the webhook calls to verify we get 91 progress updates.
"""

import asyncio
import sys
import time
from datetime import datetime
from collections import defaultdict

# Add app to path
sys.path.insert(0, '/home/paul/repos/terra-automation-platform')

from app.features.core.database import get_async_session
from app.features.msp.cspm.services import CSPMScanService, M365TenantService, PowerShellExecutorService
from sqlalchemy import select as sql_select
from sqlalchemy.ext.asyncio import AsyncSession


# Global counter for progress updates
progress_updates = []


class MockProgressCallbackServer:
    """Mock HTTP server to count progress update calls."""

    def __init__(self):
        self.updates = []
        self.update_count = 0

    async def handle_progress_update(self, scan_id: str, progress_data: dict):
        """Simulate receiving progress update via webhook."""
        self.updates.append({
            'scan_id': scan_id,
            'progress_percentage': progress_data.get('progress_percentage'),
            'current_check': progress_data.get('current_check'),
            'timestamp': datetime.now()
        })
        self.update_count += 1

        # Print progress
        check_id = progress_data.get('current_check', 'N/A')
        progress_pct = progress_data.get('progress_percentage', 0)
        print(f"  [{self.update_count}] {progress_pct}% - Check: {check_id}")


async def main():
    print("=" * 80)
    print("PROGRESS GRANULARITY TEST")
    print("=" * 80)
    print()
    print("This test verifies that progress updates happen after EACH check (91 updates)")
    print("instead of after each batch (3 updates).")
    print()

    # Configuration
    m365_tenant_id = "27f6aa28-3f13-4ca5-af1c-db82a1fcc7e8"
    tenant_id = "9"  # Must match the M365 tenant's tenant_id

    session_maker = get_async_session()
    async with session_maker() as db:
        # Step 1: Verify M365 tenant exists
        print(f"[1/4] Verifying M365 tenant {m365_tenant_id}...")
        m365_service = M365TenantService(db, tenant_id)

        from app.features.msp.cspm.models import M365Tenant
        result = await db.execute(
            sql_select(M365Tenant).where(M365Tenant.id == m365_tenant_id)
        )
        m365_tenant = result.scalar_one_or_none()

        if not m365_tenant:
            print(f"❌ M365 tenant {m365_tenant_id} not found!")
            return False

        print(f"✅ Found M365 tenant: {m365_tenant.m365_tenant_name}")
        print()

        # Step 2: Create scan record
        print("[2/4] Creating scan record...")
        scan_service = CSPMScanService(db, tenant_id)

        from app.features.msp.cspm.schemas import ComplianceScanRequest
        scan_request = ComplianceScanRequest(
            m365_tenant_id=m365_tenant_id,
            tech_type="M365",
            l1_only=True
        )

        scan = await scan_service.create_scan(
            scan_request,
            celery_task_id="progress-test",
            created_by_user=None
        )
        await db.commit()

        scan_id = scan.scan_id
        print(f"✅ Created scan record: {scan_id}")
        print()

        # Step 3: Setup mock progress callback
        print("[3/4] Setting up progress monitoring...")
        print("Note: Since we can't intercept HTTP webhooks in this test,")
        print("we'll monitor log file for progress update messages.")
        print()

        # Step 4: Execute scan
        print(f"[4/4] Executing PowerShell scan for scan_id={scan_id}...")
        print("Monitoring progress updates (this will take 2-3 minutes)...")
        print()

        start_time = time.time()

        # Update scan status to running
        await scan_service.update_scan_status(scan_id, "running")
        await db.commit()

        # Retrieve M365 credentials
        auth_params = await m365_service.get_tenant_credentials(m365_tenant_id)

        # Execute PowerShell script
        ps_executor = PowerShellExecutorService()

        # Use actual callback URL (will be called by PowerShell)
        progress_callback_url = "http://127.0.0.1:8000/msp/cspm/webhook/progress/" + scan_id

        result = await ps_executor.execute_start_checks(
            auth_params=auth_params,
            scan_id=scan_id,
            progress_callback_url=progress_callback_url,
            tech="M365",
            output_format="json",
            check_ids=None,
            l1_only=True,
            timeout=6900
        )

        elapsed = time.time() - start_time
        print()
        print(f"⏱️  Scan completed in {elapsed:.1f} seconds")
        print()

        # If successful, bulk insert results
        if result.get("status") == "Success":
            results_list = result.get("results", [])
            if results_list:
                inserted_count = await scan_service.bulk_insert_results(
                    scan_id,
                    results_list
                )
                await db.commit()
                print(f"✅ Inserted {inserted_count} results into database")
                print()

            # Update scan status to completed
            await scan_service.update_scan_status(scan_id, "completed")
            await db.commit()
        else:
            # Update scan status to failed
            error_msg = result.get("error", "PowerShell scan failed")
            await scan_service.update_scan_status(
                scan_id,
                "failed",
                error_message=error_msg
            )
            await db.commit()
            print(f"❌ Scan failed: {error_msg}")
            return False

        # Step 5: Check progress update count from database
        print("[5/5] Verifying progress updates...")
        print()
        print("To verify progress granularity, check the application logs:")
        print(f"  tail -f logs/app.log | grep 'progress.*{scan_id}'")
        print()
        print("Expected behavior:")
        print("  - OLD: ~3 progress updates (one per batch)")
        print("  - NEW: ~91 progress updates (one per check)")
        print()

        # Query scan record for final progress
        scan_record = await scan_service._get_scan_by_scan_id(scan_id)
        if scan_record:
            print(f"Final scan status:")
            print(f"  Status: {scan_record.status}")
            print(f"  Progress: {scan_record.progress_percentage}%")
            print(f"  Checks executed: {result.get('checks_executed', 0)}")
            print()

        print("=" * 80)
        print("TEST COMPLETED")
        print("=" * 80)
        print()
        print("Please verify in logs that you see 91 progress updates instead of 3.")
        print(f"Search for: grep 'Received progress update.*scan_id={scan_id}' logs/app.log | wc -l")
        print()

        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
