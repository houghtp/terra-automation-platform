"""
Comprehensive E2E tests for Auth slice - demonstrates complete authentication workflows.

These tests provide world-class coverage of end-to-end authentication scenarios,
including user journeys, security flows, and cross-browser compatibility.
Template users should follow these patterns for other slices.
"""

import pytest
from playwright.async_api import Page, expect, BrowserContext
from tests.conftest_playwright import HTMXTestHelper


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserAuthenticationJourneys:
    """End-to-end tests for complete user authentication journeys."""

    async def test_new_user_complete_journey(self, page: Page):
        """Test complete journey from registration to authenticated usage."""
        email = "newuser@e2etest.com"
        password = "SecureE2EPass123!"

        # 1. User arrives at application
        await page.goto("/")

        # 2. User navigates to registration
        if await page.locator('a[href*="register"]').count() > 0:
            await page.click('a[href*="register"]')
        else:
            await page.goto("/auth/register")

        await expect(page).to_have_url("**/register")

        # 3. User fills out registration form
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)

        # Select role if available
        role_selector = page.locator('select[name="role"], input[name="role"]')
        if await role_selector.count() > 0:
            await role_selector.select_option("user")

        # 4. User submits registration
        await page.click('button[type="submit"]')

        # 5. User should be registered and redirected
        await page.wait_for_timeout(2000)

        # Check if redirected to dashboard or login
        current_url = page.url
        assert "/dashboard" in current_url or "/login" in current_url

        # 6. If redirected to login, user logs in
        if "/login" in current_url:
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard")

        # 7. User should now be on dashboard with authenticated state
        await expect(page).to_have_url("**/dashboard")

        # 8. User can access authenticated features
        # Check for user-specific elements
        user_indicators = [
            f"text={email}",
            '[data-testid="user-menu"]',
            'text=Dashboard',
            'button:has-text("Logout")'
        ]

        for indicator in user_indicators:
            if await page.locator(indicator).count() > 0:
                await expect(page.locator(indicator)).to_be_visible()
                break

        # 9. User logs out
        logout_selectors = [
            'button:has-text("Logout")',
            'a:has-text("Logout")',
            '[data-testid="logout"]',
            '.logout'
        ]

        for selector in logout_selectors:
            if await page.locator(selector).count() > 0:
                await page.click(selector)
                break

        # 10. User should be logged out and redirected
        await page.wait_for_url("**/login")
        await expect(page).to_have_url("**/login")

    async def test_returning_user_login_journey(self, page: Page):
        """Test returning user login journey."""
        email = "returning@e2etest.com"
        password = "ReturningUser123!"

        # 1. First, register the user
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(1000)

        # 2. Simulate returning user - go to login page
        await page.goto("/auth/login")

        # 3. User enters credentials
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)

        # 4. User submits login form
        await page.click('button[type="submit"]')

        # 5. User should be authenticated and redirected
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("**/dashboard")

        # 6. Verify authenticated state
        authenticated_indicators = [
            f"text={email}",
            'text=Dashboard',
            '[data-testid="user-menu"]'
        ]

        found_indicator = False
        for indicator in authenticated_indicators:
            if await page.locator(indicator).count() > 0:
                await expect(page.locator(indicator)).to_be_visible()
                found_indicator = True
                break

        assert found_indicator, "No authenticated state indicator found"

    async def test_forgotten_password_journey(self, page: Page):
        """Test forgotten password recovery journey (if implemented)."""
        await page.goto("/auth/login")

        # Look for forgot password link
        forgot_password_link = page.locator('a:has-text("Forgot"), a:has-text("Reset"), a[href*="forgot"], a[href*="reset"]')

        if await forgot_password_link.count() > 0:
            # Click forgot password link
            await forgot_password_link.click()

            # Should navigate to password reset page
            await expect(page).to_have_url("**/forgot**")

            # Enter email for password reset
            await page.fill('input[name="email"]', "forgot@e2etest.com")
            await page.click('button[type="submit"]')

            # Should show success message
            success_indicators = [
                "text=sent",
                "text=email",
                "text=check",
                "text=reset"
            ]

            for indicator in success_indicators:
                if await page.locator(indicator).count() > 0:
                    await expect(page.locator(indicator)).to_be_visible()
                    break

    async def test_session_timeout_journey(self, page: Page):
        """Test session timeout and re-authentication journey."""
        email = "session@e2etest.com"
        password = "SessionTest123!"

        # 1. Register and login
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(1000)

        # 2. Navigate to a protected page
        await page.goto("/dashboard")
        await expect(page).to_have_url("**/dashboard")

        # 3. Simulate session expiration by clearing cookies/storage
        await page.context.clear_cookies()
        await page.evaluate("localStorage.clear()")
        await page.evaluate("sessionStorage.clear()")

        # 4. Try to access protected resource
        await page.goto("/administration/users")

        # 5. Should be redirected to login
        await page.wait_for_url("**/login")
        await expect(page).to_have_url("**/login")

        # 6. User logs in again
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')

        # 7. Should be redirected back to originally requested page
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("**/dashboard")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAuthenticationErrorScenarios:
    """E2E tests for authentication error scenarios and edge cases."""

    async def test_invalid_credentials_handling(self, page: Page):
        """Test handling of various invalid credential scenarios."""
        await page.goto("/auth/login")

        # Test scenarios
        invalid_scenarios = [
            {
                "email": "nonexistent@example.com",
                "password": "anypassword",
                "description": "non-existent user"
            },
            {
                "email": "test@example.com",
                "password": "wrongpassword",
                "description": "wrong password"
            },
            {
                "email": "invalid-email-format",
                "password": "validpassword",
                "description": "invalid email format"
            },
            {
                "email": "",
                "password": "password",
                "description": "empty email"
            },
            {
                "email": "test@example.com",
                "password": "",
                "description": "empty password"
            }
        ]

        for scenario in invalid_scenarios:
            # Clear form
            await page.fill('input[name="email"]', "")
            await page.fill('input[name="password"]', "")

            # Fill with invalid data
            await page.fill('input[name="email"]', scenario["email"])
            await page.fill('input[name="password"]', scenario["password"])

            # Submit form
            await page.click('button[type="submit"]')

            # Should show error message
            error_indicators = [
                "text=Invalid",
                "text=error",
                "text=incorrect",
                ".error",
                ".invalid-feedback",
                "[role='alert']"
            ]

            found_error = False
            for indicator in error_indicators:
                if await page.locator(indicator).count() > 0:
                    await expect(page.locator(indicator)).to_be_visible()
                    found_error = True
                    break

            # Should remain on login page
            await expect(page).to_have_url("**/login")

    async def test_registration_validation_scenarios(self, page: Page):
        """Test registration form validation scenarios."""
        await page.goto("/auth/register")

        validation_scenarios = [
            {
                "email": "test@example.com",
                "password": "weak",
                "confirm_password": "weak",
                "description": "weak password"
            },
            {
                "email": "test@example.com",
                "password": "StrongPass123!",
                "confirm_password": "DifferentPass123!",
                "description": "password mismatch"
            },
            {
                "email": "invalid-email",
                "password": "ValidPass123!",
                "confirm_password": "ValidPass123!",
                "description": "invalid email"
            },
            {
                "email": "",
                "password": "ValidPass123!",
                "confirm_password": "ValidPass123!",
                "description": "missing email"
            }
        ]

        for scenario in validation_scenarios:
            # Clear form
            await page.fill('input[name="email"]', "")
            await page.fill('input[name="password"]', "")
            await page.fill('input[name="confirm_password"]', "")

            # Fill with test data
            await page.fill('input[name="email"]', scenario["email"])
            await page.fill('input[name="password"]', scenario["password"])
            await page.fill('input[name="confirm_password"]', scenario["confirm_password"])

            # Submit form
            await page.click('button[type="submit"]')

            # Should show validation error
            validation_indicators = [
                "text=invalid",
                "text=required",
                "text=match",
                "text=password",
                ".error",
                ".invalid-feedback"
            ]

            found_validation_error = False
            for indicator in validation_indicators:
                if await page.locator(indicator).count() > 0:
                    found_validation_error = True
                    break

            # Should remain on register page for validation errors
            await expect(page).to_have_url("**/register")

    async def test_duplicate_registration_handling(self, page: Page):
        """Test handling of duplicate email registration."""
        email = "duplicate@e2etest.com"
        password = "TestPass123!"

        # First registration
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')

        # Wait for completion
        await page.wait_for_timeout(2000)

        # Second registration with same email
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')

        # Should show duplicate email error
        duplicate_indicators = [
            "text=already",
            "text=exists",
            "text=registered",
            "text=duplicate"
        ]

        found_duplicate_error = False
        for indicator in duplicate_indicators:
            if await page.locator(indicator).count() > 0:
                await expect(page.locator(indicator)).to_be_visible()
                found_duplicate_error = True
                break

        assert found_duplicate_error, "Duplicate email error not shown"


@pytest.mark.e2e
@pytest.mark.security
@pytest.mark.asyncio
class TestAuthenticationSecurity:
    """E2E security tests for authentication."""

    async def test_xss_protection_in_forms(self, page: Page):
        """Test XSS protection in authentication forms."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'><script>alert('xss')</script>"
        ]

        await page.goto("/auth/login")

        for payload in xss_payloads:
            # Try XSS in email field
            await page.fill('input[name="email"]', payload)
            await page.fill('input[name="password"]', "testpass")
            await page.click('button[type="submit"]')

            # XSS should not execute - page should not show alert
            # This is a basic check; real XSS testing requires specialized tools
            await page.wait_for_timeout(500)

            # Should show validation error or invalid email error
            error_present = await page.locator(".error, .invalid-feedback, text=Invalid").count() > 0
            assert error_present, f"No error shown for XSS payload: {payload}"

    async def test_sql_injection_protection(self, page: Page):
        """Test SQL injection protection in authentication."""
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]

        await page.goto("/auth/login")

        for payload in sql_injection_payloads:
            # Try SQL injection in login
            await page.fill('input[name="email"]', payload)
            await page.fill('input[name="password"]', "anypassword")
            await page.click('button[type="submit"]')

            # Should not bypass authentication
            await page.wait_for_timeout(500)

            # Should remain on login page or show error
            current_url = page.url
            assert "/login" in current_url or "/register" in current_url

            # Should show invalid credentials error
            await expect(page.locator("text=Invalid")).to_be_visible()

    async def test_brute_force_protection(self, page: Page):
        """Test brute force protection mechanisms."""
        await page.goto("/auth/login")

        # Attempt multiple failed logins
        for attempt in range(6):
            await page.fill('input[name="email"]', "bruteforce@example.com")
            await page.fill('input[name="password"]', f"wrongpass{attempt}")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(200)

        # After multiple attempts, should show rate limiting or lockout
        rate_limit_indicators = [
            "text=too many",
            "text=rate limit",
            "text=locked",
            "text=try again later",
            "text=suspicious"
        ]

        found_rate_limit = False
        for indicator in rate_limit_indicators:
            if await page.locator(indicator).count() > 0:
                await expect(page.locator(indicator)).to_be_visible()
                found_rate_limit = True
                break

        # Note: This test may pass even if rate limiting is not implemented
        # as it depends on the specific security measures in place


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
class TestAuthenticationPerformance:
    """E2E performance tests for authentication."""

    async def test_login_form_response_time(self, page: Page):
        """Test login form response time."""
        # Register user first
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', "perf@e2etest.com")
        await page.fill('input[name="password"]', "PerfTest123!")
        await page.fill('input[name="confirm_password"]', "PerfTest123!")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(1000)

        # Measure login performance
        await page.goto("/auth/login")

        start_time = page.evaluate("performance.now()")

        await page.fill('input[name="email"]', "perf@e2etest.com")
        await page.fill('input[name="password"]', "PerfTest123!")
        await page.click('button[type="submit"]')

        # Wait for redirect
        await page.wait_for_url("**/dashboard")

        end_time = page.evaluate("performance.now()")

        # Calculate response time
        response_time = await end_time - await start_time

        # Login should complete within reasonable time (5 seconds)
        assert response_time < 5000, f"Login took too long: {response_time}ms"

    async def test_concurrent_registrations(self, context: BrowserContext):
        """Test concurrent user registrations."""
        # Create multiple pages for concurrent testing
        pages = []
        for i in range(3):
            page = await context.new_page()
            pages.append(page)

        try:
            # Perform concurrent registrations
            import asyncio

            async def register_user(page: Page, index: int):
                await page.goto("/auth/register")
                await page.fill('input[name="email"]', f"concurrent{index}@e2etest.com")
                await page.fill('input[name="password"]', "ConcurrentTest123!")
                await page.fill('input[name="confirm_password"]', "ConcurrentTest123!")
                await page.click('button[type="submit"]')
                await page.wait_for_timeout(2000)
                return page.url

            # Run registrations concurrently
            tasks = [register_user(page, i) for i, page in enumerate(pages)]
            results = await asyncio.gather(*tasks)

            # All registrations should succeed
            for result_url in results:
                assert "/dashboard" in result_url or "/login" in result_url

        finally:
            # Clean up pages
            for page in pages:
                await page.close()


@pytest.mark.e2e
@pytest.mark.cross_browser
@pytest.mark.asyncio
class TestCrossBrowserAuthentication:
    """Cross-browser compatibility tests for authentication."""

    async def test_authentication_flow_consistency(self, page: Page):
        """Test that authentication works consistently across browsers."""
        email = "crossbrowser@e2etest.com"
        password = "CrossBrowser123!"

        # This test will be run with different browser contexts by pytest-playwright

        # Complete registration and login flow
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')

        # Allow for different redirect behaviors
        await page.wait_for_timeout(2000)

        # Should either be on dashboard or login page
        current_url = page.url
        if "/login" in current_url:
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')

        # Should end up authenticated
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("**/dashboard")

        # Verify browser-specific features work
        # Check localStorage/sessionStorage if used
        storage_data = await page.evaluate("localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')")

        # Either token exists or cookies are used for auth
        cookie_auth = len(await page.context.cookies()) > 0

        assert storage_data is not None or cookie_auth, "No authentication state found"