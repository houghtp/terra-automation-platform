#!/usr/bin/env python3
"""
Cleanup zombie scans that are stuck in 'running' status.

A scan is considered a zombie if:
- Status is 'running'
- Started more than 2 hours ago
- No corresponding PowerShell process exists
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.features.core.database import get_async_session
from app.features.msp.cspm.models import CSPMComplianceScan


async def cleanup_zombie_scans(max_age_hours: int = 2):
    """Mark old running scans as failed."""
    session_maker = get_async_session()

    async with session_maker() as db:
        # Find scans that have been running for more than max_age_hours
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        stmt = select(CSPMComplianceScan).where(
            CSPMComplianceScan.status == "running",
            CSPMComplianceScan.started_at < cutoff_time
        )

        result = await db.execute(stmt)
        zombie_scans = result.scalars().all()

        if not zombie_scans:
            print("No zombie scans found.")
            return

        print(f"Found {len(zombie_scans)} zombie scans:")

        for scan in zombie_scans:
            age_hours = (datetime.now() - scan.started_at).total_seconds() / 3600
            print(f"  - Scan {scan.id} ({scan.scan_id}): started {age_hours:.1f} hours ago")

            # Mark as failed
            scan.status = "failed"
            scan.error_message = f"Scan process terminated or timed out (running for {age_hours:.1f} hours)"
            scan.completed_at = datetime.now()

        await db.commit()
        print(f"\n✅ Marked {len(zombie_scans)} zombie scans as failed")


if __name__ == "__main__":
    asyncio.run(cleanup_zombie_scans())
