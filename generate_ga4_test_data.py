"""Generate test data for GA4 TestProperty using Measurement Protocol."""

import requests
import random
from datetime import datetime, timedelta

# Your TestProperty Measurement ID and API Secret
MEASUREMENT_ID = "G-YEBL5D8C6F"
API_SECRET = "Qb82Lk-ORdmkrGVqDwaNQw"

# Measurement Protocol endpoint
MP_URL = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"

# Sample pages and events
PAGES = [
    {"location": "https://example.com/", "title": "Home"},
    {"location": "https://example.com/products", "title": "Products"},
    {"location": "https://example.com/about", "title": "About Us"},
    {"location": "https://example.com/contact", "title": "Contact"},
    {"location": "https://example.com/pricing", "title": "Pricing"},
    {"location": "https://example.com/blog", "title": "Blog"},
    {"location": "https://example.com/features", "title": "Features"},
    {"location": "https://example.com/support", "title": "Support"},
    {"location": "https://example.com/docs", "title": "Documentation"},
    {"location": "https://example.com/signup", "title": "Sign Up"},
]

def send_events(client_id_base, num_events=5):
    """Send multiple events for a user session."""
    events = []

    # Page views
    for i in range(num_events):
        page = random.choice(PAGES)
        events.append({
            "name": "page_view",
            "params": {
                "page_location": page["location"],
                "page_title": page["title"],
                "engagement_time_msec": random.randint(5000, 60000)
            }
        })

    # Add some conversions (purchases)
    if random.random() > 0.5:  # 50% chance of purchase
        events.append({
            "name": "purchase",
            "params": {
                "currency": "USD",
                "value": random.uniform(10, 500),
                "transaction_id": f"txn_{client_id_base}_{random.randint(1000, 9999)}"
            }
        })

    payload = {
        "client_id": f"{client_id_base}.{random.randint(1000, 9999)}",
        "events": events
    }

    response = requests.post(MP_URL, json=payload, headers={"Content-Type": "application/json"})
    return response.status_code == 204

def generate_test_data(days_back=7, sessions_per_day=10):
    """Generate test data for past N days."""
    print(f"📊 Generating test data for {days_back} days...")
    print(f"   Sessions per day: {sessions_per_day}")
    print(f"   Measurement ID: {MEASUREMENT_ID}\n")

    total_sent = 0
    total_failed = 0

    for day_offset in range(days_back):
        # Note: Measurement Protocol uses current timestamp, but we're simulating different sessions
        # The actual date will be when Google receives the event

        day_sessions = 0
        for session in range(sessions_per_day):
            client_id_base = 1000 + (day_offset * 100) + session
            num_events = random.randint(2, 6)  # 2-6 events per session

            if send_events(client_id_base, num_events):
                day_sessions += 1
                total_sent += 1
            else:
                total_failed += 1

        print(f"✅ Day -{day_offset}: Sent {day_sessions} sessions")

    print(f"\n📈 Summary:")
    print(f"   Total sessions sent: {total_sent}")
    print(f"   Failed: {total_failed}")
    print(f"\n⏰ Data Processing:")
    print(f"   - Realtime: Available in GA4 Realtime reports within 30 seconds")
    print(f"   - Reporting API: Available in 24-48 hours")
    print(f"   - Your app sync: Will pull data once it appears in Reporting API")

if __name__ == "__main__":
    # Generate data for past 7 days, 10 sessions per day
    generate_test_data(days_back=7, sessions_per_day=10)
