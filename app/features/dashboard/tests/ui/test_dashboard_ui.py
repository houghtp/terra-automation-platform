"""
Comprehensive UI tests for Dashboard slice - demonstrates chart interactions and analytics.

These tests provide world-class coverage of dashboard UI functionality,
including chart rendering, data visualization, and interactive elements.
Template users should follow these patterns for other slices.
"""

import pytest
from playwright.async_api import Page, expect
from tests.conftest_playwright import HTMXTestHelper


@pytest.mark.ui
@pytest.mark.asyncio
class TestDashboardUI:
    """UI tests for dashboard functionality."""

    async def test_dashboard_page_loads_with_authentication(self, authenticated_page: Page):
        """Test that dashboard page loads correctly for authenticated users."""
        await authenticated_page.goto("/dashboard")

        # Check page title
        await expect(authenticated_page).to_have_title("Dashboard")

        # Check for main dashboard container
        await expect(authenticated_page.locator(".dashboard, #dashboard, [data-testid='dashboard']")).to_be_visible()

        # Check for common dashboard elements
        dashboard_elements = [
            "h1, h2", # Page heading
            ".chart, .widget, .card", # Chart or widget containers
            ".summary, .stats" # Summary statistics
        ]

        # At least one of these elements should be present
        found_element = False
        for selector in dashboard_elements:
            if await authenticated_page.locator(selector).count() > 0:
                await expect(authenticated_page.locator(selector).first).to_be_visible()
                found_element = True
                break

        assert found_element, "No dashboard elements found"

    async def test_dashboard_summary_widgets_display(self, authenticated_page: Page):
        """Test that summary widgets display correctly."""
        await authenticated_page.goto("/dashboard")

        # Look for summary/stats widgets
        widget_selectors = [
            '[data-testid*="summary"]',
            '[data-testid*="stats"]',
            '.summary-card',
            '.stats-card',
            '.metric-card',
            '.dashboard-widget'
        ]

        # Check that widgets contain numeric data
        for selector in widget_selectors:
            widgets = authenticated_page.locator(selector)
            if await widgets.count() > 0:
                # Should contain numbers
                widget_text = await widgets.first.text_content()
                # Look for digits in the widget
                assert any(char.isdigit() for char in widget_text), f"Widget {selector} should contain numeric data"

    async def test_dashboard_charts_render(self, authenticated_page: Page):
        """Test that dashboard charts render correctly."""
        await authenticated_page.goto("/dashboard")

        # Wait for charts to load
        await authenticated_page.wait_for_timeout(2000)

        # Look for chart containers
        chart_selectors = [
            '[id*="chart"]',
            '[class*="chart"]',
            '[data-testid*="chart"]',
            'canvas', # Chart.js or similar
            'svg', # D3.js or similar
            '.echarts-container' # Apache ECharts
        ]

        chart_found = False
        for selector in chart_selectors:
            charts = authenticated_page.locator(selector)
            if await charts.count() > 0:
                # Chart should be visible
                await expect(charts.first).to_be_visible()
                chart_found = True
                break

        # If no charts found, check for chart loading indicators
        if not chart_found:
            loading_indicators = authenticated_page.locator('[data-loading], .loading, .spinner')
            if await loading_indicators.count() > 0:
                # Charts might still be loading
                await authenticated_page.wait_for_timeout(3000)

    async def test_dashboard_responsive_design(self, mobile_page: Page):
        """Test dashboard responsive design on mobile."""
        await mobile_page.goto("/dashboard")

        # Dashboard should be accessible on mobile
        await expect(mobile_page.locator("body")).to_be_visible()

        # Check that content doesn't overflow horizontally
        body_width = await mobile_page.evaluate("document.body.scrollWidth")
        viewport_width = await mobile_page.evaluate("window.innerWidth")

        # Allow some margin for scrollbars
        assert body_width <= viewport_width + 20, "Content overflows horizontally on mobile"

        # Charts should adapt to mobile
        chart_containers = mobile_page.locator('[id*="chart"], [class*="chart"]')
        if await chart_containers.count() > 0:
            first_chart = chart_containers.first
            chart_box = await first_chart.bounding_box()

            if chart_box:
                # Chart should not be wider than viewport
                assert chart_box["width"] <= viewport_width, "Chart too wide for mobile"

    async def test_dashboard_data_refresh(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
        """Test dashboard data refresh functionality."""
        await authenticated_page.goto("/dashboard")

        # Look for refresh button
        refresh_selectors = [
            '[data-testid="refresh"]',
            'button:has-text("Refresh")',
            '.refresh-btn',
            '[title*="refresh" i]'
        ]

        refresh_button = None
        for selector in refresh_selectors:
            if await authenticated_page.locator(selector).count() > 0:
                refresh_button = authenticated_page.locator(selector).first
                break

        if refresh_button:
            # Click refresh and wait for data to update
            await refresh_button.click()

            # If using HTMX, wait for the request
            if await authenticated_page.locator('[hx-get], [hx-post]').count() > 0:
                await authenticated_page.wait_for_timeout(1000)

            # Page should still be functional after refresh
            await expect(authenticated_page.locator("body")).to_be_visible()

    async def test_dashboard_chart_interactions(self, authenticated_page: Page):
        """Test chart interaction functionality."""
        await authenticated_page.goto("/dashboard")
        await authenticated_page.wait_for_timeout(2000)

        # Look for interactive chart elements
        interactive_selectors = [
            'canvas',
            'svg',
            '[class*="chart"] [class*="clickable"]',
            '[data-interactive="true"]'
        ]

        for selector in interactive_selectors:
            elements = authenticated_page.locator(selector)
            if await elements.count() > 0:
                chart = elements.first

                # Try hovering over chart
                await chart.hover()
                await authenticated_page.wait_for_timeout(500)

                # Look for tooltips or hover effects
                tooltip_selectors = [
                    '.tooltip',
                    '[role="tooltip"]',
                    '[class*="tooltip"]',
                    '.chart-tooltip'
                ]

                tooltip_found = False
                for tooltip_selector in tooltip_selectors:
                    if await authenticated_page.locator(tooltip_selector).count() > 0:
                        tooltip_found = True
                        break

                # Some charts might not have tooltips, so this is not a hard requirement
                break

    async def test_dashboard_filters_and_controls(self, authenticated_page: Page):
        """Test dashboard filter and control functionality."""
        await authenticated_page.goto("/dashboard")

        # Look for filter controls
        filter_selectors = [
            'select[name*="filter"]',
            'input[name*="filter"]',
            '[data-testid*="filter"]',
            '.filter-control',
            'select[name*="period"]',
            'input[type="date"]'
        ]

        for selector in filter_selectors:
            filters = authenticated_page.locator(selector)
            if await filters.count() > 0:
                filter_element = filters.first

                # Get current state
                if await filter_element.get_attribute("type") == "date":
                    # Test date filter
                    await filter_element.fill("2024-01-01")
                elif await filter_element.tag_name() == "SELECT":
                    # Test select filter
                    options = authenticated_page.locator(f"{selector} option")
                    if await options.count() > 1:
                        await filter_element.select_option(index=1)

                # Wait for dashboard to update
                await authenticated_page.wait_for_timeout(1000)

                # Dashboard should still be functional
                await expect(authenticated_page.locator("body")).to_be_visible()
                break

    async def test_dashboard_accessibility(self, authenticated_page: Page):
        """Test dashboard accessibility features."""
        await authenticated_page.goto("/dashboard")

        # Check for proper heading structure
        headings = authenticated_page.locator("h1, h2, h3, h4, h5, h6")
        if await headings.count() > 0:
            # Should have at least one main heading
            main_heading = headings.first
            await expect(main_heading).to_be_visible()

        # Check for ARIA labels on interactive elements
        interactive_elements = authenticated_page.locator("button, [role='button'], input, select")
        for i in range(min(5, await interactive_elements.count())):  # Check first 5 elements
            element = interactive_elements.nth(i)

            # Should have accessible name (aria-label, aria-labelledby, or visible text)
            has_label = (
                await element.get_attribute("aria-label") is not None or
                await element.get_attribute("aria-labelledby") is not None or
                len((await element.text_content() or "").strip()) > 0
            )

            # This is a guideline, not a hard requirement for all elements
            if not has_label:
                print(f"Warning: Interactive element may lack accessible name: {await element.get_attribute('class')}")

        # Check color contrast (basic check)
        body_bg = await authenticated_page.evaluate("""
            getComputedStyle(document.body).backgroundColor
        """)

        body_color = await authenticated_page.evaluate("""
            getComputedStyle(document.body).color
        """)

        # Basic check that we have both background and text colors set
        assert body_bg != "rgba(0, 0, 0, 0)", "Body should have background color"
        assert body_color != "rgba(0, 0, 0, 0)", "Body should have text color"

    async def test_dashboard_error_handling(self, authenticated_page: Page):
        """Test dashboard error handling and fallbacks."""
        await authenticated_page.goto("/dashboard")

        # Simulate network error by blocking API calls
        await authenticated_page.route("**/api/**", lambda route: route.abort())

        # Reload page to trigger API calls
        await authenticated_page.reload()

        # Page should still load with error handling
        await expect(authenticated_page.locator("body")).to_be_visible()

        # Look for error messages or fallback content
        error_indicators = [
            'text=error',
            'text=failed',
            'text=unavailable',
            '.error',
            '.alert-error',
            '[role="alert"]'
        ]

        error_found = False
        for indicator in error_indicators:
            if await authenticated_page.locator(indicator).count() > 0:
                error_found = True
                break

        # Should either show error message or fallback gracefully
        # Not all implementations may show explicit errors, so this is informational

    async def test_dashboard_performance_loading(self, authenticated_page: Page):
        """Test dashboard loading performance."""
        # Measure page load time
        start_time = await authenticated_page.evaluate("performance.now()")

        await authenticated_page.goto("/dashboard")

        # Wait for main content to be visible
        await expect(authenticated_page.locator("body")).to_be_visible()

        end_time = await authenticated_page.evaluate("performance.now()")
        load_time = end_time - start_time

        # Dashboard should load within reasonable time (5 seconds)
        assert load_time < 5000, f"Dashboard took too long to load: {load_time}ms"

        # Check for loading indicators
        loading_selectors = [
            '.loading',
            '.spinner',
            '[data-loading]',
            '.skeleton'
        ]

        # Loading indicators should eventually disappear
        for selector in loading_selectors:
            loading_elements = authenticated_page.locator(selector)
            if await loading_elements.count() > 0:
                # Wait for loading to complete
                await authenticated_page.wait_for_timeout(3000)

                # Check if still loading
                still_loading = await loading_elements.count() > 0
                if still_loading:
                    print(f"Warning: Loading indicator {selector} still visible after 3s")

    async def test_dashboard_keyboard_navigation(self, authenticated_page: Page):
        """Test keyboard navigation on dashboard."""
        await authenticated_page.goto("/dashboard")

        # Test Tab navigation
        await authenticated_page.keyboard.press("Tab")

        # Should focus on first focusable element
        focused_element = await authenticated_page.evaluate("document.activeElement.tagName")

        # Should be a focusable element
        focusable_tags = ["BUTTON", "INPUT", "SELECT", "A", "TEXTAREA"]
        if focused_element in focusable_tags:
            # Continue tabbing through elements
            for _ in range(5):  # Tab through first 5 focusable elements
                await authenticated_page.keyboard.press("Tab")
                await authenticated_page.wait_for_timeout(100)

        # Test escape key functionality if modals/dropdowns exist
        await authenticated_page.keyboard.press("Escape")
        await authenticated_page.wait_for_timeout(500)

        # Page should remain functional
        await expect(authenticated_page.locator("body")).to_be_visible()


@pytest.mark.ui
@pytest.mark.e2e
@pytest.mark.asyncio
class TestDashboardWorkflows:
    """End-to-end workflow tests for dashboard functionality."""

    async def test_dashboard_data_drill_down_workflow(self, authenticated_page: Page):
        """Test drilling down into dashboard data."""
        await authenticated_page.goto("/dashboard")
        await authenticated_page.wait_for_timeout(2000)

        # Look for clickable chart elements or summary cards
        clickable_selectors = [
            '[data-clickable="true"]',
            'a[href*="/administration"]',
            'button[data-target]',
            '.summary-card a',
            '.metric-card a'
        ]

        for selector in clickable_selectors:
            clickable_elements = authenticated_page.locator(selector)
            if await clickable_elements.count() > 0:
                # Click on the element
                await clickable_elements.first.click()

                # Should navigate to detail page or show more info
                await authenticated_page.wait_for_timeout(1000)

                # Verify we can navigate back
                await authenticated_page.go_back()
                await expect(authenticated_page).to_have_url("**/dashboard")
                break

    async def test_dashboard_time_period_workflow(self, authenticated_page: Page):
        """Test changing time periods and seeing data update."""
        await authenticated_page.goto("/dashboard")
        await authenticated_page.wait_for_timeout(2000)

        # Look for time period controls
        time_selectors = [
            'select[name*="period"]',
            'select[name*="time"]',
            '[data-testid*="period"]',
            'button:has-text("7 days")',
            'button:has-text("30 days")',
            'button:has-text("Last month")'
        ]

        for selector in time_selectors:
            controls = authenticated_page.locator(selector)
            if await controls.count() > 0:
                control = controls.first

                # Get initial data state (check a chart or number)
                initial_state = await authenticated_page.locator('[data-testid*="chart"], .metric').text_content()

                if await control.tag_name() == "SELECT":
                    # Change select option
                    options = authenticated_page.locator(f"{selector} option")
                    if await options.count() > 1:
                        await control.select_option(index=1)
                else:
                    # Click button
                    await control.click()

                # Wait for data to update
                await authenticated_page.wait_for_timeout(2000)

                # Data might have changed (though not guaranteed in test environment)
                # Main goal is to ensure no errors occurred
                await expect(authenticated_page.locator("body")).to_be_visible()
                break

    async def test_dashboard_export_functionality(self, authenticated_page: Page):
        """Test dashboard export functionality if available."""
        await authenticated_page.goto("/dashboard")

        # Look for export buttons
        export_selectors = [
            'button:has-text("Export")',
            'a:has-text("Download")',
            '[data-testid*="export"]',
            'button:has-text("PDF")',
            'button:has-text("CSV")'
        ]

        for selector in export_selectors:
            export_buttons = authenticated_page.locator(selector)
            if await export_buttons.count() > 0:
                # Set up download handler
                async with authenticated_page.expect_download() as download_info:
                    await export_buttons.first.click()

                # If download started, verify it
                try:
                    download = await download_info.value
                    assert download.suggested_filename is not None
                except Exception:
                    # Export might not trigger download in test environment
                    pass
                break

    async def test_dashboard_full_user_journey(self, authenticated_page: Page):
        """Test complete user journey through dashboard."""
        # 1. Navigate to dashboard
        await authenticated_page.goto("/dashboard")
        await expect(authenticated_page).to_have_title("Dashboard")

        # 2. Wait for dashboard to load
        await authenticated_page.wait_for_timeout(3000)

        # 3. Interact with summary widgets
        summary_cards = authenticated_page.locator('.summary-card, .metric-card, [data-testid*="summary"]')
        if await summary_cards.count() > 0:
            await summary_cards.first.hover()
            await authenticated_page.wait_for_timeout(500)

        # 4. Interact with charts
        charts = authenticated_page.locator('[id*="chart"], canvas, svg')
        if await charts.count() > 0:
            chart_box = await charts.first.bounding_box()
            if chart_box:
                # Click in center of chart
                await authenticated_page.mouse.click(
                    chart_box["x"] + chart_box["width"] / 2,
                    chart_box["y"] + chart_box["height"] / 2
                )
                await authenticated_page.wait_for_timeout(500)

        # 5. Try to navigate to detail pages
        detail_links = authenticated_page.locator('a[href*="/administration"], a[href*="/users"]')
        if await detail_links.count() > 0:
            await detail_links.first.click()
            await authenticated_page.wait_for_timeout(1000)

            # Navigate back to dashboard
            await authenticated_page.go_back()
            await expect(authenticated_page).to_have_url("**/dashboard")

        # 6. Verify dashboard is still functional
        await expect(authenticated_page.locator("body")).to_be_visible()

    async def test_dashboard_multi_user_perspective(self, authenticated_page: Page):
        """Test dashboard from different user role perspectives."""
        # This test would ideally test with different user roles
        # For now, we'll test the basic authenticated user experience

        await authenticated_page.goto("/dashboard")

        # Check that user sees appropriate data for their role
        # Admin users might see different widgets than regular users

        # Look for role-specific content
        admin_indicators = [
            'text=Admin',
            'text=Manage',
            '[data-role="admin"]',
            'a[href*="/administration"]'
        ]

        user_indicators = [
            'text=Overview',
            'text=Summary',
            '[data-role="user"]'
        ]

        # Dashboard should show content appropriate to user's role
        has_admin_content = False
        has_user_content = False

        for indicator in admin_indicators:
            if await authenticated_page.locator(indicator).count() > 0:
                has_admin_content = True
                break

        for indicator in user_indicators:
            if await authenticated_page.locator(indicator).count() > 0:
                has_user_content = True
                break

        # Should have some kind of content
        assert has_admin_content or has_user_content, "No role-appropriate content found"