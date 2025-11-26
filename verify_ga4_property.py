"""Verify GA4 property and data stream configuration."""

import asyncio
from app.features.business_automations.marketing_intellegence_hub.services.connections.crud_services import Ga4ConnectionCrudService
from app.features.core.database import get_async_session

async def main():
    async_session = get_async_session()
    async with async_session() as db:
        service = Ga4ConnectionCrudService(db, "9")

        # List all connections
        connections = await service.list_connections()
        print("📊 All GA4 Connections:")
        for conn in connections:
            print(f"  - {conn.property_name}: {conn.property_id} (Status: {conn.status})")

        # Check test property
        test_conn = await service.get_connection("28abd0be-254b-4057-85e1-8883934cdf4d")
        if test_conn:
            print(f"\n🎯 TestProperty Details:")
            print(f"   Property ID: {test_conn.property_id}")
            print(f"   Property Name: {test_conn.property_name}")
            print(f"   Status: {test_conn.status}")
            print(f"   Last synced: {test_conn.last_synced_at}")
            print(f"\n⚠️  IMPORTANT:")
            print(f"   The Measurement ID G-YEBL5D8C6F must belong to {test_conn.property_id}")
            print(f"   Check in GA4 UI: Admin → Data Streams → Find G-YEBL5D8C6F")
            print(f"   Verify it shows Property ID: 510567171")

if __name__ == "__main__":
    asyncio.run(main())
