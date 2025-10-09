#!/usr/bin/env python3
"""Debug script to check logs table and service behavior."""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.features.core.database import async_session
from app.features.administration.logs.services import LogService
from app.features.administration.logs.models import ApplicationLog


async def main():
    """Debug the logs table and service behavior."""
    print("🔍 Debugging logs table and service...")

    async with async_session() as db:
        try:
            # Check total logs in table
            result = await db.execute(select(func.count(ApplicationLog.id)))
            total_logs = result.scalar()
            print(f"📊 Total logs in application_logs table: {total_logs}")

            if total_logs == 0:
                print("❌ No logs found in table!")
                return

            # Check tenant distribution
            result = await db.execute(
                select(ApplicationLog.tenant_id, func.count(ApplicationLog.id))
                .group_by(ApplicationLog.tenant_id)
            )
            tenant_counts = result.fetchall()
            print(f"🏢 Logs by tenant: {dict(tenant_counts)}")

            # Check recent logs
            result = await db.execute(
                select(ApplicationLog)
                .limit(5)
                .order_by(ApplicationLog.timestamp.desc())
            )
            recent_logs = result.scalars().all()
            print(f"📝 Recent logs count: {len(recent_logs)}")

            if recent_logs:
                latest = recent_logs[0]
                print(f"🕐 Most recent log:")
                print(f"   - ID: {latest.id}")
                print(f"   - Tenant: {latest.tenant_id}")
                print(f"   - Level: {latest.level}")
                print(f"   - Logger: {latest.logger_name}")
                print(f"   - Message: {latest.message[:100]}...")

            print("\n" + "="*60)

            # Test service with None tenant (global admin)
            print("🌍 Testing LogService with global admin (tenant_id=None)...")
            service_global = LogService(db, None)

            stats = await service_global.get_logs_stats('global')
            print(f"📈 Stats: {stats}")

            logs = await service_global.get_application_logs('global', limit=10)
            print(f"📋 Logs retrieved: {len(logs)}")

            if logs:
                print("🔍 First log details:")
                first_log = logs[0]
                print(f"   - ID: {first_log.id}")
                print(f"   - Tenant: {first_log.tenant_id}")
                print(f"   - Level: {first_log.level}")
                print(f"   - Message: {first_log.message[:100]}")

            print("\n" + "="*60)

            # Test service with 'global' tenant (tenant-specific)
            print("🏢 Testing LogService with 'global' tenant...")
            service_tenant = LogService(db, 'global')

            logs_tenant = await service_tenant.get_application_logs('global', limit=10)
            print(f"📋 Logs retrieved with tenant filter: {len(logs_tenant)}")

            # Check if there are logs with 'global' as tenant_id
            result = await db.execute(
                select(func.count(ApplicationLog.id))
                .where(ApplicationLog.tenant_id == 'global')
            )
            global_tenant_count = result.scalar()
            print(f"🏢 Logs with tenant_id='global': {global_tenant_count}")

        except Exception as e:
            print(f"❌ Error during debugging: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
