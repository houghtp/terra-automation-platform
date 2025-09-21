#!/usr/bin/env python3
"""
Test the running authentication server endpoints.
"""
import requests
import json


def test_live_endpoints():
    """Test authentication endpoints on the live server."""
    import time
    base_url = "http://localhost:8000"
    tenant_id = "test-tenant"

    # Use timestamp to ensure unique email
    timestamp = str(int(time.time()))
    unique_email = f"test_{timestamp}@example.com"

    print("🔐 Testing Live Authentication Server")
    print("=" * 50)

    try:
        # Test auth status (unauthenticated)
        print("1. Testing auth status (unauthenticated)...")
        headers = {"x-tenant-id": tenant_id}
        response = requests.get(f"{base_url}/auth/status", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            authenticated = data.get("authenticated", True)
            print(f"   Authenticated: {authenticated}")
            if not authenticated:
                print("   ✅ Correctly shows unauthenticated")
            else:
                print("   ❌ Should show unauthenticated")

        # Test register page
        print("\n2. Testing register page...")
        response = requests.get(f"{base_url}/auth/register", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            print("   ✅ Register page loads")
        else:
            print("   ❌ Register page failed")

        # Test login page
        print("\n3. Testing login page...")
        response = requests.get(f"{base_url}/auth/login", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            print("   ✅ Login page loads")
        else:
            print("   ❌ Login page failed")

        # Test API registration
        print("\n4. Testing API registration...")
        user_data = {
            "email": unique_email,
            "password": "securepassword123",
            "role": "user"
        }
        response = requests.post(f"{base_url}/auth/register", json=user_data, headers=headers)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")

            if access_token and refresh_token:
                print("   ✅ Registration successful - tokens received")

                # Test get current user
                print("\n5. Testing get current user...")
                auth_headers = {
                    "x-tenant-id": tenant_id,
                    "Authorization": f"Bearer {access_token}"
                }
                response = requests.get(f"{base_url}/auth/me", headers=auth_headers)
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    user_info = response.json()
                    email = user_info.get("email")
                    role = user_info.get("role")
                    print(f"   Email: {email}")
                    print(f"   Role: {role}")
                    if email == user_data["email"] and role == user_data["role"]:
                        print("   ✅ User info correct")
                    else:
                        print("   ❌ User info mismatch")
                else:
                    print(f"   ❌ Get user failed: {response.text}")

                # Test token refresh
                print("\n6. Testing token refresh...")
                refresh_data = {"refresh_token": refresh_token}
                response = requests.post(f"{base_url}/auth/refresh", json=refresh_data)
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    new_data = response.json()
                    new_access_token = new_data.get("access_token")
                    if new_access_token:
                        print("   ✅ Token refresh successful")
                        access_token = new_access_token
                    else:
                        print("   ❌ No new access token in response")
                else:
                    print(f"   ❌ Token refresh failed: {response.text}")

                # Test auth status (authenticated)
                print("\n7. Testing auth status (authenticated)...")
                auth_headers["Authorization"] = f"Bearer {access_token}"
                response = requests.get(f"{base_url}/auth/status", headers=auth_headers)
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    authenticated = data.get("authenticated", False)
                    user = data.get("user")
                    print(f"   Authenticated: {authenticated}")
                    if authenticated and user:
                        print("   ✅ Correctly shows authenticated with user data")
                    else:
                        print("   ❌ Authentication status incorrect")

                # Test protected endpoint without auth
                print("\n8. Testing protected endpoint without auth...")
                response = requests.get(f"{base_url}/auth/me", headers={"x-tenant-id": tenant_id})
                print(f"   Status: {response.status_code}")
                if response.status_code == 401:
                    print("   ✅ Correctly rejected without auth")
                else:
                    print("   ❌ Should have been rejected")

                # Test duplicate registration
                print("\n9. Testing duplicate registration...")
                response = requests.post(f"{base_url}/auth/register", json=user_data, headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 400:
                    try:
                        error_detail = response.json().get("detail", "")
                        if "already" in error_detail.lower():
                            print("   ✅ Correctly rejected duplicate email")
                        else:
                            print(f"   ❌ Wrong error message: {error_detail}")
                    except:
                        # HTML response format, extract error from it
                        if "already" in response.text.lower():
                            print("   ✅ Correctly rejected duplicate email")
                        else:
                            print("   ❌ Unexpected response format")
                else:
                    print("   ❌ Should have rejected duplicate email")

            else:
                print("   ❌ Registration failed - no tokens received")
        else:
            print(f"   ❌ Registration failed: {response.text}")

        print("\n" + "=" * 50)
        print("🎉 Authentication endpoint testing completed!")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error during testing: {e}")


if __name__ == "__main__":
    test_live_endpoints()
