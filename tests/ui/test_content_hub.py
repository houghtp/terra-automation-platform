"""Playwright smoke tests for the Community Content Hub."""

import pytest
from playwright.async_api import Page, expect


@pytest.mark.ui
@pytest.mark.skip(reason="UI tests require Playwright fixtures and authenticated session setup")
@pytest.mark.asyncio
class TestCommunityContentHub:
    async def test_content_dashboard_renders(self, authenticated_page: Page):
        """Ensure the Content Hub dashboard loads and lists starter cards."""
        await authenticated_page.goto("/features/community/content")
        await expect(authenticated_page.locator("text=Content & Learning Hub")).to_be_visible()
        await expect(authenticated_page.locator(".card-title", has_text="Articles Library")).to_be_visible()

    async def test_article_modal_flow(self, authenticated_page: Page):
        """Open the article modal and trigger markdown preview via HTMX."""
        await authenticated_page.goto("/features/community/content")
        await authenticated_page.click("text=New Article")
        await expect(authenticated_page.locator("#content-form-modal .modal-title")).to_contain_text("Create Article")
        await authenticated_page.fill("textarea[name='body_md']", "# Demo Article\nPreview test body")
        await authenticated_page.click("button:has-text('Preview Markdown')")
        await expect(authenticated_page.locator("#article-markdown-preview h1")).to_contain_text("Demo Article")

    async def test_content_tables_refresh(self, authenticated_page: Page):
        """Trigger HTMX refresh events for article/podcast/video/news tables."""
        await authenticated_page.goto("/features/community/content")
        await authenticated_page.dispatch_event("body", "refreshContentTables")
        await expect(authenticated_page.locator("#content-articles-wrapper")).to_be_visible()
