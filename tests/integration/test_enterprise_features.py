"""
Quick validation script for enterprise features.

Tests the core functionality of our newly implemented features
without complex test setup requirements.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_enterprise_features():
    """Test all enterprise features work correctly."""
    print("🧪 Testing Enterprise Features...")

    # Test 1: API Versioning
    print("\n1️⃣ Testing API Versioning...")
    try:
        from app.features.core.versioning import api_version_manager, VersionInfo

        # Test version manager (use the global instance with registered versions)
        v1_info = api_version_manager.get_version_info("v1")
        assert v1_info is not None, "v1 version info should not be None"
        assert v1_info.status.value == "active", f"Expected 'active', got {v1_info.status.value}"

        print("   ✅ API Versioning: OK")
    except Exception as e:
        print(f"   ❌ API Versioning: {e}")
        return False

    # Test 2: API Key Management
    print("\n2️⃣ Testing API Key Management...")
    try:
        from app.features.core.api_security import APIKeyManager, APIKeyScope

        # Test key generation
        key_id, secret, key_hash = APIKeyManager.generate_api_key()
        assert len(key_id) == 16
        assert len(secret) == 43
        assert len(key_hash) == 64

        # Test signature generation
        from app.features.core.api_security import RequestSignatureValidator
        payload = "test payload"
        secret_test = "test-secret"
        signature = RequestSignatureValidator.generate_signature(
            "POST", "/test", payload.encode(), "2025-01-01T00:00:00Z", secret_test
        )
        assert len(signature) > 20

        print("   ✅ API Key Management: OK")
    except Exception as e:
        print(f"   ❌ API Key Management: {e}")
        return False

    # Test 3: MFA System
    print("\n3️⃣ Testing MFA System...")
    try:
        from app.features.core.mfa import MFAManager, MFAMethod

        # Test recovery code generation
        codes = MFAManager.generate_recovery_codes(5)
        assert len(codes) == 5
        assert all(len(code) == 9 for code in codes)  # XXXX-XXXX format

        # Test code hashing
        test_code = "ABCD-1234"
        hashed = MFAManager.hash_recovery_code(test_code)
        assert len(hashed) == 64
        assert MFAManager.verify_recovery_code(test_code, hashed)

        print("   ✅ MFA System: OK")
    except Exception as e:
        print(f"   ❌ MFA System: {e}")
        return False

    # Test 4: Webhook System
    print("\n4️⃣ Testing Webhook System...")
    try:
        from app.features.core.webhooks import WebhookManager, EventType, WebhookEvent
        from datetime import datetime

        # Test webhook secret generation
        secret = WebhookManager.generate_webhook_secret()
        assert len(secret) == 43

        # Test signature generation
        payload = '{"test": "data"}'
        signature = WebhookManager.generate_signature(payload, secret)
        assert signature.startswith("sha256=")

        # Test signature verification
        is_valid = WebhookManager.verify_signature(payload, signature, secret)
        assert is_valid is True

        # Test event creation
        event = WebhookEvent(
            event_type="user.created",
            tenant_id="test-tenant",
            data={"user_id": "123"},
            timestamp=datetime.utcnow().isoformat(),
            event_id="test-event"
        )
        event_dict = event.to_dict()
        assert "event_type" in event_dict
        assert "tenant_id" in event_dict

        print("   ✅ Webhook System: OK")
    except Exception as e:
        print(f"   ❌ Webhook System: {e}")
        return False

    # Test 5: API Integration
    print("\n5️⃣ Testing API Integration...")
    try:
        from httpx import AsyncClient
        from app.main import app
        from httpx import ASGITransport

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Test versioned endpoints
            response = await client.get("/api/v1/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ok"
            assert data["version"] == "v1"

            # Test version headers
            assert "X-API-Version" in response.headers
            assert response.headers["X-API-Version"] == "v1"

        print("   ✅ API Integration: OK")
    except Exception as e:
        print(f"   ❌ API Integration: {e}")
        return False

    print("\n🎉 All Enterprise Features: PASSED")
    return True

async def test_endpoint_accessibility():
    """Test that all new endpoints are accessible."""
    print("\n🔗 Testing Endpoint Accessibility...")

    try:
        from httpx import AsyncClient
        from app.main import app
        from httpx import ASGITransport

        endpoints_to_test = [
            # API Versioning
            ("/api/v1/health", 200),
            ("/api/v1/info", 200),

            # Admin API Keys (should be protected)
            ("/features/administration/api-keys/stats", [401, 403]),
            ("/api/v1/administration/api-keys/stats", [401, 403]),

            # MFA endpoints (should be protected)
            ("/api/v1/auth/mfa/status", [401, 403]),

            # Webhook endpoints - /events is public, /endpoints requires auth
            ("/api/v1/webhooks/endpoints", [401, 403]),
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            for endpoint, expected_status in endpoints_to_test:
                try:
                    response = await client.get(endpoint)
                    if isinstance(expected_status, list):
                        assert response.status_code in expected_status, f"{endpoint}: expected {expected_status}, got {response.status_code}"
                    else:
                        assert response.status_code == expected_status, f"{endpoint}: expected {expected_status}, got {response.status_code}"

                    print(f"   ✅ {endpoint}: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ {endpoint}: {e}")
                    return False

        print("   ✅ All endpoints accessible")
        return True

    except Exception as e:
        print(f"   ❌ Endpoint testing failed: {e}")
        return False

async def main():
    """Main test runner."""
    print("🚀 Enterprise SaaS Features Validation")
    print("=" * 50)

    # Set up environment
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://dev_user:dev_password@localhost:5434/fastapi_template_dev"

    try:
        # Test core features
        features_ok = await test_enterprise_features()

        # Test endpoint accessibility
        endpoints_ok = await test_endpoint_accessibility()

        # Final result
        if features_ok and endpoints_ok:
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED - Enterprise features are working!")
            print("🎯 Ready for production use")
            return 0
        else:
            print("\n" + "=" * 50)
            print("❌ SOME TESTS FAILED - Check the output above")
            return 1

    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)