#!/usr/bin/env python3
"""
Direct test script to trigger a compliance scan and verify results.
This bypasses the HTTP layer and directly tests the service/task layer.
"""

import asyncio
import sys
import time
from datetime import datetime

# Add app to path
sys.path.insert(0, '/home/paul/repos/terra-automation-platform')

from app.features.core.database import get_async_session
from app.features.msp.cspm.services import CSPMScanService, M365TenantService, PowerShellExecutorService
from sqlalchemy import func
from sqlalchemy import select as sql_select
from sqlalchemy.ext.asyncio import AsyncSession


async def main():
    print("=" * 80)
    print("COMPLIANCE SCAN TEST")
    print("=" * 80)
    print()

    # Configuration
    m365_tenant_id = "27f6aa28-3f13-4ca5-af1c-db82a1fcc7e8"
    tenant_id = "9"  # Must match the M365 tenant's tenant_id

    session_maker = get_async_session()
    async with session_maker() as db:
        # Step 1: Verify M365 tenant exists
        print(f"[1/6] Verifying M365 tenant {m365_tenant_id}...")
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
        print("[2/6] Creating scan record...")
        scan_service = CSPMScanService(db, tenant_id)

        from app.features.msp.cspm.schemas import ComplianceScanRequest
        scan_request = ComplianceScanRequest(
            m365_tenant_id=m365_tenant_id,
            tech_type="M365",
            l1_only=True
        )

        scan = await scan_service.create_scan(
            scan_request,
            celery_task_id="direct-test",
            created_by_user=None
        )
        await db.commit()

        scan_id = scan.scan_id
        print(f"✅ Created scan record: {scan_id}")
        print()

        # Step 3: Execute scan directly via PowerShell executor
        print(f"[3/6] Executing PowerShell scan for scan_id={scan_id}...")
        print("This will take 2-3 minutes...")
        print()

        start_time = time.time()

        # Update scan status to running
        await scan_service.update_scan_status(scan_id, "running")
        await db.commit()

        # Retrieve M365 credentials
        auth_params = await m365_service.get_tenant_credentials(m365_tenant_id)

        # Execute PowerShell script directly
        ps_executor = PowerShellExecutorService()
        result = await ps_executor.execute_start_checks(
            auth_params=auth_params,
            scan_id=scan_id,
            progress_callback_url=None,
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

        # Step 4: Check result
        print("[4/6] Checking scan result...")
        print(f"Status: {result.get('status')}")
        print(f"Checks Executed: {result.get('checks_executed', 0)}")
        print(f"Results Count: {result.get('results_count', 0)}")

        if result.get('error'):
            print(f"❌ Error: {result['error']}")
            return False

        if result.get('status') != 'completed':
            print(f"❌ Scan did not complete successfully")
            return False

        print()

        # Step 5: Query database for results
        print("[5/6] Querying database for results...")

        from app.features.msp.cspm.models import ComplianceResult
        result_count_query = sql_select(func.count()).select_from(ComplianceResult).where(
            ComplianceResult.scan_id == scan_id
        )
        result_count_result = await db.execute(result_count_query)
        db_result_count = result_count_result.scalar()

        print(f"📊 Results in database: {db_result_count}")

        if db_result_count == 0:
            print("❌ No results found in database!")
            return False

        # Get breakdown by status
        status_query = sql_select(
            ComplianceResult.status,
            func.count(ComplianceResult.id).label('count')
        ).where(
            ComplianceResult.scan_id == scan_id
        ).group_by(ComplianceResult.status)

        status_result = await db.execute(status_query)
        status_breakdown = dict(status_result.all())

        print()
        print("Result breakdown:")
        for status, count in status_breakdown.items():
            print(f"  {status}: {count}")
        print()

        # Step 6: Verify expected count
        print("[6/6] Verifying result count...")
        expected_count = result.get('checks_executed', 0)

        if db_result_count == expected_count:
            print(f"✅ SUCCESS! All {expected_count} results inserted into database!")
            print()
            print("=" * 80)
            print("TEST PASSED")
            print("=" * 80)
            return True
        else:
            print(f"⚠️  MISMATCH: Expected {expected_count} results, found {db_result_count} in database")
            print()
            print("=" * 80)
            print("TEST FAILED - Result count mismatch")
            print("=" * 80)
            return False


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
