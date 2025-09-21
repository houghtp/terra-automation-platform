"""
Playwright configuration for UI testing.

This configuration is optimized for testing the FastAPI template
with HTMX interactions and multiple browsers.
"""

from playwright.sync_api import Playwright
import os

# Test configuration
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_HEADLESS = os.getenv("TEST_HEADLESS", "true").lower() == "true"
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))  # 30 seconds

def pytest_configure(config):
    """Configure Playwright for pytest."""
    config.option.base_url = TEST_BASE_URL
    config.option.headed = not TEST_HEADLESS
    config.option.browser = ["chromium", "firefox", "webkit"]

def pytest_playwright_config():
    """Playwright configuration for the template."""
    return {
        "browser_name": "chromium",  # Default browser
        "headless": TEST_HEADLESS,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "timeout": TEST_TIMEOUT,
        "base_url": TEST_BASE_URL,
        "trace": "retain-on-failure",  # Keep traces on test failures
        "screenshot": "only-on-failure",  # Screenshots on failures
        "video": "retain-on-failure",  # Videos on failures
    }

# Browser contexts for different test scenarios
BROWSER_CONTEXTS = {
    "desktop": {
        "viewport": {"width": 1280, "height": 720},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    "tablet": {
        "viewport": {"width": 768, "height": 1024},
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
    },
    "mobile": {
        "viewport": {"width": 375, "height": 667},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
    }
}