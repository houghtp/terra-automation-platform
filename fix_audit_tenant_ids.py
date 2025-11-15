"""
Script to fix audit and application log tenant IDs.

This script updates logs with tenant_id='unknown' or invalid tenant IDs
to use 'global' for consistency with the global admin system.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def fix_tenant_ids():
    """Fix tenant IDs in audit and application logs."""

    db_url = 'postgresql+asyncpg://dev_user:dev_password@localhost:5434/terra_automation_platform_dev'
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        print("\n=== Fixing Audit Log Tenant IDs ===")

        # Update 'unknown' to 'global'
        result = await conn.execute(text("""
            UPDATE audit_logs
            SET tenant_id = 'global'
            WHERE tenant_id = 'unknown'
        """))
        print(f"✅ Updated {result.rowcount} audit logs from 'unknown' to 'global'")

        # Update 'default' to 'global' for consistency
        result = await conn.execute(text("""
            UPDATE audit_logs
            SET tenant_id = 'global'
            WHERE tenant_id = 'default'
        """))
        print(f"✅ Updated {result.rowcount} audit logs from 'default' to 'global'")

        print("\n=== Verifying Changes ===")
        result = await conn.execute(text("""
            SELECT tenant_id, COUNT(*) as count
            FROM audit_logs
            GROUP BY tenant_id
            ORDER BY count DESC
        """))

        print("\nAudit Logs by Tenant:")
        for row in result:
            print(f"  {row[0]}: {row[1]} logs")

        print("\n=== Application Logs ===")
        result = await conn.execute(text("""
            SELECT tenant_id, COUNT(*) as count
            FROM application_logs
            GROUP BY tenant_id
            ORDER BY count DESC
        """))

        print("\nApplication Logs by Tenant:")
        for row in result:
            print(f"  {row[0]}: {row[1]} logs")

    await engine.dispose()
    print("\n✅ Tenant ID fix complete!")

if __name__ == "__main__":
    asyncio.run(fix_tenant_ids())
