"""Test GA4 connection and data retrieval."""

import asyncio
import os
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest, MetricAggregation
from google.oauth2.credentials import Credentials

# Import app services
from app.features.business_automations.marketing_intellegence_hub.services.connections.crud_services import Ga4ConnectionCrudService
from app.features.administration.secrets.services.crud_services import SecretsCrudService
from app.features.core.database import get_async_session


CONNECTION_ID = "28abd0be-254b-4057-85e1-8883934cdf4d"  # TestProperty - properties/510567171
TENANT_ID = "9"  # Terra IT


async def get_credentials():
    """Retrieve GA4 credentials and tokens from database."""
    async_session = get_async_session()
    async with async_session() as db:
        # Get GA4 client secret from Secrets Management
        secrets_service = SecretsCrudService(db, "global")
        ga4_secret = await secrets_service.get_secret_by_name("GA4 Client Secret")

        if not ga4_secret:
            print("❌ GA4 Client Secret not found in Secrets Management")
            return None

        # Get the actual secret value (decrypted)
        secret_value_response = await secrets_service.get_secret_value(ga4_secret.id)
        client_secret = secret_value_response.value
        client_id = os.getenv("GA4_CLIENT_ID")

        print(f"✅ GA4 Client ID: {client_id}")
        print(f"✅ GA4 Client Secret: {'*' * 20} (loaded from Secrets Management)")

        # Get connection tokens
        ga4_service = Ga4ConnectionCrudService(db, TENANT_ID)
        connection = await ga4_service.get_connection(CONNECTION_ID)

        if not connection:
            print(f"❌ Connection {CONNECTION_ID} not found")
            return None

        print(f"✅ Connection found: {connection.property_name} ({connection.property_id})")

        tokens = await ga4_service.get_tokens(CONNECTION_ID)

        if not tokens:
            print("❌ No tokens found for this connection")
            return None

        print(f"✅ Tokens retrieved (access: {tokens['access_token'][:20] if tokens.get('access_token') else 'None'}...)")
        print(f"✅ Refresh token: {tokens['refresh_token'][:20] if tokens.get('refresh_token') else 'None'}...")

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "property_id": connection.property_id,
        }


async def test_ga4_api(creds_dict):
    """Test GA4 API with various configurations."""
    print("\n" + "="*80)
    print("TESTING GA4 DATA API")
    print("="*80)

    creds = Credentials(
        token=creds_dict["access_token"],
        refresh_token=creds_dict["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_dict["client_id"],
        client_secret=creds_dict["client_secret"],
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )

    client = BetaAnalyticsDataClient(credentials=creds)
    property_id = creds_dict["property_id"]

    # Test 1: Today only, minimal metrics
    print(f"\n📊 TEST 1: Today only, minimal metrics")
    print(f"Property: {property_id}")
    today = date.today()
    try:
        req = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=today.isoformat(), end_date=today.isoformat())],
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions")],
        )
        resp = client.run_report(req)
        print(f"  ✅ row_count: {resp.row_count}")
        print(f"  ✅ rows: {len(resp.rows)}")
        if resp.rows:
            for row in resp.rows[:3]:
                print(f"    - {row.dimension_values[0].value}: {row.metric_values[0].value} sessions")
        else:
            print(f"  ⚠️  No rows returned")
            if resp.totals:
                print(f"  📊 Totals present: {resp.totals}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 2: Last 30 days, all metrics (your current request)
    print(f"\n📊 TEST 2: Last 30 days, all metrics + aggregations")
    start = today - timedelta(days=30)
    try:
        req = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start.isoformat(), end_date=today.isoformat())],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
                Metric(name="engagementRate"),
                Metric(name="bounceRate"),
            ],
            metric_aggregations=[MetricAggregation.TOTAL],
        )
        resp = client.run_report(req)
        print(f"  ✅ row_count: {resp.row_count}")
        print(f"  ✅ rows: {len(resp.rows)}")
        print(f"  ✅ totals: {len(resp.totals)}")
        if resp.rows:
            print(f"  📊 First 3 rows:")
            for row in resp.rows[:3]:
                date_val = row.dimension_values[0].value
                sessions = row.metric_values[0].value
                users = row.metric_values[1].value
                print(f"    - {date_val}: {sessions} sessions, {users} users")
        else:
            print(f"  ⚠️  No rows returned")
        if resp.totals:
            print(f"  📊 Totals:")
            for total in resp.totals:
                print(f"    - Total sessions: {total.metric_values[0].value}")
                print(f"    - Total users: {total.metric_values[1].value}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 3: Date range matching test events we just sent (today only)
    print(f"\n📊 TEST 3: Testing with Measurement Protocol date (today)")
    try:
        req = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=today.isoformat(), end_date=today.isoformat())],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
                Metric(name="eventCount"),
            ],
        )
        resp = client.run_report(req)
        print(f"  ✅ row_count: {resp.row_count}")
        print(f"  ✅ rows: {len(resp.rows)}")
        if resp.rows:
            for row in resp.rows:
                date_val = row.dimension_values[0].value
                sessions = row.metric_values[0].value
                users = row.metric_values[1].value
                conversions = row.metric_values[2].value
                events = row.metric_values[3].value
                print(f"    - {date_val}: {sessions} sessions, {users} users, {conversions} conversions, {events} events")
        else:
            print(f"  ⚠️  No rows returned for today")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 4: Check metadata
    print(f"\n📊 TEST 4: Response metadata")
    try:
        req = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start.isoformat(), end_date=today.isoformat())],
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions")],
        )
        resp = client.run_report(req)
        print(f"  ✅ Metadata: {resp.metadata}")
        print(f"  ✅ Currency code: {resp.metadata.currency_code if hasattr(resp.metadata, 'currency_code') else 'N/A'}")
        print(f"  ✅ Time zone: {resp.metadata.time_zone if hasattr(resp.metadata, 'time_zone') else 'N/A'}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


async def main():
    """Main test runner."""
    print("🔍 Retrieving GA4 credentials from database...")
    creds = await get_credentials()

    if not creds:
        print("\n❌ Failed to retrieve credentials")
        return

    await test_ga4_api(creds)

    print("\n" + "="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)
    print("""
Key things to check:
1. Property ID match: Does properties/510567171 match the Measurement ID G-YEBL5D8C6F?
2. Data stream: Is G-YEBL5D8C6F configured for property 510567171?
3. Timezone: GA4 property timezone vs. date ranges
4. Data freshness: Measurement Protocol events can take 24-48 hours to appear in reports
5. Real-time vs. reporting: Check GA4 UI Realtime tab for immediate data

If TEST 1 shows no data, the property may be empty or timezone-mismatched.
If TEST 3 shows data, then date range or aggregation settings may be the issue.
    """)


if __name__ == "__main__":
    asyncio.run(main())
