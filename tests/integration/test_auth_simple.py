#!/usr/bin/env python3
"""
Simple authentication endpoint test script.
"""
import sys
import traceback

# Add the app to path
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from app.main import app


def test_basic_endpoints():
    """Test basic authentication endpoints."""
    print("🔐 Testing FastAPI Authentication System")
    print("=" * 50)

    try:
        with TestClient(app) as client:
            # Test health check
            print("Testing health check...")
            response = client.get("/")
            print(f"Health check: {response.status_code}")

            # Test auth status (unauthenticated)
            print("Testing auth status (unauthenticated)...")
            response = client.get("/auth/status", headers={"x-tenant-id": "test-tenant"})
            print(f"Auth status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Authenticated: {data.get('authenticated')}")

            # Test register page
            print("Testing register page...")
            response = client.get("/auth/register", headers={"x-tenant-id": "test-tenant"})
            print(f"Register page: {response.status_code}")

            # Test login page
            print("Testing login page...")
            response = client.get("/auth/login", headers={"x-tenant-id": "test-tenant"})
            print(f"Login page: {response.status_code}")

            # Test API registration
            print("Testing API registration...")
            user_data = {
                "email": "test@example.com",
                "password": "securepassword123",
                "role": "user"
            }
            response = client.post(
                "/auth/register",
                json=user_data,
                headers={"x-tenant-id": "test-tenant"}
            )
            print(f"Registration: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ Registration successful!")
                access_token = data.get("access_token")

                if access_token:
                    # Test protected endpoint
                    print("Testing protected endpoint...")
                    auth_headers = {
                        "x-tenant-id": "test-tenant",
                        "Authorization": f"Bearer {access_token}"
                    }
                    response = client.get("/auth/me", headers=auth_headers)
                    print(f"Get current user: {response.status_code}")

                    if response.status_code == 200:
                        user_info = response.json()
                        print(f"User email: {user_info.get('email')}")
                        print("✅ Authentication system working!")
                    else:
                        print(f"❌ Protected endpoint failed: {response.text}")
                else:
                    print("❌ No access token received")
            else:
                print(f"❌ Registration failed: {response.text}")

            print("\n🎉 Basic authentication tests completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_basic_endpoints()
