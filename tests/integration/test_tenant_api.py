#!/usr/bin/env python3
"""
Quick script to test tenant API functionality
"""
import asyncio
import httpx

async def test_tenant_api():
    async with httpx.AsyncClient() as client:
        print("🔐 Logging in as global admin...")

        # Login
        login_response = await client.post(
            "http://localhost:8090/auth/login",
            data={
                "email": "admin@system.local",
                "password": "admin123"
            },
            follow_redirects=True
        )

        print(f"Login status: {login_response.status_code}")
        if login_response.status_code != 200:
            print("❌ Login failed")
            print(f"Response: {login_response.text}")
            return

        print("✅ Login successful")

        # Test tenant API
        print("\n📋 Testing tenant API...")
        tenant_response = await client.get("http://localhost:8090/administration/tenants/api")

        print(f"Tenant API status: {tenant_response.status_code}")
        if tenant_response.status_code == 200:
            tenants = tenant_response.json()
            print(f"✅ Found {len(tenants)} tenants")
            for tenant in tenants:
                print(f"  - {tenant.get('name', 'Unknown')} ({tenant.get('status', 'Unknown')})")
        else:
            print(f"❌ Tenant API failed: {tenant_response.text}")

        # Test tenant management page
        print("\n🖥️ Testing tenant management page...")
        page_response = await client.get("http://localhost:8090/administration/tenants/")
        print(f"Tenant page status: {page_response.status_code}")

        if page_response.status_code == 200:
            print("✅ Tenant management page accessible")
        else:
            print(f"❌ Tenant page failed: {page_response.text}")

if __name__ == "__main__":
    asyncio.run(test_tenant_api())
