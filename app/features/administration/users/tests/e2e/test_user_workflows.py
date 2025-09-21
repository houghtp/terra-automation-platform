"""
End-to-end workflow tests for Users slice.

Tests complete user management workflows from start to finish,
demonstrating real-world usage patterns and complex scenarios.
"""

import pytest
from playwright.async_api import Page, expect
from tests.conftest_playwright import HTMXTestHelper
from app.features.administration.users.tests.factories import (
    generate_valid_user_form_data,
    generate_user_update_form_data
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCompleteUserLifecycle:
    """Test complete user lifecycle workflows."""

    async def test_full_user_management_workflow(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test complete workflow: create -> view -> edit -> manage -> delete."""
        # 1. Navigate to user management
        await authenticated_page.goto("/features/administration/users")
        await expect(authenticated_page.locator("h1")).to_contain_text("User Management")

        # 2. Create a new user
        user_data = generate_valid_user_form_data()

        # Open create modal
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        # Fill form
        await authenticated_page.fill('input[name="name"]', user_data["name"])
        await authenticated_page.fill('input[name="email"]', user_data["email"])
        await authenticated_page.fill('input[name="password"]', user_data["password"])
        await authenticated_page.fill('input[name="confirm_password"]', user_data["confirm_password"])
        await authenticated_page.fill('textarea[name="description"]', user_data["description"])

        # Submit form
        await htmx_helper.click_and_wait_htmx(
            'button[type="submit"]',
            "**/administration/users"
        )

        # 3. Verify user appears in list
        await expect(authenticated_page.locator("text=" + user_data["name"])).to_be_visible()
        await expect(authenticated_page.locator("text=" + user_data["email"])).to_be_visible()

        # 4. Edit the user
        user_row = authenticated_page.locator(f'tr:has-text("{user_data["email"]}")')
        await user_row.locator('[data-testid="edit-user-btn"]').click()

        # Wait for edit modal
        await authenticated_page.wait_for_selector("#modal-form")

        update_data = generate_user_update_form_data()
        await authenticated_page.fill('input[name="name"]', update_data["name"])
        await authenticated_page.fill('textarea[name="description"]', update_data["description"])

        # Submit update
        await htmx_helper.click_and_wait_htmx(
            'button[type="submit"]',
            "**/administration/users"
        )

        # 5. Verify updates
        await expect(authenticated_page.locator("text=" + update_data["name"])).to_be_visible()

        # 6. Test user status management
        updated_user_row = authenticated_page.locator(f'tr:has-text("{update_data["name"]}")')

        # Toggle user status via quick actions
        await updated_user_row.locator('[data-testid="toggle-user-status"]').click()

        # Verify status change visual feedback
        await expect(updated_user_row.locator('.status-indicator')).to_have_class(/inactive/)

        # 7. Delete the user
        # Handle confirmation dialog
        authenticated_page.on("dialog", lambda dialog: dialog.accept())
        await updated_user_row.locator('[data-testid="delete-user-btn"]').click()

        # 8. Verify user is removed
        await expect(authenticated_page.locator("text=" + update_data["name"])).not_to_be_visible()

    async def test_bulk_user_operations_workflow(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test bulk operations on multiple users."""
        await authenticated_page.goto("/features/administration/users")

        # Create multiple users for bulk operations
        users_to_create = [generate_valid_user_form_data() for _ in range(3)]

        for user_data in users_to_create:
            # Create each user
            await htmx_helper.click_and_wait_htmx(
                '[data-testid="create-user-btn"]',
                "**/partials/form"
            )

            await authenticated_page.fill('input[name="name"]', user_data["name"])
            await authenticated_page.fill('input[name="email"]', user_data["email"])
            await authenticated_page.fill('input[name="password"]', user_data["password"])
            await authenticated_page.fill('input[name="confirm_password"]', user_data["confirm_password"])

            await htmx_helper.click_and_wait_htmx(
                'button[type="submit"]',
                "**/administration/users"
            )

        # Test bulk selection
        await authenticated_page.click('[data-testid="select-all-users"]')

        # Verify all checkboxes are selected
        checkboxes = authenticated_page.locator('input[type="checkbox"][name="selected_users"]')
        checkbox_count = await checkboxes.count()

        for i in range(checkbox_count):
            await expect(checkboxes.nth(i)).to_be_checked()

        # Test bulk status change
        await authenticated_page.click('[data-testid="bulk-actions-dropdown"]')
        await authenticated_page.click('[data-testid="bulk-deactivate"]')

        # Confirm bulk action
        await authenticated_page.click('[data-testid="confirm-bulk-action"]')

        # Verify all users are now inactive
        for user_data in users_to_create:
            user_row = authenticated_page.locator(f'tr:has-text("{user_data["email"]}")')
            await expect(user_row.locator('.status-indicator')).to_have_class(/inactive/)

    async def test_user_search_and_filter_workflow(self, authenticated_page: Page):
        """Test comprehensive search and filtering workflows."""
        await authenticated_page.goto("/features/administration/users")

        # Test text search
        await authenticated_page.fill('[data-testid="user-search"]', "admin")
        await authenticated_page.press('[data-testid="user-search"]', "Enter")

        # Wait for results to filter
        await authenticated_page.wait_for_timeout(500)

        # Verify search results
        search_results = authenticated_page.locator('[data-testid="user-table"] tbody tr')
        search_count = await search_results.count()

        if search_count > 0:
            # Verify all visible results contain search term
            for i in range(search_count):
                row_text = await search_results.nth(i).text_content()
                assert "admin" in row_text.lower()

        # Test status filter
        await authenticated_page.select_option('[data-testid="status-filter"]', "active")
        await authenticated_page.wait_for_timeout(500)

        # Test role filter
        await authenticated_page.select_option('[data-testid="role-filter"]', "admin")
        await authenticated_page.wait_for_timeout(500)

        # Clear all filters
        await authenticated_page.click('[data-testid="clear-filters"]')
        await authenticated_page.wait_for_timeout(500)

        # Verify all users are visible again
        all_results = authenticated_page.locator('[data-testid="user-table"] tbody tr')
        all_count = await all_results.count()
        assert all_count >= search_count  # Should show more or equal results

    async def test_user_profile_management_workflow(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test detailed user profile management workflow."""
        await authenticated_page.goto("/features/administration/users")

        # Create a user with comprehensive data
        user_data = generate_valid_user_form_data()
        user_data.update({
            "description": "Senior Full Stack Developer with 5+ years experience",
            "tags": ["developer", "senior", "fullstack", "react", "python"]
        })

        # Create user
        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        await authenticated_page.fill('input[name="name"]', user_data["name"])
        await authenticated_page.fill('input[name="email"]', user_data["email"])
        await authenticated_page.fill('input[name="password"]', user_data["password"])
        await authenticated_page.fill('input[name="confirm_password"]', user_data["confirm_password"])
        await authenticated_page.fill('textarea[name="description"]', user_data["description"])

        # Add tags using tag selector
        for tag in user_data["tags"]:
            await authenticated_page.fill('[data-testid="tag-input"]', tag)
            await authenticated_page.press('[data-testid="tag-input"]', "Enter")

        await htmx_helper.click_and_wait_htmx('button[type="submit"]', "**/administration/users")

        # Test viewing user details
        user_row = authenticated_page.locator(f'tr:has-text("{user_data["email"]}")')
        await user_row.locator('[data-testid="view-user-btn"]').click()

        # Verify user details modal/page
        await expect(authenticated_page.locator('[data-testid="user-detail-name"]')).to_contain_text(user_data["name"])
        await expect(authenticated_page.locator('[data-testid="user-detail-email"]')).to_contain_text(user_data["email"])
        await expect(authenticated_page.locator('[data-testid="user-detail-description"]')).to_contain_text(user_data["description"])

        # Verify tags are displayed
        for tag in user_data["tags"]:
            await expect(authenticated_page.locator(f'[data-testid="user-tag"]:has-text("{tag}")')).to_be_visible()

        # Test role assignment workflow
        await authenticated_page.click('[data-testid="change-role-btn"]')
        await authenticated_page.select_option('[data-testid="role-selector"]', "admin")
        await authenticated_page.click('[data-testid="confirm-role-change"]')

        # Verify role change
        await expect(authenticated_page.locator('[data-testid="user-role-display"]')).to_contain_text("Admin")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserPermissionsAndSecurity:
    """Test user permissions and security workflows."""

    async def test_admin_vs_user_permissions_workflow(self, authenticated_page: Page):
        """Test different permission levels and access controls."""
        # This test would require different authenticated sessions
        # For now, we test the UI elements that appear based on permissions

        await authenticated_page.goto("/features/administration/users")

        # Verify admin-level actions are available
        await expect(authenticated_page.locator('[data-testid="create-user-btn"]')).to_be_visible()
        await expect(authenticated_page.locator('[data-testid="bulk-actions-dropdown"]')).to_be_visible()

        # Test that sensitive actions require confirmation
        first_user_row = authenticated_page.locator('[data-testid="user-table"] tbody tr').first

        # Test delete confirmation
        authenticated_page.on("dialog", lambda dialog: dialog.dismiss())  # Dismiss dialog
        await first_user_row.locator('[data-testid="delete-user-btn"]').click()

        # User should still be visible (delete was cancelled)
        await expect(first_user_row).to_be_visible()

    async def test_password_security_workflow(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test password security requirements and validation."""
        await authenticated_page.goto("/features/administration/users")

        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        # Test weak password rejection
        await authenticated_page.fill('input[name="name"]', "Security Test User")
        await authenticated_page.fill('input[name="email"]', "security@test.com")
        await authenticated_page.fill('input[name="password"]', "weak")

        # Trigger password validation
        await authenticated_page.press('input[name="password"]', "Tab")

        # Verify validation message appears
        await expect(authenticated_page.locator('.invalid-feedback')).to_be_visible()
        await expect(authenticated_page.locator('.invalid-feedback')).to_contain_text("password")

        # Test strong password acceptance
        await authenticated_page.fill('input[name="password"]', "StrongPass123!@#")
        await authenticated_page.fill('input[name="confirm_password"]', "StrongPass123!@#")

        # Trigger validation
        await authenticated_page.press('input[name="confirm_password"]', "Tab")

        # Verify validation passes
        await expect(authenticated_page.locator('.valid-feedback')).to_be_visible()

    async def test_data_validation_workflow(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test comprehensive data validation workflows."""
        await authenticated_page.goto("/features/administration/users")

        await htmx_helper.click_and_wait_htmx(
            '[data-testid="create-user-btn"]',
            "**/partials/form"
        )

        # Test email validation
        await authenticated_page.fill('input[name="email"]', "invalid-email")
        await authenticated_page.press('input[name="email"]', "Tab")

        await expect(authenticated_page.locator('.invalid-feedback')).to_contain_text("email")

        # Test duplicate email validation
        await authenticated_page.fill('input[name="email"]', "admin@example.com")  # Assuming this exists
        await authenticated_page.press('input[name="email"]', "Tab")

        # Wait for HTMX validation
        await authenticated_page.wait_for_timeout(500)

        # May show duplicate email error if admin user exists
        error_feedback = authenticated_page.locator('.invalid-feedback')
        if await error_feedback.is_visible():
            await expect(error_feedback).to_contain_text("exists")

        # Test name validation
        await authenticated_page.fill('input[name="name"]', "A")  # Too short
        await authenticated_page.press('input[name="name"]', "Tab")

        await expect(authenticated_page.locator('.invalid-feedback')).to_contain_text("2 characters")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserTableInteractions:
    """Test complex table interactions and data management."""

    async def test_table_sorting_workflow(self, authenticated_page: Page):
        """Test table sorting functionality."""
        await authenticated_page.goto("/features/administration/users")

        # Test sorting by name
        await authenticated_page.click('[data-testid="sort-by-name"]')

        # Wait for table to re-render
        await authenticated_page.wait_for_timeout(500)

        # Verify sorting indicator
        sort_indicator = authenticated_page.locator('[data-testid="sort-by-name"] .sort-indicator')
        await expect(sort_indicator).to_have_class(/asc|desc/)

        # Test reverse sorting
        await authenticated_page.click('[data-testid="sort-by-name"]')
        await authenticated_page.wait_for_timeout(500)

        # Test sorting by different columns
        await authenticated_page.click('[data-testid="sort-by-email"]')
        await authenticated_page.wait_for_timeout(500)

        await authenticated_page.click('[data-testid="sort-by-status"]')
        await authenticated_page.wait_for_timeout(500)

        await authenticated_page.click('[data-testid="sort-by-created"]')
        await authenticated_page.wait_for_timeout(500)

    async def test_table_pagination_workflow(self, authenticated_page: Page):
        """Test table pagination functionality."""
        await authenticated_page.goto("/features/administration/users")

        # Check if pagination controls exist
        pagination = authenticated_page.locator('[data-testid="pagination"]')

        if await pagination.is_visible():
            # Test page size selection
            await authenticated_page.select_option('[data-testid="page-size-selector"]', "25")
            await authenticated_page.wait_for_timeout(500)

            # Test next page navigation
            next_button = authenticated_page.locator('[data-testid="next-page"]')
            if await next_button.is_enabled():
                await next_button.click()
                await authenticated_page.wait_for_timeout(500)

                # Verify page number changed
                await expect(authenticated_page.locator('[data-testid="current-page"]')).to_contain_text("2")

                # Test previous page
                await authenticated_page.click('[data-testid="prev-page"]')
                await authenticated_page.wait_for_timeout(500)
                await expect(authenticated_page.locator('[data-testid="current-page"]')).to_contain_text("1")

            # Test direct page navigation
            page_input = authenticated_page.locator('[data-testid="page-input"]')
            if await page_input.is_visible():
                await page_input.fill("2")
                await page_input.press("Enter")
                await authenticated_page.wait_for_timeout(500)

    async def test_table_export_workflow(self, authenticated_page: Page):
        """Test data export functionality."""
        await authenticated_page.goto("/features/administration/users")

        # Test CSV export
        with authenticated_page.expect_download() as download_info:
            await authenticated_page.click('[data-testid="export-csv"]')

        download = await download_info.value
        assert download.suggested_filename.endswith('.csv')

        # Test filtered export
        await authenticated_page.fill('[data-testid="user-search"]', "admin")
        await authenticated_page.press('[data-testid="user-search"]', "Enter")
        await authenticated_page.wait_for_timeout(500)

        with authenticated_page.expect_download() as filtered_download_info:
            await authenticated_page.click('[data-testid="export-filtered-csv"]')

        filtered_download = await filtered_download_info.value
        assert filtered_download.suggested_filename.endswith('.csv')


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserAccessibilityWorkflow:
    """Test accessibility features and keyboard navigation."""

    async def test_keyboard_navigation_workflow(self, authenticated_page: Page):
        """Test complete keyboard navigation workflow."""
        await authenticated_page.goto("/features/administration/users")

        # Test tab navigation through main elements
        await authenticated_page.press('body', 'Tab')  # Should focus first interactive element

        # Navigate to create button via keyboard
        create_button = authenticated_page.locator('[data-testid="create-user-btn"]')
        await create_button.focus()
        await expect(create_button).to_be_focused()

        # Open modal via keyboard
        await authenticated_page.press('[data-testid="create-user-btn"]', 'Enter')
        await authenticated_page.wait_for_selector('#modal-form')

        # Test tab navigation within modal
        await authenticated_page.press('body', 'Tab')  # Should focus first form field

        name_field = authenticated_page.locator('input[name="name"]')
        await expect(name_field).to_be_focused()

        # Navigate through form fields
        await authenticated_page.press('input[name="name"]', 'Tab')
        await expect(authenticated_page.locator('input[name="email"]')).to_be_focused()

        # Test escape to close modal
        await authenticated_page.press('body', 'Escape')
        await expect(authenticated_page.locator('#modal-form')).not_to_be_visible()

    async def test_screen_reader_workflow(self, authenticated_page: Page):
        """Test screen reader compatibility."""
        await authenticated_page.goto("/features/administration/users")

        # Verify ARIA labels and roles
        await expect(authenticated_page.locator('[data-testid="user-table"]')).to_have_attribute('role', 'table')
        await expect(authenticated_page.locator('[data-testid="create-user-btn"]')).to_have_attribute('aria-label')

        # Test form accessibility
        await authenticated_page.click('[data-testid="create-user-btn"]')
        await authenticated_page.wait_for_selector('#modal-form')

        # Verify form labels are properly associated
        form_fields = ['name', 'email', 'password', 'confirm_password']
        for field in form_fields:
            field_input = authenticated_page.locator(f'input[name="{field}"]')
            input_id = await field_input.get_attribute('id')
            if input_id:
                label = authenticated_page.locator(f'label[for="{input_id}"]')
                await expect(label).to_be_visible()

    async def test_high_contrast_workflow(self, authenticated_page: Page):
        """Test high contrast mode compatibility."""
        # Enable high contrast simulation
        await authenticated_page.emulate_media(color_scheme='dark')

        await authenticated_page.goto("/features/administration/users")

        # Verify important elements are still visible and accessible
        await expect(authenticated_page.locator('[data-testid="create-user-btn"]')).to_be_visible()
        await expect(authenticated_page.locator('[data-testid="user-table"]')).to_be_visible()

        # Test form visibility in high contrast
        await authenticated_page.click('[data-testid="create-user-btn"]')
        await authenticated_page.wait_for_selector('#modal-form')

        form_elements = [
            'input[name="name"]',
            'input[name="email"]',
            'button[type="submit"]'
        ]

        for element in form_elements:
            await expect(authenticated_page.locator(element)).to_be_visible()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestUserPerformanceWorkflows:
    """Test performance with realistic data volumes."""

    async def test_large_user_list_performance(self, authenticated_page: Page):
        """Test performance with large user datasets."""
        # This test assumes a large dataset has been seeded
        await authenticated_page.goto("/features/administration/users")

        import time
        start_time = time.time()

        # Wait for table to load completely
        await authenticated_page.wait_for_selector('[data-testid="user-table"] tbody tr')

        load_time = time.time() - start_time

        # Assert reasonable load time (adjust threshold as needed)
        assert load_time < 3.0, f"Page took {load_time}s to load (> 3s threshold)"

        # Test search performance with large dataset
        start_time = time.time()

        await authenticated_page.fill('[data-testid="user-search"]', "test")
        await authenticated_page.press('[data-testid="user-search"]', "Enter")

        # Wait for search results
        await authenticated_page.wait_for_timeout(1000)

        search_time = time.time() - start_time
        assert search_time < 2.0, f"Search took {search_time}s (> 2s threshold)"

    async def test_rapid_user_operations(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test rapid succession of user operations."""
        await authenticated_page.goto("/features/administration/users")

        # Perform rapid create operations
        for i in range(3):
            user_data = generate_valid_user_form_data()
            user_data["email"] = f"rapid{i}@test.com"

            await htmx_helper.click_and_wait_htmx(
                '[data-testid="create-user-btn"]',
                "**/partials/form"
            )

            await authenticated_page.fill('input[name="name"]', user_data["name"])
            await authenticated_page.fill('input[name="email"]', user_data["email"])
            await authenticated_page.fill('input[name="password"]', user_data["password"])
            await authenticated_page.fill('input[name="confirm_password"]', user_data["confirm_password"])

            await htmx_helper.click_and_wait_htmx(
                'button[type="submit"]',
                "**/administration/users"
            )

            # Verify user was created
            await expect(authenticated_page.locator(f"text={user_data['email']}")).to_be_visible()

        # Test rapid status changes
        user_rows = authenticated_page.locator('[data-testid="user-table"] tbody tr')
        row_count = min(await user_rows.count(), 3)

        for i in range(row_count):
            row = user_rows.nth(i)
            toggle_button = row.locator('[data-testid="toggle-user-status"]')
            if await toggle_button.is_visible():
                await toggle_button.click()
                await authenticated_page.wait_for_timeout(100)  # Brief pause between operations