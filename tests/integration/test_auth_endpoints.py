#!/usr/bin/env python3
"""
Comprehensive Authentication Endpoint Testing Script
Tests all authentication endpoints to verify functionality.
"""
import sys
from typing import Dict, Any, Optional

import httpx
from fastapi.testclient import TestClient

from app.main import app


class AuthEndpointTester:
    """Comprehensive tester for authentication endpoints."""

    def __init__(self):
        self.client = TestClient(app)
        self.base_url = "http://testserver"
        self.tenant_id = "test-tenant"
        self.test_user = {
            "email": "test@example.com",
            "password": "securepassword123",
            "role": "user"
        }
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def get_headers(self, auth: bool = False) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {"x-tenant-id": self.tenant_id}
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def test_health_check(self) -> bool:
        """Test application health check."""
        try:
            response = self.client.get("/")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_auth_status_unauthenticated(self) -> bool:
        """Test auth status when not authenticated."""
        try:
            response = self.client.get("/auth/status", headers=self.get_headers())
            if response.status_code == 200:
                data = response.json()
                return data.get("authenticated") is False
            return False
        except Exception as e:
            print(f"❌ Auth status (unauthenticated) failed: {e}")
            return False

    def test_register_page(self) -> bool:
        """Test registration page loads."""
        try:
            response = self.client.get("/auth/register", headers=self.get_headers())
            return response.status_code == 200 and "text/html" in response.headers.get("content-type", "")
        except Exception as e:
            print(f"❌ Register page failed: {e}")
            return False

    def test_login_page(self) -> bool:
        """Test login page loads."""
        try:
            response = self.client.get("/auth/login", headers=self.get_headers())
            return response.status_code == 200 and "text/html" in response.headers.get("content-type", "")
        except Exception as e:
            print(f"❌ Login page failed: {e}")
            return False

    def test_api_registration(self) -> bool:
        """Test API user registration."""
        try:
            response = self.client.post(
                "/auth/register",
                json=self.test_user,
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if all(key in data for key in ["access_token", "refresh_token", "expires_in"]):
                    self.access_token = data["access_token"]
                    self.refresh_token = data["refresh_token"]
                    return True
            return False
        except Exception as e:
            print(f"❌ API registration failed: {e}")
            return False

    def test_api_login(self) -> bool:
        """Test API user login."""
        try:
            # First, register a user if we haven't already
            if not self.access_token:
                self.test_api_registration()

            # Test login
            login_data = {
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }

            response = self.client.post(
                "/auth/login",
                json=login_data,
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if all(key in data for key in ["access_token", "refresh_token", "expires_in"]):
                    self.access_token = data["access_token"]
                    self.refresh_token = data["refresh_token"]
                    return True
            return False
        except Exception as e:
            print(f"❌ API login failed: {e}")
            return False

    def test_get_current_user(self) -> bool:
        """Test getting current user information."""
        try:
            response = self.client.get("/auth/me", headers=self.get_headers(auth=True))

            if response.status_code == 200:
                data = response.json()
                return (
                    data.get("email") == self.test_user["email"] and
                    data.get("tenant_id") == self.tenant_id and
                    data.get("role") == self.test_user["role"] and
                    data.get("is_active") is True
                )
            return False
        except Exception as e:
            print(f"❌ Get current user failed: {e}")
            return False

    def test_token_refresh(self) -> bool:
        """Test token refresh."""
        try:
            refresh_data = {"refresh_token": self.refresh_token}

            response = self.client.post("/auth/refresh", json=refresh_data)

            if response.status_code == 200:
                data = response.json()
                if all(key in data for key in ["access_token", "refresh_token"]):
                    # Token should be different
                    new_token = data["access_token"]
                    return new_token != self.access_token
            return False
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            return False

    def test_auth_status_authenticated(self) -> bool:
        """Test auth status when authenticated."""
        try:
            response = self.client.get("/auth/status", headers=self.get_headers(auth=True))

            if response.status_code == 200:
                data = response.json()
                return (
                    data.get("authenticated") is True and
                    "user" in data and
                    data["user"].get("email") == self.test_user["email"]
                )
            return False
        except Exception as e:
            print(f"❌ Auth status (authenticated) failed: {e}")
            return False

    def test_protected_endpoint_no_auth(self) -> bool:
        """Test protected endpoint without authentication."""
        try:
            response = self.client.get("/auth/me", headers=self.get_headers(auth=False))
            return response.status_code == 401
        except Exception as e:
            print(f"❌ Protected endpoint (no auth) failed: {e}")
            return False

    def test_invalid_token(self) -> bool:
        """Test with invalid token."""
        try:
            headers = self.get_headers()
            headers["Authorization"] = "Bearer invalid.token.here"

            response = self.client.get("/auth/me", headers=headers)
            return response.status_code == 401
        except Exception as e:
            print(f"❌ Invalid token test failed: {e}")
            return False

    def test_duplicate_registration(self) -> bool:
        """Test duplicate email registration."""
        try:
            response = self.client.post(
                "/auth/register",
                json=self.test_user,
                headers=self.get_headers()
            )

            return response.status_code == 400 and "already registered" in response.json().get("detail", "")
        except Exception as e:
            print(f"❌ Duplicate registration test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all authentication tests."""
        tests = [
            ("Health Check", self.test_health_check),
            ("Auth Status (Unauthenticated)", self.test_auth_status_unauthenticated),
            ("Registration Page", self.test_register_page),
            ("Login Page", self.test_login_page),
            ("API Registration", self.test_api_registration),
            ("API Login", self.test_api_login),
            ("Get Current User", self.test_get_current_user),
            ("Token Refresh", self.test_token_refresh),
            ("Auth Status (Authenticated)", self.test_auth_status_authenticated),
            ("Protected Endpoint (No Auth)", self.test_protected_endpoint_no_auth),
            ("Invalid Token", self.test_invalid_token),
            ("Duplicate Registration", self.test_duplicate_registration),
        ]

        results = {}
        passed = 0
        total = len(tests)

        print("\n🧪 Running Authentication Endpoint Tests\n")
        print("=" * 50)

        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status}: {test_name}")
                if result:
                    passed += 1
            except Exception as e:
                results[test_name] = False
                print(f"❌ FAIL: {test_name} - {e}")

        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All authentication tests passed!")
        else:
            print("⚠️  Some tests failed. Check the results above.")

        return results


def main():
    """Main function to run authentication tests."""
    print("🔐 FastAPI Authentication System Test Suite")
    print("=" * 50)

    tester = AuthEndpointTester()
    results = tester.run_all_tests()

    # Return appropriate exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
