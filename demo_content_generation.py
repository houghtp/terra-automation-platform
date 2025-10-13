#!/usr/bin/env python3
"""
Demo script to showcase AI content generation workflow.

This script demonstrates the complete flow:
1. Create a content plan (content idea)
2. Process it with AI (research + generation)
3. View the generated draft content

Usage:
    python demo_content_generation.py
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin@example.com"  # Replace with your admin email
PASSWORD = "admin123"  # Replace with your admin password


async def login(client: httpx.AsyncClient) -> dict:
    """Login and get authentication token."""
    print("🔐 Logging in...")

    response = await client.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": USERNAME,
            "password": PASSWORD
        }
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        raise Exception("Login failed")

    print("✅ Login successful\n")
    return response.json()


async def create_content_plan(client: httpx.AsyncClient) -> str:
    """Create a new content plan."""
    print("📝 Creating content plan...")

    plan_data = {
        "title": "The Future of AI in Software Development",
        "description": "Explore how AI is transforming software development practices, tools, and workflows",
        "target_channels": ["wordpress", "linkedin"],
        "target_audience": "Software developers and tech leaders",
        "tone": "professional",
        "seo_keywords": ["AI", "software development", "automation", "productivity"],
        "competitor_urls": [],
        "min_seo_score": 90,
        "max_iterations": 2
    }

    response = await client.post(
        f"{BASE_URL}/features/content-broadcaster/planning/create",
        json=plan_data
    )

    if response.status_code != 200:
        print(f"❌ Failed to create plan: {response.text}")
        raise Exception("Failed to create plan")

    result = response.json()
    plan_id = result["plan_id"]

    print(f"✅ Content plan created: {plan_id}")
    print(f"   Title: {result['title']}")
    print(f"   Status: {result['status']}\n")

    return plan_id


async def process_content_plan(client: httpx.AsyncClient, plan_id: str) -> dict:
    """Process the content plan with AI."""
    print("🤖 Processing content plan with AI...")
    print("   This may take 30-60 seconds...\n")

    response = await client.post(
        f"{BASE_URL}/features/content-broadcaster/planning/{plan_id}/process",
        json={"use_research": False},  # Set to True if you have scraping API key
        timeout=120.0  # Allow 2 minutes for AI processing
    )

    if response.status_code != 200:
        print(f"❌ Failed to process plan: {response.text}")
        raise Exception("Failed to process plan")

    result = response.json()

    print("✅ Content generated successfully!")
    print(f"   Plan ID: {result['plan_id']}")
    print(f"   Content Item ID: {result['content_item_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Content Length: {result['content_length']} characters")
    print(f"   Research Sources: {result['research_sources']}\n")

    return result


async def get_content_item(client: httpx.AsyncClient, content_id: str) -> dict:
    """Get the generated content item."""
    print("📄 Fetching generated content...")

    response = await client.get(
        f"{BASE_URL}/features/content-broadcaster/api/{content_id}"
    )

    if response.status_code != 200:
        print(f"❌ Failed to get content: {response.text}")
        raise Exception("Failed to get content")

    content = response.json()

    print("✅ Content retrieved successfully!\n")
    print("=" * 80)
    print(f"TITLE: {content['title']}")
    print("=" * 80)
    print(f"\n{content['body'][:500]}...")
    print(f"\n[Content truncated - Full length: {len(content['body'])} characters]")
    print("=" * 80)
    print(f"\nState: {content['state']}")
    print(f"Tags: {', '.join(content.get('tags', []))}")
    print(f"Created: {content['created_at']}\n")

    return content


async def main():
    """Run the demo workflow."""
    print("\n" + "=" * 80)
    print("AI CONTENT GENERATION DEMO")
    print("=" * 80 + "\n")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # Step 1: Login
            await login(client)

            # Step 2: Create content plan
            plan_id = await create_content_plan(client)

            # Step 3: Process with AI
            result = await process_content_plan(client, plan_id)

            # Step 4: View generated content
            content = await get_content_item(client, result["content_item_id"])

            print("\n" + "=" * 80)
            print("✅ DEMO COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print(f"\n📌 Content Plan ID: {plan_id}")
            print(f"📌 Content Item ID: {result['content_item_id']}")
            print(f"\nYou can now:")
            print(f"  - View the content at: {BASE_URL}/features/content-broadcaster")
            print(f"  - Submit it for review")
            print(f"  - Approve and schedule for publishing")
            print("\n")

        except Exception as e:
            print(f"\n❌ Demo failed: {e}\n")
            raise


if __name__ == "__main__":
    asyncio.run(main())
