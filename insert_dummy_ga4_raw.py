"""Insert dummy GA4 metrics data using raw SQL."""

import asyncio
from datetime import date, timedelta
import random
import uuid
import json
from sqlalchemy import text
from app.features.core.database import get_async_session

CONNECTION_ID = "28abd0be-254b-4057-85e1-8883934cdf4d"  # TestProperty
TENANT_ID = "9"

async def insert_dummy_data():
    """Generate and insert 30 days of realistic dummy GA4 data using raw SQL."""
    async_session = get_async_session()
    async with async_session() as db:

        print(f"📊 Generating 30 days of dummy GA4 data...\n")

        today = date.today()
        values_list = []

        for day_offset in range(30):
            current_date = today - timedelta(days=day_offset)
            
            # Generate realistic metrics with some variation
            base_sessions = random.randint(100, 500)
            base_users = int(base_sessions * random.uniform(0.7, 0.9))
            new_users = int(base_users * random.uniform(0.2, 0.4))  # 20-40% new users
            pageviews = int(base_sessions * random.uniform(2.5, 5.0))  # 2.5-5 pages per session
            
            conversions = random.randint(5, 50)
            conversion_rate = conversions / base_sessions if base_sessions > 0 else 0
            conversions_per_1k = (conversions / base_sessions * 1000) if base_sessions > 0 else 0
            
            engagement_rate = round(random.uniform(0.45, 0.85), 4)
            engaged_sessions = int(base_sessions * engagement_rate)
            bounce_rate = round(random.uniform(0.15, 0.45), 4)
            avg_engagement_time = round(random.uniform(45, 180), 2)  # 45-180 seconds
            
            # Channel breakdown (percentages that sum to ~100%)
            organic_pct = random.uniform(0.3, 0.5)
            paid_pct = random.uniform(0.1, 0.25)
            direct_pct = random.uniform(0.15, 0.3)
            social_pct = random.uniform(0.05, 0.15)
            referral_pct = max(0, 1.0 - (organic_pct + paid_pct + direct_pct + social_pct))
            
            channel_breakdown = {
                "Organic Search": round(base_sessions * organic_pct),
                "Paid Search": round(base_sessions * paid_pct),
                "Direct": round(base_sessions * direct_pct),
                "Social": round(base_sessions * social_pct),
                "Referral": round(base_sessions * referral_pct)
            }
            
            # Device breakdown
            mobile_pct = random.uniform(0.5, 0.7)
            desktop_pct = random.uniform(0.2, 0.4)
            tablet_pct = max(0, 1.0 - (mobile_pct + desktop_pct))
            
            device_breakdown = {
                "mobile": round(base_sessions * mobile_pct),
                "desktop": round(base_sessions * desktop_pct),
                "tablet": round(base_sessions * tablet_pct)
            }
            
            # Geo breakdown (top countries)
            geo_breakdown = {
                "United States": round(base_sessions * random.uniform(0.4, 0.6)),
                "United Kingdom": round(base_sessions * random.uniform(0.15, 0.25)),
                "Canada": round(base_sessions * random.uniform(0.05, 0.15)),
                "Australia": round(base_sessions * random.uniform(0.03, 0.1)),
                "Other": round(base_sessions * random.uniform(0.05, 0.15))
            }
            
            # Generate UUID for this record
            record_id = str(uuid.uuid4())
            
            values_list.append({
                'id': record_id,
                'date': current_date,
                'sessions': float(base_sessions),
                'users': float(base_users),
                'new_users': float(new_users),
                'pageviews': float(pageviews),
                'conversions': float(conversions),
                'conversion_rate': round(conversion_rate, 4),
                'conversions_per_1k': round(conversions_per_1k, 4),
                'engagement_rate': engagement_rate,
                'engaged_sessions': float(engaged_sessions),
                'bounce_rate': bounce_rate,
                'avg_engagement_time': avg_engagement_time,
                'channel_breakdown': channel_breakdown,
                'device_breakdown': device_breakdown,
                'geo_breakdown': geo_breakdown
            })
            
            print(f"  {current_date}: {base_sessions} sessions, {base_users} users ({new_users} new), "
                  f"{pageviews} pageviews, {conversions} conversions ({conversion_rate:.2%})")
        
        print(f"\n💾 Inserting {len(values_list)} records into database using raw SQL...")
        
        # Build the INSERT query with ON CONFLICT DO UPDATE
        sql = text("""
            INSERT INTO ga4_daily_metrics 
                (id, tenant_id, connection_id, date, sessions, users, new_users, pageviews, 
                 conversions, conversion_rate, conversions_per_1k, engagement_rate, engaged_sessions,
                 bounce_rate, avg_engagement_time, channel_breakdown, device_breakdown, geo_breakdown)
            VALUES 
                (:id, :tenant_id, :connection_id, :date, :sessions, :users, :new_users, :pageviews,
                 :conversions, :conversion_rate, :conversions_per_1k, :engagement_rate, :engaged_sessions,
                 :bounce_rate, :avg_engagement_time, :channel_breakdown, :device_breakdown, :geo_breakdown)
            ON CONFLICT (connection_id, tenant_id, date) 
            DO UPDATE SET
                sessions = EXCLUDED.sessions,
                users = EXCLUDED.users,
                new_users = EXCLUDED.new_users,
                pageviews = EXCLUDED.pageviews,
                conversions = EXCLUDED.conversions,
                conversion_rate = EXCLUDED.conversion_rate,
                conversions_per_1k = EXCLUDED.conversions_per_1k,
                engagement_rate = EXCLUDED.engagement_rate,
                engaged_sessions = EXCLUDED.engaged_sessions,
                bounce_rate = EXCLUDED.bounce_rate,
                avg_engagement_time = EXCLUDED.avg_engagement_time,
                channel_breakdown = EXCLUDED.channel_breakdown,
                device_breakdown = EXCLUDED.device_breakdown,
                geo_breakdown = EXCLUDED.geo_breakdown
        """)
        
        # Insert each record
        for values in values_list:
            await db.execute(
                sql,
                {
                    'id': values['id'],
                    'tenant_id': TENANT_ID,
                    'connection_id': CONNECTION_ID,
                    'date': values['date'],
                    'sessions': values['sessions'],
                    'users': values['users'],
                    'new_users': values['new_users'],
                    'pageviews': values['pageviews'],
                    'conversions': values['conversions'],
                    'conversion_rate': values['conversion_rate'],
                    'conversions_per_1k': values['conversions_per_1k'],
                    'engagement_rate': values['engagement_rate'],
                    'engaged_sessions': values['engaged_sessions'],
                    'bounce_rate': values['bounce_rate'],
                    'avg_engagement_time': values['avg_engagement_time'],
                    'channel_breakdown': json.dumps(values['channel_breakdown']),
                    'device_breakdown': json.dumps(values['device_breakdown']),
                    'geo_breakdown': json.dumps(values['geo_breakdown'])
                }
            )

        # COMMIT the transaction
        await db.commit()
        
        print(f"✅ Successfully inserted {len(values_list)} days of GA4 metrics!")
        print(f"\n📊 Summary:")
        print(f"   Date range: {values_list[-1]['date']} to {values_list[0]['date']}")
        print(f"   Total sessions: {sum(int(v['sessions']) for v in values_list):,}")
        print(f"   Total users: {sum(int(v['users']) for v in values_list):,}")
        print(f"   Total new users: {sum(int(v['new_users']) for v in values_list):,}")
        print(f"   Total pageviews: {sum(int(v['pageviews']) for v in values_list):,}")
        print(f"   Total conversions: {sum(int(v['conversions']) for v in values_list):,}")
        print(f"   Avg conversion rate: {sum(v['conversion_rate'] for v in values_list) / len(values_list):.2%}")
        print(f"   Avg engagement rate: {sum(v['engagement_rate'] for v in values_list) / len(values_list):.1%}")
        print(f"   Avg bounce rate: {sum(v['bounce_rate'] for v in values_list) / len(values_list):.1%}")
        print(f"   Avg engagement time: {sum(v['avg_engagement_time'] for v in values_list) / len(values_list):.1f}s")

if __name__ == "__main__":
    asyncio.run(insert_dummy_data())
