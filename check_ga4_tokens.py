"""Check GA4 tokens validity."""

import asyncio
import traceback
from app.features.core.database import get_async_session
from app.features.business_automations.marketing_intellegence_hub.services.connections.crud_services import Ga4ConnectionCrudService

TENANT_ID = "9"  # Terra IT tenant
CONNECTION_ID = None  # if you want a specific connection; else it will list all

async def main():
    async_session = get_async_session()
    async with async_session() as db:
        svc = Ga4ConnectionCrudService(db, TENANT_ID)
        try:
            conns = await svc.list_connections()
            print(f"Connections ({len(conns)}):")
            for c in conns:
                print(f"\n📊 Connection: {c.property_name}")
                print(f"   ID: {c.id}")
                print(f"   Tenant: {c.tenant_id}")
                print(f"   Property: {c.property_id}")
                print(f"   Status: {c.status}")
                print(f"   Last synced: {c.last_synced_at}")

                if CONNECTION_ID and c.id != CONNECTION_ID:
                    continue

                tokens = await svc.get_tokens(c.id)
                if tokens:
                    print(f"   ✅ Tokens retrieved:")
                    print(f"      Access token: {tokens.get('access_token', 'N/A')[:30]}..." if tokens.get('access_token') else "      ❌ No access token")
                    print(f"      Refresh token: {tokens.get('refresh_token', 'N/A')[:30]}..." if tokens.get('refresh_token') else "      ❌ No refresh token")
                else:
                    print(f"   ❌ No tokens found")
        except Exception:
            print("\n❌ Error occurred:")
            traceback.print_exc()

asyncio.run(main())
