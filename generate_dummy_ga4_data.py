"""Insert dummy GA4 metrics data for testing."""

import asyncio
from datetime import date, timedelta
import random
from app.features.core.database import get_async_session
from app.features.business_automations.marketing_intellegence_hub.services.metrics.crud_services import Ga4MetricsIngestionService
from app.features.business_automations.marketing_intellegence_hub.schemas import Ga4DailyMetricPayload

CONNECTION_ID = "28abd0be-254b-4057-85e1-8883934cdf4d"  # TestProperty
TENANT_ID = "9"

async def generate_dummy_data():
    """Generate 30 days of realistic dummy GA4 data."""
    async_session = get_async_session()
    async with async_session() as db:
        service = Ga4MetricsIngestionService(db, TENANT_ID)

        payloads = []
        today = date.today()

        print(f"📊 Generating 30 days of dummy GA4 data...\n")

        for day_offset in range(30):
            current_date = today - timedelta(days=day_offset)

            # Generate realistic metrics with some variation
            base_sessions = random.randint(100, 500)
            base_users = int(base_sessions * random.uniform(0.7, 0.9))  # Users typically less than sessions

            payload = Ga4DailyMetricPayload(
                date=current_date,
                sessions=float(base_sessions),
                users=float(base_users),
                conversions=float(random.randint(5, 50)),
                engagement_rate=round(random.uniform(0.45, 0.85), 4),  # 45-85%
                bounce_rate=round(random.uniform(0.15, 0.45), 4),  # 15-45%
            )
            payloads.append(payload)

            print(f"  {current_date}: {int(payload.sessions)} sessions, {int(payload.users)} users, "
                  f"{int(payload.conversions)} conversions, "
                  f"{payload.engagement_rate:.1%} engagement, {payload.bounce_rate:.1%} bounce")

        print(f"\n💾 Inserting {len(payloads)} records into database...")
        await service.upsert_daily_metrics(CONNECTION_ID, payloads, user=None)

        print(f"✅ Successfully inserted {len(payloads)} days of GA4 metrics!")
        print(f"\n📊 Summary:")
        print(f"   Date range: {payloads[-1].date} to {payloads[0].date}")
        print(f"   Total sessions: {sum(int(p.sessions) for p in payloads):,}")
        print(f"   Total users: {sum(int(p.users) for p in payloads):,}")
        print(f"   Total conversions: {sum(int(p.conversions) for p in payloads):,}")
        print(f"   Avg engagement rate: {sum(p.engagement_rate for p in payloads) / len(payloads):.1%}")
        print(f"   Avg bounce rate: {sum(p.bounce_rate for p in payloads) / len(payloads):.1%}")

if __name__ == "__main__":
    asyncio.run(generate_dummy_data())
