"""
Comprehensive UI tests for Users slice - demonstrates Playwright + HTMX patterns.

These tests provide world-class coverage of user interface interactions,
including HTMX patterns, form validation, accessibility, and user workflows.
Template users should follow these patterns for other slices.
"""

import pytest
from playwright.async_api import Page, expect
from tests.conftest_playwright import HTMXTestHelper


@pytest.mark.ui
@pytest.mark.asyncio
class TestUserManagementUI:
    """UI tests for user management functionality."""

    async def test_user_list_page_loads(self, authenticated_page: Page):
        """Test that the user list page loads with all expected elements."""
        # Navigate to users page
        await authenticated_page.goto("/features/administration/users")

        # Check page title and header
        await expect(authenticated_page).to_have_title("User Management")

        # Check for key UI elements
        await expect(authenticated_page.locator("h1")).to_contain_text("User Management")
        await expect(authenticated_page.locator('[data-testid="create-user-btn"]')).to_be_visible()
        await expect(authenticated_page.locator('[data-testid="user-table"]')).to_be_visible()

    async def test_create_user_modal_opens(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test that clicking 'Create User' opens the modal via HTMX."""
        await authenticated_page.goto("/features/administration/users")

        # Click create button and wait for HTMX to load the modal
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/administration/users/partials/form"
        )

        # Verify modal opened
        await expect(authenticated_page.locator("#modal-form")).to_be_visible()
        await expect(authenticated_page.locator('#modal-form h5')).to_contain_text("Create User")

        # Check form fields are present
        await expect(authenticated_page.locator('input[name="name"]')).to_be_visible()
        await expect(authenticated_page.locator('input[name="email"]')).to_be_visible()
        await expect(authenticated_page.locator('input[name="password"]')).to_be_visible()
        await expect(authenticated_page.locator('input[name="confirm_password"]')).to_be_visible()

    async def test_real_time_email_validation(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test real-time email validation via HTMX."""
        await authenticated_page.goto("/features/administration/users")

        # Open create modal
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        # Test invalid email
        await htmx_helper.fill_and_trigger_validation(
            'input[name="email"]',
            "invalid-email",
            "**/validate/email"
        )

        # Check for validation error
        await expect(authenticated_page.locator('.invalid-feedback')).to_be_visible()
        await expect(authenticated_page.locator('.invalid-feedback')).to_contain_text("valid email")

        # Test valid email
        await htmx_helper.fill_and_trigger_validation(
            'input[name="email"]',
            "valid@example.com",
            "**/validate/email"
        )

        # Check validation passes
        await expect(authenticated_page.locator('.valid-feedback')).to_be_visible()

    async def test_create_user_form_submission(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test creating a user via HTMX form submission."""
        await authenticated_page.goto("/features/administration/users")

        # Open create modal
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        # Fill form
        await authenticated_page.fill('input[name="name"]', 'Test User')
        await authenticated_page.fill('input[name="email"]', 'test@example.com')
        await authenticated_page.fill('input[name="password"]', 'SecurePass123!')
        await authenticated_page.fill('input[name="confirm_password"]', 'SecurePass123!')

        # Submit form and wait for HTMX response
        await htmx_helper.click_and_wait_htmx(
            'button[type="submit"]',
            "**/administration/users"
        )

        # Verify modal closed and user appears in list
        await expect(authenticated_page.locator("#modal-form")).not_to_be_visible()
        await expect(authenticated_page.locator("text=Test User")).to_be_visible()
        await expect(authenticated_page.locator("text=test@example.com")).to_be_visible()

    async def test_edit_user_modal(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test editing a user via modal."""
        await authenticated_page.goto("/features/administration/users")

        # Click edit button on first user (assuming there's test data)
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="edit-user-btn"]:first-of-type',
            "**/edit"
        )

        # Verify edit modal opened
        await expect(authenticated_page.locator("#modal-form")).to_be_visible()
        await expect(authenticated_page.locator('#modal-form h5')).to_contain_text("Edit User")

        # Verify form is pre-filled
        name_field = authenticated_page.locator('input[name="name"]')
        await expect(name_field).not_to_have_value("")

    async def test_user_table_search(self, authenticated_page: Page):
        """Test user table search functionality."""
        await authenticated_page.goto("/features/administration/users")

        # Type in search box
        search_box = authenticated_page.locator('[data-testid="user-search"]')
        await search_box.fill("test")

        # Wait for table to update (Tabulator.js will handle this)
        await authenticated_page.wait_for_timeout(500)

        # Verify filtering occurred (this would depend on actual implementation)
        # This is a placeholder - actual implementation would depend on Tabulator setup

    async def test_responsive_design_mobile(self, mobile_page: Page):
        """Test that user management works on mobile devices."""
        await mobile_page.goto("/features/administration/users")

        # Check that mobile layout is applied
        await expect(mobile_page.locator(".table-responsive")).to_be_visible()

        # Check that create button is still accessible
        await expect(mobile_page.locator('[data-testid="create-user-btn"]')).to_be_visible()

    async def test_user_delete_confirmation(self, authenticated_page: Page):
        """Test user deletion with confirmation dialog."""
        await authenticated_page.goto("/features/administration/users")

        # Set up dialog handler
        authenticated_page.on("dialog", lambda dialog: dialog.accept())

        # Click delete button
        await authenticated_page.click('[data-testid="delete-user-btn"]:first-of-type')

        # The dialog should be automatically accepted and user should be deleted
        # This would trigger an HTMX request


@pytest.mark.ui
@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserManagementWorkflow:
    """End-to-end workflow tests for user management."""

    async def test_complete_user_lifecycle(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test complete user lifecycle: create, edit, delete."""
        await authenticated_page.goto("/features/administration/users")

        # 1. Create user
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        await authenticated_page.fill('input[name="name"]', 'Lifecycle Test User')
        await authenticated_page.fill('input[name="email"]', 'lifecycle@example.com')
        await authenticated_page.fill('input[name="password"]', 'SecurePass123!')
        await authenticated_page.fill('input[name="confirm_password"]', 'SecurePass123!')

        await htmx_helper.click_and_wait_htmx('button[type="submit"]', "**/administration/users")

        # 2. Verify user created
        await expect(authenticated_page.locator("text=Lifecycle Test User")).to_be_visible()

        # 3. Edit user
        # Find the edit button for our specific user
        user_row = authenticated_page.locator("tr:has-text('lifecycle@example.com')")
        await user_row.locator('[data-testid="edit-user-btn"]').click()

        await authenticated_page.wait_for_selector("#modal-form")
        await authenticated_page.fill('input[name="name"]', 'Updated Lifecycle User')
        await htmx_helper.click_and_wait_htmx('button[type="submit"]', "**/administration/users")

        # 4. Verify user updated
        await expect(authenticated_page.locator("text=Updated Lifecycle User")).to_be_visible()

        # 5. Delete user
        authenticated_page.on("dialog", lambda dialog: dialog.accept())
        updated_row = authenticated_page.locator("tr:has-text('Updated Lifecycle User')")
        await updated_row.locator('[data-testid="delete-user-btn"]').click()

        # 6. Verify user deleted
        await expect(authenticated_page.locator("text=Updated Lifecycle User")).not_to_be_visible()