"""Test GA4 Realtime API to see current events."""

import asyncio
import os
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest, Metric, Dimension
from google.oauth2.credentials import Credentials

from app.features.business_automations.marketing_intellegence_hub.services.connections.crud_services import Ga4ConnectionCrudService
from app.features.administration.secrets.services.crud_services import SecretsCrudService
from app.features.core.database import get_async_session


CONNECTION_ID = "28abd0be-254b-4057-85e1-8883934cdf4d"
TENANT_ID = "9"


async def test_realtime():
    """Test GA4 Realtime API."""
    async_session = get_async_session()
    async with async_session() as db:
        # Get credentials
        secrets_service = SecretsCrudService(db, "global")
        ga4_secret = await secrets_service.get_secret_by_name("GA4 Client Secret")
        secret_value_response = await secrets_service.get_secret_value(ga4_secret.id)
        client_secret = secret_value_response.value
        client_id = os.getenv("GA4_CLIENT_ID")

        # Get connection
        ga4_service = Ga4ConnectionCrudService(db, TENANT_ID)
        connection = await ga4_service.get_connection(CONNECTION_ID)
        tokens = await ga4_service.get_tokens(CONNECTION_ID)

        print(f"🔍 Testing Realtime API for {connection.property_id}")

        creds = Credentials(
            token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )

        client = BetaAnalyticsDataClient(credentials=creds)

        # Test Realtime API
        print("\n📊 REALTIME DATA (last 30 minutes):")
        resp = None
        try:
            req = RunRealtimeReportRequest(
                property=connection.property_id,
                metrics=[
                    Metric(name="activeUsers"),
                ],
            )
            resp = client.run_realtime_report(req)

            print(f"  ✅ Active users right now: {resp.row_count}")

            # Try with event breakdown
            req2 = RunRealtimeReportRequest(
                property=connection.property_id,
                dimensions=[Dimension(name="unifiedScreenName")],
                metrics=[Metric(name="screenPageViews")],
                limit=10,
            )
            resp2 = client.run_realtime_report(req2)

            if resp2.rows:
                print(f"  📊 Recent activity:")
                for row in resp2.rows[:5]:
                    page = row.dimension_values[0].value
                    views = row.metric_values[0].value
                    print(f"    - {page}: {views} views")
            else:
                print(f"  ⚠️  No realtime activity")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print("\n" + "="*80)
        print("CONCLUSION:")
        print("="*80)
        if resp and resp.row_count > 0:
            print("✅ Events ARE being received by GA4!")
            print("⏰ Wait 24-48 hours for them to appear in Data API (reporting)")
            print("📊 Your app should check Realtime API for immediate data")
        else:
            print("⚠️  No events in Realtime = Not receiving data")
            print("🔍 Check:")
            print("   1. Measurement ID G-YEBL5D8C6F configured correctly")
            print("   2. Events sent recently (Realtime = last 30 min only)")
            print("   3. Try sending test events NOW and rerun this script")


if __name__ == "__main__":
    asyncio.run(test_realtime())
