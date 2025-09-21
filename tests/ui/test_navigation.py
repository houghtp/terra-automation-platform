"""
Cross-slice UI tests for navigation and global functionality.

These tests verify that the overall application navigation
and cross-slice interactions work correctly.
"""

import pytest
from playwright.async_api import Page, expect


@pytest.mark.ui
@pytest.mark.skip(reason="UI tests require Playwright fixtures and authentication setup")
@pytest.mark.asyncio
class TestGlobalNavigation:
    """Test global navigation and cross-slice functionality."""

    async def test_main_navigation_menu(self, authenticated_page: Page):
        """Test that all main navigation links work."""
        # Start at dashboard
        await authenticated_page.goto("/dashboard")

        # Test navigation to each slice
        navigation_items = [
            ("Users", "/features/administration/users", "User Management"),
            ("Tenants", "/features/administration/tenants", "Tenant Management"),
            ("Secrets", "/features/administration/secrets", "Secrets Management"),
            ("Audit", "/features/administration/audit", "Audit Dashboard"),
        ]

        for nav_text, url, page_title in navigation_items:
            # Click navigation item
            await authenticated_page.click(f'nav a:has-text("{nav_text}")')

            # Verify we're on the correct page
            await expect(authenticated_page).to_have_url(f"**{url}")
            await expect(authenticated_page.locator("h1")).to_contain_text(page_title)

    async def test_breadcrumb_navigation(self, authenticated_page: Page):
        """Test breadcrumb navigation works correctly."""
        # Navigate deep into a slice
        await authenticated_page.goto("/features/administration/users")

        # Check breadcrumbs are present
        await expect(authenticated_page.locator(".breadcrumb")).to_be_visible()
        await expect(authenticated_page.locator(".breadcrumb")).to_contain_text("Administration")
        await expect(authenticated_page.locator(".breadcrumb")).to_contain_text("Users")

    async def test_user_profile_dropdown(self, authenticated_page: Page):
        """Test user profile dropdown functionality."""
        await authenticated_page.goto("/dashboard")

        # Click user profile dropdown
        await authenticated_page.click('[data-testid="user-profile-dropdown"]')

        # Check dropdown items
        await expect(authenticated_page.locator("text=Profile")).to_be_visible()
        await expect(authenticated_page.locator("text=Settings")).to_be_visible()
        await expect(authenticated_page.locator("text=Logout")).to_be_visible()

    async def test_logout_functionality(self, authenticated_page: Page):
        """Test logout redirects to login page."""
        await authenticated_page.goto("/dashboard")

        # Click logout
        await authenticated_page.click('[data-testid="user-profile-dropdown"]')
        await authenticated_page.click("text=Logout")

        # Should redirect to login
        await expect(authenticated_page).to_have_url("**/auth/login")

    async def test_responsive_navigation_mobile(self, mobile_page: Page):
        """Test navigation works on mobile devices."""
        # Login on mobile (this would need actual auth setup)
        await mobile_page.goto("/dashboard")

        # Check mobile menu burger
        await expect(mobile_page.locator('[data-testid="mobile-menu-toggle"]')).to_be_visible()

        # Open mobile menu
        await mobile_page.click('[data-testid="mobile-menu-toggle"]')

        # Check navigation items are visible
        await expect(mobile_page.locator("nav a:has-text('Users')")).to_be_visible()
        await expect(mobile_page.locator("nav a:has-text('Tenants')")).to_be_visible()


@pytest.mark.ui
@pytest.mark.skip(reason="UI tests require Playwright fixtures and authentication setup")
@pytest.mark.asyncio
class TestGlobalUIComponents:
    """Test global UI components that appear across slices."""

    async def test_toast_notifications(self, authenticated_page: Page):
        """Test toast notification system works."""
        await authenticated_page.goto("/features/administration/users")

        # Trigger an action that should show a toast (e.g., create user)
        await authenticated_page.click('[data-testid="create-user-btn"]')

        # Fill and submit form to trigger success toast
        await authenticated_page.fill('input[name="name"]', 'Toast Test User')
        await authenticated_page.fill('input[name="email"]', 'toast@example.com')
        await authenticated_page.fill('input[name="password"]', 'SecurePass123!')
        await authenticated_page.fill('input[name="confirm_password"]', 'SecurePass123!')
        await authenticated_page.click('button[type="submit"]')

        # Check for success toast
        await expect(authenticated_page.locator('.toast')).to_be_visible()
        await expect(authenticated_page.locator('.toast')).to_contain_text("success")

    async def test_loading_states(self, authenticated_page: Page):
        """Test loading indicators appear during long operations."""
        await authenticated_page.goto("/features/administration/users")

        # Trigger an action that might show loading
        await authenticated_page.click('[data-testid="refresh-data-btn"]')

        # Check for loading indicator (if implemented)
        # This would depend on actual implementation
        # await expect(authenticated_page.locator('[data-testid="loading-spinner"]')).to_be_visible()

    async def test_error_handling_ui(self, authenticated_page: Page):
        """Test error states are displayed correctly."""
        # This would test error boundaries and error messages
        # Implementation would depend on actual error handling

    async def test_accessibility_basics(self, authenticated_page: Page):
        """Test basic accessibility features."""
        await authenticated_page.goto("/features/administration/users")

        # Check for proper heading structure
        h1_count = await authenticated_page.locator("h1").count()
        assert h1_count == 1, "Page should have exactly one h1"

        # Check for alt text on images
        images = authenticated_page.locator("img")
        count = await images.count()
        for i in range(count):
            img = images.nth(i)
            alt_text = await img.get_attribute("alt")
            assert alt_text is not None, f"Image {i} missing alt text"

        # Check for proper form labels
        inputs = authenticated_page.locator("input[type='text'], input[type='email'], input[type='password']")
        input_count = await inputs.count()
        for i in range(input_count):
            input_elem = inputs.nth(i)
            input_id = await input_elem.get_attribute("id")
            if input_id:
                label = authenticated_page.locator(f"label[for='{input_id}']")
                await expect(label).to_be_visible()


@pytest.mark.ui
@pytest.mark.performance
@pytest.mark.skip(reason="UI tests require Playwright fixtures and authentication setup")
@pytest.mark.asyncio
class TestUIPerformance:
    """Test UI performance characteristics."""

    async def test_page_load_times(self, authenticated_page: Page):
        """Test that pages load within reasonable time."""
        pages_to_test = [
            "/dashboard",
            "/features/administration/users",
            "/features/administration/tenants",
            "/features/administration/secrets",
            "/features/administration/audit"
        ]

        for page_url in pages_to_test:
            start_time = authenticated_page.evaluate("() => performance.now()")
            await authenticated_page.goto(page_url)
            await authenticated_page.wait_for_load_state("networkidle")
            end_time = authenticated_page.evaluate("() => performance.now()")

            load_time = end_time - start_time
            assert load_time < 3000, f"Page {page_url} took {load_time}ms to load (>3s)"

    async def test_htmx_response_times(self, authenticated_page: Page):
        """Test HTMX requests complete quickly."""
        await authenticated_page.goto("/features/administration/users")

        # Measure HTMX modal load time
        start_time = authenticated_page.evaluate("() => performance.now()")

        # Click create button
        async with authenticated_page.expect_response("**/partials/form") as response_info:
            await authenticated_page.click('[data-testid="create-user-btn"]')

        response = await response_info.value
        end_time = authenticated_page.evaluate("() => performance.now()")

        htmx_time = end_time - start_time
        assert htmx_time < 1000, f"HTMX request took {htmx_time}ms (>1s)"
        assert response.status == 200, f"HTMX response status: {response.status}"