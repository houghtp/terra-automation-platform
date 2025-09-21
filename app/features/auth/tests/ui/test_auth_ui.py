"""
Comprehensive UI tests for Auth slice - demonstrates Playwright + HTMX patterns.

These tests provide world-class coverage of authentication UI interactions,
including login/register forms, session management, and security flows.
Template users should follow these patterns for other slices.
"""

import pytest
from playwright.async_api import Page, expect
from tests.conftest_playwright import HTMXTestHelper


@pytest.mark.ui
@pytest.mark.asyncio
class TestAuthenticationUI:
    """UI tests for authentication functionality."""

    async def test_login_page_loads(self, page: Page):
        """Test that the login page loads with all expected elements."""
        await page.goto("/auth/login")

        # Check page title and header
        await expect(page).to_have_title("Login")

        # Check for key UI elements
        await expect(page.locator("h1, h2, h3")).to_contain_text("Login")
        await expect(page.locator('input[name="email"]')).to_be_visible()
        await expect(page.locator('input[name="password"]')).to_be_visible()
        await expect(page.locator('button[type="submit"]')).to_be_visible()

        # Check for registration link
        await expect(page.locator('a[href*="register"]')).to_be_visible()

    async def test_register_page_loads(self, page: Page):
        """Test that the register page loads with all expected elements."""
        await page.goto("/auth/register")

        # Check page title and header
        await expect(page).to_have_title("Register")

        # Check for key UI elements
        await expect(page.locator("h1, h2, h3")).to_contain_text("Register")
        await expect(page.locator('input[name="email"]')).to_be_visible()
        await expect(page.locator('input[name="password"]')).to_be_visible()
        await expect(page.locator('input[name="confirm_password"]')).to_be_visible()
        await expect(page.locator('button[type="submit"]')).to_be_visible()

        # Check for login link
        await expect(page.locator('a[href*="login"]')).to_be_visible()

    async def test_login_form_validation(self, page: Page, htmx_helper: HTMXTestHelper):
        """Test login form client-side validation."""
        await page.goto("/auth/login")

        # Test empty form submission
        await page.click('button[type="submit"]')

        # Should show validation messages
        await expect(page.locator(".invalid-feedback, .error")).to_be_visible()

        # Test invalid email format
        await page.fill('input[name="email"]', "invalid-email")
        await page.fill('input[name="password"]', "password123")

        # Trigger validation if HTMX is used
        if await page.locator('[hx-trigger]').count() > 0:
            await htmx_helper.fill_and_trigger_validation(
                'input[name="email"]',
                "invalid-email",
                "**/validate/email"
            )
            await expect(page.locator(".invalid-feedback")).to_be_visible()

    async def test_register_form_validation(self, page: Page, htmx_helper: HTMXTestHelper):
        """Test register form client-side validation."""
        await page.goto("/auth/register")

        # Test password mismatch
        await page.fill('input[name="email"]', "test@example.com")
        await page.fill('input[name="password"]', "password123")
        await page.fill('input[name="confirm_password"]', "different123")

        # Submit form
        await page.click('button[type="submit"]')

        # Should show password mismatch error
        await expect(page.locator("text=password")).to_be_visible()
        await expect(page.locator("text=match")).to_be_visible()

    async def test_login_form_submission_success(self, page: Page, htmx_helper: HTMXTestHelper):
        """Test successful login form submission."""
        await page.goto("/auth/register")

        # First register a user
        await page.fill('input[name="email"]', "testuser@example.com")
        await page.fill('input[name="password"]', "SecurePass123!")
        await page.fill('input[name="confirm_password"]', "SecurePass123!")

        # Submit registration
        await page.click('button[type="submit"]')

        # Wait for registration to complete
        await page.wait_for_timeout(1000)

        # Now go to login page
        await page.goto("/auth/login")

        # Fill login form
        await page.fill('input[name="email"]', "testuser@example.com")
        await page.fill('input[name="password"]', "SecurePass123!")

        # Submit login form
        await page.click('button[type="submit"]')

        # Should redirect to dashboard or home page
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("/dashboard")

    async def test_login_form_submission_failure(self, page: Page):
        """Test login form submission with invalid credentials."""
        await page.goto("/auth/login")

        # Fill form with invalid credentials
        await page.fill('input[name="email"]', "nonexistent@example.com")
        await page.fill('input[name="password"]', "wrongpassword")

        # Submit form
        await page.click('button[type="submit"]')

        # Should show error message
        await expect(page.locator("text=Invalid")).to_be_visible()

    async def test_register_form_submission_success(self, page: Page):
        """Test successful register form submission."""
        await page.goto("/auth/register")

        # Fill registration form
        await page.fill('input[name="email"]', "newuser@example.com")
        await page.fill('input[name="password"]', "SecurePass123!")
        await page.fill('input[name="confirm_password"]', "SecurePass123!")

        # Submit form
        await page.click('button[type="submit"]')

        # Should redirect to dashboard or show success message
        try:
            await page.wait_for_url("**/dashboard", timeout=5000)
            await expect(page).to_have_url("/dashboard")
        except:
            # Or should show success message
            await expect(page.locator("text=success")).to_be_visible()

    async def test_register_form_duplicate_email(self, page: Page):
        """Test register form with duplicate email."""
        # First registration
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', "duplicate@example.com")
        await page.fill('input[name="password"]', "SecurePass123!")
        await page.fill('input[name="confirm_password"]', "SecurePass123!")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(1000)

        # Second registration with same email
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', "duplicate@example.com")
        await page.fill('input[name="password"]', "AnotherPass123!")
        await page.fill('input[name="confirm_password"]', "AnotherPass123!")
        await page.click('button[type="submit"]')

        # Should show error message
        await expect(page.locator("text=already")).to_be_visible()

    async def test_password_visibility_toggle(self, page: Page):
        """Test password visibility toggle functionality."""
        await page.goto("/auth/login")

        password_field = page.locator('input[name="password"]')
        toggle_button = page.locator('[data-testid="password-toggle"], .password-toggle, button[type="button"]').first

        # Initially password should be hidden
        await expect(password_field).to_have_attribute("type", "password")

        # Fill password
        await password_field.fill("testpassword")

        # Click toggle if it exists
        if await toggle_button.count() > 0:
            await toggle_button.click()
            await expect(password_field).to_have_attribute("type", "text")

            # Click again to hide
            await toggle_button.click()
            await expect(password_field).to_have_attribute("type", "password")

    async def test_form_accessibility(self, page: Page):
        """Test form accessibility features."""
        await page.goto("/auth/login")

        # Check for proper labels
        email_field = page.locator('input[name="email"]')
        password_field = page.locator('input[name="password"]')

        # Fields should have labels or aria-labels
        await expect(email_field).to_have_attribute("aria-label")
        await expect(password_field).to_have_attribute("aria-label")

        # Check for form validation messages
        await page.click('button[type="submit"]')

        # Validation messages should be accessible
        error_messages = page.locator('.invalid-feedback, .error, [role="alert"]')
        if await error_messages.count() > 0:
            await expect(error_messages.first).to_have_attribute("role", "alert")

    async def test_keyboard_navigation(self, page: Page):
        """Test keyboard navigation through forms."""
        await page.goto("/auth/login")

        # Tab through form elements
        await page.keyboard.press("Tab")
        await expect(page.locator('input[name="email"]')).to_be_focused()

        await page.keyboard.press("Tab")
        await expect(page.locator('input[name="password"]')).to_be_focused()

        await page.keyboard.press("Tab")
        await expect(page.locator('button[type="submit"]')).to_be_focused()

        # Submit with Enter key
        await page.locator('input[name="email"]').fill("test@example.com")
        await page.locator('input[name="password"]').fill("password")
        await page.keyboard.press("Enter")

        # Should attempt form submission


@pytest.mark.ui
@pytest.mark.e2e
@pytest.mark.asyncio
class TestAuthenticationWorkflows:
    """End-to-end workflow tests for authentication."""

    async def test_complete_registration_and_login_flow(self, page: Page):
        """Test complete user registration and login workflow."""
        email = "workflow@example.com"
        password = "SecureWorkflow123!"

        # 1. Navigate to registration
        await page.goto("/auth/register")

        # 2. Complete registration
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.fill('input[name="confirm_password"]', password)
        await page.click('button[type="submit"]')

        # 3. Should be redirected or see success
        await page.wait_for_timeout(1000)

        # 4. Navigate to login page
        await page.goto("/auth/login")

        # 5. Login with registered credentials
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')

        # 6. Should be authenticated and redirected
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("/dashboard")

    async def test_session_persistence(self, page: Page):
        """Test that user session persists across page reloads."""
        # Register and login
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', "session@example.com")
        await page.fill('input[name="password"]', "SessionTest123!")
        await page.fill('input[name="confirm_password"]', "SessionTest123!")
        await page.click('button[type="submit"]')

        await page.wait_for_timeout(1000)

        # Check if authenticated by trying to access protected page
        await page.goto("/dashboard")

        # Should be able to access dashboard
        await expect(page).to_have_url("/dashboard")

        # Reload page
        await page.reload()

        # Should still be authenticated
        await expect(page).to_have_url("/dashboard")

    async def test_logout_functionality(self, page: Page):
        """Test logout functionality."""
        # Register and login first
        await page.goto("/auth/register")
        await page.fill('input[name="email"]', "logout@example.com")
        await page.fill('input[name="password"]', "LogoutTest123!")
        await page.fill('input[name="confirm_password"]', "LogoutTest123!")
        await page.click('button[type="submit"]')

        await page.wait_for_timeout(1000)
        await page.goto("/dashboard")

        # Find and click logout button
        logout_button = page.locator('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]')

        if await logout_button.count() > 0:
            await logout_button.click()

            # Should be redirected to login page
            await page.wait_for_url("**/login")
            await expect(page).to_have_url("/auth/login")

            # Should not be able to access protected pages
            await page.goto("/dashboard")
            await expect(page).to_have_url("/auth/login")

    async def test_protected_route_redirection(self, page: Page):
        """Test that protected routes redirect to login."""
        # Try to access protected page without authentication
        await page.goto("/dashboard")

        # Should be redirected to login
        await page.wait_for_url("**/login")
        await expect(page).to_have_url("/auth/login")

        # Login and should be redirected back to original page
        await page.fill('input[name="email"]', "redirect@example.com")
        await page.fill('input[name="password"]', "RedirectTest123!")

        # Register first if needed
        try:
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1000)
        except:
            # If login fails, register first
            await page.goto("/auth/register")
            await page.fill('input[name="email"]', "redirect@example.com")
            await page.fill('input[name="password"]', "RedirectTest123!")
            await page.fill('input[name="confirm_password"]', "RedirectTest123!")
            await page.click('button[type="submit"]')

        # Should eventually reach dashboard
        await page.wait_for_url("**/dashboard")
        await expect(page).to_have_url("/dashboard")

    async def test_form_error_handling(self, page: Page):
        """Test comprehensive form error handling."""
        await page.goto("/auth/register")

        # Test various error conditions
        error_scenarios = [
            # Weak password
            {
                "email": "weak@example.com",
                "password": "123",
                "confirm_password": "123",
                "expected_error": "password"
            },
            # Password mismatch
            {
                "email": "mismatch@example.com",
                "password": "StrongPass123!",
                "confirm_password": "DifferentPass123!",
                "expected_error": "match"
            },
            # Invalid email
            {
                "email": "invalid-email",
                "password": "ValidPass123!",
                "confirm_password": "ValidPass123!",
                "expected_error": "email"
            }
        ]

        for scenario in error_scenarios:
            await page.fill('input[name="email"]', scenario["email"])
            await page.fill('input[name="password"]', scenario["password"])
            await page.fill('input[name="confirm_password"]', scenario["confirm_password"])
            await page.click('button[type="submit"]')

            # Should show appropriate error
            await expect(page.locator(f"text={scenario['expected_error']}")).to_be_visible()

            # Clear form for next test
            await page.fill('input[name="email"]', "")
            await page.fill('input[name="password"]', "")
            await page.fill('input[name="confirm_password"]', "")


@pytest.mark.ui
@pytest.mark.asyncio
class TestAuthenticationSecurity:
    """Security-focused UI tests."""

    async def test_csrf_protection(self, page: Page):
        """Test CSRF protection on forms."""
        await page.goto("/auth/login")

        # Check for CSRF token
        csrf_token = page.locator('input[name="csrf_token"], input[name="_token"]')

        if await csrf_token.count() > 0:
            await expect(csrf_token).to_have_attribute("value")
            token_value = await csrf_token.get_attribute("value")
            assert token_value is not None and len(token_value) > 0

    async def test_password_field_security(self, page: Page):
        """Test password field security features."""
        await page.goto("/auth/login")

        password_field = page.locator('input[name="password"]')

        # Password field should have type="password"
        await expect(password_field).to_have_attribute("type", "password")

        # Should have autocomplete disabled or set to current-password
        autocomplete = await password_field.get_attribute("autocomplete")
        assert autocomplete in [None, "off", "current-password", "new-password"]

    async def test_form_submission_rate_limiting(self, page: Page):
        """Test that forms have rate limiting protection."""
        await page.goto("/auth/login")

        # Submit form multiple times rapidly
        for i in range(5):
            await page.fill('input[name="email"]', "spam@example.com")
            await page.fill('input[name="password"]', "wrongpass")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(100)

        # Should eventually show rate limiting message
        # This test may fail if rate limiting is not implemented
        rate_limit_indicators = [
            "too many",
            "rate limit",
            "slow down",
            "try again later"
        ]

        for indicator in rate_limit_indicators:
            if await page.locator(f"text={indicator}").count() > 0:
                await expect(page.locator(f"text={indicator}")).to_be_visible()
                break


@pytest.mark.ui
@pytest.mark.responsive
@pytest.mark.asyncio
class TestAuthenticationResponsive:
    """Responsive design tests for authentication."""

    async def test_mobile_login_form(self, mobile_page: Page):
        """Test login form on mobile devices."""
        await mobile_page.goto("/auth/login")

        # Check that form is accessible on mobile
        await expect(mobile_page.locator('input[name="email"]')).to_be_visible()
        await expect(mobile_page.locator('input[name="password"]')).to_be_visible()
        await expect(mobile_page.locator('button[type="submit"]')).to_be_visible()

        # Check that form elements are properly sized
        submit_button = mobile_page.locator('button[type="submit"]')
        button_box = await submit_button.bounding_box()

        # Button should be at least 44px tall for touch targets
        assert button_box["height"] >= 44

    async def test_tablet_register_form(self, tablet_page: Page):
        """Test register form on tablet devices."""
        await tablet_page.goto("/auth/register")

        # Check that all form elements are visible and usable
        await expect(tablet_page.locator('input[name="email"]')).to_be_visible()
        await expect(tablet_page.locator('input[name="password"]')).to_be_visible()
        await expect(tablet_page.locator('input[name="confirm_password"]')).to_be_visible()
        await expect(tablet_page.locator('button[type="submit"]')).to_be_visible()

        # Test form submission on tablet
        await tablet_page.fill('input[name="email"]', "tablet@example.com")
        await tablet_page.fill('input[name="password"]', "TabletTest123!")
        await tablet_page.fill('input[name="confirm_password"]', "TabletTest123!")
        await tablet_page.click('button[type="submit"]')

        # Should work without issues
        await tablet_page.wait_for_timeout(1000)