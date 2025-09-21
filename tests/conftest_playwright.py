"""
Playwright-specific fixtures and utilities for UI testing.

This file provides shared Playwright fixtures that can be used
across all slices for consistent UI testing.
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import AsyncGenerator
from playwright.sync_api import Playwright
import os

# Import our database fixtures
from tests.conftest import test_db_session, test_db_engine

# Test server configuration
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
TEST_HEADLESS = os.getenv("TEST_HEADLESS", "true").lower() == "true"


@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Create a browser instance for the test session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=TEST_HEADLESS,
            args=["--disable-web-security", "--disable-features=VizDisplayCompositor"]
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def browser_context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
        base_url=TEST_SERVER_URL
    )
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(browser_context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await browser_context.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="function")
async def authenticated_page(page: Page, test_db_session) -> AsyncGenerator[Page, None]:
    """Create an authenticated page session."""
    # For now, we'll implement a simple login flow
    # Template users can customize this for their authentication

    # Navigate to login page
    await page.goto("/auth/login")

    # Wait for login form and fill it
    await page.wait_for_selector("form")
    await page.fill('input[name="email"]', "admin@example.com")
    await page.fill('input[name="password"]', "admin123")
    await page.click('button[type="submit"]')

    # Wait for successful login (redirect to dashboard)
    await page.wait_for_url("**/dashboard")

    yield page


# HTMX-specific utilities
class HTMXTestHelper:
    """Helper class for testing HTMX interactions."""

    def __init__(self, page: Page):
        self.page = page

    async def wait_for_htmx_request(self, url_pattern: str, timeout: int = 5000):
        """Wait for an HTMX request to complete."""
        async with self.page.expect_response(url_pattern, timeout=timeout) as response_info:
            pass
        return await response_info.value

    async def click_and_wait_htmx(self, selector: str, url_pattern: str = "*"):
        """Click an element and wait for HTMX to complete."""
        async with self.page.expect_response(url_pattern) as response_info:
            await self.page.click(selector)
        return await response_info.value

    async def fill_and_trigger_validation(self, selector: str, value: str, validation_pattern: str = "**/validate/**"):
        """Fill a field and wait for HTMX validation."""
        await self.page.fill(selector, value)
        # Trigger blur to start validation
        await self.page.press(selector, "Tab")
        # Wait for validation response
        try:
            async with self.page.expect_response(validation_pattern, timeout=2000) as response_info:
                pass
            return await response_info.value
        except:
            # No validation triggered, which is also valid
            return None


@pytest.fixture(scope="function")
async def htmx_helper(page: Page) -> HTMXTestHelper:
    """Provide HTMX testing utilities."""
    return HTMXTestHelper(page)


@pytest.fixture(scope="function")
async def mobile_page(browser: Browser) -> AsyncGenerator[Page, None]:
    """Create a mobile viewport page for responsive testing."""
    context = await browser.new_context(
        viewport={"width": 375, "height": 667},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15"
    )
    page = await context.new_page()
    yield page
    await context.close()


@pytest.fixture(scope="function")
async def tablet_page(browser: Browser) -> AsyncGenerator[Page, None]:
    """Create a tablet viewport page for responsive testing."""
    context = await browser.new_context(
        viewport={"width": 768, "height": 1024},
        user_agent="Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15"
    )
    page = await context.new_page()
    yield page
    await context.close()